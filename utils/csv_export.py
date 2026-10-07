import csv
from io import StringIO


def export_trades_to_csv(trades):

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Date",
        "Symbol",
        "Market",
        "Type",
        "Entry",
        "Exit",
        "Quantity",
        "Profit/Loss",
        "Status",
        "Strategy",
        "Timeframe"
    ])

    for trade in trades:

        writer.writerow([
            trade.created_at.strftime("%Y-%m-%d %H:%M"),
            trade.symbol,
            trade.market,
            trade.trade_type,
            trade.entry_price,
            trade.exit_price,
            trade.quantity,
            trade.profit_loss,
            trade.status,
            trade.strategy,
            trade.timeframe
        ])

    return output.getvalue()