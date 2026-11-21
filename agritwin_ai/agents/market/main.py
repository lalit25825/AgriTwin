import sys

from agritwin_ai.agents.market.agent import (
    run_agent,
)


def main():
    print("=" * 50)
    print("AgriTwin Market Agent")
    print("Type 'exit' to quit.")
    print("=" * 50)

    if not sys.stdin.isatty():

        for line in sys.stdin:

            line = line.strip()

            if not line:
                continue

            if line.lower() == "exit":
                break

            answer = run_agent(line)

            print("\nMarket Agent:\n")

            try:
                print(answer)
            except UnicodeEncodeError:
                print(
                    answer.encode(
                        "cp1252",
                        errors="replace",
                    ).decode("cp1252")
                )

    else:

        while True:

            question = input("\nYou: ")

            if question.lower() in {
                "exit",
                "quit",
            }:
                break

            answer = run_agent(question)

            print("\nMarket Agent:\n")

            try:
                print(answer)
            except UnicodeEncodeError:
                print(
                    answer.encode(
                        "cp1252",
                        errors="replace",
                    ).decode("cp1252")
                )


if __name__ == "__main__":
    main()