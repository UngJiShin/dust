################################################
# 사용방법 - 복사하여 주석만 제거하여 사용
# import sys
# from pathlib import Path

# # 현재 노트북(.ipynb)이 src/ 안에 있으니 상위 폴더(프로젝트 루트)를 추가
# BASE_DIR    = Path().resolve().parent    # Notebook이 src/ 안이라면 .parent
# config_path = BASE_DIR / 'config' / 'data_paths.yaml'
# proj_root = Path().resolve().parent
# sys.path.insert(0, str(proj_root))


# # 이제 바로 import
# from scripts.data_loader import load_data

# # 테스트
# df_pm10 = load_data('pm10')
################################################

import yaml
from pathlib import Path
import pandas as pd
import os

# Determine project root directory supporting both script and interactive environments
def _get_base_dir():
    try:
        # When running as a module
        return Path(__file__).resolve().parent.parent
    except NameError:
        # Interactive (e.g., Jupyter Notebook)
        return Path().resolve().parent

BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / 'config' / 'data_paths.yaml'

# Load YAML config
def _load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_cfg = _load_config()

# Helper function to load datasets based on config keys
def load_data(name: str, section: str = 'raw') -> pd.DataFrame:
    """
    Load a DataFrame based on the key and section defined in config/data_paths.yaml.

    Parameters:
        name (str): Key under data.<section> in the config (e.g., 'pm10', 'asthma', 'pm10_top30').
        section (str): One of 'raw', 'processed', or 'reference'.

    Returns:
        pd.DataFrame: Loaded DataFrame from the specified path.
    """
    # Retrieve path string from config
    try:
        path_str = _cfg['data'][section][name]
    except KeyError:
        raise KeyError(f"Config for data.{section}.{name} not found in {CONFIG_PATH}")

    path = BASE_DIR / path_str
    # If filename has no extension, assume CSV
    if not os.path.splitext(path.name)[1]:
        path = path.with_suffix('.csv')
    suffix = path.suffix.lower()

    # Check file existence
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    # Read based on extension
    if suffix in ('.xls', '.xlsx'):
        return pd.read_excel(path)
    elif suffix == '.csv':
        return pd.read_csv(path)
    elif suffix == '.parquet':
        return pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")