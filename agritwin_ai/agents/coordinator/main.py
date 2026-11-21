from agritwin_ai.agents.coordinator.agent import run_agent


def main():
    print("=" * 50)
    print("AgriTwin Coordinator")
    print("Type 'exit' to quit.")
    print("=" * 50)

    while True:
        question = input("\nYou: ")

        if question.lower() == "exit":
            break

        answer = run_agent(question)

        print("\nCoordinator:\n")
        try:
            print(answer)
        except UnicodeEncodeError:
            print(answer.encode('cp1252', errors='replace').decode('cp1252'))


if __name__ == "__main__":
    main()