import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# -------------------
# CONFIG & UNIVERSES
# -------------------

st.set_page_config(page_title="AI Market Bot", layout="wide")

# Liquid stock universe (you can add/remove tickers any time)
STOCK_UNIVERSE = [
    # Mega-cap tech / growth
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "NFLX",
    # Semis / AI
    "AMD", "AVGO", "SMCI", "INTC",
    # Index / sector ETFs
    "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "XLV",
]

# Major & meme crypto that Yahoo Finance supports
CRYPTO_UNIVERSE = [
    # Majors
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    # Meme / degen
    "DOGE-USD", "SHIB-USD", "PEPE-USD", "BONK-USD",
]

# -------------------
# DATA & INDICATORS
# -------------------

@st.cache_data(show_spinner=False)
def load_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Download historical data for a single symbol."""
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        return df
    df = df.rename(columns=str.lower)
    df.index = df.index.tz_localize(None) if hasattr(df.index, "tz_localize") else df.index
    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators: SMAs, RSI, ATR, volume avg."""
    if df.empty:
        return df.copy()

    df = df.copy()

    # Simple moving averages
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    # RSI 14
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    roll_up = pd.Series(gain).rolling(14).mean()
    roll_down = pd.Series(loss).rolling(14).mean()
    rs = roll_up / (roll_down + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    df["rsi14"] = rsi.values

    # ATR 14
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()

    # Volume 20-day average
    if "volume" in df.columns:
        df["vol_ma20"] = df["volume"].rolling(20).mean()
    else:
        df["vol_ma20"] = np.nan

    return df


def classify_trend(last_close, sma20, sma50, sma200) -> str:
    """Simple trend classification."""
    if np.isnan(sma20) or np.isnan(sma50) or np.isnan(sma200):
        return "No Trend (insufficient data)"
    if last_close > sma20 > sma50 > sma200:
        return "Strong Uptrend"
    if last_close > sma20 > sma50 and sma200 <= sma50:
        return "Uptrend"
    if last_close < sma20 < sma50 < sma200:
        return "Strong Downtrend"
    if last_close < sma20 < sma50:
        return "Downtrend"
    return "Sideways / Mixed"


def generate_signal_row(symbol: str, df: pd.DataFrame, capital: float, risk_pct: float):
    """Generate a single row of signal info for scanner."""
    if df.empty or len(df) < 30:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    last_close = float(last["close"])
    prev_close = float(prev["close"])
    pct_change = (last_close - prev_close) / prev_close * 100.0

    rsi = float(last.get("rsi14", np.nan))
    sma20 = float(last.get("sma20", np.nan))
    sma50 = float(last.get("sma50", np.nan))
    sma200 = float(last.get("sma200", np.nan))
    atr = float(last.get("atr14", np.nan))

    trend = classify_trend(last_close, sma20, sma50, sma200)

    # Basic signal logic
    signal = "No Trade"

    # Momentum long: strong uptrend, RSI in healthy range
    if trend.startswith("Strong Uptrend") and 55 <= rsi <= 75 and pct_change > 0:
        signal = "Momentum Long"

    # Oversold bounce watch
    elif rsi < 30 and last_close > sma200:
        signal = "Oversold Watch"

    # Breakdown risk
    elif trend.startswith("Strong Downtrend") and rsi < 45:
        signal = "Avoid / Short Bias"

    # Risk management: ATR-based stop & position size
    stop_distance = atr if atr > 0 else last_close * 0.03  # fallback 3%
    stop_loss = last_close - stop_distance
    if stop_loss <= 0:
        position_size = 0
        risk_dollars = 0
    else:
        risk_dollars = capital * risk_pct
        position_size = risk_dollars / (last_close - stop_loss) if (last_close - stop_loss) > 0 else 0

    return {
        "Symbol": symbol,
        "Last Price": round(last_close, 4),
        "1D %": round(pct_change, 2),
        "RSI14": round(rsi, 2) if not np.isnan(rsi) else np.nan,
        "Trend": trend,
        "Signal": signal,
        "ATR14": round(atr, 4) if not np.isnan(atr) else np.nan,
        "Suggested Stop": round(stop_loss, 4),
        "Risk $": round(risk_dollars, 2),
        "Size (units)": int(position_size),
    }


def simple_backtest_momentum(df: pd.DataFrame):
    """
    Very primitive momentum backtest:
    - Entry when Momentum Long signal appears
    - Exit when price closes below SMA20 or RSI < 50
    Uses daily data; returns rough stats.
    """
    if df.empty or len(df) < 60:
        return {"Trades": 0, "Win %": np.nan, "Avg R": np.nan, "Total R": np.nan}

    df = df.copy()
    df = compute_indicators(df)
    df = df.dropna(subset=["sma20", "sma50", "sma200", "rsi14"])

    in_trade = False
    entry_price = None
    results = []

    for i in range(1, len(df)):
        row_prev = df.iloc[i - 1]
        row = df.iloc[i]

        # Build a "momentum signal" condition like in scanner
        trend = classify_trend(row_prev["close"], row_prev["sma20"], row_prev["sma50"], row_prev["sma200"])
        momentum_cond = (
            trend.startswith("Strong Uptrend") and
            55 <= row_prev["rsi14"] <= 75 and
            row_prev["close"] > row_prev["close"] * 0.995  # just to avoid flat days
        )

        if not in_trade and momentum_cond:
            in_trade = True
            entry_price = row["open"] if "open" in df.columns else row["close"]
            continue

        if in_trade:
            exit_cond = (row["close"] < row["sma20"]) or (row["rsi14"] < 50)
            if exit_cond:
                exit_price = row["close"]
                r = (exit_price - entry_price) / entry_price
                results.append(r)
                in_trade = False
                entry_price = None

    if not results:
        return {"Trades": 0, "Win %": np.nan, "Avg R": np.nan, "Total R": np.nan}

    wins = sum(1 for r in results if r > 0)
    trades = len(results)
    win_pct = wins / trades * 100
    avg_r = np.mean(results)
    total_r = np.sum(results)

    return {
        "Trades": trades,
        "Win %": round(win_pct, 1),
        "Avg R": round(avg_r, 3),
        "Total R": round(total_r, 3),
    }

# -------------------
# UI LAYOUT
# -------------------

st.title("AI Market Bot – Stocks & Crypto Scanner")

with st.sidebar:
    st.header("Global Settings")

    capital = st.number_input("Account Size ($)", min_value=1000.0, value=25000.0, step=1000.0)
    risk_pct = st.slider("Risk per Trade (%)", min_value=0.1, max_value=5.0, value=0.5, step=0.1) / 100.0

    asset_class = st.selectbox("Asset Class", ["Stocks", "Crypto"])
    universe_choice = st.selectbox(
        "Universe",
        ["Default (liquid names)", "Custom symbols"],
    )

    custom_symbols = st.text_input(
        "Custom symbols (comma separated)",
        value="",
        placeholder="AAPL,TSLA,NVDA or BTC-USD,ETH-USD",
        help="Leave blank to use the default universe.",
    )

    period = st.selectbox("History Period", ["3mo", "6mo", "1y"], index=1)
    interval = st.selectbox("Timeframe", ["1d", "1h"], index=0)

    run_scan = st.button("Run Scan", type="primary")

tab_scan, tab_detail, tab_help = st.tabs(["Scanner", "Symbol Detail", "How it Works"])

# -------------------
# SCANNER TAB
# -------------------

with tab_scan:
    st.subheader("Multi-Symbol Scanner")

    if run_scan:
        if universe_choice == "Default (liquid names)":
            symbols = STOCK_UNIVERSE if asset_class == "Stocks" else CRYPTO_UNIVERSE
        else:
            if not custom_symbols.strip():
                st.warning("You selected Custom symbols but didn't enter any.")
                symbols = []
            else:
                raw = [s.strip() for s in custom_symbols.split(",") if s.strip()]
                symbols = raw

        if not symbols:
            st.stop()

        st.write(f"Scanning **{len(symbols)}** symbols...")

        rows = []
        progress = st.progress(0)
        status = st.empty()

        for i, sym in enumerate(symbols):
            progress.progress(int((i + 1) / len(symbols) * 100))
            status.text(f"Loading {sym} ({i+1}/{len(symbols)})")

            try:
                df = load_history(sym, period=period, interval=interval)
                df = compute_indicators(df)
                row = generate_signal_row(sym, df, capital, risk_pct)
                if row:
                    rows.append(row)
            except Exception as e:
                # Skip symbols that fail
                continue

        progress.empty()
        status.empty()

        if not rows:
            st.error("No valid data returned for any symbols. Try a different period/timeframe.")
        else:
            df_signals = pd.DataFrame(rows)
            # Sort: Momentum Long first, then by 1D %
            df_signals["SignalRank"] = df_signals["Signal"].map({
                "Momentum Long": 0,
                "Oversold Watch": 1,
                "Avoid / Short Bias": 2,
                "No Trade": 3,
            }).fillna(4)

            df_signals = df_signals.sort_values(["SignalRank", "1D %"], ascending=[True, False])

            st.dataframe(
                df_signals.drop(columns=["SignalRank"]),
                use_container_width=True,
            )

            st.caption("Signals are NOT financial advice. Use them as a starting point, not as blind orders.")

    else:
        st.info("Configure settings in the sidebar and click **Run Scan** to analyze the market.")


# -------------------
# SYMBOL DETAIL TAB
# -------------------

with tab_detail:
    st.subheader("Single Symbol Deep Dive")

    default_symbol = "AAPL" if asset_class == "Stocks" else "BTC-USD"
    symbol = st.text_input("Symbol", value=default_symbol)

    if st.button("Analyze Symbol"):
        df = load_history(symbol, period=period, interval=interval)
        if df.empty:
            st.error("No data for that symbol / timeframe.")
        else:
            df = compute_indicators(df)
            last = df.iloc[-1]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Last Price", f"{last['close']:.4f}")
                st.metric("RSI 14", f"{last['rsi14']:.1f}")
            with col2:
                st.metric("SMA20", f"{last['sma20']:.4f}")
                st.metric("SMA50", f"{last['sma50']:.4f}")
            with col3:
                st.metric("SMA200", f"{last['sma200']:.4f}")
                st.metric("ATR14", f"{last['atr14']:.4f}")

            st.line_chart(df[["close", "sma20", "sma50", "sma200"]].dropna())

            # Backtest
            stats = simple_backtest_momentum(df)
            st.markdown("### Simple Momentum Backtest (daily data)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Trades", stats["Trades"])
            c2.metric("Win %", f"{stats['Win %'] if stats['Win %'] == stats['Win %'] else 'N/A'}")
            c3.metric("Avg R/Trade", f"{stats['Avg R'] if stats['Avg R'] == stats['Avg R'] else 'N/A'}")
            c4.metric("Total R", f"{stats['Total R'] if stats['Total R'] == stats['Total R'] else 'N/A'}")

            st.caption(
                "Backtest is rough & simplified. It uses a basic momentum rule set and does not account for slippage, "
                "fees, or intraday behavior."
            )


# -------------------
# HELP TAB
# -------------------

with tab_help:
    st.subheader("What This Bot Actually Does")

    st.markdown("""
    **This app is an analysis & idea-generation bot, not an auto-trading bot.**

    **Scanner tab**
    - Pulls price data for multiple stocks or cryptos.
    - Calculates SMA20/50/200, RSI14, ATR14, and volume averages.
    - Classifies trend (strong uptrend / downtrend / sideways).
    - Tags each symbol with a signal:
        - `Momentum Long` – strong uptrend + healthy RSI.
        - `Oversold Watch` – oversold RSI but above long-term trend (possible bounce).
        - `Avoid / Short Bias` – strong downtrend + weak RSI.
        - `No Trade` – nothing clear.
    - Suggests an ATR-based stop and position size given your account size + risk %.

    **Symbol Detail tab**
    - Lets you deep dive one symbol.
    - Shows key indicators and a price + moving average chart.
    - Runs a very rough momentum backtest so you can see if the idea has had edge historically.

    **Important**
    - This is **not** financial advice.
    - Use it as a starting point to focus your attention, not as an autopilot money machine.
    - Real edge comes from testing, discipline, and risk management, not a single script.
    """)
