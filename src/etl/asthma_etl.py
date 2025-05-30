import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import re
import datetime
from scripts.data_loader import load_data

"""
천식(asthma) 진료 데이터와 PM10 데이터를 결합하기 위한 ETL 스크립트
- PM10 전처리 결과 파일에서 시도 리스트 추출
- 광역시/특별자치시는 province_name 기준으로 집계
- 나머지 지역은 district_name에서 province 접두사를 뽑아 집계
- 결과를 날짜(year_month) 및 region 순으로 정렬
"""

# PM10,PM25 전처리 결과 파일 로드
pm10_df = load_data('pm10_processed_v1', section='processed')
pm25_df = load_data('pm25_processed_v1', section='processed')

# province 리스트 추출
provinces_10 = [c for c in pm10_df.columns if c != 'year_month']
provinces_25 = [c for c in pm25_df.columns if c != 'year_month']

# 광역시·특별자치시 리스트
metros = [
    '서울특별시','부산광역시','대구광역시','인천광역시',
    '광주광역시','대전광역시','울산광역시','세종특별자치시'
]

# 병원(천식) 원본 데이터 로드
hosp_df = load_data('asthma')

# 컬럼명 영어로 변경
df = hosp_df.rename(columns={
    '요양개시연월':      'year_month',
    '시도명':            'province_name',
    '시군구명':          'district_name',
    '성별':              'gender',
    '연령군':            'age_group',
    '진료에피소드 건수': 'visit_count'
})

def aggregate_by_pollutant(provinces, pollutant):
    # 광역시는 province_name 기준 집계
    metro = (
        df[df['province_name'].isin(metros)]
        .groupby(['year_month','province_name','gender','age_group'],
                 as_index=False)['visit_count']
        .sum()
        .rename(columns={'province_name':'region'})
    )
    # 기타 지역은 district_name에서 prefix 추출
    pattern = r'^(' + '|'.join(map(re.escape, provinces)) + ')'
    other = df[~df['province_name'].isin(metros)].copy()
    other['region'] = other['district_name'].str.extract(pattern, expand=False)
    other = other.dropna(subset=['region'])
    other_agg = (
        other
        .groupby(['year_month','region','gender','age_group'],
                 as_index=False)['visit_count']
        .sum()
    )
    # 합치고 정렬
    result = pd.concat([metro, other_agg], ignore_index=True)
    result = result.sort_values(['year_month','region']).reset_index(drop=True)
    # 저장
    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = f"{pollutant}_asthma_processed_{today}_v1.0.xlsx"
    out_dir = BASE_DIR / 'data' / 'processed'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    result.to_excel(out_path, index=False)
    print(f"Saved {pollutant.upper()}-asthma data to: {out_path}")
    return result

# PM10 기반 집계
aggregate_by_pollutant(provinces_10, 'pm10')
# PM2.5 기반 집계
aggregate_by_pollutant(provinces_25, 'pm25')

