import sys
from agritwin_ai.agents.climate.agent import run_agent


def main():
    print("=" * 50)
    print("AgriTwin Climate Agent")
    print("Type 'exit' to quit.")
    print("=" * 50)

    if not sys.stdin.isatty():
        # Piped input mode: each line is a question
        for line in sys.stdin:
            line = line.strip()
            if line:
                if line.lower() == "exit":
                    break
                answer = run_agent(line)
                print("\nClimate Agent:\n")
                try:
                    print(answer)
                except UnicodeEncodeError:
                    print(answer.encode('cp1252', errors='replace').decode('cp1252'))
    else:
        # Interactive mode
        while True:
            question = input("\nYou: ")

            if question.lower() == "exit":
                break

            answer = run_agent(question)

            print("\nClimate Agent:\n")
            try:
                print(answer)
            except UnicodeEncodeError:
                print(answer.encode('cp1252', errors='replace').decode('cp1252'))


if __name__ == "__main__":
    main()