RESPONSE_RULES = """
OUTPUT FORMAT

Always reply with valid JSON.

Tool Call

{
    "action":"tool_name",
    "arguments":{}
}

OR

{
    "final_answer":"..."
}
"""