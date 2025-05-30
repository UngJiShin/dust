# 5번가설.py
# 실행 
# python -m streamlit run src/analysis/5_analysis.py

import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

import pandas as pd
import re
import datetime
from scripts.data_loader import load_data


import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from pathlib import Path
from scripts.data_loader import load_data
import statsmodels.api as sm

# 한글 폰트 설정
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 1) 데이터 준비
@st.cache
def prepare():
    # 천식-PM10 전처리 데이터 로드
    asthma_df = load_data('pm10_asthma_processed_v1', section='processed')
    
    # 날짜 매핑(season 붙이기)
    date_map = load_data('date_map', section='reference')
    date_map['date_id'] = date_map['date_id'].astype(str)
    date_map['year_month'] = date_map['date_id'].str[:4] + '-' + date_map['date_id'].str[4:6]
    season_map = date_map[['year_month','season']].drop_duplicates()
    
    # season 컬럼 병합
    df = asthma_df.merge(season_map, on='year_month', how='left')
    
    # 월별 전국 총 진료 건수 집계
    monthly = (
        df
        .groupby(['year_month','season'], as_index=False)['visit_count']
        .sum()
        .rename(columns={'visit_count':'total_visit_count'})
    )
    
    # PM10 월별 평균 계산
    pm10_wide = load_data('pm10_processed_v1', section='processed')
    pm10_long = pm10_wide.melt(
        id_vars='year_month',
        var_name='region',
        value_name='pm10'
    )
    pm10_avg = (
        pm10_long
        .groupby('year_month', as_index=False)['pm10']
        .mean()
    )
    
    # EDA용 데이터프레임 결합
    eda_df = monthly.merge(pm10_avg, on='year_month', how='left')
    
    # 지역별 PM10-진료 기울기 계산
    #    (지역·월별 진료 합계와 pm10을 병합한 뒤 회귀)
    df2 = (
        asthma_df
        .groupby(['year_month','region'], as_index=False)['visit_count']
        .sum()
        .merge(pm10_long, on=['year_month','region'], how='left')
    )
    slopes = {}
    for region, sub in df2.groupby('region'):
        if len(sub) < 10:
            continue
        model = smf.ols('visit_count ~ pm10', data=sub).fit()
        slopes[region] = model.params['pm10']
    slopes_df = pd.DataFrame({
        'region': list(slopes.keys()),
        'coef':   list(slopes.values())
    })
    
    return eda_df, slopes_df

eda_df, slopes_df = prepare()

st.title("5번 가설 — 계절별 PM10↔천식 진료")

# EDA: 계절별 요약 통계
st.header("계절별 요약 통계")
seasonal_stats = eda_df.groupby('season')[['pm10','total_visit_count']].agg(['mean','std'])
st.dataframe(seasonal_stats)

# EDA: 산점도·회귀
st.header("계절별 산점도 & 회귀선")
for s in eda_df['season'].unique():
    sub = eda_df[eda_df['season']==s]
    fig, ax = plt.subplots()
    ax.scatter(sub['pm10'], sub['total_visit_count'])
    m = smf.ols('total_visit_count~pm10', data=sub).fit()
    x0 = np.linspace(sub['pm10'].min(), sub['pm10'].max(), 100)
    ax.plot(x0, m.params['Intercept']+m.params['pm10']*x0, color='red')
    ax.set_title(f"{s} 계절")
    st.pyplot(fig)

# 모델: Poisson & NB GLM
st.header("Poisson / Negative Binomial GLM 결과")
poisson = smf.glm('total_visit_count~pm10*season', data=eda_df, family=sm.families.Poisson()).fit()
st.text(poisson.summary().as_text())

nb = smf.glm('total_visit_count~pm10*season', data=eda_df, family=sm.families.NegativeBinomial()).fit()
st.text(nb.summary().as_text())

# 지도 시각화
st.header("지역별 PM10 효과 기울기 (β)")
import json, plotly.express as px
with open(BASE/'data'/'geo'/'skorea_municipalities_geo.json','r',encoding='utf-8') as f:
    geo = json.load(f)

# 2) NAME_2 에서 접미사 제거해 region_base 속성 추가
suffix_pattern = r'(특별자치도|특별자치시|광역시|시|군|구)$'
for feat in geo['features']:
    name = feat['properties']['name']
    base = re.sub(suffix_pattern, '', name)
    feat['properties']['region_base'] = base

# 3) slopes_df 준비 (region 컬럼이 이미 접미사 없는 한글명이라 가정)
slopes_df['region_base'] = slopes_df['region']

fig = px.choropleth_mapbox(
    slopes_df, geojson=geo,
    locations='region_base', featureidkey='properties.region_base',
    color='coef', mapbox_style='carto-positron',
    zoom=5, center={'lat':37.5,'lon':127.8}
)
st.plotly_chart(fig, use_container_width=True)