"""Deterministic decision coordination for agent workflows."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from agritwin_ai.runtime.decision_context import DecisionContextBuilder


class DecisionManager:
    """Run an injected deterministic evaluator when its workflow is ready."""

    def __init__(self, context_builder: Optional[DecisionContextBuilder] = None) -> None:
        self._context_builder = context_builder or DecisionContextBuilder()

    def run(
        self,
        workflow: Any,
        intent: str,
        evaluator: Any,
    ) -> Optional[dict[str, str]]:
        """Evaluate *workflow* and return immutable LLM decision context when ready.

        Tool failure payloads are never evaluated.  The intent selects the evaluator,
        preventing stale current-weather or forecast data from changing the outcome.
        """
        if workflow.state.decision is not None:
            return self._context_builder.build(workflow.state.decision)

        if not workflow.ready_for_evaluation():
            return None

        try:
            decision = evaluator.evaluate(workflow, intent)
        except Exception:
            # If the evaluator raises an exception (e.g., missing keys), treat as error.
            return None

        if self._is_error(decision):
            return None

        workflow.set_decision(decision)
        workflow.complete()
        return self._context_builder.build(decision)

    @staticmethod
    def _is_error(payload: Any) -> bool:
        return isinstance(payload, Mapping) and "error" in payload