import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date

# 設定頁面標題與品牌圖示
st.set_page_config(page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP® (體驗版)", page_icon="🏛️", layout="wide")

# 徹底隱藏右下角所有 Streamlit 官方浮動標誌與裝飾按鈕
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton { visibility: hidden !important; display: none !important; }
    div[data-testid="stToolbar"], div[data-testid="manage-app-button"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yG6_ { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
MAX_DEMO_POLICIES = 3  # 體驗版保單筆數限制

# 初始化資料庫 (確保結構)
def get_conn(): return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, birth_date TEXT, phone TEXT, family_id TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT, policy_no TEXT, policy_name TEXT, policy_type TEXT, is_main TEXT DEFAULT '👑 主約', pay_years INTEGER, pay_frequency TEXT, max_renew_age INTEGER, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, FOREIGN KEY (client_id) REFERENCES clients (client_id))")
        c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT DEFAULT '萬元', outpatient_limit REAL, FOREIGN KEY (policy_id) REFERENCES policies (policy_id))")
        conn.commit()

init_db()

def get_total_policy_count():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM policies")
        return c.fetchone()[0]

# 側邊欄設計 (含體驗版計數器)
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px 14px; border-radius: 12px; text-align: center;">
            <div style="color: #F8FAFC; font-weight: 700;">🏛️ 澄璞財務顧問工作室</div>
            <div style="color: #F59E0B; font-size: 0.8rem;">體驗版 (上限 3 筆)</div>
        </div>
    """, unsafe_allow_html=True)
    
    count = get_total_policy_count()
    st.info(f"📋 目前建檔保單：{count} / {MAX_DEMO_POLICIES}")
    
    if count > 0 and st.button("🔄 清空體驗資料"):
        with get_conn() as conn:
            conn.execute("DELETE FROM policy_benefits"); conn.execute("DELETE FROM policies"); conn.execute("DELETE FROM clients"); conn.commit()
        st.rerun()

    menu = st.radio("功能模組導航", ["📝 主約+附約體系建檔", "🚗 新增車險", "📊 精準條款健診", "🔔 續期/車險排程", "👥 客戶管理"])

# 這裡延續原本的邏輯... (為了節省空間，請直接複製您原本完整的邏輯放在下方)
# 在建立保單的「提交儲存」按鈕前，務必加入這段檢查：

if menu == "📝 主約+附約體系建檔":
    if get_total_policy_count() >= MAX_DEMO_POLICIES:
        st.warning(f"🔒 體驗版已達上限（{MAX_DEMO_POLICIES} 筆），請先清空資料後再試。")
    else:
        st.write("這是您的建檔區...") # 這裡填入您原本完整的保單建立 UI
