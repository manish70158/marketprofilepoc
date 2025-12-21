
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

import pandas as pd
import pytz
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

try:
    from SmartApi import SmartConnect
except ImportError as e:
    raise SystemExit(f"Import error: {e}\nMake sure all dependencies are installed: pip install -r requirements.txt")

from .day_types import (
    classify_day_type,
    classify_ib_size,
)

IST = pytz.timezone("Asia/Kolkata")

# Angel One updated tokens for indices
INDICES = {
    "NIFTY_50": {"exchange": "NSE", "symboltoken": "99926000", "trading_symbol": "Nifty 50"},
    "NIFTY_BANK": {"exchange": "NSE", "symboltoken": "99926009", "trading_symbol": "Nifty Bank"},
}

# NSE regular session times
MARKET_OPEN = datetime.strptime("09:15", "%H:%M").time()
MARKET_CLOSE = datetime.strptime("15:30", "%H:%M").time()
IB_END = datetime.strptime("10:15", "%H:%M").time()


def _env(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing env var: {key}")
    return v


def angel_login() -> SmartConnect:
    """Authenticate with Angel One SmartAPI using env credentials."""
    api_key = _env("ANGEL_API_KEY")
    client_code = _env("ANGEL_CLIENT_CODE")
    pin_or_pwd = _env("ANGEL_PIN")
    totp_token = _env("ANGEL_TOTP_TOKEN")

    obj = SmartConnect(api_key=api_key)
    import pyotp
    totp = pyotp.TOTP(totp_token).now()

    data = obj.generateSession(client_code, pin_or_pwd, totp)
    if not data or not data.get("status"):
        raise RuntimeError(f"Login failed: {data}")
    _ = obj.getfeedToken()
    return obj


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_day_candles(obj: SmartConnect, exchange: str, token: str, day: date, interval: str) -> pd.DataFrame:
    start_dt = IST.localize(datetime.combine(day, MARKET_OPEN))
    end_dt = IST.localize(datetime.combine(day, MARKET_CLOSE))

    params = {
        "exchange": exchange,
        "symboltoken": token,
        "interval": interval,
        "fromdate": start_dt.strftime("%Y-%m-%d %H:%M"),
        "todate": end_dt.strftime("%Y-%m-%d %H:%M"),
    }
    data = obj.getCandleData(params)

    if not data or not data.get("status") or not data.get("data"):
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(data["data"], columns=["datetime", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df[(df["datetime"].dt.tz_convert(IST).dt.time >= MARKET_OPEN) &
            (df["datetime"].dt.tz_convert(IST).dt.time <= MARKET_CLOSE)]
    return df


def compute_ib_and_day_metrics(df: pd.DataFrame) -> Optional[Dict]:
    if df.empty:
        return None
    times = df["datetime"].dt.tz_convert(IST).dt.time
    ib_mask = (times >= MARKET_OPEN) & (times <= IB_END)
    ib_bars = df[ib_mask]
    if ib_bars.empty:
        return None

    ib_high = ib_bars["high"].max()
    ib_low = ib_bars["low"].min()
    ib_range = ib_high - ib_low

    day_high = df["high"].max()
    day_low = df["low"].min()
    day_range = day_high - day_low

    open_915_row = df[df["datetime"].dt.tz_convert(IST).dt.time == MARKET_OPEN]
    if open_915_row.empty:
        open_915 = float(df.iloc[0]["open"])
    else:
        open_915 = float(open_915_row.iloc[0]["open"])

    close = float(df.iloc[-1]["close"])

    re_up = day_high > ib_high
    re_down = day_low < ib_low

    ib_pct = (ib_range / open_915) * 100 if open_915 else 0.0
    ib_ratio = (ib_range / day_range) if day_range else 0.0

    mid = (day_high + day_low) / 2.0
    close_pos_mid = abs(close - mid) / day_range if day_range else 0.0
    close_dist_from_extreme = min(abs(close - day_low), abs(close - day_high)) / day_range if day_range else 1.0

    return {
        "ib_high": ib_high, "ib_low": ib_low, "ib_range": ib_range,
        "day_high": day_high, "day_low": day_low, "day_range": day_range,
        "open_915": open_915, "close": close,
        "re_up": bool(re_up), "re_down": bool(re_down),
        "ib_pct": ib_pct, "ib_ratio": ib_ratio,
        "close_pos_mid": close_pos_mid,
        "close_dist_from_extreme": close_dist_from_extreme,
    }


def daterange(start: date, end: date):
    for n in range((end - start).days + 1):
        yield start + timedelta(n)


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def compute_stats():
    """Main fetch-and-classify. Returns DataFrame and writes a dated CSV to data/."""
    load_dotenv()
    interval = os.getenv("INTERVAL", "FIFTEEN_MINUTE")
    years_back = int(os.getenv("YEARS_BACK", "1"))

    obj = angel_login()

    end_date = date.today()
    start_date = end_date - timedelta(days=years_back * 365)
    start_date = start_date + timedelta(days=1)

    records: List[Dict] = []

    for index_name, meta in INDICES.items():
        print(f"Processing {index_name} ({meta['trading_symbol']}) ...")
        for d in tqdm(list(daterange(start_date, end_date)), desc=f"{index_name} days", ncols=100):
            if is_weekend(d):
                continue
            df = fetch_day_candles(obj, meta["exchange"], meta["symboltoken"], d, interval)
            if df.empty:
                continue
            metrics = compute_ib_and_day_metrics(df)
            if not metrics:
                continue
            ib_size = classify_ib_size(metrics["ib_pct"])
            day_type = classify_day_type(metrics)

            records.append({
                "date": d.isoformat(),
                "index": index_name,
                "day_type": day_type,
                "ib_size": ib_size,
                "ib_pct": metrics["ib_pct"],
                "ib_ratio": metrics["ib_ratio"],
                "day_range": metrics["day_range"],
            })
            time.sleep(0.02)

    result = pd.DataFrame(records)
    if result.empty:
        print("No data collected.")
        return None

    out_csv = f"data/mp_daytype_stats_{date.today().isoformat()}.csv"
    os.makedirs("data", exist_ok=True)
    result.to_csv(out_csv, index=False)
    print(f"Saved detailed records to {out_csv}")
    return result
