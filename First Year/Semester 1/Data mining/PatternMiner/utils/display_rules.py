def display_rules(rules, algorithm, execution_time):
    print(f"\nTop Association Rules ({algorithm}) - Execution Time: {execution_time:.4f} seconds")
    print("-" * 80)
    if rules.empty:
        print(f"No rules found for {algorithm}.")
    else:
        for idx, row in rules.head(5).iterrows():
            antecedents = ", ".join(row['antecedents'])
            consequents = ", ".join(row['consequents'])
            print(
                f"{antecedents} => {consequents} | Support: {row['support']:.4f} | Confidence: {row['confidence']:.4f} | Lift: {row['lift']:.4f}")
