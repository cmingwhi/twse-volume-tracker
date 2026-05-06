import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量對比分析", layout="wide")

def get_data_from_twse(target_date):
    """
    使用證交所最新 API 路徑 (非 RWD 版以避免跳轉問題)
    """
    date_str = target_date.strftime("%Y%m%d")
    # 更新後的 API 終端點
    url = "https://www.twse.com.tw/exchangeReport/MI_STOCK20"
    
    params = {
        'date': date_str,
        'response': 'json',
        '_': str(int(time.time() * 1000)) # 加入隨機時間戳避免快取
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://www.twse.com.tw/zh/trading/historical/mi_stock20.html'
    }

    try:
        # allow_redirects=True 處理 307 跳轉
        response = requests.get(url, params=params, headers=headers, timeout=10, verify=False, allow_redirects=True)
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
            
        res_json = response.json()
        
        # 證交所 API 的回應欄位通常在 'data' 或 'data1'，視日期而定
        if 'data' in res_json and res_json['data']:
            df = pd.DataFrame(res_json['data'], columns=res_json['fields'])
            df = df.head(15).copy()
            # 數值清洗：處理成交股數
            df['成交股數'] = df['成交股數'].apply(lambda x: str(x).replace(',', '')).astype(float)
            return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        else:
            return None, res_json.get('stat', '該日無資料')
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- UI ---
st.title("📊 台股成交量 TOP 15 變動分析")
st.markdown("針對 `HTTP 307` 與 `404` 錯誤已修正 API 路徑。")

if st.button("🔍 執行最新數據抓取"):
    found_data = []
    search_date = datetime.now()
    
    with st.status("連線至證交所資料庫...", expanded=True) as status:
        # 搜尋最近 10 天
        for i in range(10):
            target = search_date - timedelta(days=i)
            if target.weekday() >= 5: continue # 跳過週末
            
            date_str = target.strftime('%Y-%m-%d')
            df, msg = get_data_from_twse(target)
            
            if df is not None:
                st.write(f"✅ {date_str} 資料獲取成功")
                found_data.append({"date": date_str, "df": df})
            else:
                st.write(f"⚠️ {date_str} 略過 ({msg})")
            
            if len(found_data) == 2:
                status.update(label="數據對比就緒", state="complete", expanded=False)
                break
            time.sleep(2) # 延長間隔避免被鎖

    if len(found_data) == 2:
        today = found_data[0]
        prev = found_data[1]
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"📅 本日 ({today['date']})")
            st.dataframe(today['df'], hide_index=True)
        with c2:
            st.subheader(f"📅 前日 ({prev['date']})")
            st.dataframe(prev['df'], hide_index=True)
            
        # 變動分析
        st.divider()
        st.subheader("💡 榜單變動分析")
        
        now_codes = set(today['df']['證券代號'])
        old_codes = set(prev['df']['證券代號'])
        
        new_in = now_codes - old_codes
        out_list = old_codes - now_codes
        
        res1, res2 = st.columns(2)
        with res1:
            st.success("🔥 新進榜")
            if new_in:
                st.table(today['df'][today['df']['證券代號'].isin(new_in)][['證券代號', '證券名稱']])
            else: st.write("無")
        with res2:
            st.error("❄️ 掉出榜")
            if out_list:
                st.table(prev['df'][prev['df']['證券代號'].isin(out_list)][['證券代號', '證券名稱']])
            else: st.write("無")
    else:
        st.error("未能找到足夠的交易日資料，請確認 API 狀態。")