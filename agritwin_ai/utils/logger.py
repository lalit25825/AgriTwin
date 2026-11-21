def log_step(step):

    print(f"\n{'='*40}")
    print(f"STEP {step}")
    print("="*40)


def log_tool(name, args):

    print(f"\nTool : {name}")
    print(f"Arguments : {args}")


def log_result(result):

    print(f"\nObservation : {result}")