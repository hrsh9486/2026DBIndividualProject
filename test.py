import yfinance as yf

# Ticker for India Nifty 50
nifty_symbol ="^NSEI"
nifty_ticker = yf.Ticker(nifty_symbol)

# Ticker for Sensex
bse_symbol = "^BSESN"
bse_ticker = yf.Ticker(bse_symbol)


nifty_data = nifty_ticker.history(period="10y")
nifty_financial = nifty_ticker.financials
bse_data = bse_ticker.history(period="10y")
# print(nifty_data)
print(nifty_financial)
# print(bse_data)
