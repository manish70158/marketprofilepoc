
# -*- coding: utf-8 -*-
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams.update({"figure.dpi": 150})

DAY_TYPES_ORDER = [
    "Non-trend Day",
    "Normal Day",
    "Normal Variation Day",
    "Neutral Center Day",
    "Neutral Extreme Day",
    "Trend Day",
]


def _ensure_reports_dir():
    os.makedirs("reports", exist_ok=True)


def _pct_table(df, group_cols, value_col="day_type"):
    counts = df.groupby(group_cols)[value_col].value_counts().rename("count").reset_index()
    totals = counts.groupby(group_cols)["count"].transform("sum")
    counts["pct"] = (counts["count"] / totals) * 100.0
    return counts


def _heatmap(data, index, columns, values, title, out_path):
    pivot = data.pivot_table(index=index, columns=columns, values=values, fill_value=0)
    pivot = pivot.reindex(columns=DAY_TYPES_ORDER, fill_value=0)
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlGnBu")
    plt.title(title)
    plt.xlabel(columns.replace("_", " ").title())
    plt.ylabel(index.replace("_", " ").title())
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def build_heatmaps(csv_path: str):
    _ensure_reports_dir()
    df = pd.read_csv(csv_path)
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["month"] = pd.to_datetime(df["date"]).dt.month

    for idx in df["index"].unique():
        sub = df[df["index"] == idx]

        # Year × Day Type %
        year_pct = _pct_table(sub, ["year"], "day_type")
        _heatmap(
            year_pct,
            index="year",
            columns="day_type",
            values="pct",
            title=f"{idx} – Year × Day Type (%)",
            out_path=f"reports/{idx.lower()}_year_daytype_heatmap.png",
        )

        # Month × Day Type % (aggregated across years)
        month_pct = _pct_table(sub, ["month"], "day_type")
        _heatmap(
            month_pct,
            index="month",
            columns="day_type",
            values="pct",
            title=f"{idx} – Month × Day Type (%)",
            out_path=f"reports/{idx.lower()}_month_daytype_heatmap.png",
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build Market Profile heatmaps from CSV")
    ap.add_argument("--csv", required=True, help="Path to mp_daytype_stats CSV")
    args = ap.parse_args()
    build_heatmaps(args.csv)
