"""
CSV Import Utility - Tradenza
Parses tabular CSV files containing past trade records,
normalizes columns, and imports them into the user's trading journal.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from services.market_data_service import TwelveDataService


def parse_trades_csv(file_stream) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses an uploaded CSV file stream and returns valid trade dictionaries
    and any error messages encountered.
    """
    trades: List[Dict[str, Any]] = []
    errors: List[str] = []

    try:
        content = file_stream.read()
        if isinstance(content, bytes):
            # Try utf-8 first, fallback to latin-1
            try:
                decoded = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                decoded = content.decode("latin-1")
        else:
            decoded = content

        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames:
            return [], ["CSV file is empty or headers are missing."]

        def norm_key(k: str) -> str:
            return k.strip().lower().replace(" ", "_").replace("-", "_")

        # Normalized header map for flexible matching (handles spaces, dashes, case)
        header_map = {norm_key(col): col for col in reader.fieldnames if col}

        def get_val(row, keys, default=None):
            for k in keys:
                actual = header_map.get(norm_key(k))
                if actual and row.get(actual) is not None:
                    val = str(row[actual]).strip()
                    if val != "":
                        return val
            return default

        for idx, row in enumerate(reader, start=2):  # line 2 is first data row
            # 1. Symbol
            raw_symbol = get_val(row, ["symbol", "ticker", "instrument", "tradingsymbol", "asset"])
            if not raw_symbol:
                errors.append(f"Row {idx}: Missing Symbol.")
                continue
            symbol = raw_symbol.upper()

            # 2. Market
            market = get_val(row, ["market", "segment", "asset_class", "exchange"])
            if not market:
                market = TwelveDataService.infer_market(symbol)

            # 3. Type / Direction
            raw_type = get_val(row, ["type", "trade_type", "action", "side", "direction"], "BUY").upper()
            trade_type = "SELL" if "SELL" in raw_type or "SHORT" in raw_type else "BUY"

            # 4. Entry Price
            raw_entry = get_val(row, ["entry", "entry_price", "price", "buy_price", "open_price", "avg_price"])
            try:
                entry_price = float(raw_entry.replace(",", "").replace("$", "").replace("₹", "")) if raw_entry else None
            except (ValueError, AttributeError):
                entry_price = None

            if entry_price is None or entry_price <= 0:
                errors.append(f"Row {idx}: Invalid entry price '{raw_entry}' for {symbol}.")
                continue

            # 5. Quantity
            raw_qty = get_val(row, ["quantity", "qty", "size", "shares", "contracts", "volume"], "1.0")
            try:
                qty = abs(float(raw_qty.replace(",", "")))
                if qty <= 0:
                    qty = 1.0
            except (ValueError, AttributeError):
                qty = 1.0

            # 6. Exit Price
            raw_exit = get_val(row, ["exit", "exit_price", "close_price", "sell_price"])
            exit_price = None
            if raw_exit:
                try:
                    exit_price = float(raw_exit.replace(",", "").replace("$", "").replace("₹", ""))
                except (ValueError, AttributeError):
                    exit_price = None

            # 7. Stop Loss & Target
            raw_sl = get_val(row, ["stop_loss", "stop", "sl", "stop loss"])
            stop_loss = None
            if raw_sl:
                try:
                    stop_loss = float(raw_sl.replace(",", "").replace("$", "").replace("₹", ""))
                except (ValueError, AttributeError):
                    pass

            raw_target = get_val(row, ["target", "tp", "take_profit", "take profit"])
            target = None
            if raw_target:
                try:
                    target = float(raw_target.replace(",", "").replace("$", "").replace("₹", ""))
                except (ValueError, AttributeError):
                    pass

            # 8. Strategy & Notes
            strategy = get_val(row, ["strategy", "setup", "tag", "pattern"], "Manual Import")
            notes = get_val(row, ["notes", "comment", "remarks", "description"], "")

            # 9. Date / Time
            raw_date = get_val(row, ["date", "time", "entry_time", "created_at", "timestamp"])
            entry_time = None
            if raw_date:
                # Try common date formats
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        entry_time = datetime.strptime(raw_date, fmt)
                        break
                    except ValueError:
                        pass
            if not entry_time:
                entry_time = datetime.now(timezone.utc).replace(tzinfo=None)

            # 10. Status and P&L
            if exit_price is not None:
                status = "CLOSED"
                if trade_type == "BUY":
                    pnl = (exit_price - entry_price) * qty
                else:
                    pnl = (entry_price - exit_price) * qty
            else:
                status = "OPEN"
                pnl = None

            trades.append({
                "market": market,
                "symbol": symbol,
                "trade_type": trade_type,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": qty,
                "stop_loss": stop_loss,
                "target": target,
                "strategy": strategy,
                "notes": notes,
                "status": status,
                "profit_loss": round(pnl, 2) if pnl is not None else None,
                "created_at": entry_time,
                "entry_time": entry_time,
                "exit_time": entry_time if status == "CLOSED" else None,
            })

    except Exception as e:
        errors.append(f"Failed to read CSV: {str(e)}")

    return trades, errors
