import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
import io
import json

# 設定頁面標題與品牌圖示
st.set_page_config(
    page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP®", 
    page_icon="🏛️", 
    layout="wide"
)

# 徹底隱藏頂部選單、頁尾、部署按鈕以及右下角所有 Streamlit 浮動裝飾
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {
        visibility: hidden !important;
        display: none !important;
    }
    div[data-testid="stToolbar"], div[data-testid="manage-app-button"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yG6_ {
        visibility: hidden !important;
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
REGULATION_CUTOFF_DATE = "2024-07-01"

# 資料庫初始化與欄位自動修復機制
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, birth_date TEXT, phone TEXT, family_id TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT NOT NULL, policy_no TEXT NOT NULL, policy_name TEXT NOT NULL, policy_type TEXT NOT NULL, is_main TEXT DEFAULT '👑 主約', pay_years INTEGER DEFAULT 20, pay_frequency TEXT DEFAULT '年繳', max_renew_age INTEGER DEFAULT 80, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, card_expiry TEXT, FOREIGN KEY (client_id) REFERENCES clients (client_id))")
        c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT DEFAULT '萬元', plan_unit_name TEXT DEFAULT '', outpatient_limit REAL, has_227_clause TEXT, receipt_type TEXT, clause_details TEXT, FOREIGN KEY (policy_id) REFERENCES policies (policy_id))")
        conn.commit()

init_db()

# 工具函式
def calculate_age(birth_d):
    if not birth_d: return 0
    today = date.today()
    return today.year - birth_d.year - ((today.month, today.day) < (birth_d.month, birth_d.day))

def calculate_next_due_date(start_d, pay_freq, pay_years):
    today = date.today()
    if pay_years == 0 or pay_freq == "躉繳": return "已躉繳/期滿"
    if pay_years > 0 and (today.year - start_d.year) >= pay_years: return "已繳費期滿 (免繳)"
    freq_months = {"年繳": 12, "半年繳": 6, "季繳": 3, "月繳": 1}.get(pay_freq, 12)
    cur_date = start_d
    while cur_date <= today:
        month = cur_date.month + freq_months
        year = cur_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(start_d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        cur_date = date(year, month, day)
    return cur_date.strftime("%Y-%m-%d")

# 側邊導航
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px 14px; border-radius: 12px; text-align: center;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">🏛️ 澄璞財務顧問工作室</div>
            <div style="background: #F59E0B; color: #FFFFFF; font-size: 0.8rem; padding: 2px 10px; border-radius: 20px; display: inline-block;">JennyHsieh CFP®</div>
        </div>
    """, unsafe_allow_html=True)
    menu = st.radio("功能模組導航", ["📝 主約+附約體系建檔", "🚗 新增車險", "📊 精準條款健診", "🔔 續期/車險排程", "👥 客戶管理"])

# 主程式邏輯 (修正後)
if menu == "🔔 續期/車險排程":
    st.header("🔔 續期應繳與產險到期排程")
    conn = get_conn()
    df = pd.read_sql_query("SELECT p.*, c.name AS '客戶姓名', c.phone AS '電話' FROM policies p JOIN clients c ON p.client_id = c.client_id", conn)
    conn.close()

    if df.empty:
        st.info("目前無資料。")
    else:
        car_df = df[df['policy_type'] == '車險'].copy()
        life_df = df[(df['policy_type'] != '車險') & (df['is_main'] == '👑 主約')].copy()

        tab1, tab2 = st.tabs(["📑 壽險續期", "🚗 車險到期"])
        with tab1:
            st.dataframe(life_df[['客戶姓名', '電話', 'company', 'policy_no', 'policy_name', 'next_due_date', 'premium']], use_container_width=True)
        with tab2:
            today = date.today()
            car_df['到期日_date'] = pd.to_datetime(car_df['expiry_date']).dt.date
            car_df['剩餘天數'] = (car_df['到期日_date'] - today).apply(lambda x: x.days)
            # 修正處：確保括號正確閉合
            st.dataframe(car_df[['客戶姓名', '電話', 'company', 'policy_no', 'policy_name', 'expiry_date', '剩餘天數', 'premium', 'payment_method']], use_container_width=True)

else:
    st.write("請選擇左側功能模組。")
