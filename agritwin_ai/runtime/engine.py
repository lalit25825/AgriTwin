"""Generic execution engine used by AgriTwin agents."""

from __future__ import annotations

import json
import time
from typing import Any

from agritwin_ai.config.settings import MAX_RETRIES, MAX_STEPS
from agritwin_ai.memory.conversation_memory import ConversationMemory
from agritwin_ai.memory.manager import MemoryManager
from agritwin_ai.runtime.context_builder import ContextBuilder
from agritwin_ai.runtime.decision_manager import DecisionManager
from agritwin_ai.runtime.pipeline import ConversationPipeline
from agritwin_ai.runtime.planner import Planner, Plan
from agritwin_ai.runtime.reasoning_loop import ReasoningLoop
from agritwin_ai.runtime.response_handler import ResponseHandler
from agritwin_ai.runtime.response_generator import ResponseGenerator
from agritwin_ai.runtime.session_manager import SessionManager
from agritwin_ai.runtime.state import AgentState
from agritwin_ai.runtime.tool_executor import ToolExecutor


class AgentEngine:
    """
    Generic execution engine used by AgriTwin agents.

    Pipeline:

        user
          ↓
        understanding
          ↓
        readiness
          ↓
        reasoning
          ↓
        tools
          ↓
        decision
          ↓
        response
    """

    # These intents do not require tools or deterministic decisions.
    DIRECT_INTENTS = frozenset(
        {
            "greeting",
            "thanks",
            "farewell",
            "acknowledgement",
        }
    )

    def __init__(
        self,
        prompt: str,
        workflow_factory: Any,
        evaluator: Any,
        tools: dict[str, dict[str, Any]],
        decision_label: str,
    ) -> None:

        self.memory = ConversationMemory(prompt)

        self.memory_manager = MemoryManager()

        self.context_builder = ContextBuilder()

        self.pipeline = ConversationPipeline(
            self.memory,
            self.memory_manager,
            self.context_builder,
            tools,
        )

        self.tools = tools

        self.reasoning = ReasoningLoop(self.tools)

        self.tool_executor = ToolExecutor(tools)

        self.decision_manager = DecisionManager()

        self.response_handler = ResponseHandler()

        self.session = SessionManager(self.memory)

        self.state = AgentState()

        self.workflow_factory = workflow_factory

        self.workflow = workflow_factory()

        self.evaluator = evaluator

        self.decision_label = decision_label

        self.response_generator = ResponseGenerator()

        self.planner = Planner()

        self.prompt = prompt

        self.active_intent = None

    # =========================================================
    # MAIN ENTRY
    # =========================================================

    def run(self, user_message: str) -> Any:
        """
        Process one user request.
        """

        # Create a fresh workflow for the current request while
        # preserving conversation and working memory.
        self.workflow = self.workflow_factory()

        self._reset_state()

        # -----------------------------------------------------
        # UNDERSTANDING
        # -----------------------------------------------------

        understanding, messages = self.pipeline.prepare(user_message)

        # -----------------------------------------------------
        # MULTI-TURN REQUEST CONTINUATION
        # -----------------------------------------------------
        #
        # A follow-up message may contain only missing fields.
        #
        # Example:
        #
        #   User: give me best route from Nashik to Lasangaon
        #   Agent: I need commodity and quantity_tons
        #   User: onions 10 tons
        #
        # The second message may be classified as "unknown"
        # because it does not contain a complete standalone intent.
        # If an active incomplete request exists, continue it.
        #

        if (
            understanding.intent == "unknown"
            and self.active_intent is not None
            and understanding.updates
        ):
            understanding.intent = self.active_intent

        elif understanding.intent != "unknown":
            self.active_intent = understanding.intent


        # Load working memory into workflow for readiness checking.
        self.workflow.load_memory(
            self.memory_manager.get_working()
        )

        # =====================================================
        # DIRECT CONVERSATION FAST PATH
        # =====================================================
        #
        # Conversational intents do not require:
        # - tools
        # - specialist workflows
        # - DecisionManager
        # - ResponseGenerator
        #
        # This applies to ALL agents, not only Coordinator.
        #

        if understanding.intent in self.DIRECT_INTENTS:
            return self._handle_direct_intent(
                understanding.intent,
                user_message,
                messages,
            )

        # =====================================================
        # DETERMINISTIC PLANNING
        # =====================================================
        #
        # The Planner converts UnderstandingResult into
        # deterministic tool actions.
        #

        working_memory = self.memory_manager.get_working()

        plan = self.planner.plan(
            understanding,
            self.workflow,
            working_memory,
        )

        # If the planner created a deterministic plan,
        # execute it directly and skip the LLM reasoning loop.
        if plan.actions:
            return self._execute_plan_directly(
                plan,
                understanding,
                messages,
            )

        reflection = self.workflow.reflect(
            understanding.intent
        )

        if not reflection["ready"]:

            answer = (
                "I need the following information: "
                f"{', '.join(reflection['missing'])}"
            )

            self.memory.add_assistant(answer)

            return answer

        # -----------------------------------------------------
        # REASONING LOOP
        # -----------------------------------------------------

        decision_context = None

        while self.state.step <= MAX_STEPS:

            assistant_text, parsed = self.reasoning.think(
                messages
            )

            self.memory.add_assistant(
                assistant_text
            )

            # -------------------------------------------------
            # INVALID RESPONSE
            # -------------------------------------------------

            if parsed["type"] == "invalid":

                if not self._retry_invalid_response():

                    return {
                        "error":
                        "Maximum retry limit exceeded."
                    }

                messages = self._build_context(
                    decision_context
                )

                continue

            self.state.retry_count = 0

            # -------------------------------------------------
            # FINAL RESPONSE
            # -------------------------------------------------

            if parsed["type"] == "final":

                if (
                    self.workflow.requires_decision(
                        understanding.intent
                    )
                    and self.workflow.state.decision is None
                ):

                    self.memory.add_user(
                        "Use the required tools before "
                        "providing a final explanation."
                    )

                    messages = self._build_context(
                        decision_context
                    )

                    self.state.step += 1

                    continue

                # If the parsed response contains a data field
                # and no deterministic decision is required,
                # return it directly.
                if (
                    "data" in parsed
                    and not self.workflow.requires_decision(
                        understanding.intent
                    )
                ):

                    self.print_statistics()

                    return parsed["data"]

                self.print_statistics()

                observations = {
                    key: value
                    for key, value in vars(
                        self.workflow.state
                    ).items()
                    if value is not None
                    and key not in {
                        "decision",
                        "completed",
                    }
                }

                response = self.response_handler.final(
                    parsed,
                    decision=self.workflow.state.decision,
                    decision_label=self.decision_label,
                )

                self.print_statistics()

                return response

            # -------------------------------------------------
            # TOOL CALL
            # -------------------------------------------------

            action, arguments = (
                self.response_handler.tool(
                    parsed
                )
            )

            succeeded, tool_result = (
                self.tool_executor.execute(
                    action,
                    arguments,
                )
            )

            if succeeded:

                self.state.current_tool = action
                self.state.tool_calls += 1

                self.workflow.handle_tool_result(
                    action,
                    tool_result,
                )

            observation = {
                "success": succeeded,
                "tool": action,
                "arguments": arguments,
                "result": tool_result,
            }
            self.memory.add_tool(
                json.dumps(observation, default=str)
            )

            if succeeded:
                self.memory.add_user(
                    "Continue solving the user's request using this observation. "
                    "Use another tool if needed, or answer when sufficient."
                )
            else:
                self.memory.add_user(
                    f"The tool '{action}' failed. Inspect the error observation. "
                    "Do not claim it succeeded; try a different valid approach "
                    "if one exists, otherwise explain the limitation."
                )

            # Only run DecisionManager if workflow requires
            # a deterministic decision.
            if self.workflow.requires_decision(
                understanding.intent
            ):

                decision_context = (
                    self.decision_manager.run(
                        workflow=self.workflow,
                        intent=understanding.intent,
                        evaluator=self.evaluator,
                    )
                )

            else:
                decision_context = None

            messages = self._build_context(
                decision_context
            )

            self.state.step += 1

        self.print_statistics()

        return {
            "error":
            "Maximum reasoning steps reached."
        }

    # =========================================================
    # DIRECT INTENT
    # =========================================================

    def _handle_direct_intent(
        self,
        intent: str,
        user_message: str,
        messages: list[dict[str, str]],
    ) -> str:
        """Handle simple conversation without exposing specialist tools."""

        text = user_message.strip().lower()

        # A small fallback keeps greetings available even if the LLM
        # provider is unavailable. Normal responses come from the LLM.
        if intent == "greeting":
            if "morning" in text:
                fallback = (
                    "Good morning! I'm AgriTwin. "
                    "How can I help you with your farming needs?"
                )
            elif "evening" in text:
                fallback = (
                    "Good evening! I'm AgriTwin. "
                    "How can I help you with your farming needs?"
                )
            else:
                fallback = (
                    "Hello! I'm AgriTwin. "
                    "How can I help you with your farming needs?"
                )
        elif intent == "thanks":
            fallback = "You're welcome! I'm here to help."
        elif intent == "farewell":
            fallback = "Goodbye! AgriTwin is here whenever you need help."
        elif intent == "acknowledgement":
            fallback = "Got it."
        else:
            fallback = "I'm here to help with your agricultural questions."

        try:
            assistant_text, parsed = self.reasoning.think(
                messages,
                tools={},
            )
            if parsed.get("type") == "final":
                answer = str(parsed.get("data", "")).strip() or fallback
            else:
                answer = fallback
        except Exception as exc:
            print("Direct conversation response failed:", str(exc))
            answer = fallback

        self.memory.add_assistant(answer)
        self.state.step = 1
        self.print_statistics()
        return answer

    # =========================================================
    # STATE
    # =========================================================

    def _reset_state(self) -> None:

        self.state.step = 1
        self.state.tool_calls = 0
        self.state.current_tool = None
        self.state.retry_count = 0
        self.state.start_time = time.time()

    # =========================================================
    # RETRY
    # =========================================================

    def _retry_invalid_response(self) -> bool:

        self.state.retry_count += 1

        if self.state.retry_count > MAX_RETRIES:

            return False

        self.memory.add_user(
            "Your previous response was invalid JSON. "
            "Respond again using valid JSON only."
        )

        return True

    # =========================================================
    # CONTEXT
    # =========================================================

    def _build_context(
        self,
        decision_context: dict[str, str] | None,
    ) -> list[dict[str, str]]:

        return self.context_builder.build(
            conversation=self.memory.get_messages(),
            working_memory=(
                self.memory_manager.get_working()
            ),
            semantic_memory=(
                self.memory_manager.semantic.get_all()
            ),
            episodic_memory=(
                self.memory_manager.episodic.get_all()
            ),
            decision=decision_context,
        )

    # =========================================================
    # DETERMINISTIC EXECUTION
    # =========================================================

    def _execute_plan_directly(
        self,
        plan: Plan,
        understanding: Any,
        messages: list[dict[str, str]],
    ) -> Any:
        """Execute deterministic actions, then reason over their observations."""

        completed_calls: set[tuple[str, str]] = set()

        for tool_action in plan.actions:
            call_key = (
                tool_action.name,
                json.dumps(
                    tool_action.arguments,
                    sort_keys=True,
                    default=str,
                ),
            )
            # Record attempts, including failures, so the reasoning loop
            # cannot retry the exact same failing call indefinitely.
            completed_calls.add(call_key)

            succeeded, tool_result = self.tool_executor.execute(
                tool_action.name,
                tool_action.arguments,
            )

            observation = {
                "success": succeeded,
                "tool": tool_action.name,
                "arguments": tool_action.arguments,
                "result": tool_result,
            }

            if succeeded:
                self.state.current_tool = tool_action.name
                self.state.tool_calls += 1
                self.workflow.handle_tool_result(
                    tool_action.name,
                    tool_result,
                )

            self.memory.add_tool(
                json.dumps(observation, default=str)
            )

            if succeeded:
                self.memory.add_user(
                    "Interpret the latest tool observation in the context "
                    "of the original request. Use another tool if needed."
                )
            else:
                # Stop executing later planned actions because they may
                # depend on the failed action. Let the reasoning loop recover.
                self.memory.add_user(
                    f"The planned tool '{tool_action.name}' failed. "
                    "Use the error observation to decide whether a different "
                    "valid tool call can recover. Do not claim success."
                )
                break

        decision_context = None
        if self.workflow.requires_decision(understanding.intent):
            decision_context = self.decision_manager.run(
                workflow=self.workflow,
                intent=understanding.intent,
                evaluator=self.evaluator,
            )

        return self._reason_after_plan(
            understanding=understanding,
            decision_context=decision_context,
            completed_tools=completed_calls,
        )

    def _reason_after_plan(
        self,
        understanding: Any,
        decision_context: dict[str, Any] | None,
        completed_tools: set[tuple[str, str]],
    ) -> str:
        """Reason over tool results and safely execute additional tool calls."""

        executed_calls = set(completed_tools)

        instruction = f"""
    You are the {self.decision_label} agent in AgriTwin.

    The user's request has already been understood and the initial
    deterministic plan has been executed.

    Use the conversation, working memory, tool observations, and
    deterministic decision provided in the context.

    Rules:
    1. Explain actual tool results naturally.
    2. Never invent data or claim a failed tool succeeded.
    3. Distinguish live data from estimates.
    4. Ask a concise question if essential information is missing.
    5. Call another tool when necessary and when its arguments are available.
    6. You may call the same tool with different arguments.
    7. Never repeat a tool call with the same name and arguments.
    8. Never override a deterministic Python decision.
    9. Otherwise, provide the final answer in natural language.
    10. Never expose internal reasoning or implementation details.

    Preserve the agent's existing system prompt and domain rules.
    """

        def build_reasoning_messages() -> list[dict[str, str]]:
            current_messages = self._build_context(decision_context)
            current_messages.insert(
                1,
                {
                    "role": "system",
                    "content": instruction,
                },
            )
            return current_messages

        messages = build_reasoning_messages()

        while self.state.step <= MAX_STEPS:
            try:
                assistant_text, parsed = self.reasoning.think(
                    messages,
                    tools=self.tools,
                )
            except Exception as exc:
                print("Post-tool reasoning failed:", str(exc))
                break

            if parsed["type"] == "invalid":
                if assistant_text:
                    self.memory.add_assistant(assistant_text)

                self.memory.add_user(
                    "Provide a concise natural-language answer using "
                    "the available observations. Do not invent data."
                )
                self.state.step += 1
                messages = build_reasoning_messages()
                continue

            self.state.retry_count = 0
            self.memory.add_assistant(assistant_text)

            # -------------------------------------------------
            # FINAL ANSWER
            # -------------------------------------------------

            if parsed["type"] == "final":
                answer = str(parsed["data"]).strip()

                if self.workflow.requires_decision(
                    understanding.intent
                ):
                    if self.workflow.state.decision is None:
                        self.memory.add_user(
                            "A deterministic decision is required. "
                            "Use the available tools to obtain the "
                            "required evidence before answering."
                        )
                        self.state.step += 1
                        messages = build_reasoning_messages()
                        continue

                    observations = {
                        key: value
                        for key, value in vars(
                            self.workflow.state
                        ).items()
                        if value is not None
                        and key not in {"decision", "completed"}
                    }

                    answer = self.response_handler.final(
                        {"data": answer},
                        decision=self.workflow.state.decision,
                        decision_label=self.decision_label,
                    )

                self.print_statistics()
                return answer

            # -------------------------------------------------
            # TOOL CALL
            # -------------------------------------------------

            if parsed["type"] != "tool":
                self.state.step += 1
                messages = build_reasoning_messages()
                continue

            action, arguments = self.response_handler.tool(parsed)

            call_key = (
                action,
                json.dumps(
                    arguments,
                    sort_keys=True,
                    default=str,
                ),
            )

            if call_key in executed_calls:
                self.memory.add_user(
                    f"The tool '{action}' with these exact arguments "
                    "has already been attempted. Use its existing "
                    "observation, or choose different arguments if "
                    "another call is genuinely necessary."
                )
                self.state.step += 1
                messages = build_reasoning_messages()
                continue

            # Track attempts, including failures, to prevent infinite
            # repetition of the same failing call.
            executed_calls.add(call_key)

            succeeded, tool_result = self.tool_executor.execute(
                action,
                arguments,
            )

            if succeeded:
                self.state.current_tool = action
                self.state.tool_calls += 1

                self.workflow.handle_tool_result(
                    action,
                    tool_result,
                )

                if self.workflow.requires_decision(
                    understanding.intent
                ):
                    decision_context = self.decision_manager.run(
                        workflow=self.workflow,
                        intent=understanding.intent,
                        evaluator=self.evaluator,
                    )

                # Preserve existing Coordinator delegation behavior.
                if (
                    self.decision_label == "Coordinator"
                    and action in {"run_climate", "run_harvest"}
                    and isinstance(tool_result, str)
                ):
                    self.memory.add_tool(
                        json.dumps(
                            {
                                "success": True,
                                "tool": action,
                                "result": tool_result,
                            },
                            default=str,
                        )
                    )
                    self.print_statistics()
                    return tool_result

            observation = {
                "success": succeeded,
                "tool": action,
                "arguments": arguments,
                "result": tool_result,
            }

            self.memory.add_tool(
                json.dumps(observation, default=str)
            )

            if succeeded:
                self.memory.add_user(
                    "Interpret the latest tool observation in the "
                    "context of the original request. If sufficient "
                    "information is available, answer naturally. "
                    "Otherwise, choose another available tool if needed."
                )
            else:
                self.memory.add_user(
                    "The latest tool call failed. Inspect its error "
                    "carefully. Do not claim it succeeded. If another "
                    "valid approach exists, try it; otherwise explain "
                    "the limitation clearly."
                )

            self.state.step += 1
            messages = build_reasoning_messages()

        # Preserve the existing deterministic fallback.
        observations = {
            key: value
            for key, value in vars(self.workflow.state).items()
            if value is not None
            and key not in {"decision", "completed"}
        }

        fallback = self.response_generator.generate(
            agent_name=self.decision_label,
            intent=understanding.intent,
            decision=self.workflow.state.decision,
            observations=observations,
        )

        self.print_statistics()
        return fallback


    # =========================================================
    # STATISTICS
    # =========================================================

    def print_statistics(self) -> None:
        """Print basic runtime statistics."""

        elapsed = (
            time.time()
            - self.state.start_time
        )

        print(
            f"Agent statistics: "
            f"steps={self.state.step}, "
            f"tools={self.state.tool_calls}, "
            f"elapsed={elapsed:.2f}s, "
            f"last_tool={self.state.current_tool}"
        )