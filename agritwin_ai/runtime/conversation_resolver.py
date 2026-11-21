"""Resolve follow-up messages into complete, context-aware requests."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


class ConversationResolver:
    """Reconstruct requests using recent dialogue and working memory."""

    DIRECT_MESSAGES = frozenset({
        "hi", "hii", "hello", "hey", "heya",
        "good morning", "good afternoon", "good evening",
        "thanks", "thank you", "thx", "bye", "goodbye",
        "see you", "ok", "okay", "k", "got it", "cool",
        "nice", "awesome", "help", "what can you do",
    })

    TASK_KEYWORDS = (
        "route", "map", "directions", "transport", "logistics", "truck", "vehicle",
        "shipment", "deliver", "delivery", "send", "carry",
        "freight", "travel time", "distance", "transport cost",
        "harvest", "weather", "rain", "climate", "irrigat",
        "market price", "price", "sell", "crop", "fertilizer",
        "disease", "water", "farm",
    )

    CLARIFICATION_PHRASES = (
        "i need the following information",
        "i need the following details",
        "which city", "which location", "which mandi", "which market", "what city",
        "what location", "what market", "what mandi", "specify market", "specify the market", "what are you transporting",
        "how many tons", "how much", "please provide",
        "could you provide", "what is the quantity",
        "what quantity", "which crop",
    )

    FOLLOW_UP_STARTERS = (
        "what about", "how about", "what if", "instead",
        "actually", "change", "make it", "use ", "which one",
        "why", "how much", "and ", "also ",
    )

    CROP_PLURALS = {
        "onion": "onions",
        "potato": "potatoes",
        "tomato": "tomatoes",
        "wheat": "wheat",
        "rice": "rice",
        "cotton": "cotton",
        "maize": "maize",
        "corn": "corn",
        "sugarcane": "sugarcane",
        "soybean": "soybeans",
        "chilli": "chillies",
        "chili": "chilis",
    }

    def resolve(
        self,
        conversation_history: Sequence[Mapping[str, str]],
        working_memory: Mapping[str, Any],
        latest_user_message: str,
    ) -> str:
        """Return a concrete request, preserving context where appropriate."""

        latest = latest_user_message.strip()
        if not latest:
            return latest

        if self._clean(latest) in self.DIRECT_MESSAGES:
            return latest

        latest_assistant = self._last_message(
            conversation_history, "assistant"
        )
        previous_request = self._find_previous_task(conversation_history)

        # An explicit request for today's/current price supersedes a pending
        # forecast horizon. Do not carry an earlier future date into the new
        # request just because the user is correcting the same market task.
        if previous_request and self._is_current_price_override(latest):
            commodity = (
                self._memory_value(working_memory, "crop")
                or self._memory_value(working_memory, "commodity")
            )
            market = (
                self._memory_value(working_memory, "market")
                or self._memory_value(working_memory, "city")
            )
            if isinstance(commodity, str) and commodity.strip() and isinstance(market, str) and market.strip():
                return (
                    f"Get the current observed market price only for {commodity} "
                    f"at {market}. This request supersedes earlier future forecast "
                    "dates and horizons. Do not forecast or calculate profit, "
                    "storage, transport, or sell/hold decisions."
                )

        # Prefer concrete resolution for common slot questions instead of
        # sending a generic meta-instruction to the understanding model.
        if previous_request and self._assistant_requested_details(latest_assistant):
            # A new request in a different domain is not an answer to the
            # previous clarification. This prevents a market-price question
            # from contaminating a later harvest or logistics request.
            if not self._is_new_task_domain(previous_request, latest):
                resolved = self._resolve_clarification_answer(
                    previous_request, latest, latest_assistant
                )
                if resolved:
                    return resolved
                if self._looks_like_slot_answer(latest) or self._shares_task_domain(previous_request, latest):
                    return self._combine(
                        previous_request,
                        latest,
                        "The user is answering the pending clarification.",
                    )

        # Reuse known city/crop for a new complete request. This makes the
        # request explicit for understanding, not just for downstream tools.
        enriched = self._enrich_from_memory(latest, working_memory)
        if enriched != latest:
            return enriched

        looks_like_follow_up = self._looks_like_follow_up(
            latest, latest_assistant
        )

        if previous_request and looks_like_follow_up:
            return self._combine(
                previous_request,
                latest,
                "Continue or update the previous task.",
            )

        if previous_request and self._looks_like_slot_answer(latest):
            return self._combine(
                previous_request,
                latest,
                "The user supplied additional task details.",
            )

        return latest

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    @staticmethod
    def _memory_value(memory: Mapping[str, Any], key: str) -> Any:
        item = memory.get(key)
        if hasattr(item, "value"):
            return item.value
        if isinstance(item, Mapping):
            return item.get("value", item)
        return item

    @staticmethod
    def _last_message(
        history: Sequence[Mapping[str, str]], role: str
    ) -> str:
        for message in reversed(history):
            if message.get("role") == role:
                return message.get("content", "").strip()
        return ""

    def _find_previous_task(
        self, history: Sequence[Mapping[str, str]]
    ) -> str | None:
        for message in reversed(history):
            if message.get("role") != "user":
                continue
            content = message.get("content", "").strip()
            if not content or self._looks_like_slot_answer(content):
                continue
            if self._contains_task_keyword(content):
                return content
            if len(content.split()) >= 5:
                return content
        return None

    def _assistant_requested_details(self, text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in self.CLARIFICATION_PHRASES)

    def _resolve_clarification_answer(
        self,
        previous_request: str,
        answer: str,
        assistant_message: str,
    ) -> str | None:
        task = previous_request.lower()
        asked = assistant_message.lower()

        if (
            any(word in asked for word in ("city", "location"))
            and any(word in task for word in ("rain", "weather", "forecast", "climate"))
        ):
            return self._add_city(previous_request, answer)

        if "crop" in asked and "harvest" in task:
            return self._add_crop(previous_request, answer)

        if (
            any(term in asked for term in ("market", "mandi"))
            and any(term in task for term in ("market", "mandi", "price", "onion", "tomato", "potato"))
        ):
            return self._combine(
                previous_request,
                answer,
                "The user is supplying the requested mandi/market for the same price task.",
            )

        return None

    def _contains_crop(self, text: str, crop: str) -> bool:
        lowered = text.lower()
        name = crop.lower().strip()
        plural = self.CROP_PLURALS.get(name)
        return bool(
            re.search(rf"\b{re.escape(name)}\b", lowered)
            or (plural and re.search(rf"\b{re.escape(plural)}\b", lowered))
        )

    def _enrich_from_memory(
        self, request: str, working_memory: Mapping[str, Any]
    ) -> str:
        lowered = request.lower()
        enriched = request

        city = self._memory_value(working_memory, "city")
        if (
            isinstance(city, str)
            and city.strip()
            and any(word in lowered for word in ("rain", "weather", "forecast", "climate"))
            and city.lower() not in lowered
            and not re.search(r"\b(?:in|at|near|around)\s+(?:the\s+)?(?:morning|afternoon|evening|future|winter|summer)\b", lowered)
        ):
            if not re.search(r"\b(?:in|at|near|around)\s+[A-Za-z][\w.-]*", enriched):
                enriched = self._add_city(enriched, city)

        crop = self._memory_value(working_memory, "crop")
        if not crop:
            crop = self._memory_value(working_memory, "commodity")
        if (
            isinstance(crop, str)
            and crop.strip()
            and "harvest" in lowered
            and not self._contains_crop(lowered, crop)
        ):
            enriched = self._add_crop(enriched, crop)

        # Follow-up market requests often omit the crop or mandi because
        # the user has already supplied them in the same browser session.
        market_query = any(
            term in lowered
            for term in ("price", "mandi", "market", "sell", "forecast")
        )
        if market_query:
            if not crop:
                crop = self._memory_value(working_memory, "commodity") or self._memory_value(working_memory, "crop")
            if isinstance(crop, str) and crop.strip() and not self._contains_crop(enriched, crop):
                enriched = f"{enriched.rstrip()} for {crop}"

            market = self._memory_value(working_memory, "market")
            if not market:
                market = city
            if isinstance(market, str) and market.strip() and market.lower() not in enriched.lower():
                if not re.search(r"\b(?:in|at|near)\s+[A-Za-z][\w.-]*", enriched):
                    enriched = f"{enriched.rstrip()} in {market}"

        return enriched

    @staticmethod
    def _is_current_price_override(text: str) -> bool:
        lowered = text.lower()
        return (
            bool(re.search(r"\bcurrent\b.{0,40}\b(price|rate)\b", lowered))
            or any(
                phrase in lowered
                for phrase in (
                    "today's price", "todays price", "price today",
                    "market rate now", "just the price", "only the price",
                    "don't calculate my profit", "dont calculate my profit",
                )
            )
        )

    @staticmethod
    def _task_domains(text: str) -> set[str]:
        lowered = text.lower()
        domains: set[str] = set()
        if any(word in lowered for word in ("harvest", "harvesting", "reap")):
            domains.add("harvest")
        if any(word in lowered for word in ("weather", "rain", "climate", "humidity", "temperature", "wind")):
            domains.add("climate")
        if any(word in lowered for word in ("market", "mandi", "price", "sell", "storage", "forecast")):
            domains.add("market")
        if any(word in lowered for word in ("route", "map", "direction", "transport", "truck", "vehicle", "shipment", "deliver", "delivery", "freight", "logistics")):
            domains.add("logistics")
        return domains

    def _shares_task_domain(self, first: str, second: str) -> bool:
        return bool(self._task_domains(first) & self._task_domains(second))

    def _is_new_task_domain(self, previous: str, latest: str) -> bool:
        previous_domains = self._task_domains(previous)
        latest_domains = self._task_domains(latest)
        return bool(previous_domains and latest_domains and not (previous_domains & latest_domains))

    def _add_city(self, request: str, city: str) -> str:
        if city.lower() in request.lower():
            return request
        text, punctuation = self._split_punctuation(request)
        if re.search(r"\b(?:in|at|near|around)\s+[A-Za-z][\w.-]*", text):
            return request
        return f"{text} in {city}{punctuation}"

    def _add_crop(self, request: str, crop: str) -> str:
        if crop.lower() in request.lower():
            return request
        crop_name = self.CROP_PLURALS.get(crop.lower(), crop)
        text, punctuation = self._split_punctuation(request)

        # Replace generic crop references first, then insert after "harvest".
        updated, count = re.subn(
            r"\b(?:my\s+)?(?:crop|crops|produce)\b",
            crop_name,
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        if count == 0:
            updated, count = re.subn(
                r"\bharvest\b",
                f"harvest {crop_name}",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        if count == 0:
            return request
        return f"{updated}{punctuation}"

    @staticmethod
    def _split_punctuation(text: str) -> tuple[str, str]:
        match = re.search(r"([?.!])$", text)
        if not match:
            return text.rstrip(), ""
        return text[:match.start()].rstrip(), match.group(1)

    def _looks_like_follow_up(
        self, latest: str, latest_assistant: str
    ) -> bool:
        lowered = latest.lower().strip()
        if any(phrase in lowered for phrase in (
            "show me the map", "open the map", "show me route",
            "show the route", "route on map", "open route",
            "show directions", "display the route",
        )):
            return True
        if any(lowered.startswith(prefix) for prefix in self.FOLLOW_UP_STARTERS):
            return True
        if len(lowered.split()) <= 4:
            return True
        if lowered.startswith(("and what", "then what", "for that")):
            return True
        return False

    def _looks_like_slot_answer(self, text: str) -> bool:
        lowered = text.lower().strip()
        words = lowered.split()
        if not words:
            return False

        if len(words) <= 4:
            if re.search(r"\b\d+(?:\.\d+)?\b", lowered):
                return True
            if any(crop in lowered for crop in self.CROP_PLURALS):
                return True
            if not any(keyword in lowered for keyword in self.TASK_KEYWORDS):
                return True
        return False

    def _contains_task_keyword(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.TASK_KEYWORDS)

    @staticmethod
    def _combine(
        previous_request: str, latest: str, context_note: str
    ) -> str:
        return (
            f"Previous task: {previous_request}\n"
            f"Latest user message: {latest}\n"
            f"Conversation context: {context_note}\n"
            "Interpret the latest user message in the context of the "
            "previous task. Preserve previous details unless the latest "
            "message explicitly changes them. Extract all relevant "
            "entities and identify any information still missing."
        )
