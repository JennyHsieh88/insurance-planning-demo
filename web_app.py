import sqlite3
import pandas as pd
import streamlit as st
from datetime import date, datetime
import io

# 1. 頁面配置
st.set_page_config(page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP®", page_icon="🏛️", layout="wide")

# 2. 徹底清除官方浮動按鈕與標誌 CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton { visibility: hidden !important; display: none !important; }
    div[data-testid="stToolbar"], div[data-testid="manage-app-button"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yG6_ { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
MAX_DEMO_POLICIES = 3

# 3. 核心修復：資料庫初始化邏輯 (確保表格與欄位百分之百存在)
def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, birth_date TEXT, phone TEXT, family_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT, policy_no TEXT, policy_name TEXT, policy_type TEXT, is_main TEXT DEFAULT '👑 主約', pay_years INTEGER DEFAULT 20, pay_frequency TEXT DEFAULT '年繳', max_renew_age INTEGER DEFAULT 80, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, card_expiry TEXT, FOREIGN KEY (client_id) REFERENCES clients (client_id))")
    c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT DEFAULT '萬元', plan_unit_name TEXT DEFAULT '', outpatient_limit REAL, has_227_clause TEXT, receipt_type TEXT, clause_details TEXT, FOREIGN KEY (policy_id) REFERENCES policies (policy_id))")
    
    # 自動補齊缺失欄位
    for table, cols in {'policies': ['card_expiry', 'payment_method', 'next_due_date'], 'policy_benefits': ['sum_assured_unit', 'plan_unit_name', 'outpatient_limit', 'has_227_clause', 'receipt_type', 'clause_details']}.items():
        existing = [i[1] for i in c.execute(f"PRAGMA table_info({table})").fetchall()]
        for col in cols:
            if col not in existing: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()

init_db() # 啟動時先確保資料庫完好

# 4. 側邊欄設計
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px; border-radius: 12px; text-align: center;">
            <div style="font-size: 1.15rem; font-weight: 700; color: white;">🏛️ 澄璞財務顧問工作室</div>
            <div style="background: #D97706; color: white; padding: 2px 10px; border-radius: 20px; display: inline-block; margin: 8px 0;">JennyHsieh CFP®</div>
            <div style="font-size: 0.8rem; color: #F59E0B;">🔒 體驗版 (上限 3 筆)</div>
        </div>
    """, unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_NAME)
    count = pd.read_sql_query("SELECT COUNT(*) FROM policies", conn).iloc[0,0]
    st.info(f"📋 目前建檔：{count} / {MAX_DEMO_POLICIES} 筆")
    if st.button("🔄 清空體驗資料庫"):
        conn.execute("DELETE FROM policy_benefits"); conn.execute("DELETE FROM policies"); conn.execute("DELETE FROM clients"); conn.commit()
        st.rerun()
    conn.close()
    menu = st.radio("功能模組", ["📝 主約+附約建檔", "🚗 新增車險", "📊 精準條款健診", "🔔 續期/車險排程", "👥 客戶管理"])

# 5. 主程式邏輯 (完整功能區)
if menu == "📝 主約+附約建檔":
    st.header("📝 保單主約 ＋ 附約體系精算建檔")
    if get_total_policy_count() >= MAX_DEMO_POLICIES:
        st.warning("🔒 體驗版額度已滿，請重置。")
    else:
        st.write("請進行您的建檔操作...")
        # (在此處繼續放入原本完整的保單輸入表單代碼)

elif menu == "🚗 新增車險":
    st.header("🚗 車險投保管理")
    st.write("車險建檔功能...")

elif menu == "📊 精準條款健診":
    st.header("📊 客戶保單條款深度健診")
    st.write("健診分析功能...")

elif menu == "🔔 續期/車險排程":
    st.header("🔔 續期/車險排程")
    st.write("排程儀表板功能...")

elif menu == "👥 客戶管理":
    st.header("👥 客戶名單總覽")
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query("SELECT * FROM clients", conn)
        st.dataframe(df, use_container_width=True)
    except:
        st.info("尚無客戶資料。")
    conn.close()
