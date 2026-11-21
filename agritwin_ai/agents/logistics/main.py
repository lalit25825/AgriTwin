import sys

from agritwin_ai.agents.logistics.agent import run_agent


def main():
    print("=" * 50)
    print("AgriTwin Logistics Agent")
    print("Type 'exit' to quit.")
    print("=" * 50)

    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                break
            answer = run_agent(line)
            print("\nLogistics Agent:\n")
            print(answer)
    else:
        while True:
            question = input("\nYou: ")
            if question.lower() in {"exit", "quit"}:
                break
            answer = run_agent(question)
            print("\nLogistics Agent:\n")
            print(answer)


if __name__ == "__main__":
    main()
