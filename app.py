import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import io

st.set_page_config(page_title="台股成交量對比分析", layout="wide")

def get_data_via_pandas(target_date):
    """
    直接模擬瀏覽器請求並由 Pandas 解析網頁 HTML 表格
    這種方法比直接請求 JSON 更容易繞過 307 挑戰
    """
    date_str = target_date.strftime("%Y%m%d")
    # 使用網頁版 URL
    url = f"https://www.twse.com.tw/zh/trading/historical/mi-stock20.html?date={date_str}&response=html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            # 使用 Pandas 讀取 HTML 中的表格
            tables = pd.read_html(io.StringIO(response.text))
            if tables:
                df = tables[0]
                # 證交所表格通常有層級標題，我們重新整理
                df.columns = [
                    '排名', '證券代號', '證券名稱', '成交股數', '成交筆數', 
                    '開盤價', '最高價', '最低價', '收盤價', '漲跌', '漲跌價差', 
                    '最後揭示買價', '最後揭示賣價'
                ]
                df = df.head(15).copy()
                # 數值清理
                df['成交股數'] = df['成交股數'].astype(str).str.replace(',', '').astype(float)
                return df[['排名', '證券代號', '證券名稱', '成交股數']], "OK"
        return None, f"HTTP {response.status_code}"
    except Exception as e:
        return None, str(e)

# --- 介面 ---
st.title("🚀 台股成交量 TOP 15 專業對比")
st.warning("若持續出現 307 錯誤，請靜置 10 分鐘再試，或嘗試部署至 GitHub 利用雲端 IP 抓取。")

if st.button("📊 執行深度抓取"):
    found_data = []
    search_date = datetime.now()
    
    with st.status("發起模擬連線...", expanded=True) as status:
        for i in range(12):
            target = search_date - timedelta(days=i)
            if target.weekday() >= 5: continue
            
            date_label = target.strftime('%Y-%m-%d')
            df, msg = get_data_via_pandas(target)
            
            if df is not None:
                st.write(f"✅ {date_label} 成功取得數據")
                found_data.append({"date": date_label, "df": df})
            else:
                st.write(f"⚠️ {date_label} 跳過 ({msg})")
            
            if len(found_data) == 2:
                status.update(label="分析完成", state="complete", expanded=False)
                break
            time.sleep(5) # 延長冷卻時間至 5 秒，避免 IP 被鎖

    if len(found_data) == 2:
        d1, d2 = found_data[0], found_data[1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📅 本日 {d1['date']}")
            st.dataframe(d1['df'], hide_index=True)
        with col2:
            st.subheader(f"📅 前日 {d2['date']}")
            st.dataframe(d2['df'], hide_index=True)

        # 比對邏輯
        st.divider()
        now_codes = set(d1['df']['證券代號'])
        old_codes = set(d2['df']['證券代號'])
        
        new_in = now_codes - old_codes
        out_list = old_codes - now_codes
        
        r1, r2 = st.columns(2)
        with r1:
            st.success("✨ **新進榜單**")
            if new_in:
                st.table(d1['df'][d1['df']['證券代號'].isin(new_in)][['證券代號', '證券名稱']])
        with r2:
            st.error("📉 **跌出榜單**")
            if out_list:
                st.table(d2['df'][d2['df']['證券代號'].isin(out_list)][['證券代號', '證券名稱']])
    else:
        st.error("連線受阻，無法獲取足夠資料。")