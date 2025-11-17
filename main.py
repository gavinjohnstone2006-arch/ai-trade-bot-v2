import argparse
import sys
import textwrap
from utils import alerts  # assumes utils/alerts.py already exists as we set up before

# --- SYMBOL UNIVERSES ---------------------------------------------------------

# You can edit/expand these lists any time.
STOCK_UNIVERSE = [
    # Mega-cap tech / growth
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOGL", "NFLX",
    # Semis / AI
    "AMD", "AVGO", "SMCI",
    # Index / sector ETFs
    "SPY", "QQQ", "IWM", "XLK", "XLF",
]

CRYPTO_UNIVERSE = [
    # Majors
    "BTC/USD", "ETH/USD", "SOL/USD",
    # Meme / degen names
    "DOGE/USD", "SHIB/USD", "PEPE/USD", "FLOKI/USD", "BONK/USD",
]


# --- ARG PARSING --------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="AI Trades Bot")

    p.add_argument("--mode", choices=["paper", "live"], default="paper")
    p.add_argument("--asset_class", choices=["stock", "crypto"], default="stock")

    # NOTE: symbols is optional now.
    # If empty or 'ALL', we expand it to STOCK_UNIVERSE / CRYPTO_UNIVERSE.
    p.add_argument(
        "--symbols",
        default="",
        help="Comma-separated list of symbols OR 'ALL' (uses the default universe)",
    )

    p.add_argument(
        "--strategy",
        choices=["gap_and_go", "orb_breakout", "vwap_reversion"],
        default="orb_breakout",
    )
    p.add_argument("--broker", default="")
    p.add_argument("--capital", type=float, default=25000)
    p.add_argument("--risk", type=float, default=0.003)
    p.add_argument("--interval", default="1m")
    p.add_argument("--partials", default="50@1R,50@2R")
    p.add_argument("--trail_pct", type=float, default=0.0)
    p.add_argument("--notify", action="store_true")

    return p.parse_args()


# --- SYMBOL EXPANSION ---------------------------------------------------------

def expand_symbols(args):
    """
    Turn args.symbols into a clean list.

    Rules:
    - If symbols is empty or 'ALL' -> use the universe for the asset_class.
    - Otherwise, split the comma-separated list.
    """
    raw = (args.symbols or "").strip()

    if not raw or raw.upper() == "ALL":
        if args.asset_class == "stock":
            syms = STOCK_UNIVERSE
        elif args.asset_class == "crypto":
            syms = CRYPTO_UNIVERSE
        else:
            # Fallback: everything
            syms = STOCK_UNIVERSE + CRYPTO_UNIVERSE
    else:
        syms = [s.strip() for s in raw.split(",") if s.strip()]

    return syms


def notify_if_enabled(args, msg: str):
    if args.notify:
        alerts.discord(msg)


# --- MAIN BOT LOGIC STUB ------------------------------------------------------

def run_bot(args):
    symbols_list = expand_symbols(args)
    symbols_str = ",".join(symbols_list)

    summary = textwrap.dedent(f"""
        Running AI Trades Bot
        --------------------
        Mode          : {args.mode}
        Asset Class   : {args.asset_class}
        Symbols       : {symbols_str}
        Strategy      : {args.strategy}
        Capital       : {args.capital}
        Risk per Trade: {args.risk}
        Interval      : {args.interval}
        Partials      : {args.partials}
        Trailing Stop : {args.trail_pct}
        Broker        : {args.broker or 'None'}
        Notifications : {'On' if args.notify else 'Off'}
    """).strip()

    print(summary)

    # 🔔 Discord: run started
    notify_if_enabled(
        args,
        f"▶️ Bot run: {args.mode.upper()} {args.asset_class.upper()} "
        f"{args.strategy} on {symbols_str} (risk {args.risk}, interval {args.interval})",
    )

    # TODO: Real trading logic goes here.
    # For each symbol in symbols_list you will eventually:
    #  - fetch data
    #  - generate signals
    #  - size positions
    #  - send orders to broker
    #  - manage TP/SL & alerts
    print("\nThis is a placeholder — plug your trading logic in here.")

    # 🔔 Discord: run finished
    notify_if_enabled(args, "✔️ Bot run complete.")


def main():
    args = parse_args()
    run_bot(args)


if __name__ == "__main__":
    main()
