def hot_encode(x):
    return 1 if x >= 1 else 0


def prepare_basket(data):
    basket = (data.groupby(['InvoiceNo', 'Description'])['Quantity']
              .sum().unstack().reset_index().fillna(0)
              .set_index('InvoiceNo'))
    basket = basket.apply(lambda x: x.map(hot_encode)).astype(bool)
    return basket.astype(bool)
