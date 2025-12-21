
# -*- coding: utf-8 -*-
"""Day-type classification utilities (Market Profile)

Implements rules for:
- Normal Day
- Normal Variation Day
- Trend Day
- Neutral Center Day
- Neutral Extreme Day
- Non-trend Day

References:
- LinnSoft DayTypes: https://www.linnsoft.com/techind/day-types-rtx
- Market Profile overviews: https://tradingbalance.co.uk/market-profile-and-understanding-different-day-types/
"""
from typing import Dict

# IB size thresholds (percent of 09:15 open price)
IB_SMALL_LT = 0.33
IB_MEDIUM_LE = 1.00

# Day-type classification thresholds (tunable)
IB_RATIO_WIDE = 0.50       # IB occupies >= 50% of day range => wide IB
IB_RATIO_VERY_WIDE = 0.80  # IB occupies >= 80% => Non-trend candidate
IB_RATIO_TREND_SMALL = 0.25  # small IB => Trend candidate
CLOSE_NEAR_EXTREME_LE = 0.15  # close within 15% of day range from an extreme
CLOSE_NEAR_MID_LE = 0.30      # Neutral Center: close near mid (<=30%)


def classify_ib_size(ib_pct: float) -> str:
    if ib_pct < IB_SMALL_LT:
        return "Small"
    if ib_pct <= IB_MEDIUM_LE:
        return "Medium"
    return "Large"


def classify_day_type(m: Dict) -> str:
    """Return one of day types using IB vs day range and extension behavior.

    Inputs (from metrics dict):
    - ib_ratio: IB range / day range
    - re_up / re_down: range extension beyond IB high/low
    - close_pos_mid: |close - mid| / day range
    - close_dist_from_extreme: min distance to an extreme / day range
    """
    ib_ratio = m["ib_ratio"]
    re_up, re_down = m["re_up"], m["re_down"]
    close_pos_mid = m["close_pos_mid"]
    close_near_extreme = m["close_dist_from_extreme"] <= CLOSE_NEAR_EXTREME_LE

    # Neutral Center: both-side extension & close near mid
    if re_up and re_down and close_pos_mid <= CLOSE_NEAR_MID_LE:
        return "Neutral Center Day"

    # Neutral Extreme: both-side extension & close near one extreme
    if re_up and re_down and close_near_extreme:
        return "Neutral Extreme Day"

    # Non-trend: very wide IB and no extension
    if ib_ratio >= IB_RATIO_VERY_WIDE and not re_up and not re_down:
        return "Non-trend Day"

    # Normal: wide IB, no extension
    if ib_ratio >= IB_RATIO_WIDE and not re_up and not re_down:
        return "Normal Day"

    # Normal Variation: wide IB, one-sided extension
    if ib_ratio >= IB_RATIO_WIDE and (re_up ^ re_down):
        return "Normal Variation Day"

    # Trend: small IB, one-sided extension with close near extreme
    if ib_ratio <= IB_RATIO_TREND_SMALL and (re_up ^ re_down) and close_near_extreme:
        return "Trend Day"

    # Fallbacks
    if re_up and re_down:
        # if both extensions but not mid/extreme, general Neutral
        return "Neutral Center Day"
    if (re_up ^ re_down):
        return "Normal Variation Day"
    return "Non-trend Day"
