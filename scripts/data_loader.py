# scripts/data_loader.py

import os
import sys
import yaml
import pandas as pd
from pathlib import Path

# boot.py를 import하여, init_project_path()가 자동 실행되도록 한다
import scripts.boot

# 프로젝트 루트 경로를 결정 → BASE_DIR 변수로 저장
from scripts.boot import find_project_root
BASE_DIR = find_project_root()
CONFIG_PATH = BASE_DIR / "config" / "data_paths.yaml"

# YAML config 로드
def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_cfg = _load_config()

def load_data(name: str, section: str = "raw") -> pd.DataFrame:
    """
    config/data_paths.yaml에서 data.<section>.<name> 키로 지정된 경로를 읽어서 DataFrame으로 반환합니다.
    - name: data.<section>에 정의된 키 (예: 'pm10_processed_v1', 'reference_date_mapping' 등)
    - section: 'raw', 'processed', 'reference' 중 하나
    """
    try:
        path_str = _cfg["data"][section][name]
    except KeyError:
        raise KeyError(f"Config for data.{section}.{name} not found in {CONFIG_PATH}")

    full_path = BASE_DIR / path_str

    # 확장자가 없으면 .csv로 가정
    if not os.path.splitext(full_path.name)[1]:
        full_path = full_path.with_suffix(".csv")

    suffix = full_path.suffix.lower()
    if not full_path.exists():
        raise FileNotFoundError(f"Data file not found: {full_path}")

    # 확장자별로 읽기
    if suffix in (".xls", ".xlsx"):
        return pd.read_excel(full_path)
    elif suffix == ".csv":
        return pd.read_csv(full_path)
    elif suffix == ".parquet":
        return pd.read_parquet(full_path)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")