import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

# Load the data
data = pd.read_csv('./data/online_retail.csv')
data['Description'] = data['Description'].str.strip()
data.dropna(axis=0, subset=['InvoiceNo'], inplace=True)
data['InvoiceNo'] = data['InvoiceNo'].astype('str')
data = data[~data['InvoiceNo'].str.contains('C')]

# Function to prepare baskets for specific countries
def prepare_basket(country):
    basket = (data[data['Country'] == country]
              .groupby(['InvoiceNo', 'Description'])['Quantity']
              .sum().unstack().reset_index().fillna(0)
              .set_index('InvoiceNo'))
    basket = basket.apply(lambda x: x.map(hot_encode)).astype(bool)
    return basket

# Hot encoding function
def hot_encode(x):
    return 1 if x >= 1 else 0

# Prepare baskets for different countries
basket_France = prepare_basket("France")
basket_UK = prepare_basket("United Kingdom")
basket_Por = prepare_basket("Portugal")
basket_Sweden = prepare_basket("Sweden")

# Build the Apriori model
frq_items = apriori(basket_France, min_support=0.05, use_colnames=True)

# Ensure num_itemsets is calculated explicitly if required
num_itemsets = len(frq_items)

# Generate association rules
rules = association_rules(frq_items, metric="lift", min_threshold=1, num_itemsets=num_itemsets)
rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])

pd.set_option('display.max_columns', None)

# Optionally, adjust the width of the console display
pd.set_option('display.width', 1000)

# Print the rules DataFrame again
print(rules.head())