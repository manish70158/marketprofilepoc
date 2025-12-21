
# Market Profile Day-Type Stats & Heatmaps (NIFTY 50 & NIFTY BANK)

This repository fetches last **10 years** of intraday data for **NIFTY 50** and **NIFTY BANK** from **Angel One SmartAPI**, classifies each trading session into Market Profile **day types**, and generates **matplotlib heatmaps** showing distribution by **year** and **month**. It also distinguishes **Neutral Center** vs **Neutral Extreme** day types (per common Market Profile conventions and tools like LinnSoft DayTypes).

> **References**:
> - Angel One SmartAPI (historical candles, tokens for indices)
>   - SmartAPI docs: https://smartapi.angelbroking.com/docs / Historical: https://smartapi.angelbroking.com/docs/Historical
>   - Index tokens update (NIFTY50 `99926000`, BANKNIFTY `99926009`): https://smartapi.angelone.in/smartapi/forum/topic/3986/smartapi-now-provides-real-time-market-data-for-120-indices-across-nse-bse-and-mcx
> - Market Profile day-type logic (IB vs Day range; Neutral, Neutral Extreme, Normal, Normal Variation, Trend, Non-trend):
>   - LinnSoft DayTypes: https://www.linnsoft.com/techind/day-types-rtx
>   - TradingBalance overview: https://tradingbalance.co.uk/market-profile-and-understanding-different-day-types/
> - NSE market timings (IB = 09:15–10:15 IST): https://www.nseindia.com/static/market-data/market-timings

## Quick start

1) Install requirements

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

3) Run end-to-end

```bash
python run_all.py
```

4) Just visuals on existing CSV

```bash
# Replace the date with your actual CSV file date, e.g., 2025-12-21
python src/viz_dashboard.py --csv data/mp_daytype_stats_2025-12-21.csv
```
