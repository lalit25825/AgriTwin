"""Tool call validation."""

from typing import Any


def validate_tool(
    action: str,
    arguments: dict[str, Any],
    tools: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, str] | None]:
    """Validate tool name, required keys, and argument types."""

    if action not in tools:
        return False, {
            "error": f"Unknown tool '{action}'."
        }

    if not isinstance(arguments, dict):
        return False, {
            "error": "Tool arguments must be a JSON object."
        }

    schema = tools[action]

    argument_types = schema["arguments"]

    required_arguments = schema.get(
        "required",
        set(argument_types.keys()),
    )

    # ---------------------------------------------------------
    # REQUIRED ARGUMENTS
    # ---------------------------------------------------------

    missing = [
        name
        for name in required_arguments
        if name not in arguments
    ]

    if missing:
        return False, {
            "error": (
                f"Missing arguments: "
                f"{', '.join(missing)}"
            )
        }

    # ---------------------------------------------------------
    # UNEXPECTED ARGUMENTS
    # ---------------------------------------------------------

    unexpected = (
        set(arguments)
        - set(argument_types)
    )

    if unexpected:
        return False, {
            "error": (
                "Unexpected arguments: "
                f"{', '.join(sorted(unexpected))}"
            )
        }

    # ---------------------------------------------------------
    # ARGUMENT TYPES
    # ---------------------------------------------------------

    invalid = []

    for name, expected_type in argument_types.items():

        # Optional argument not supplied.
        if name not in arguments:
            continue

        value = arguments[name]

        # Optional argument explicitly supplied as None.
        if (
            name not in required_arguments
            and value is None
        ):
            continue

        if not isinstance(
            value,
            expected_type,
        ):
            invalid.append(name)

    if invalid:
        return False, {
            "error": (
                "Invalid argument types: "
                f"{', '.join(invalid)}"
            )
        }

    return True, None