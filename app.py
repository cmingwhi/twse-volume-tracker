import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta
import time

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交量對比分析 (Session 版)", layout="wide")

# 建立一個全局 Session 物件，模仿瀏覽器行為保持 Cookie
if 'session' not in st.session_state:
    st.session_state.session = requests.Session()
    st.session_state.session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.twse.com.tw/zh/trading/historical/mi-stock20.html'
    })

def get_data_from_twse(target_date):
    date_str = target_date.strftime("%Y%m%d")
    # 使用官方最新的 API Endpoint
    url = f"https://www.twse.com.tw/exchangeReport/MI_STOCK20?response=json&date={date_str}"
    
    try:
        # 1. 先訪問一次主頁面獲取潛在的 Cookie (針對 307 預防)
        st.session_state.session.get("https://www.twse.com.tw/zh/trading/historical/mi-stock20.html", verify=False, timeout=5)
        
        # 2. 正式請求 API
        response = st.session_state.session.get(url, timeout=10, verify=False, allow_redirects=True)
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
            
        res_json = response.json()
        
        if 'data' in res_json and res_json['data']:
            df = pd.DataFrame(res_json['data'], columns=res_json['fields'])
            df = df.head(15).copy()
            # 數值清洗
            df['成交股數'] = df['成交股數'].apply(lambda x: str(x).replace(',', '')).astype(float)
            return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        else:
            return None, res_json.get('stat', '查無資料')
    except Exception as e:
        return None, f"連線異常: {str(e)}"

# --- UI ---
st.title("📊 台股成交量 TOP 15 變動分析 (穩定版)")

if st.button("🔍 執行最新數據抓取"):
    found_data = []
    search_date = datetime.now()
    
    # 清除 session 嘗試重新獲取 Cookie
    st.session_state.session.cookies.clear()
    
    with st.status("正在建立安全連線並獲取 Cookie...", expanded=True) as status:
        for i in range(10):
            target = search_date - timedelta(days=i)
            if target.weekday() >= 5: continue
            
            date_str = target.strftime('%Y-%m-%d')
            df, msg = get_data_from_twse(target)
            
            if df is not None:
                st.write(f"✅ {date_str} 資料獲取成功")
                found_data.append({"date": date_str, "df": df})
            else:
                st.write(f"⚠️ {date_str} 嘗試失敗 ({msg})")
            
            if len(found_data) == 2:
                status.update(label="數據對比就緒", state="complete", expanded=False)
                break
            time.sleep(3) # 證交所 API 限制極嚴，建議拉長到 3 秒

    if len(found_data) == 2:
        today, prev = found_data[0], found_data[1]
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"📅 本日 ({today['date']})")
            st.dataframe(today['df'], hide_index=True)
        with c2:
            st.subheader(f"📅 前日 ({prev['date']})")
            st.dataframe(prev['df'], hide_index=True)
            
        st.divider()
        st.subheader("💡 榜單變動分析")
        
        now_codes = set(today['df']['證券代號'])
        old_codes = set(prev['df']['df']['證券代號'] if isinstance(prev['df'], dict) else prev['df']['證券代號'])
        
        new_in = now_codes - old_codes
        out_list = old_codes - now_codes
        
        res1, res2 = st.columns(2)
        with res1:
            st.success("🔥 新進榜")
            if new_in:
                st.table(today['df'][today['df']['證券代號'].isin(new_in)][['證券代號', '證券名稱']])
            else: st.write("無新進榜")
        with res2:
            st.error("❄️ 掉出榜")
            if out_list:
                st.table(prev['df'][prev['df']['證券代號'].isin(out_list)][['證券代號', '證券名稱']])
            else: st.write("無掉出榜")
    else:
        st.error("抓取失敗次數過多。這通常是因為證交所偵測到頻繁存取而封鎖了當前 IP。")
        st.info("建議解決方案：\n1. 等待 5-10 分鐘後再試。\n2. 部署到 GitHub + Streamlit Cloud，使用雲端 IP 通常可以繞過本地網路的限制。")