from .basket_preparer import prepare_basket
from .algorithm_runner import run_algorithm_until_success, run_fpgrowth


def analyze_full_database(data, default_support=0.5, default_confidence=1):
    print("\n" + "=" * 40)
    print(f"Processing Dataset...")
    print("=" * 40)

    basket = prepare_basket(data)
    if basket.empty:
        print(f"No transactions found in the dataset.")
        return

    values_found, best_min_support, best_conf_threshold = run_algorithm_until_success(
        basket, min_support_start=default_support, min_support_min=0.02, conf_threshold_start=default_confidence, conf_threshold_min=0.5
    )

    if values_found:
        run_fpgrowth(basket, best_min_support, best_conf_threshold)
    else:
        print("\nNo rules could be generated after all attempts.")


def analyze_data_with_options(data):
    default_support = 0.05
    default_confidence = 1

    while True:
        print("\nSelect Analysis Option:")
        print("0: Exit")
        print("1: Analyze Entire Dataset")
        print("2: Analyze Data for a Specific Country")
        print("3: Analyze Data for a Group of Countries")
        print("4: Manually enter Support and Confidence values")
        print("5: Reset Support and Confidence values to normal run")
        print("6: Go back to Data Loader")

        option = input("Enter your option: ").strip()
        unique_countries = data['Country'].unique()

        if option == '0':
            print("\nExiting...\n")
            exit()
        elif option == '1':
            analyze_full_database(data, 0.02, 0.5)

        elif option == '4':
            default_support = float(input("Set value for Support (between 0.01 and 0.1): "))
            default_confidence = float(input("Set value for Confidence (between 0.1 and 1): "))

        elif option == '5':
            default_support = 0.05
            default_confidence = 1
            print("The values are back to default mode")

        elif option == '2':
            print("\nAvailable Countries:")
            for idx, country in enumerate(unique_countries, start=1):
                print(f"{idx}: {country}")

            selected_index = input("\nEnter the number corresponding to the country: ").strip()
            try:
                selected_index = int(selected_index)
                if 0 < selected_index <= len(unique_countries):
                    selected_country = unique_countries[selected_index - 1]
                    country_data = data[data['Country'] == selected_country]

                    if country_data.empty:
                        print(f"No data found for country '{selected_country}'.")
                    else:
                        analyze_full_database(country_data, default_support, default_confidence)
                else:
                    print("\nInvalid number. Please select a valid country number.")
            except ValueError:
                print("\nInvalid input. Please enter a number.")

        elif option == '3':
            print("\nAvailable Countries:")
            for idx, country in enumerate(unique_countries, start=1):
                print(f"{idx}: {country}")

            selected_indices = input("\nEnter the numbers corresponding to the countries (comma-separated): ").strip()
            try:
                selected_indices = [int(i) for i in selected_indices.split(",")]
                selected_countries = [unique_countries[i - 1] for i in selected_indices if
                                      0 < i <= len(unique_countries)]
                group_data = data[data['Country'].isin(selected_countries)]

                if group_data.empty:
                    print(f"No data found for selected countries: {selected_countries}")
                else:
                    analyze_full_database(group_data, 0.02, 0.5)
            except ValueError:
                print("\nInvalid input. Please enter valid numbers.")

        elif option == '6':
            print("\nReturning to Data Loader Menu...")
            return

        else:
            print("\nInvalid option. Please enter 0, 1, 2, 3, 4, 5, or 6. Try again.")
