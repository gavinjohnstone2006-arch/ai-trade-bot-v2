import argparse, sys, textwrap

def parse_args():
    parser = argparse.ArgumentParser(description="AI Trades Bot")
    parser.add_argument("--mode", choices=["paper","live"], default="paper")
    parser.add_argument("--symbols", default="AAPL,TSLA,NVDA")
    parser.add_argument("--strategy", choices=["gap_and_go","orb_breakout","vwap_reversion"], default="orb_breakout")
    parser.add_argument("--asset_class", choices=["stock","crypto"], default="stock")
    parser.add_argument("--broker", default="")
    parser.add_argument("--capital", type=float, default=25000)
    parser.add_argument("--risk", type=float, default=0.003)
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--partials", default="50@1R,50@2R")
    parser.add_argument("--trail_pct", type=float, default=0.0)
    parser.add_argument("--notify", action="store_true")
    return parser.parse_args()

def run_bot(args):
    print(textwrap.dedent(f"""
        Running AI Trades Bot
        --------------------
        Mode          : {args.mode}
        Asset Class   : {args.asset_class}
        Symbols       : {args.symbols}
        Strategy      : {args.strategy}
        Capital       : {args.capital}
        Risk per Trade: {args.risk}
        Interval      : {args.interval}
        Partials      : {args.partials}
        Trailing Stop : {args.trail_pct}
        Broker        : {args.broker or 'None'}
        Notifications : {'On' if args.notify else 'Off'}
    """))
    print("\nThis is a placeholder — plug in your trading logic here.")

def main():
    args = parse_args()
    run_bot(args)

if __name__ == "__main__":
    main()