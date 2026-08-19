import sqlite3
import pandas as pd
import streamlit as st
from datetime import date, datetime
import io

# 1. 設定頁面
st.set_page_config(page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP®", layout="wide")
st.markdown("""<style>#MainMenu, footer, header, .stDeployButton { visibility: hidden !important; } </style>""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"

# 2. 核心：最簡單的初始化 (保證一定先執行)
def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    # 強制建立表結構
    conn.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, birth_date TEXT, phone TEXT, family_id TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT, policy_no TEXT, policy_name TEXT, policy_type TEXT, is_main TEXT, start_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, clause_details TEXT)")
    conn.commit()
    return conn

# 3. 功能區 (將讀取資料庫的動作放進函數裡，不要寫在最外層)
def get_clients_df():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM clients", conn)
    conn.close()
    return df

# 4. 側邊欄與頁面顯示
with st.sidebar:
    st.write("🏛️ 澄璞財務顧問工作室")
    menu = st.radio("導航", ["📝 主約建檔", "👥 客戶管理"])

if menu == "📝 主約建檔":
    st.header("📝 保單建檔")
    name = st.text_input("客戶姓名")
    if st.button("儲存"):
        conn = get_db()
        conn.execute("INSERT INTO clients (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        st.rerun()

elif menu == "👥 客戶管理":
    st.header("👥 客戶名單")
    df = get_clients_df() # 這裡讀取時，表格一定已經存在了
    st.dataframe(df)
