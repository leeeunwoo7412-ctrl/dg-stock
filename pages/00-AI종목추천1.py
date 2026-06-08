import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="AI 주식 대시보드", layout="wide")

st.title("🤖 글로벌 AI(인공지능) 주식 분석 대시보드")
st.markdown("인공지능 생태계를 이끄는 글로벌 핵심 기업들의 주가와 수익률을 실시간으로 비교해보세요.")

# 2. 사이드바: AI 세부 섹션별 종목 프리셋
st.sidebar.header("⚙️ 대시보드 설정")

# AI 관련 핵심 종목 분류
ai_presets = {
    "🇺🇸 미국 AI 반도체 & 하드웨어": {
        "엔비디아 (NVDA)": "NVDA",
        "AMD (AMD)": "AMD",
        "브로드컴 (AVGO)": "AVGO",
        "ASML (ASML)": "ASML"
    },
    "🇺🇸 미국 AI 플랫폼 & 클라우드": {
        "마이크로소프트 (MSFT)": "MSFT",
        "알파벳/구글 (GOOGL)": "GOOGL",
        "아마존 (AMZN)": "AMZN",
        "메타 (META)": "META"
    },
    "🇰🇷 한국 AI 반도체 소부장": {
        "삼성전자 (005930.KS)": "005930.KS",
        "SK하이닉스 (000660.KS)": "000660.KS",
        "한미반도체 (042700.KS)": "042700.KS"
    },
    "🇰🇷 한국 AI 소프트웨어/서비스": {
        "NAVER (035420.KS)": "035420.KS",
        "카카오 (035720.KS)": "035720.KS"
    }
}

selected_tickers = []
st.sidebar.subheader("1. AI 섹터별 종목 선택")

# 각 섹터별로 멀티셀렉트 생성 (기본값으로 몇 개 지정)
for sector, stocks in ai_presets.items():
    # 기본 선택 항목 설정 (엔비디아, 마이크로소프트, SK하이닉스 등)
    default_vals = []
    if "💡 미국 AI 반도체" in sector or "엔비디아" in str(stocks.keys()):
        default_vals = ["엔비디아 (NVDA)"]
    elif "마이크로소프트" in str(stocks.keys()):
        default_vals = ["마이크로소프트 (MSFT)"]
    elif "SK하이닉스" in str(stocks.keys()):
        default_vals = ["SK하이닉스 (000660.KS)"]

    selected_stocks = st.sidebar.multiselect(sector, list(stocks.keys()), default=default_vals)
    for stock in selected_stocks:
        selected_tickers.append(stocks[stock])

# 커스텀 AI 티커 입력
custom_ticker = st.sidebar.text_input("✍️ 기타 AI 종목 직접 입력 (쉼표 구분, 예: PLTR, TSMC)")
if custom_ticker:
    custom_list = [t.strip().upper() for t in custom_ticker.split(",") if t.strip()]
    selected_tickers.extend(custom_list)

# 중복 제거
selected_tickers = list(set(selected_tickers))

# 조회 기간 설정
st.sidebar.subheader("2. 분석 기간 설정")
end_date = datetime.today()
start_date = end_date - timedelta(days=365) # 기본 1년

start_date = st.sidebar.date_input("시작일", start_date)
end_date = st.sidebar.date_input("종료일", end_date)

# 3. 메인 데이터 시각화 로직
if not selected_tickers:
    st.warning("👈 왼쪽 사이드바에서 분석할 AI 종목을 선택해 주세요!")
else:
    @st.cache_data(ttl=3600)
    def load_ai_data(tickers, start, end):
        data = yf.download(tickers, start=start, end=end)
        if 'Close' in data.columns:
            df = data['Close']
        else:
            df = data
        if isinstance(df, pd.Series):
            df = df.to_frame(name=tickers[0])
        return df

    with st.spinner('AI 종목들의 주가 데이터를 가져오는 중...'):
        try:
            df_close = load_ai_data(selected_tickers, start_date, end_date)
            
            if df_close.empty:
                st.error("데이터가 비어있습니다. 선택한 기간이나 티커를 확인해주세요.")
            else:
                # 결측치 보정 (국가간 휴장일 차이 메움)
                df_close = df_close.ffill().bfill()
                
                # 시작일 기준 수익률 계산
                df_return = (df_close / df_close.iloc[0] - 1) * 100

                # 상단 스탯 카드 배치 (현재가 및 수익률 간단 요약)
                st.subheader("📌 종목별 최근 누적 수익률")
                cols = st.columns(len(df_return.columns))
                for idx, ticker in enumerate(df_return.columns):
                    current_return = df_return[ticker].iloc[-1]
                    with cols[idx % len(cols)]:
                        st.metric(label=ticker, value=f"{df_close[ticker].iloc[-1]:,.2f}", delta=f"{current_return:+.2f}%")

                st.markdown("---")

                # 섹션 1: 누적 수익률 비교 차트
                st.subheader("📈 AI 주도주 누적 수익률 비교 (%)")
                fig_return = go.Figure()
                for ticker in df_return.columns:
                    fig_return.add_trace(go.Scatter(
                        x=df_return.index, y=df_return[ticker], 
                        mode='lines', name=str(ticker),
                        hovertemplate=f'{ticker}: %{{y:.2f}}%<extra></extra>'
                    ))
                fig_return.update_layout(
                    xaxis_title="날짜", yaxis_title="수익률 (%)",
                    hovermode="x unified", template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_return, use_container_width=True)

                st.markdown("---")

                # 섹션 2: 상세 데이터 테이블 & 개별 종목 절대 주가 차트
                col1, col2 = st.columns([1, 1.2])
                
                with col1:
                    st.subheader("📋 성과 요약")
                    summary_list = []
                    for ticker in df_close.columns:
                        s_price = df_close[ticker].iloc[0]
                        e_price = df_close[ticker].iloc[-1]
                        t_return = df_return[ticker].iloc[-1]
                        summary_list.append({
                            "AI 종목": ticker,
                            "시작일 주가": f"{s_price:,.2f}",
                            "현재 주가": f"{e_price:,.2f}",
                            "누적 수익률": f"{t_return:+.2f}%"
                        })
                    st.dataframe(pd.DataFrame(summary_list).set_index("AI 종목"), use_container_width=True)

                with col2:
                    st.subheader("🔍 개별 AI 주가 추이")
                    target_stock = st.selectbox("집중 분석할 종목을 선택하세요", df_close.columns)
                    
                    fig_price = go.Figure()
                    fig_price.add_trace(go.Scatter(
                        x=df_close.index, y=df_close[target_stock], 
                        mode='lines', line=dict(color='#00CC96'),
                        hovertemplate=f'{target_stock}: %{{y:,.2f}}<extra></extra>'
                    ))
                    fig_price.update_layout(
                        title=f"{target_stock} 절대 주가 흐름",
                        xaxis_title="날짜", yaxis_title="주가 (통화 기준)",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig_price, use_container_width=True)

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
