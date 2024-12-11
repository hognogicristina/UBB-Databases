import pandas as pd


def load_data():
    while True:
        print("\nChoose Dataset:")
        print("0: Exit")
        print("1: online_retail.csv")
        print("2: online_retail_II.csv")
        choice = input("Enter your option: ").strip()

        if choice == '0':
            print("\nExiting...\n")
            exit()
        elif choice == '1':
            file_path = './data/online_retail.csv'
            break
        elif choice == '2':
            file_path = './data/online_retail_II.csv'
            break
        else:
            print("\nInvalid input. Please enter 0, 1 or 2. Try again.\n")

    try:
        data = pd.read_csv(file_path, encoding='ISO-8859-1')

        if 'Invoice' in data.columns:
            data.rename(columns={
                'Invoice': 'InvoiceNo',
                'StockCode': 'StockCode',
                'Description': 'Description',
                'Quantity': 'Quantity',
                'InvoiceDate': 'InvoiceDate',
                'Price': 'Price',
                'Customer ID': 'CustomerID',
                'Country': 'Country'
            }, inplace=True)

        print(f"Dataset '{file_path}' loaded successfully.")
        data['Description'] = data['Description'].str.strip()
        data.dropna(axis=0, subset=['InvoiceNo'], inplace=True)
        data['InvoiceNo'] = data['InvoiceNo'].astype('str')
        data = data[~data['InvoiceNo'].str.contains('C')]
        return data

    except Exception as e:
        print(f"Error loading the file: {e}")
        exit()
