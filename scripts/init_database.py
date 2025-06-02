# scripts/init_database.py

import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

# 프로젝트 루트 등록
import scripts.boot
from scripts.boot import find_project_root

BASE_DIR = find_project_root()
CONFIG_PATH = BASE_DIR / "config" / "data_paths.yaml"
cfg = yaml.safe_load(open(CONFIG_PATH, "r", encoding="utf-8"))

#  load_data 함수 가져오기
from scripts.data_loader import load_data

#  DB 접속 정보 .env에서 로드
load_dotenv()
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_NAME     = os.getenv("DB_NAME")

# MySQL 엔진 생성 (DB가 없다면 생성)
engine0 = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
)
with engine0.connect() as conn:
    conn.execute(text(
        f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    ))

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 기존 테이블(외래키 포함) DROP
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    for t in [
        "pm10_fact", "pm10_asthma_fact", "pm10_rhinitis_fact",
        "pm25_fact", "pm25_asthma_fact", "pm25_rhinitis_fact",
        "date_dim", "age_group_dim"
    ]:
        conn.execute(text(f"DROP TABLE IF EXISTS {t};"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

# DDL 정의
DDL = [
    # date_dim
    """
    CREATE TABLE IF NOT EXISTS date_dim (
        date_id CHAR(6) PRIMARY KEY,
        year SMALLINT NOT NULL,
        month TINYINT NOT NULL,
        quarter TINYINT NOT NULL,
        season VARCHAR(10) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # age_group_dim
    """
    CREATE TABLE IF NOT EXISTS age_group_dim (
        age_group VARCHAR(10) PRIMARY KEY,
        age_range VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm10_asthma_fact (천식+PM10)
    """
    CREATE TABLE IF NOT EXISTS pm10_asthma_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ym CHAR(6),
        region VARCHAR(50),
        gender VARCHAR(10),
        age_group VARCHAR(10),
        visit_count INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm10_rhinitis_fact (비염+PM10)
    """
    CREATE TABLE IF NOT EXISTS pm10_rhinitis_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ym CHAR(6),
        region VARCHAR(50),
        gender VARCHAR(10),
        age_group VARCHAR(10),
        visit_count INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm10_fact (PM10 농도)
    """
    CREATE TABLE IF NOT EXISTS pm10_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date_id CHAR(6),
        region_name VARCHAR(50),
        pm10 DECIMAL(5,2),
        FOREIGN KEY(date_id) REFERENCES date_dim(date_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm25_asthma_fact (천식+PM2.5)
    """
    CREATE TABLE IF NOT EXISTS pm25_asthma_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ym CHAR(6),
        region VARCHAR(50),
        gender VARCHAR(10),
        age_group VARCHAR(10),
        visit_count INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm25_rhinitis_fact (비염+PM2.5)
    """
    CREATE TABLE IF NOT EXISTS pm25_rhinitis_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ym CHAR(6),
        region VARCHAR(50),
        gender VARCHAR(10),
        age_group VARCHAR(10),
        visit_count INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # pm25_fact (PM2.5 농도)
    """
    CREATE TABLE IF NOT EXISTS pm25_fact (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date_id CHAR(6),
        region_name VARCHAR(50),
        pm25 DECIMAL(5,2),
        FOREIGN KEY(date_id) REFERENCES date_dim(date_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
]

# DDL 실행
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
    for ddl in DDL:
        conn.execute(text(ddl))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

# 데이터 로드
age_group_df       = load_data("agegroup_map", section="reference")
date_df_map        = load_data("date_map",     section="reference")
pm10_df            = load_data("pm10_processed_v1",    section="processed")
pm25_df            = load_data("pm25_processed_v1",    section="processed")
pm10_asthma_df     = load_data("pm10_asthma_processed_v1", section="processed")
pm25_asthma_df     = load_data("pm25_asthma_processed_v1", section="processed")
pm10_rhinitis_df   = load_data("pm10_rhinitis_processed_v1", section="processed")
pm25_rhinitis_df   = load_data("pm25_rhinitis_processed_v1", section="processed")

# date_dim 삽입 (date_df_map에는 ['year_month','date_id','year','month','quarter','season'] 포함)
date_df_map["date_id"] = date_df_map["date_id"].astype(str)
with engine.begin() as conn:
    conn.execute(text("DELETE FROM date_dim;"))
# dtype 인자 제거: MySQL이 자동으로 타입을 생성하도록 함
date_df_map.to_sql(
    "date_dim",
    engine,
    if_exists="append",
    index=False
)

# age_group_dim 삽입
age_group_df.columns = ["age_group", "age_range"]
with engine.begin() as conn:
    conn.execute(text("DELETE FROM age_group_dim;"))
age_group_df.to_sql(
    "age_group_dim",
    engine,
    if_exists="append",
    index=False
)

# pm10_fact (wide → long)
pm10_long = pm10_df.melt(
    id_vars="year_month", var_name="region_name", value_name="pm10"
)
pm10_long["date_id"] = pm10_long["year_month"].str.replace("-", "")
pm10_long = pm10_long[["date_id", "region_name", "pm10"]].dropna()
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm10_fact;"))
pm10_long.to_sql(
    "pm10_fact",
    engine,
    if_exists="append",
    index=False
)

# pm25_fact (wide → long)
pm25_long = pm25_df.melt(
    id_vars="year_month", var_name="region_name", value_name="pm25"
)
pm25_long["date_id"] = pm25_long["year_month"].str.replace("-", "")
pm25_long = pm25_long[["date_id", "region_name", "pm25"]].dropna()
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm25_fact;"))
pm25_long.to_sql(
    "pm25_fact",
    engine,
    if_exists="append",
    index=False
)

# pm10_asthma_fact 삽입 (ym: 'YYYYMM' 형식으로 변경)
pm10_asthma_df = pm10_asthma_df.rename(columns={"year_month": "ym"})
pm10_asthma_df["ym"] = pm10_asthma_df["ym"].str.replace("-", "")
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm10_asthma_fact;"))
pm10_asthma_df.to_sql(
    "pm10_asthma_fact",
    engine,
    if_exists="append",
    index=False
)

# pm25_asthma_fact 삽입
pm25_asthma_df = pm25_asthma_df.rename(columns={"year_month": "ym"})
pm25_asthma_df["ym"] = pm25_asthma_df["ym"].str.replace("-", "")
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm25_asthma_fact;"))
pm25_asthma_df.to_sql(
    "pm25_asthma_fact",
    engine,
    if_exists="append",
    index=False
)

# pm10_rhinitis_fact 삽입
pm10_rhinitis_df = pm10_rhinitis_df.rename(columns={"year_month": "ym"})
pm10_rhinitis_df["ym"] = pm10_rhinitis_df["ym"].str.replace("-", "")
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm10_rhinitis_fact;"))
pm10_rhinitis_df.to_sql(
    "pm10_rhinitis_fact",
    engine,
    if_exists="append",
    index=False
)

# pm25_rhinitis_fact 삽입
pm25_rhinitis_df = pm25_rhinitis_df.rename(columns={"year_month": "ym"})
pm25_rhinitis_df["ym"] = pm25_rhinitis_df["ym"].str.replace("-", "")
with engine.begin() as conn:
    conn.execute(text("DELETE FROM pm25_rhinitis_fact;"))
pm25_rhinitis_df.to_sql(
    "pm25_rhinitis_fact",
    engine,
    if_exists="append",
    index=False
)

print("DB 구조 초기화 및 데이터 삽입 완료")