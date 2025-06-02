import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
from sklearn.linear_model import LinearRegression

# ----------------------------------------
# 1) 페이지 설정: 가장 최상단에 딱 한 번만 호출해야 합니다.
# ----------------------------------------
st.set_page_config(
    page_title="환자 수 예측 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------
# 2) 다크 테마용 CSS 적용 (글씨 흰색, 배경 어둡게)
# ----------------------------------------
st.markdown(
    """
    <style>
    /* 전체 배경, 컨테이너 어둡게 */
    .reportview-container, .main, .block-container {
        background-color: #121212;
        color: #EEEEEE;
    }
    /* 사이드바 어둡게 */
    .sidebar .sidebar-content {
        background-color: #1F1F1F;
        color: #EEEEEE;
    }
    /* 제목(H1) 흰색 */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF;
    }
    /* Plotly 차트 배경을 투명으로 만들어, 뒤 배경이 보이도록 */
    .plotly-graph-div .main-svg {
        background-color: rgba(0,0,0,0) !important;
    }
    /* Markdown 텍스트 흰색으로 */
    .stMarkdown p {
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------
# 3) 데이터 생성 함수 (월별 환자 수가 100명대 스케일)
# ----------------------------------------
@st.cache_data
def generate_data():
    np.random.seed(42)
    months = pd.date_range("2023-06-01", periods=12, freq="M")
    regions = ["서울", "부산", "대구", "광주", "대전", "울산"]
    data = []
    for region in regions:
        for month in months:
            # PM/온도/의료인력 등 랜덤 생성
            pm10 = np.random.randint(10, 80)      # 10~79
            pm25 = np.random.randint(5, 50)       # 5~49
            temp = np.random.uniform(0, 25)       # 0~25도
            nurses = np.random.randint(30, 100)   # 30~99명
            doctors = np.random.randint(15, 60)   # 15~59명
            beds_total = np.random.randint(200, 400)  # 전체 병상 200~399
            # 환자 수: PM*1.5 + PM2.5*2 + (25-temp)*2 + 노이즈
            patients = int(pm10 * 1.5 + pm25 * 2 + (25 - temp) * 2 + np.random.normal(0, 10))
            patients = max(patients, 0)  # 음수 방지
            # 남은 병상 = 전체 - 사용(=랜덤으로 50~100명 차감)
            used_beds = np.random.randint(50, 100)
            beds_left = max(beds_total - used_beds, 0)
            fatigue = np.random.randint(30, 80)  # 피로도 30~79
            data.append({
                "지역": region,
                "월": month.strftime("%Y-%m"),
                "date": month,
                "PM10": pm10,
                "PM2.5": pm25,
                "평균기온": round(temp, 1),
                "환자 수": patients,
                "총 병상 수": beds_total,
                "남은 병상 수": beds_left,
                "간호사 수": nurses,
                "의사 수": doctors,
                "의료진 피로도": fatigue
            })
    return pd.DataFrame(data)

df = generate_data()

# ----------------------------------------
# 4) 사이드바: 연도, 지역, 예측용 슬라이더
# ----------------------------------------
st.sidebar.header("조건 선택")
years = sorted(df["월"].str[:4].unique())
selected_year = st.sidebar.selectbox("년도 선택", years, index=0)
selected_region = st.sidebar.selectbox("지역 선택", sorted(df["지역"].unique()), index=0)

# 예측 입력값(슬라이더)
input_pm10 = st.sidebar.slider("예상 PM10", min_value=0, max_value=150, value=50)
input_pm25 = st.sidebar.slider("예상 PM2.5", min_value=0, max_value=80, value=30)
input_temp = st.sidebar.slider("예상 평균기온(°C)", min_value=-5.0, max_value=35.0, value=18.0)

# ----------------------------------------
# 5) 제목: 선택된 지역을 중앙 정렬, 흰 글씨 처리
# ----------------------------------------
st.markdown(
    f"<h1 style='text-align:center;'>지역별 환자 수 예측 대시보드 [{selected_region}]</h1>",
    unsafe_allow_html=True
)

# ----------------------------------------
# 6) 해당 연도·지역 데이터만 필터링 & 선형회귀 모델로 예측
# ----------------------------------------
region_df = df[
    (df["지역"] == selected_region) &
    (df["월"].str.startswith(selected_year))
].reset_index(drop=True)

# X, y 세팅
X = region_df[["PM10", "PM2.5", "평균기온"]]
y = region_df["환자 수"]
lr_model = LinearRegression().fit(X, y)
predicted_base = int(lr_model.predict([[input_pm10, input_pm25, input_temp]])[0])

# “가장 최근 월” 복사해서, 슬라이더 입력값으로 교체 + 예측값 대입
latest = region_df.iloc[-1].copy()
latest["PM10"] = input_pm10
latest["PM2.5"] = input_pm25
latest["평균기온"] = input_temp
latest["환자 수"] = predicted_base
# 남은 병상 수도 “예측치 기준으로 간이 보정”
latest_used = (latest["총 병상 수"] - latest["남은 병상 수"])  # 실제 사용 중인 병상
# 예측 후 사용 병상을 +5% 정도로 늘린다고 가정
predicted_used = int(latest_used * 1.05)
predicted_used = min(predicted_used, latest["총 병상 수"])
latest["남은 병상 수"] = latest["총 병상 수"] - predicted_used

# 예측값만 붙여 놓을 새로운 DF (실측 데이터 뒤에 한 행 추가)
pred_row = latest[["지역","월","date","PM10","PM2.5","평균기온","환자 수",
                   "총 병상 수","남은 병상 수","간호사 수","의사 수","의료진 피로도"]]
region_with_pred = pd.concat([region_df, pd.DataFrame([pred_row])], ignore_index=True)

# ----------------------------------------
# 7) 상단 레이아웃: 왼쪽(생략) / 중앙(월별 환자 추이+예측) / 오른쪽(병상·의료진 현황)
# ----------------------------------------
col1, col2, col3 = st.columns([1, 2, 1])

# (■ 왼쪽: 공기질·날씨 부분 필요 시 삽입)

# ■ 중앙: “월별 환자 수 실측(파란 실선) + 예측(노란 점선)” ■
with col2:
    st.markdown("<h4 style='color:white;'>월별 환자 수 추이 & 예측</h4>", unsafe_allow_html=True)

    # (1) 실측치만 파란 실선
    actual_fig = px.line(
        region_df,
        x="월", y="환자 수",
        labels={"환자 수": "환자 수"},
        line_shape="linear"
    )
    actual_fig.update_traces(
        line=dict(color="#1E90FF", width=3),
        marker=dict(size=6, color="#1E90FF"),
        showlegend=False
    )

    # (2) 예측선: 마지막 실측 월 → 한 달 뒤 예측 점선을 노란으로
    last_month = region_df["월"].iloc[-1]  # 예: "2023-12"
    base_date = pd.to_datetime(last_month + "-01")
    next_month = (base_date + pd.DateOffset(months=1)).strftime("%Y-%m")  # 예: "2024-01"
    pred_df = pd.DataFrame({
        "월": [last_month, next_month],
        "환자 수": [region_df["환자 수"].iloc[-1], predicted_base]
    })
    pred_fig = px.line(
        pred_df,
        x="월", y="환자 수",
        line_shape="linear"
    )
    pred_fig.update_traces(
        line=dict(color="#FFD700", dash="dash", width=2),
        marker=dict(size=6, color="#FFD700"),
        showlegend=False
    )

    # (3) 두 Figure 데이터를 합쳐 하나로 보여주기
    combined_fig = px.line()
    combined_fig.add_traces(actual_fig.data + pred_fig.data)

    # (4) “현재” 레이블(마지막 실측 월 바로 위)
    combined_fig.add_annotation(
        x=last_month,
        y=region_df["환자 수"].iloc[-1],
        text="현재",
        showarrow=True,
        arrowhead=2,
        ay=-12,
        font=dict(color="white", size=12)
    )
    # (5) “예측” 레이블(다음 달 점 바로 위)
    combined_fig.add_annotation(
        x=next_month,
        y=predicted_base,
        text=f"{predicted_base:,}명",
        showarrow=True,
        arrowhead=2,
        ay=-12,
        font=dict(color="#FFD700", size=12)
    )

    # (6) 다크 모드 맞춤 레이아웃
    combined_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis=dict(showgrid=False, tickfont=dict(color="white")),
        yaxis=dict(showgrid=True, gridcolor="gray", tickfont=dict(color="white")),
        margin=dict(t=20, b=20, l=20, r=20)
    )

    st.plotly_chart(combined_fig, use_container_width=True, height=320)

# ■ 오른쪽: 병상 & 의료진 현황 (센터 정렬)
with col3:
    st.markdown("<h4 style='color:white;'>병상 & 의료진 현황</h4>", unsafe_allow_html=True)

    # 현재 사용 병상 = 총 병상 - 남은 병상, 다음 달 예측 사용 병상 = 총 병상 - 남은 병상(예측)
    current_used = int(latest["총 병상 수"] - region_df["남은 병상 수"].iloc[-1])
    predicted_used = int(latest["총 병상 수"] - latest["남은 병상 수"])

    # “현재” 병상 사용, “다음 달” 예측 병상 사용을 각각 색상 구분
    current_color = "#00FF7F"   # 연두색
    pred_color = "#FF4136"      # 빨간

    # 각 수치 출력
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#2E2E2E; padding:12px; border-radius:8px; margin-bottom:8px;'>"
        f"<span style='font-size:16px; color:white;'>현재 사용 병상</span><br>"
        f"<span style='font-size:28px; color:{current_color};'>{current_used:,}</span>"
        f"<span style='font-size:14px; color:#BBBBBB;'> / {latest['총 병상 수']:,}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='background:#2E2E2E; padding:12px; border-radius:8px;'>"
        f"<span style='font-size:16px; color:white;'>다음 달 예측 병상</span><br>"
        f"<span style='font-size:28px; color:{pred_color};'>{predicted_used:,}</span>"
        f"<span style='font-size:14px; color:#BBBBBB;'> / {latest['총 병상 수']:,}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# 상단 부분 끝
st.markdown("<hr style='border:1px solid gray;'>", unsafe_allow_html=True)

# ----------------------------------------
# 8) 하단: 의료진 피로도 버블맵 + 호흡기 질환 상태(탭)
# ----------------------------------------
col4, col5 = st.columns([1, 1])

# ■ 좌측(Col4): 의료진 피로도 버블맵
with col4:
    st.markdown("<h4 style='color:white;'>의료진 피로도 버블 맵</h4>", unsafe_allow_html=True)

    bubble_df = (
        df[df["월"].str.startswith(selected_year)]
        .groupby("지역")["의료진 피로도"]
        .mean()
        .reset_index()
    )
    # 대략적인 위도/경도 매핑
    coords = {
        "서울": (37.57, 126.98),
        "부산": (35.18, 129.07),
        "대구": (35.87, 128.60),
        "광주": (35.16, 126.85),
        "대전": (36.35, 127.38),
        "울산": (35.54, 129.31)
    }
    bubble_df["lat"] = bubble_df["지역"].map(lambda x: coords[x][0])
    bubble_df["lon"] = bubble_df["지역"].map(lambda x: coords[x][1])

    fig_bubble = px.scatter_mapbox(
        bubble_df,
        lat="lat", lon="lon",
        size="의료진 피로도",
        color="의료진 피로도",
        color_continuous_scale="OrRd",
        size_max=40,
        zoom=5.5,
        mapbox_style="carto-positron",
        hover_name="지역",
        title=""  # 제목은 위에서 처리했으므로 빈 문자열
    )
    fig_bubble.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        margin=dict(t=0, b=0, l=0, r=0),
        mapbox=dict(
            bearing=0,
            pitch=0,
            style="carto-positron",
            center=dict(lat=36.5, lon=127.8),
            zoom=5.5
        )
    )
    st.plotly_chart(fig_bubble, use_container_width=True, height=350)

# ■ 우측(Col5): 호흡기 환자 질환 상태 + 연령·진단·중증도별 탭
with col5:
    st.markdown("<h4 style='color:white;'>호흡기 환자 질환 상태</h4>", unsafe_allow_html=True)
    tabs = st.tabs(["연령대별", "진단별", "중증도별"])

    # 예시용 랜덤 데이터 세팅 (필요 시 실제 DB/CSV에서 가져오세요)
    age_groups = ["0-9세", "10-19세", "20-39세", "40-59세", "60세 이상"]
    diagnoses = ["천식", "폐렴", "COPD"]
    severities = ["경증", "중등도", "중증"]

    # 탭1: 연령대별 환자 수 막대차트
    with tabs[0]:
        st.markdown("**연령대별 환자 수**", unsafe_allow_html=True)
        age_counts = [np.random.randint(3, 30) for _ in age_groups]
        df_age = pd.DataFrame({"연령대": age_groups, "환자 수": age_counts})
        fig_age = px.bar(
            df_age,
            x="연령대", y="환자 수",
            color="연령대",
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        fig_age.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(tickfont=dict(color="white")),
            yaxis=dict(tickfont=dict(color="white"))
        )
        st.plotly_chart(fig_age, use_container_width=True, height=250)

    # 탭2: 진단별 환자 수 파이차트
    with tabs[1]:
        st.markdown("**진단별 환자 수**", unsafe_allow_html=True)
        diag_counts = [np.random.randint(5, 40) for _ in diagnoses]
        df_diag = pd.DataFrame({"진단": diagnoses, "환자 수": diag_counts})
        fig_diag = px.pie(
            df_diag,
            names="진단", values="환자 수",
            color_discrete_sequence=px.colors.sequential.Plasma_r
        )
        fig_diag.update_traces(textposition="inside", textinfo="percent+label")
        fig_diag.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white"
        )
        st.plotly_chart(fig_diag, use_container_width=True, height=250)

    # 탭3: 중증도별 환자 수 막대차트
    with tabs[2]:
        st.markdown("**중증도별 환자 수**", unsafe_allow_html=True)
        sev_counts = [np.random.randint(1, 25) for _ in severities]
        df_sev = pd.DataFrame({"중증도": severities, "환자 수": sev_counts})
        fig_sev = px.bar(
            df_sev,
            x="중증도", y="환자 수",
            color="중증도",
            color_discrete_sequence=["#2ECC40", "#FF851B", "#FF4136"]
        )
        fig_sev.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(tickfont=dict(color="white")),
            yaxis=dict(tickfont=dict(color="white"))
        )
        st.plotly_chart(fig_sev, use_container_width=True, height=250)

# 맨 아래에는 더 보여줄 내용이 없으므로 여백 남겨 놓습니다.
st.markdown("", unsafe_allow_html=True)