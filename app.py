import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 忽略 SSL 安全性警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量對比工具", layout="wide")

def fetch_twse_data(date_obj):
    """從證交所抓取指定日期的成交量數據"""
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date={date_str}&response=json"
    
    try:
        # 使用 verify=False 並加上 Headers 模擬瀏覽器，減少被阻擋機率
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=15, verify=False, headers=headers)
        
        if response.status_code != 200:
            return None, f"HTTP 錯誤: {response.status_code}"
        
        data = response.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            df = df.head(15).copy()
            # 轉換數值欄位以利後續分析
            df['成交股數'] = df['成交股數'].str.replace(',', '').astype(float)
            return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        
        return None, data.get('stat', '該日非交易日或無資料')
    except Exception as e:
        return None, f"連線異常: {str(e)}"

def find_latest_two_trade_days():
    """搜尋最近兩個有資料的交易日"""
    found_data = []
    # 從當天（或昨天）開始搜尋
    current_date = datetime.now()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 最多搜尋過去 15 天
    search_range = 15
    for i in range(search_range):
        target_date = current_date - timedelta(days=i)
        
        # 進度條更新
        progress = (i + 1) / search_range
        progress_bar.progress(progress)
        status_text.text(f"正在檢查日期: {target_date.strftime('%Y-%m-%d')}...")

        # 週末通常沒資料，直接跳過節省額度
        if target_date.weekday() >= 5:
            continue
            
        df, status = fetch_twse_data(target_date)
        if status == "OK":
            found_data.append((target_date.strftime("%Y-%m-%d"), df))
            # 找到資料後稍微停頓，保護 API
            time.sleep(1.2) 
            
        if len(found_data) == 2:
            break
            
    progress_bar.empty()
    status_text.empty()
    return found_data

# --- 介面設計 ---
st.title("📊 台股成交量 TOP 15 變動對比")

if st.button("🔍 獲取最新對比數據"):
    results = find_latest_two_trade_days()
    
    if len(results) == 2:
        (date_today, df_today), (date_prev, df_prev) = results
        
        # 顯示基礎數據
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"📅 最新交易日：{date_today}")
            st.dataframe(df_today, hide_index=True, use_container_width=True)
        with col2:
            st.info(f"📅 前一交易日：{date_prev}")
            st.dataframe(df_prev, hide_index=True, use_container_width=True)
            
        # --- 異動分析 ---
        st.divider()
        st.subheader("💡 進榜異動分析")
        
        today_codes = set(df_today['證券代號'])
        prev_codes = set(df_prev['證券代號'])
        
        new_in = today_codes - prev_codes
        drop_out = prev_codes - today_codes
        
        ans1, ans2 = st.columns(2)
        with ans1:
            st.write("### 🆕 新進入前15名")
            if new_in:
                st.table(df_today[df_today['證券代號'].isin(new_in)][['證券代號', '證券名稱']])
            else:
                st.write("無新進榜證券")
                
        with ans2:
            st.write("### ❌ 跌出前15名")
            if drop_out:
                st.table(df_prev[df_prev['證券代號'].isin(drop_out)][['證券代號', '證券名稱']])
            else:
                st.write("無證券跌出榜單")
    else:
        st.error(f"❌ 搜尋了過去 15 天仍無法湊齊兩個交易日的資料。")
        st.warning("原因可能是：\n1. 證交所 API 暫時限制您的 IP 訪問（請等待 5 分鐘再試）。\n2. 目前正值長假期間。\n3. 網路連線至證交所不穩定。")

st.sidebar.markdown("### 🛠 系統檢查")
st.sidebar.write(f"最後檢查時間: {datetime.now().strftime('%H:%M:%S')}")