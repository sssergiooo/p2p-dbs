def calculate_net_spread(buy_price: float, sell_price: float, amount: float = 5000.0) -> dict:
    if not buy_price or not sell_price or buy_price <= 0:
        return {"net_spread": 0.0, "net_profit": 0.0}

    # Покупка USDT на сумму amount
    usdt_bought = amount / buy_price
    
    # Продажа USDT по курсу sell_price с учетом символической комиссии 0.1%
    gross_return = usdt_bought * sell_price
    net_return = gross_return * 0.999 

    net_profit = net_return - amount
    net_spread = (net_profit / amount) * 100

    return {
        "net_spread": round(net_spread, 2),
        "net_profit": round(net_profit, 2)
    }