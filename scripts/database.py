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
      date_id   CHAR(6)     NOT NULL,
      region_id VARCHAR(20) NOT NULL,
      pm10      DECIMAL(5,2),
      season    VARCHAR(10),
      PRIMARY KEY (date_id, region_id),
      FOREIGN KEY (date_id)   REFERENCES date_dim(date_id),
      FOREIGN KEY (region_id) REFERENCES region_dim(region_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # pm25_fact
    "DROP TABLE IF EXISTS pm25_fact",
    """
    CREATE TABLE pm25_fact (
      date_id   CHAR(6)     NOT NULL,
      region_id VARCHAR(20) NOT NULL,
      pm25      DECIMAL(5,2),
      season    VARCHAR(10),
      PRIMARY KEY (date_id, region_id),
      FOREIGN KEY (date_id)   REFERENCES date_dim(date_id),
      FOREIGN KEY (region_id) REFERENCES region_dim(region_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # asthma_fact
    "DROP TABLE IF EXISTS asthma_fact",
    """
    CREATE TABLE asthma_fact (
      date_id       CHAR(6)     NOT NULL,
      region_id     VARCHAR(20) NOT NULL,
      gender        CHAR(1)     NOT NULL,
      age_group     VARCHAR(10) NOT NULL,
      episode_count INT,
      PRIMARY KEY (date_id, region_id, gender, age_group),
      FOREIGN KEY (date_id)   REFERENCES date_dim(date_id),
      FOREIGN KEY (region_id) REFERENCES region_dim(region_id),
      FOREIGN KEY (age_group) REFERENCES age_dim(age_group)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    
    # rhinitis_fact
    "DROP TABLE IF EXISTS rhinitis_fact",
    """
    CREATE TABLE rhinitis_fact (
      date_id       CHAR(6)     NOT NULL,
      region_id     VARCHAR(20) NOT NULL,
      gender        CHAR(1)     NOT NULL,
      age_group     VARCHAR(10) NOT NULL,
      episode_count INT,
      PRIMARY KEY (date_id, region_id, gender, age_group),
      FOREIGN KEY (date_id)   REFERENCES date_dim(date_id),
      FOREIGN KEY (region_id) REFERENCES region_dim(region_id),
      FOREIGN KEY (age_group) REFERENCES age_dim(age_group)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # age_dim
    "DROP TABLE IF EXISTS age_dim",
    """
    CREATE TABLE age_dim (
      age_group VARCHAR(10) PRIMARY KEY,
      age_desc  VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # region_dim
    "DROP TABLE IF EXISTS region_dim",
    """
    CREATE TABLE region_dim (
      region_id   VARCHAR(20) PRIMARY KEY,
      province    VARCHAR(20),
      region_name VARCHAR(50),
      city        VARCHAR(50),
      district    VARCHAR(50)
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

with engine.connect() as conn:
    # 1) 외래키 검사 잠시 비활성화
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

    # 2) 전체 DROP & CREATE 문 실행
    for ddl in ddl_statements:
        conn.execute(text(ddl))

    # 3) 외래키 검사 재활성화
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

# with engine.connect() as conn:
#     for ddl in ddl_statements:
#         conn.execute(text(ddl))

# ─── DIM 테이블 데이터 적재 ───────────────────────────
# 날짜 차원
df_date   = load_data('date_map',   section='reference')
df_date.to_sql('date_dim',   engine, if_exists='append', index=False)

# 지역 차원
df_region = load_data('region_map', section='reference')
# 컬럼명이 mapping 파일과 다를 경우 미리 rename 필요
df_region.to_sql('region_dim', engine, if_exists='append', index=False)

# 연령대 차원
df_age    = load_data('agegroup_map', section='reference')
df_age.columns = ['age_group', 'age_desc']   # mapping 파일 컬럼에 맞춰 조정
df_age.to_sql('age_dim', engine, if_exists='append', index=False)

# ─── FACT 테이블 데이터 적재 ──────────────────────────
# PM10 Fact
df_pm_raw = load_data('pm10', section='raw')
# wide→long 변환
pm10_long = df_pm_raw.melt(
    id_vars=['구분'], value_vars=[c for c in df_pm_raw.columns if c!='구분' and '도평균' not in c],
    var_name='region_name', value_name='pm10'
)
# key 생성 및 조인
pm10_long['date_id'] = pm10_long['구분'].astype(str).str.replace('.', '', regex=False)
pm10_long = pm10_long.merge(df_region[['region_id','region_name']], on='region_name', how='left')
pm10_long = pm10_long.merge(df_date[['date_id','season']],           on='date_id',    how='left')
pm10_fact_df = pm10_long[['date_id','region_id','pm10','season']]
pm10_fact_df.to_sql('pm10_fact', engine, if_exists='append', index=False)

# PM2.5 Fact
df_p25_raw = load_data('pm25', section='raw')
p25_long = df_p25_raw.melt(
    id_vars=['구분'], value_vars=[c for c in df_p25_raw.columns if c!='구분' and '도평균' not in c],
    var_name='region_name', value_name='pm25'
)
p25_long['date_id'] = p25_long['구분'].astype(str).str.replace('.', '', regex=False)
p25_long = p25_long.merge(df_region[['region_id','region_name']], on='region_name', how='left')
p25_long = p25_long.merge(df_date[['date_id','season']],           on='date_id',    how='left')
p25_fact_df = p25_long[['date_id','region_id','pm25','season']]
p25_fact_df.to_sql('pm25_fact', engine, if_exists='append', index=False)

# Asthma Fact
df_asthma = load_data('asthma', section='raw')
# raw 데이터 컬럼에 맞춰 date_id 생성 예시
df_asthma['date_id'] = pd.to_datetime(df_asthma['date']).dt.strftime('%Y%m')
asthma_fact_df = df_asthma[['date_id','region_id','gender','age_group','episode_count']]
asthma_fact_df.to_sql('asthma_fact', engine, if_exists='append', index=False)

# Rhinitis Fact
df_rhinitis = load_data('rhinitis', section='raw')
df_rhinitis['date_id'] = pd.to_datetime(df_rhinitis['date']).dt.strftime('%Y%m')
rhinitis_fact_df = df_rhinitis[['date_id','region_id','gender','age_group','episode_count']]
rhinitis_fact_df.to_sql('rhinitis_fact', engine, if_exists='append', index=False)

print("DB 및 테이블 생성·적재 완료")