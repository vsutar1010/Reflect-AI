from analyzer import PersonalityAnalyzer
from chat import TwinChat


def banner():
    print("=" * 55)
    print("             ReflectAI Terminal")
    print("=" * 55)
    print()


def menu():
    print("1. Analyze Personality")
    print("2. Chat With AI Twin")
    print("3. Exit")
    print()


def main():

    while True:

        banner()
        menu()

        choice = input("Select Option : ").strip()

        if choice == "1":

            analyzer = PersonalityAnalyzer()
            analyzer.run()

        elif choice == "2":

            try:

                chat = TwinChat()
                chat.run()

            except FileNotFoundError as exc:

                print()
                print(str(exc))
                input("\nPress Enter to continue...")

        elif choice == "3":

            print("\nThank you for using ReflectAI.")
            break

        else:

            print("\nInvalid Choice.")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()