import sqlite3
import pandas as pd
import streamlit as st
from datetime import date, datetime
import io

# 1. 頁面配置與 CSS 清除
st.set_page_config(page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP®", page_icon="🏛️", layout="wide")
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton { visibility: hidden !important; display: none !important; }
    div[data-testid="stToolbar"], div[data-testid="manage-app-button"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yG6_ { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
MAX_DEMO_POLICIES = 3

# 2. 核心資料庫防彈引擎 (檢查欄位並自動修復)
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # 建立表單
    c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, birth_date TEXT, phone TEXT, family_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT, policy_no TEXT, policy_name TEXT, policy_type TEXT, is_main TEXT, pay_years INTEGER, pay_frequency TEXT, max_renew_age INTEGER, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, card_expiry TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT, plan_unit_name TEXT, outpatient_limit REAL, has_227_clause TEXT, receipt_type TEXT, clause_details TEXT)")
    
    # 自動補齊缺失欄位，防止錯誤
    cols = {'policies': ['card_expiry', 'payment_method', 'next_due_date'], 'policy_benefits': ['sum_assured_unit', 'plan_unit_name', 'outpatient_limit', 'has_227_clause', 'receipt_type', 'clause_details']}
    for table, clist in cols.items():
        existing = [i[1] for i in c.execute(f"PRAGMA table_info({table})").fetchall()]
        for col in clist:
            if col not in existing: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()

init_db()

# 3. 實用工具
def get_total_count():
    conn = get_conn()
    count = pd.read_sql_query("SELECT COUNT(*) FROM policies", conn).iloc[0,0]
    conn.close()
    return count

# 4. 側邊欄設計
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px; border-radius: 12px; text-align: center;">
            <div style="font-size: 1.1rem; font-weight: 700; color: white;">🏛️ 澄璞財務顧問工作室</div>
            <div style="background: #D97706; color: white; padding: 2px 10px; border-radius: 15px; display: inline-block; margin: 8px 0;">JennyHsieh CFP®</div>
            <div style="font-size: 0.8rem; color: #F59E0B;">🔒 體驗版 (上限 3 筆)</div>
        </div>
    """, unsafe_allow_html=True)
    count = get_total_count()
    st.info(f"📋 目前建檔：{count} / {MAX_DEMO_POLICIES} 筆")
    if st.button("🔄 清空體驗資料庫"):
        conn = get_conn()
        conn.execute("DELETE FROM policy_benefits"); conn.execute("DELETE FROM policies"); conn.execute("DELETE FROM clients"); conn.commit()
        conn.close(); st.rerun()
    
    menu = st.radio("功能導航", ["📝 主約+附約建檔", "🚗 新增車險", "📊 精準條款健診", "🔔 續期/車險排程", "👥 客戶管理"])

# 5. 主功能邏輯
if menu == "📝 主約+附約建檔":
    st.header("📝 保單主約 ＋ 附約體系精算建檔")
    if get_total_count() >= MAX_DEMO_POLICIES: st.warning("🔒 額度已滿，請先清空資料。")
    else:
        name = st.text_input("客戶姓名")
        if st.button("儲存保單"):
            conn = get_conn()
            conn.execute("INSERT INTO clients (name) VALUES (?)", (name,))
            c_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type) VALUES (?, '全球人壽', '000', '範例保單', '壽險')", (c_id,))
            conn.commit(); conn.close(); st.success("儲存成功！"); st.rerun()

elif menu == "🚗 新增車險":
    st.header("🚗 車險投保管理")
    st.write("車險建檔模組")

elif menu == "📊 精準條款健診":
    st.header("📊 精準條款健診")
    st.write("健診分析模組")

elif menu == "🔔 續期/車險排程":
    st.header("🔔 續期/車險排程")
    st.write("排程儀表板")

elif menu == "👥 客戶管理":
    st.header("👥 客戶名單總覽")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM clients", conn)
    st.dataframe(df, use_container_width=True)
    conn.close()
