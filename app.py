import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="台股成交量前15大對比工具", layout="wide")

def fetch_twse_data(date_str):
    """從證交所抓取特定日期的成交量前20名數據"""
    url = f"https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date={date_str}&response=json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['stat'] == 'OK':
            # 欄位通常包含：排名、證券代號、證券名稱、成交張數等
            df = pd.DataFrame(data['data'], columns=data['fields'])
            df = df.head(15)  # 僅取前15名
            return df[['排名', '證券代號', '證券名稱', '成交股數']]
        return None
    except Exception as e:
        st.error(f"抓取日期 {date_str} 時發生錯誤: {e}")
        return None

def get_last_two_trade_days():
    """獲取最近兩個交易日（簡化版，實際需考慮國定假日）"""
    today = datetime.now()
    dates = []
    current = today
    while len(dates) < 2:
        # 排除週六(5)、週日(6)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y%m%d"))
        current -= timedelta(days=1)
    return dates[0], dates[1]

# --- 網頁介面 ---
st.title("📊 台股成交量前 15 大證券對比")
today_str, yesterday_str = get_last_two_trade_days()

if st.button("更新數據"):
    df_today = fetch_twse_data(today_str)
    df_prev = fetch_twse_data(yesterday_str)

    if df_today is not None and df_prev is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"📅 本日 ({today_str})")
            st.dataframe(df_today, use_container_width=True)

        with col2:
            st.subheader(f"📅 前一交易日 ({yesterday_str})")
            st.dataframe(df_prev, use_container_width=True)

        # --- 對比邏輯 ---
        st.divider()
        st.subheader("🔍 變動分析")
        
        today_set = set(df_today['證券代號'])
        prev_set = set(df_prev['證券代號'])
        
        new_entries = today_set - prev_set
        stay_entries = today_set & prev_set

        c1, c2 = st.columns(2)
        with c1:
            st.success(f"✨ 新進榜 (共 {len(new_entries)} 檔)")
            st.write(df_today[df_today['證券代號'].isin(new_entries)][['證券代號', '證券名稱']])
            
        with c2:
            st.info("🔄 持續留榜")
            st.write(df_today[df_today['證券代號'].isin(stay_entries)][['證券代號', '證券名稱']])
    else:
        st.warning("無法取得資料，可能今日尚未收盤或非交易日。")