# scripts/database.py

import sys
from pathlib import Path

# 프로젝트 루트 자동 탐색 함수
def find_project_root(config_relpath='config/data_paths.yaml'):
    current = Path(__file__).resolve()
    for p in (current, *current.parents):
        if (p / config_relpath).exists():
            return p
    raise FileNotFoundError(f"Cannot find {config_relpath}")

# BASE_DIR 결정 & PYTHONPATH 등록
BASE_DIR = find_project_root()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 설정 파일 경로 & 로드
import yaml
CONFIG_PATH = BASE_DIR / 'config' / 'data_paths.yaml'
cfg = yaml.safe_load(open(CONFIG_PATH, 'r', encoding='utf-8'))

# 나머지 임포트
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from scripts.data_loader import load_data

from scripts.transformers import (
    clean_date, clean_region, clean_age,
    clean_avgcode, clean_pm10, clean_pm25,
    clean_asthma, clean_rhinitis
)

# ─── 환경 설정 ────────────────────────────────────────
# 프로젝트 루트 & 설정 파일 경로
# BASE_DIR    = Path(__file__).resolve().parent.parent
# CONFIG_PATH = BASE_DIR / 'config' / 'data_paths.yaml'


# DB 접속 정보 (필요에 맞게 변경)
load_dotenv()  

DB_USER     = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST     = os.getenv('DB_HOST')
DB_PORT     = os.getenv('DB_PORT')
DB_NAME     = os.getenv('DB_NAME')

# YAML config 로드
cfg = yaml.safe_load(open(CONFIG_PATH, 'r', encoding='utf-8'))

# ─── 데이터베이스 생성 & 연결 ─────────────────────────
# DB 생성용 엔진 (database 제외)
engine0 = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}")
with engine0.connect() as conn:
    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))

# 실제 사용할 엔진
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─── 테이블 DROP & CREATE DDL 정의 ────────────────────
ddl_statements = [
    # pm10_fact
    "DROP TABLE IF EXISTS pm10_fact",
    """
    CREATE TABLE pm10_fact (
      date_id      CHAR(6),
      region_name  VARCHAR(50),
      pm10         DECIMAL(5,2),
      season       VARCHAR(10)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # pm25_fact
    "DROP TABLE IF EXISTS pm25_fact",
    """
    CREATE TABLE pm25_fact (
      date_id      CHAR(6),
      region_name  VARCHAR(50),
      pm25         DECIMAL(5,2),
      season       VARCHAR(10)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # asthma_fact
    "DROP TABLE IF EXISTS asthma_fact",
    """
    CREATE TABLE asthma_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date_id       VARCHAR(6),
        region_id     INT,
        region_name   VARCHAR(50),     -- 시도명
        district_name VARCHAR(50),     -- 시군구명
        gender        VARCHAR(10),
        age_group     VARCHAR(20),
        episode_count INT
    );
    """,
    
    # rhinitis_fact
    "DROP TABLE IF EXISTS rhinitis_fact",
    """
    CREATE TABLE rhinitis_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date_id       VARCHAR(6),
        region_id     INT,
        region_name   VARCHAR(50),     -- 시도명
        district_name VARCHAR(50),     -- 시군구명
        gender        VARCHAR(10),
        age_group     VARCHAR(20),
        episode_count INT
    );
    """,

    # age_dim
    "DROP TABLE IF EXISTS age_dim",
    """
    CREATE TABLE age_dim (
      age_group VARCHAR(10) PRIMARY KEY,
      age_desc  VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # avgcode_dim
    "DROP TABLE IF EXISTS avgcode_dim",
    """
    CREATE TABLE avgcode_dim (
      avg_code      VARCHAR(20) PRIMARY KEY,
      province_name VARCHAR(50)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # region_dim
    "DROP TABLE IF EXISTS region_dim",
    """
    CREATE TABLE region_dim (
      region_id   VARCHAR(20),
      province    VARCHAR(20),
      region_name VARCHAR(50)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # date_dim
    "DROP TABLE IF EXISTS date_dim",
    """
    CREATE TABLE date_dim (
      date_id CHAR(6)       PRIMARY KEY,
      year    SMALLINT      NOT NULL,
      month   TINYINT       NOT NULL,
      quarter TINYINT       NOT NULL,
      season  VARCHAR(10)   NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

# DDL: DROP & CREATE (FK 검사 비활성화 포함)
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    for ddl in ddl_statements:
        conn.execute(text(ddl))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

# DIM 로딩
raw_date_map    = load_data('date_map', section='reference')
df_date         = clean_date(raw_date_map).drop_duplicates(['date_id'])
df_date.to_sql('date_dim', engine, if_exists='append', index=False)

raw_avg_map = load_data('avgcode_map', section='reference')
df_avg      = clean_avgcode(raw_avg_map).drop_duplicates(subset=['avg_code'])
df_avg.to_sql('avgcode_dim', engine, if_exists='append', index=False)

raw_region_map  = load_data('region_map', section='reference')
df_region       = clean_region(raw_region_map).drop_duplicates(['region_id'])
df_region.to_sql('region_dim', engine, if_exists='append', index=False)

raw_age_map     = load_data('agegroup_map', section='reference')
df_age          = clean_age(raw_age_map).drop_duplicates(['age_group'])
df_age.to_sql('age_dim', engine, if_exists='append', index=False)

# FACT 로딩 (필요 시 TRUNCATE 한 뒤 로드)
for name, clean_fn, table in [
    ('pm10',    clean_pm10,    'pm10_fact'),
    ('pm25',    clean_pm25,    'pm25_fact'),
    ('asthma',  clean_asthma,  'asthma_fact'),
    ('rhinitis',clean_rhinitis,'rhinitis_fact'),
]:
    if name == 'pm10':
        raw = load_data('pm10_rename_region', section='processed')
        df = clean_fn(raw, df_date=df_date)
    elif name == 'pm25':
        raw = load_data('pm25_rename_region', section='processed')
        df = clean_fn(raw, df_date=df_date)
    else:
        raw = load_data(name, section='raw')
        df = clean_fn(raw, df_region=df_region, df_date=df_date)

    df.to_sql(table, engine, if_exists='append', index=False)

print("DB 및 테이블 생성·적재 완료")