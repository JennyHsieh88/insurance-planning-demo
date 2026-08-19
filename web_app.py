import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, date

# 設定頁面標題與品牌圖示
st.set_page_config(
    page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP®", 
    page_icon="🏛️", 
    layout="wide"
)

# 徹底隱藏頂部選單、頁尾、部署按鈕以及右下角所有 Streamlit 官方浮動裝飾
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton { visibility: hidden !important; display: none !important; }
    div[data-testid="stToolbar"], div[data-testid="manage-app-button"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yG6_ { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
MAX_DEMO_POLICIES = 3  # 體驗版保單筆數上限

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_and_migrate_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, birth_date TEXT, phone TEXT, family_id TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT NOT NULL, policy_no TEXT NOT NULL, policy_name TEXT NOT NULL, policy_type TEXT NOT NULL, is_main TEXT DEFAULT '👑 主約', pay_years INTEGER DEFAULT 20, pay_frequency TEXT DEFAULT '年繳', max_renew_age INTEGER DEFAULT 80, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, card_expiry TEXT, FOREIGN KEY (client_id) REFERENCES clients (client_id))")
        c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT DEFAULT '萬元', plan_unit_name TEXT DEFAULT '', outpatient_limit REAL, has_227_clause TEXT, receipt_type TEXT, clause_details TEXT, FOREIGN KEY (policy_id) REFERENCES policies (policy_id))")
        conn.commit()

init_and_migrate_db()

def get_total_policy_count():
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM policies")
            return cur.fetchone()[0]
    except:
        return 0

with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px 14px; border-radius: 12px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">🏛️ 澄璞財務顧問工作室</div>
            <div style="background: #D97706; color: #FFFFFF; font-size: 0.82rem; padding: 2px 10px; border-radius: 20px; display: inline-block; margin-top: 8px;">JennyHsieh CFP®</div>
            <div style="font-size: 0.78rem; color: #F59E0B; margin-top: 8px; font-weight: 600;">🔒 體驗版 (上限 3 筆)</div>
        </div>
    """, unsafe_allow_html=True)

    current_count = get_total_policy_count()
    st.info(f"📋 **目前已建檔保單**：`{current_count} / {MAX_DEMO_POLICIES} 筆`")

    if st.button("🔄 清空體驗資料庫"):
        with get_conn() as conn:
            conn.execute("DELETE FROM policy_benefits")
            conn.execute("DELETE FROM policies")
            conn.execute("DELETE FROM clients")
            conn.commit()
        st.success("✅ 已清空！")
        st.rerun()

    menu = st.radio("功能模組導航", ["📝 主約+附約體系建檔", "🚗 新增車險", "📊 精準條款健診", "🔔 續期/車險排程", "👥 客戶管理"])

if menu == "📝 主約+附約體系建檔":
    st.header("📝 保單主約 ＋ 附約體系精算建檔（體驗版）")
    if get_total_policy_count() >= MAX_DEMO_POLICIES:
        st.warning("🔒 **體驗版額度已滿**，請清空資料庫後重試。")
    else:
        st.write("請進行您的建檔操作...")

elif menu == "🚗 新增車險":
    st.header("🚗 車險投保管理（體驗版）")
    if get_total_policy_count() >= MAX_DEMO_POLICIES:
        st.warning("🔒 **體驗版額度已滿**。")
    else:
        st.write("請進行您的車險建檔操作...")

elif menu == "📊 精準條款健診":
    st.header("📊 客戶保單條款深度健診")
    st.write("請選擇客戶進行分析...")

elif menu == "🔔 續期/車險排程":
    st.header("🔔 續期應繳與到期排程")
    st.write("保單排程一覽...")

elif menu == "👥 客戶管理":
    st.header("👥 客戶名單總覽")
    conn = get_conn()
    all_clients = pd.read_sql_query("SELECT * FROM clients", conn)
    st.dataframe(all_clients, use_container_width=True)
    conn.close()
