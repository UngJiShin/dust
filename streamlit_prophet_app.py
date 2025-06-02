# 설치 필요: streamlit-plotly-events
# pip install streamlit-plotly-events
# 설치 필요: prophet
# pip install prophet

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from prophet import Prophet
import matplotlib.pyplot as plt
from streamlit_plotly_events import plotly_events
import os, requests

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 페이지 설정
st.set_page_config(page_title="한국 미세먼지 대시보드", layout="wide")

# GeoJSON 다운로드 (없을 경우)
GEO_PATH = 'data/skorea_municipalities_geo.json'
if not os.path.exists(GEO_PATH):
    os.makedirs(os.path.dirname(GEO_PATH), exist_ok=True)
    url = ('https://raw.githubusercontent.com/' 
           'southkorea/southkorea-maps/master/' 
           'kostat/2013/json/skorea_municipalities_geo.json')
    resp = requests.get(url)
    resp.encoding = 'utf-8'
    with open(GEO_PATH, 'w', encoding='utf-8') as f:
        f.write(resp.text)

@st.cache_data
# 데이터 로드 및 전처리
# - PM10: data/raw/env_pm10_raw_20241001.xlsx
# - 천식: data/raw/respdisease_asthma_raw_20231231.xlsx
# 반환: df_pm10_long(date, region, pm10), df_asthma_monthly(date, region, asthma_cases)
def load_data():
    # PM10 원본
    df_pm10_raw = pd.read_excel('data/raw/env_pm10_raw_20241001.xlsx')
    # 날짜 추출 및 datetime 변환
    df_pm10_raw['date'] = pd.to_datetime(
        df_pm10_raw['구분'].str.replace(' 월',''), format='%Y.%m'
    )
    # '구분' 제거 후 long format
    df_pm10_clean = df_pm10_raw.drop(columns=['구분'])
    df_pm10_long = df_pm10_clean.melt(
        id_vars=['date'], var_name='region', value_name='pm10'
    )
    # 숫자형 변환
    df_pm10_long['pm10'] = pd.to_numeric(df_pm10_long['pm10'], errors='coerce')

    # 천식 진료 원본
    df_asthma_raw = pd.read_excel('data/raw/respdisease_asthma_raw_20231231.xlsx')
    df_asthma = df_asthma_raw.rename(columns={
        '요양개시연월':'date', '시군구명':'region', '진료에피소드 건수':'asthma_cases'
    })
    df_asthma['date'] = pd.to_datetime(df_asthma['date'])
    df_asthma_monthly = (
        df_asthma.groupby(['date','region'], as_index=False)
                 ['asthma_cases'].sum()
    )
    return df_pm10_long, df_asthma_monthly

@st.cache_data
# GeoJSON 로드
def load_geojson():
    with open(GEO_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# 데이터 준비
df_pm10, df_asthma = load_data()
geojson = load_geojson()

# 사이드바: 연도 선택
years = sorted(df_pm10['date'].dt.year.unique())
year = st.sidebar.select_slider('연도 선택', options=years, value=years[-1])

# 선택 연도 평균 PM10 계산
pm10_year = (
    df_pm10[df_pm10['date'].dt.year == year]
          .groupby('region', as_index=False)['pm10'].mean()
)

# Choropleth 지도
fig_map = px.choropleth_mapbox(
    pm10_year,
    geojson=geojson,
    locations='region',
    featureidkey='properties.adm_nm',
    color='pm10',
    color_continuous_scale='YlOrRd',
    mapbox_style='carto-positron',
    zoom=6,
    center={'lat':36.5,'lon':127.8},
    opacity=0.6,
    labels={'pm10':'평균 PM10'}
)
fig_map.update_layout(margin={'r':0,'t':0,'l':0,'b':0})

st.title(f"한국 {year}년 지역별 평균 미세먼지(PM10)")
st.write("지도에서 지역 클릭 또는 사이드바에서 선택하세요.")
st.plotly_chart(fig_map, use_container_width=True)

# 지도 클릭/드롭다운으로 지역 선택
sel = plotly_events(fig_map, click_event=True, hover_event=False)
if sel:
    region = sel[0]['location']
else:
    region = st.sidebar.selectbox('지역 선택', sorted(df_pm10['region'].unique()))
st.sidebar.markdown(f"**선택된 지역:** {region}")

# 선택 지역 데이터
df_r_pm10 = df_pm10[df_pm10['region']==region].sort_values('date')
df_r_asthma = df_asthma[df_asthma['region']==region].sort_values('date')

# Prophet 학습
@st.cache_resource
def train_prophet(df):
    m = Prophet(interval_width=0.95)
    m.add_regressor('asthma_cases')
    m.fit(df)
    return m

# merge 및 예측
df_merge = pd.merge(
    df_r_pm10.rename(columns={'date':'ds','pm10':'y'}),
    df_r_asthma.rename(columns={'date':'ds','asthma_cases':'asthma_cases'}),
    on='ds', how='inner'
)
model = train_prophet(df_merge)
future = model.make_future_dataframe(periods=12, freq='M')
# 외부변수 채우기
last = df_merge['asthma_cases'].iloc[-1]
future['asthma_cases'] = last
forecast = model.predict(future)

# 시계열 플롯 및 테이블
st.subheader(f"{region} PM10 예측 (향후 12개월)")
fig_ts = model.plot(forecast)
st.pyplot(fig_ts)

st.subheader("예측 결과 (95% 신뢰구간)")
res = forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(12)
res = res.rename(columns={'ds':'날짜','yhat':'예측값','yhat_lower':'하한','yhat_upper':'상한'})
st.dataframe(res.set_index('날짜'))
