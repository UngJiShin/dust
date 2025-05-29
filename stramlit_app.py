# streamlit_app.py

import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from scripts.data_loader import load_data

import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import json
import re

# 한글 폰트 설정
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
asthma_df = load_data('pm10_asthma_processed_v1', section='processed')
pm10_wide  = load_data('pm10_processed_v1', section='processed')


# 2) PM10 월별 평균
pm10_long   = pm10_wide.melt(id_vars='year_month', var_name='region', value_name='pm10')
pm10_monthly_avg = pm10_long.groupby('year_month', as_index=False)['pm10'].mean()

# 3) 지역·월별 진료 건수 합계
visit_monthly = (
    asthma_df
    .groupby(['year_month','region'], as_index=False)['visit_count']
    .sum()
)

# 4) 두 개 합치기
df = visit_monthly.merge(pm10_long, on=['year_month','region'], how='left')

# 5) 지역별 기울기 계산
slopes = {}
for region, sub in df.groupby('region'):
    if len(sub) < 10:
        continue
    m = smf.ols('visit_count ~ pm10', data=sub).fit()
    slopes[region] = m.params['pm10']

slopes_df = pd.DataFrame({
    'region': list(slopes.keys()),
    'coef':   list(slopes.values())
})

# 6) 대시보드 헤더
st.title("PM10 ↔ 천식 진료 건수 대시보드")

# 7) 월별 시계열 차트
ts = (
    visit_monthly
    .groupby('year_month', as_index=False)['visit_count']
    .sum()
    .merge(pm10_monthly_avg, on='year_month')
    .melt('year_month', var_name='지표', value_name='값')
)
fig1 = px.line(ts, x='year_month', y='값', color='지표')
st.subheader("전국 월별 진료 건수 vs PM10")
st.plotly_chart(fig1, use_container_width=True)

# 8) 계절별 산점도
eda_df = asthma_df.merge(
    pd.read_excel(BASE_DIR/'data'/'reference'/'reference_date_mapping.xlsx')
      .assign(date_id=lambda d: d.date_id.astype(str))
      .assign(year_month=lambda d: d.date_id.str[:4]+'-'+d.date_id.str[4:6])
      [['year_month','season']],
    on='year_month', how='left'
)
season = st.selectbox("계절 선택", eda_df['season'].unique())
sub = eda_df[eda_df['season']==season]\
      .groupby('year_month', as_index=False).agg({'visit_count':'sum'})\
      .merge(pm10_monthly_avg, on='year_month')
fig2 = px.scatter(sub, x='pm10', y='visit_count', trendline='ols',
                  labels={'pm10':'PM10','visit_count':'진료 건수'})
st.subheader(f"{season} 계절 산점도 및 회귀선")
st.plotly_chart(fig2, use_container_width=True)

# 9) 지도 기반 시각화
with open(BASE_DIR/'data'/'geo'/'skorea_municipalities_geo.json', encoding='utf-8') as f:
    geo  = json.load(f)

# 2) NAME_2 에서 접미사 제거해 region_base 속성 추가
suffix_pattern = r'(특별자치도|특별자치시|광역시|시|군|구)$'
for feat in geo['features']:
    name = feat['properties']['name']
    base = re.sub(suffix_pattern, '', name)
    feat['properties']['region_base'] = base

# 3) slopes_df 준비 (region 컬럼이 이미 접미사 없는 한글명이라 가정)
slopes_df['region_base'] = slopes_df['region']

# Choropleth 그리기
fig3 = px.choropleth_mapbox(
    slopes_df,
    geojson=geo,
    locations='region_base',            
    featureidkey='properties.region_base',
    color='coef',
    mapbox_style='carto-positron',
    zoom=5,
    center={'lat':37.5, 'lon':127.8},
    color_continuous_scale='Viridis',
    labels={'coef':'기울기(β)'}
)
st.plotly_chart(fig3, use_container_width=True)