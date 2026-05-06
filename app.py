import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 1. 強制忽略 SSL 憑證警告 (解決您的 SSL 問題)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量對比分析", layout="wide")

def fetch_twse_data(date_obj):
    """抓取證交所資料的後端核心"""
    # 格式必須為 YYYYMMDD (西元)
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date={date_str}&response=json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # verify=False 繞過 SSL 驗證
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # 檢查證交所回傳狀態
        if data.get('stat') == 'OK' and 'data' in data:
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 取得前 15 名
            df = df.head(15).copy()
            # 清洗數據：移除數字中的逗號
            df['成交股數'] = df['成交股數'].str.replace(',', '')
            return df[['排名', '證券代號', '證券名稱', '成交股數']]
        return None
    except:
        return None

# --- UI 介面 ---
st.title("📈 台股成交量 TOP 15 變動對照")
st.info("系統將自動抓取最近兩個有效的交易日資料進行分析")

if st.button("🔄 執行數據比對"):
    found_days = []
    # 從當天往前搜尋最多 20 天，確保能跨越連假
    search_date = datetime.now()
    
    with st.spinner("正在檢索證交所 API..."):
        for i in range(20):
            target_date = search_date - timedelta(days=i)
            # 略過週末
            if target_date.weekday() >= 5:
                continue
                
            df = fetch_twse_data(target_date)
            if df is not None:
                found_days.append({
                    "date": target_date.strftime("%Y-%m-%d"),
                    "data": df
                })
            
            # 找到兩天就停止
            if len(found_days) == 2:
                break
            # 稍微延遲避免頻率過快
            time.sleep(0.5)

    if len(found_days) == 2:
        day1 = found_days[0] # 最近的一天 (例如 05-06)
        day2 = found_days[1] # 前一天 (例如 05-05)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📅 本日 ({day1['date']})")
            st.dataframe(day1['data'], use_container_width=True, hide_index=True)
        with col2:
            st.subheader(f"📅 前日 ({day2['date']})")
            st.dataframe(day2['data'], use_container_width=True, hide_index=True)
            
        # --- 比較邏輯 ---
        st.divider()
        st.subheader("🔍 榜單變動分析")
        
        # 使用證券代號作為唯一識別
        now_codes = set(day1['data']['證券代號'])
        prev_codes = set(day2['data']['證券代號'])
        
        new_in = now_codes - prev_codes
        out_list = prev_codes - now_codes
        
        c1, c2 = st.columns(2)
        with c1:
            st.success("✨ **新進榜名單 (昨日未在前15)**")
            if new_in:
                new_df = day1['data'][day1['data']['證券代號'].isin(new_in)]
                st.table(new_df[['證券代號', '證券名稱']])
            else:
                st.write("名單無變動")
                
        with c2:
            st.warning("📉 **掉出榜名單 (本日跌出前15)**")
            if out_list:
                out_df = day2['data'][day2['data']['證券代號'].isin(out_list)]
                st.table(out_df[['證券代號', '證券名稱']])
            else:
                st.write("無證券掉出榜單")
    else:
        st.error("無法抓取足夠資料。請確認目前是否為交易時間（下午2點後資料較齊全），或請稍後再試。")