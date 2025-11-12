import streamlit as st, subprocess, sys, time
import pandas as pd
from scanner import Scanner

st.set_page_config(page_title="AI Trades Bot", layout="wide")
st.title("AI Trades Bot & Market Scanner")

tabs = st.tabs(["Bot Controller","Market Scanners"])
scanner = Scanner()

with tabs[0]:
    st.subheader("Run your trading bot")
    mode = st.selectbox("Mode",["paper","live"])
    asset = st.selectbox("Asset Class",["stock","crypto"])
    symbols = st.text_input("Symbols (comma-separated)","AAPL,TSLA,NVDA")
    strategy = st.selectbox("Strategy",["gap_and_go","orb_breakout","vwap_reversion"])
    broker = st.text_input("Broker (optional)")
    risk = st.number_input("Risk fraction",0.001,0.02,0.003,0.001)
    interval = st.selectbox("Interval",["1m","5m","15m"])
    partials = st.text_input("Partials","50@1R,50@2R")
    trail = st.number_input("Trailing stop fraction",0.0,0.1,0.0,0.001)
    notify = st.checkbox("Send Discord/Telegram Alerts")

    if st.button("Run Once"):
        cmd = [sys.executable,"main.py","--mode",mode,"--symbols",symbols,"--strategy",strategy,
               "--asset_class",asset,"--broker",broker,"--risk",str(risk),"--interval",interval,
               "--partials",partials,"--trail_pct",str(trail)]
        if notify: cmd += ["--notify"]
        st.code(" ".join(cmd))
        out = subprocess.run(cmd,capture_output=True,text=True).stdout
        st.text_area("Output",out,height=300)

with tabs[1]:
    st.subheader("Market scanners")
    scan_type = st.selectbox("Scanner",["Stocks","Futures","Forex","Crypto","Meme Coins"])
    custom_syms = st.text_input("Symbols", "AAPL,TSLA" if scan_type=="Stocks" else "BTC/USD,ETH/USD")
    if st.button("Run Scan"):
        if scan_type=="Stocks":
            syms = [s.strip() for s in custom_syms.split(",")]
            df = scanner.scan_stocks(syms)
        elif scan_type=="Futures": df = scanner.scan_futures()
        elif scan_type=="Forex": df = scanner.scan_forex()
        elif scan_type=="Crypto":
            syms = [s.strip() for s in custom_syms.split(",")]
            df = scanner.scan_crypto(syms)
        else: df = scanner.scan_memecoins()
        if df.empty: st.warning("No data (may be market closed or no internet)")
        else:
            st.dataframe(df)
            df.set_index("Symbol", inplace=True)
            st.bar_chart(df["Pct Change"])