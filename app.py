import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 1. 忽略 SSL 安全性警告 (解決您遇到的 SSL 錯誤)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量前15大對比", layout="wide")

# --- 資料抓取函式 ---
def fetch_twse_data(date_obj):
    """從證交所抓取指定日期的成交量數據"""
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date={date_str}&response=json"
    
    try:
        # verify=False 繞過憑證檢查
        response = requests.get(url, timeout=15, verify=False)
        if response.status_code != 200:
            return None, "連線失敗"
        
        data = response.json()
        if data.get('stat') == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 整理欄位：只取前15名，並轉化成交張數為整數
            df = df.head(15).copy()
            df['成交股數'] = df['成交股數'].str.replace(',', '').astype(int)
            # 建立簡單的顯示清單
            return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        return None, data.get('stat', '無資料')
    except Exception as e:
        return None, str(e)

def find_latest_two_trade_days():
    """自動尋找最近兩個有資料的交易日"""
    found_data = []
    current_date = datetime.now()
    
    # 最多往前回溯 10 天，直到找到兩天份的資料
    for i in range(10):
        target_date = current_date - timedelta(days=i)
        # 跳過週末提高效率
        if target_date.weekday() >= 5: 
            continue
            
        df, status = fetch_twse_data(target_date)
        if status == "OK":
            found_data.append((target_date.strftime("%Y-%m-%d"), df))
            time.sleep(0.5) # 稍微停頓避免被封鎖
            
        if len(found_data) == 2:
            break
    return found_data

# --- 網頁介面 ---
st.title("📊 台股成交量 TOP 15 對比工具")
st.caption("自動抓取證交所最新兩個交易日之成交量前 15 名進行比較")

if st.button("🚀 開始分析最新數據"):
    with st.spinner("正在向證交所請求資料中..."):
        results = find_latest_two_trade_days()
        
    if len(results) == 2:
        date_today, df_today = results[0]
        date_prev, df_prev = results[1]
        
        # 佈局顯示
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"📅 本日交易日：{date_today}")
            st.table(df_today[['排名', '證券代號', '證券名稱']])
            
        with col2:
            st.info(f"📅 前一交易日：{date_prev}")
            st.table(df_prev[['排名', '證券代號', '證券名稱']])
            
        # --- 分析邏輯 ---
        st.divider()
        st.subheader("💡 異動分析")
        
        today_list = df_today['證券代號'].tolist()
        prev_list = df_prev['證券代號'].tolist()
        
        # 新進榜名單
        new_in = [code for code in today_list if code not in prev_list]
        # 掉出榜名單
        drop_out = [code for code in prev_list if code not in today_list]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔥 新進榜證券")
            if new_in:
                new_df = df_today[df_today['證券代號'].isin(new_in)]
                st.dataframe(new_df[['證券代號', '證券名稱']], hide_index=True)
            else:
                st.write("名單與昨日相同")
                
        with c2:
            st.markdown("#### 🧊 掉出榜證券")
            if drop_out:
                drop_df = df_prev[df_prev['證券代號'].isin(drop_out)]
                st.dataframe(drop_df[['證券代號', '證券名稱']], hide_index=True)
            else:
                st.write("無證券掉出榜單")
    else:
        st.error("無法取得足夠的交易日資料，請稍後再試。")

st.sidebar.info("""
**使用說明：**
1. 點擊「開始分析」按鈕。
2. 程式會自動過濾週末，抓取證交所最新兩天的資料。
3. 若發生 SSL 錯誤，程式已自動忽略驗證。
""")