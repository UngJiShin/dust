import sys
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Ensure project root on path for imports
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from pandas.tseries.offsets import DateOffset
import datetime
from scripts.data_loader import load_data


def has_mid_long_na(s, n=10):
    first = s.first_valid_index()
    if first is None:
        return False
    is_na = s.loc[first:].isna()
    groups = (is_na != is_na.shift()).cumsum()
    runs = is_na.groupby(groups).sum()
    return runs.max() >= n


def fill_mid_na(s):
    is_na = s.isna()
    groups = (is_na != is_na.shift()).cumsum()
    for gid, block in s[is_na].groupby(groups[is_na]):
        idxs = block.index
        if len(idxs) < 10:
            for dt in idxs:
                prev_dt = dt - DateOffset(years=1)
                next_dt = dt + DateOffset(years=1)
                prev_exists = prev_dt in s.index and pd.notna(s.at[prev_dt])
                next_exists = next_dt in s.index and pd.notna(s.at[next_dt])
                if prev_exists and next_exists:
                    s.at[dt] = (s.at[prev_dt] + s.at[next_dt]) / 2
                elif prev_exists:
                    s.at[dt] = s.at[prev_dt]
                elif next_exists:
                    s.at[dt] = s.at[next_dt]
    return s


def main():
    df_raw = load_data('pm25')

    df_raw['year_month'] = (
        df_raw['구분']
          .str.replace(r"\s*월$", "", regex=True)
          .str.replace('.', '-', 1)
          .str.strip() + '-01'
    )
    df_raw['year_month'] = pd.to_datetime(df_raw['year_month'], format='%Y-%m-%d')

    df = df_raw.set_index('year_month').drop(columns=['구분'])

    if '군산' in df.columns:
        df['군산'] = pd.to_numeric(df['군산'], errors='coerce')

    to_drop = [c for c in df.columns if has_mid_long_na(df[c], n=10)]
    df = df.drop(columns=to_drop)

    df_filled = df.apply(fill_mid_na, axis=0)

    map_df = load_data('avgcode_map', section='reference')
    rename_dict = dict(zip(map_df['avg_code'], map_df['province_name']))
    df_filled.rename(columns=rename_dict, inplace=True)

    df_filled = df_filled.reset_index()
    df_filled['year_month'] = df_filled['year_month'].dt.to_period('M').astype(str)

    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = f"pm25_processed_{today}_v1.0.xlsx"
    out_dir = BASE_DIR / 'data' / 'processed'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    df_filled.to_excel(out_path, index=False)
    print(f"PM2.5 processed and saved to: {out_path}")

if __name__ == '__main__':
    main()
