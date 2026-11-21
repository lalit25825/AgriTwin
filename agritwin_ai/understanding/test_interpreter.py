from agritwin_ai.understanding.interpreter import understand


TEST_CASES = [

    "Should I harvest onions tomorrow?",

    "Should I harvest my kanda day after tomorrow?",

    "Kanda tomorrow Nashik",

    "What crop should I grow this season?",

    "Will it rain tomorrow in Nashik?",

    "Market price of onions",

    "माझा कांदा काढू का?",

    "Should I irrigate wheat today?",

    "There are purple spots on my onion leaves.",

    "Hi"

]


def main():

    print("=" * 70)
    print("AgriTwin Understanding Layer Test")
    print("=" * 70)

    for question in TEST_CASES:

        print()

        print("-" * 70)

        print("USER:")
        print(question)

        print()

        result = understand(question)

        print()

        print("UNDERSTANDING RESULT")

        print("Intent:")
        print(result.intent)

        print()

        print("Entities:")
        print(result.entities)

        print()

        print("Missing:")
        print(result.missing)

        print()

        print("Updates:")
        print(result.updates)

        print()

        print("Confidence:")
        print(result.confidence)

        print("-" * 70)


if __name__ == "__main__":

    main()