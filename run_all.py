
#!/usr/bin/env python3
from datetime import date
from src.fetch_and_classify import compute_stats
from src.viz_dashboard import build_heatmaps

if __name__ == "__main__":
    df = compute_stats()  # writes CSV to data/
    if df is None:
        raise SystemExit("No data produced.")
    csv_path = f"data/mp_daytype_stats_{date.today().isoformat()}.csv"
    build_heatmaps(csv_path)
