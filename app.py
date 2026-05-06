import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量前15大比對", layout="wide")

def get_data_from_twse(target_date):
    """
    精準抓取證交所資料
    API 範例: https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date=20260506&response=json
    """
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20"
    params = {
        'date': date_str,
        'response': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 使用 params 傳遞參數比直接拼湊字串更穩定
        response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
            
        res_json = response.json()
        
        if res_json.get('stat') == 'OK' and 'data' in res_json:
            raw_data = res_json['data']
            fields = res_json['fields']
            df = pd.DataFrame(raw_data, columns=fields)
            
            # 確保欄位正確，並取前 15 名
            df = df.head(15).copy()
            # 數值清洗
            df['成交股數'] = df['成交股數'].apply(lambda x: str(x).replace(',', '')).astype(float)
            return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        else:
            return None, res_json.get('stat', '無資料')
    except Exception as e:
        return None, str(e)

# --- 網頁前端 ---
st.title("📈 台股成交量 TOP 15 每日變動比對")

if st.button("🚀 抓取並分析最新數據"):
    found_data = []
    # 從今天開始往前找，範圍擴大到 30 天以防長假
    check_date = datetime.now()
    
    with st.status("正在連線證交所伺服器...", expanded=True) as status:
        for i in range(30):
            current_target = check_date - timedelta(days=i)
            
            # 排除週末 (週六為 5, 週日為 6)
            if current_target.weekday() >= 5:
                continue
                
            df, msg = get_data_from_twse(current_target)
            
            date_display = current_target.strftime('%Y-%m-%d')
            if df is not None:
                st.write(f"✅ {date_display} 抓取成功")
                found_data.append({"date": date_display, "df": df})
            else:
                st.write(f"❌ {date_display} 無法讀取 ({msg})")
            
            if len(found_data) == 2:
                status.update(label="數據獲取完成！", state="complete", expanded=False)
                break
                
            # 關鍵：每次請求間隔 1.5 秒，避免被證交所防護機制阻擋
            time.sleep(1.5)

    if len(found_data) == 2:
        # 準備對比數據
        today = found_data[0]
        yesterday = found_data[1]
        
        # 顯示表格
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"📅 本日榜單 ({today['date']})")
            st.dataframe(today['df'], use_container_width=True, hide_index=True)
        with c2:
            st.subheader(f"📅 前日榜單 ({yesterday['date']})")
            st.dataframe(yesterday['df'], use_container_width=True, hide_index=True)
            
        # --- 變動邏輯計算 ---
        st.divider()
        st.subheader("💡 榜單席位變動")
        
        t15_set = set(today['df']['證券代號'])
        y15_set = set(yesterday['df']['證券代號'])
        
        new_in = t15_set - y15_set
        out_list = y15_set - t15_set
        
        diff_col1, diff_col2 = st.columns(2)
        with diff_col1:
            st.success("🔥 **新進入前 15 名**")
            if new_in:
                new_df = today['df'][today['df']['證券代號'].isin(new_in)]
                st.table(new_df[['證券代號', '證券名稱']])
            else:
                st.write("名單維持不變")
                
        with diff_col2:
            st.error("❄️ **掉出前 15 名**")
            if out_list:
                out_df = yesterday['df'][yesterday['df']['證券代號'].isin(out_list)]
                st.table(out_df[['證券代號', '證券名稱']])
            else:
                st.write("無證券掉出榜單")
    else:
        st.error("抱歉，即便在晚上 10 點也無法抓齊兩天資料。")
        st.info("請檢查您的網路是否能正常開啟：[證交所 API 測試連結](https://www.twse.com.tw/rwd/zh/trading/historical/mi_stock20?date=20260506&response=json)")