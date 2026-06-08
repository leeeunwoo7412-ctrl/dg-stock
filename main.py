import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="글로벌 주식 분석 대시보드", layout="wide")

st.title("📊 글로벌 주식 수익률 & 차트 비교 분석기")
st.markdown("한국(KOSPI/KOSDAQ) 및 미국 주요 주식의 수익률을 Plotly 동적 차트로 한눈에 비교해 보세요.")

# 2. 사이드바 설정
st.sidebar.header("⚙️ 대시보드 설정")

stock_preset = {
    "미국 주식": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "NVIDIA (NVDA)": "NVDA",
        "Tesla (TSLA)": "TSLA",
        "S&P 500 ETF (SPY)": "SPY"
    },
    "한국 주식": {
        "삼성전자 (005930.KS)": "005930.KS",
        "SK하이닉스 (000660.KS)": "000660.KS",
        "현대차 (005380.KS)": "005380.KS",
        "NAVER (035420.KS)": "035420.KS",
        "KOSPI 200 ETF (102110.KS)": "102110.KS"
    }
}

selected_tickers = []
st.sidebar.subheader("1. 비교할 종목 선택")

us_selected = st.sidebar.multiselect("🇺🇸 미국 주식 선택", list(stock_preset["미국 주식"].keys()), default=["Apple (AAPL)", "NVIDIA (NVDA)"])
for stock in us_selected:
    selected_tickers.append(stock_preset["미국 주식"][stock])

kr_selected = st.sidebar.multiselect("🇰🇷 한국 주식 선택", list(stock_preset["한국 주식"].keys()), default=["삼성전자 (005930.KS)"])
for stock in kr_selected:
    selected_tickers.append(stock_preset["한국 주식"][stock])

custom_ticker = st.sidebar.text_input("✍️ 직접 티커 입력 (쉼표 구분, 예: GOOG, 005490.KS)")
if custom_ticker:
    custom_list = [t.strip().upper() for t in custom_ticker.split(",") if t.strip()]
    selected_tickers.extend(custom_list)

selected_tickers = list(set(selected_tickers))

st.sidebar.subheader("2. 조회 기간 설정")
end_date = datetime.today()
start_date = end_date - timedelta(days=365)

start_date = st.sidebar.date_input("시작일", start_date)
end_date = st.sidebar.date_input("종료일", end_date)

# 3. 메인 데이터 처리 로직
if not selected_tickers:
    st.warning("👈 왼쪽 사이드바에서 분석할 주식 종목을 최소 하나 이상 선택해 주세요!")
else:
    @st.cache_data(ttl=3600)
    def load_data(tickers, start, end):
        # 복수 종목 혹은 단일 종목 다운로드 안정성 확보
        data = yf.download(tickers, start=start, end=end)
        
        # yfinance 다운로드 포맷 대응
        if 'Close' in data.columns:
            df = data['Close']
        else:
            df = data
            
        if isinstance(df, pd.Series):
            df = df.to_frame(name=tickers[0])
        return df

    with st.spinner('야후 파이낸스에서 실시간 주가 데이터를 가져오는 중...'):
        try:
            df_close = load_data(selected_tickers, start_date, end_date)
            
            if df_close.empty:
                st.error("선택한 기간 또는 종목에 대한 데이터가 없습니다. 기간을 다시 설정해 주세요.")
            else:
                # 결측치 보정
                df_close = df_close.ffill().bfill()
                df_return = (df_close / df_close.iloc[0] - 1) * 100

                # -------------------------------------------------------------
                # SECTION 1: 누적 수익률 비교 차트
                # -------------------------------------------------------------
                st.subheader("📈 선택 종목 누적 수익률 비교 (%)")
                st.caption("설정한 '시작일'의 주가를 0% 기준으로 잡고 현재까지의 상대적 변동률을 비교합니다.")
                
                fig_return = go.Figure()
                for ticker in df_return.columns:
                    fig_return.add_trace(go.Scatter(
                        x=df_return.index, 
                        y=df_return[ticker], 
                        mode='lines', 
                        name=str(ticker),
                        hovertemplate=f'{ticker}: %{{y:.2f}}%<extra></extra>'
                    ))
                
                fig_return.update_layout(
                    xaxis_title="날짜", yaxis_title="수익률 (%)",
                    hovermode="x unified", template="plotly_dark",
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_return, use_container_width=True)

                st.markdown("---")

                # -------------------------------------------------------------
                # SECTION 2: 성과 요약 테이블 & 개별 종목 절대 가격 차트
                # -------------------------------------------------------------
                col1, col2 = st.columns([1, 1.5])
                
                with col1:
                    st.subheader("📋 성과 요약 테이블")
                    summary_list = []
                    for ticker in df_close.columns:
                        s_price = df_close[ticker].iloc[0]
                        e_price = df_close[ticker].iloc[-1]
                        t_return = df_return[ticker].iloc[-1]
                        summary_list.append({
                            "종목 티커": ticker,
                            "시작일 종가": f"{s_price:,.2f}",
                            "최종일 종가": f"{e_price:,.2f}",
                            "총 누적 수익률": f"{t_return:+.2f}%"
                        })
                    st.dataframe(pd.DataFrame(summary_list).set_index("종목 티커"), use_container_width=True)

                with col2:
                    st.subheader("🔍 개별 주가 절대 가격 추이")
                    target_stock = st.selectbox("자세히 볼 종목을 선택하세요", df_close.columns)
                    
                    fig_price = go.Figure()
                    fig_price.add_trace(go.Scatter(
                        x=df_close.index, 
                        y=df_close[target_stock], 
                        mode='lines', 
                        line=dict(color='#00CC96'),
                        hovertemplate=f'{target_stock}: %{{y:,.2f}}<extra></extra>'
                    ))
                    fig_price.update_layout(
                        title=f"{target_stock} 절대 주가 흐름 (해당국가 통화 기준)",
                        xaxis_title="날짜", yaxis_title="주가",
                        template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_price, use_container_width=True)

        except Exception as e:
            st.error(f"데이터를 처리하는 중 오류가 발생했습니다: {e}")
