import pandas as pd
import yfinance as yf

class Scanner:
    def _download(self, symbols, period="5d", interval="1d"):
        tickers = " ".join(symbols)
        raw = yf.download(tickers=tickers, period=period, interval=interval, progress=False, group_by="ticker")
        if isinstance(raw, pd.DataFrame) and len(symbols) == 1:
            return {symbols[0]: raw}
        return raw

    def _calc(self, data, symbol):
        closes = data['Close'].dropna()
        vols = data['Volume'].dropna()
        if len(closes) < 2: return None
        last, prev = closes.iloc[-1], closes.iloc[-2]
        pct = ((last - prev) / prev) * 100
        vol = vols.iloc[-1]
        return {"Symbol": symbol, "Last Close": last, "Pct Change": pct, "Volume": vol}

    def _to_df(self, res): return pd.DataFrame(res).sort_values("Pct Change", ascending=False)

    def scan_stocks(self, symbols): 
        raw = self._download(symbols)
        out = [self._calc(raw.get(s), s) for s in symbols if self._calc(raw.get(s), s)]
        return self._to_df(out)

    def scan_futures(self): return self.scan_stocks(["ES=F","NQ=F","YM=F","GC=F","CL=F"])
    def scan_forex(self): return self.scan_stocks(["EURUSD=X","GBPUSD=X","JPY=X","AUDUSD=X"])
    def scan_crypto(self, symbols): return self.scan_stocks([s.replace("/","") for s in symbols])
    def scan_memecoins(self): return self.scan_crypto(["DOGE/USD","SHIB/USD","PEPE/USD","FLOKI/USD"])