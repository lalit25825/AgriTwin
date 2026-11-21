def execute_tool(action, arguments, tools):

    if action not in tools:

        return {
            "error": f"Unknown tool '{action}'."
        }

    print(f"\nExecuting Tool : {action}")
    print("Arguments :", arguments)

    tool = tools[action]["function"]

    try:

        result = tool(**arguments)

        print("Result :", result)

        return result

    except Exception as e:

        print("Tool Failed :", str(e))

        return {
            "error": str(e)
        }
