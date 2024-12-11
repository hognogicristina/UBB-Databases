from algorithms.apriori import apriori
from algorithms.fpgrowth import fpgrowth
from algorithms.association_rules import association_rules
from .display_rules import display_rules
import time


def run_algorithm_until_success(basket, min_support_start, min_support_min, conf_threshold_start, conf_threshold_min):
    min_support = min_support_start
    min_tries = 1

    while min_support >= min_support_min or min_tries >= 1:
        conf_threshold = conf_threshold_start
        while conf_threshold >= conf_threshold_min or min_tries >= 1:
            print(f"\nRunning Algorithms with min_support={min_support:.2f} and confidence={conf_threshold:.2f}")
            start_time = time.time()

            try:
                frequent_items = apriori(basket, min_support=min_support, use_colnames=True)
                num_itemsets = len(frequent_items)

                if frequent_items.empty:
                    print("No frequent itemsets found.")
                else:
                    rules = association_rules(frequent_items, metric="confidence", min_threshold=conf_threshold,
                                              num_itemsets=num_itemsets)
                    execution_time = time.time() - start_time

                    if not rules.empty:
                        rules_sorted = rules.sort_values(by=['confidence', 'lift'], ascending=[False, False])
                        display_rules(rules_sorted, "Apriori", execution_time)
                        return True, min_support, conf_threshold

            except Exception as e:
                print(f"Error running Algorithms: {e}")

            conf_threshold -= 0.1
            min_tries -= 1

        min_support -= 0.03

    print("No matches found after trying all support and confidence values.")
    return False, None, None


def run_fpgrowth(basket, min_support, conf_threshold):
    print(f"\nRunning FP-Growth with min_support={min_support:.2f} and confidence={conf_threshold:.2f}")
    start_time = time.time()

    try:
        frequent_items = fpgrowth(basket, min_support=min_support, use_colnames=True)
        num_itemsets = len(frequent_items)

        if frequent_items.empty:
            print("No frequent itemsets found for FP-Growth.")
        else:
            rules = association_rules(frequent_items, metric="confidence", min_threshold=conf_threshold,
                                      num_itemsets=num_itemsets)
            execution_time = time.time() - start_time

            if not rules.empty:
                rules_sorted = rules.sort_values(by=['confidence', 'lift'], ascending=[False, False])
                display_rules(rules_sorted, "FP-Growth", execution_time)
            else:
                print("No rules found at this confidence level for FP-Growth.")
    except Exception as e:
        print(f"Error running FP-Growth: {e}")
