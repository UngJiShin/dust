import streamlit as st
import pandas as pd
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from scipy.stats import spearmanr, pearsonr, ttest_rel
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
matplotlib.rcParams['font.family'] = 'Malgun Gothic' #맑은 고딕
matplotlib.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="미세먼지 통합 분석 대시보드", layout="wide")
st.title("🌫️ 미세먼지(PM10, PM2.5) 통합 분석 대시보드")

st.sidebar.header("📁 분석용 파일 업로드")
pm10_file = st.sidebar.file_uploader("PM10 상관계수 파일", type=["xlsx"])
pm25_file = st.sidebar.file_uploader("PM2.5 상관계수 파일", type=["xlsx"])

if pm10_file and pm25_file:

    def load_and_prepare(file, pollutant):
        df = pd.read_excel(file)
        df["구간"] = df["구간"].fillna(method="ffill")
        df["구간숫자"] = df["구간"].str.extract(r"(\d)").astype(int)
        df["성별코드"] = df["성별"].map({"남자": 0, "여자": 1})
        city_cols = df.columns.difference(["구간", "성별", "구간숫자", "성별코드"])
        df["평균상관계수"] = df[city_cols].mean(axis=1)
        df["오염원"] = pollutant
        return df[["구간", "구간숫자", "성별", "성별코드", "평균상관계수", "오염원"]]

    df_pm10 = load_and_prepare(pm10_file, "PM10")
    df_pm25 = load_and_prepare(pm25_file, "PM2.5")
    df = pd.concat([df_pm10, df_pm25], ignore_index=True)

    # [1] 연령별 분석 섹션
    with st.container():
        st.header("👶 연령별 미세먼지 vs 천식 상관관계 분석")

        model = ols("평균상관계수 ~ 구간숫자 + 성별코드 + C(오염원)", data=df).fit()
        st.markdown("#### 📈 다중회귀분석 결과")
        st.text(model.summary())

        st.markdown("#### 🔍 Spearman / Pearson 상관분석")
        for pollutant in ["PM10", "PM2.5"]:
            sub = df[df["오염원"] == pollutant]
            sp_corr, sp_p = spearmanr(sub["구간숫자"], sub["평균상관계수"])
            pe_corr, pe_p = pearsonr(sub["구간숫자"], sub["평균상관계수"])
            st.markdown(f"**{pollutant}**")
            st.write(f"• Spearman: `{sp_corr:.3f}` (p = `{sp_p:.4f}`)")
            st.write(f"• Pearson: `{pe_corr:.3f}` (p = `{pe_p:.4f}`)")

        st.markdown("#### 📋 ANOVA 결과")
        anova_model = ols("평균상관계수 ~ C(구간) + C(오염원)", data=df).fit()
        anova_result = anova_lm(anova_model)
        st.dataframe(anova_result)

        st.markdown("#### 📊 연령구간별 상관계수 시각화")
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="구간", y="평균상관계수", hue="오염원", ax=ax1)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig1)

    # [2] PM2.5 vs PM10 평균 비교 섹션
    with st.container():
        st.header("🌫️ PM2.5가 PM10보다 건강에 더 큰 영향을 주는가?")

        # 정렬 및 평균 계산
        df_pm10 = df_pm10.sort_values(by=["구간", "성별"]).reset_index(drop=True)
        df_pm25 = df_pm25.sort_values(by=["구간", "성별"]).reset_index(drop=True)

        mean_pm10 = df_pm10["평균상관계수"].mean()
        mean_pm25 = df_pm25["평균상관계수"].mean()
        t_stat, p_val = ttest_rel(df_pm25["평균상관계수"], df_pm10["평균상관계수"])

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="PM10 평균 상관계수", value=f"{mean_pm10:.4f}")
            st.metric(label="PM2.5 평균 상관계수", value=f"{mean_pm25:.4f}")
            st.write(f"**쌍체 t-test 결과**: t = `{t_stat:.4f}`, p = `{p_val:.4f}`")
            if p_val < 0.05:
                st.success("✅ PM2.5가 PM10보다 건강에 더 큰 영향을 줍니다. (통계적으로 유의)")
            else:
                st.info("⚠️ 통계적으로 유의한 차이는 없습니다.")

        with col2:
            fig2, ax2 = plt.subplots(figsize=(5, 4))
            sns.barplot(x=["PM10", "PM2.5"], y=[mean_pm10, mean_pm25], palette="pastel", ax=ax2)
            ax2.set_title("PM10 vs PM2.5 평균 상관계수 비교")
            ax2.set_ylabel("평균 상관계수")
            st.pyplot(fig2)

else:
    st.warning("PM10과 PM2.5 상관계수 파일을 모두 업로드해주세요.")
