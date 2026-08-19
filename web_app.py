import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import io
import json

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# 設定頁面標題與品牌圖示
st.set_page_config(
    page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP® (體驗版)", 
    page_icon="🏛️", 
    layout="wide"
)

# ==================== 強力隱藏官方工具、徽章與選單 ====================
st.markdown("""
    <style>
    /* 隱藏頂部選單、頁尾、Fork、Header */
    #MainMenu, footer, header, .stDeployButton {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* 徹底隱藏右下角所有懸浮小工具與 Viewer 徽章 */
    [data-testid="stStatusWidget"],
    .viewerBadge_container__1QSob,
    div[class*="viewerBadge"],
    div[class*="floatingBadge"],
    div[class*="ProfilePagePreview"],
    div[class*="manageApp"],
    div[data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

DB_NAME = "client_vault.db"
MAX_DEMO_POLICIES = 3  # 體驗版最大保單上限

def get_conn():
    return sqlite3.connect(DB_NAME)

def init_and_migrate_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            family_id TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            company TEXT NOT NULL,
            policy_no TEXT NOT NULL,
            policy_name TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            expiry_date TEXT,
            premium INTEGER,
            payment_method TEXT,
            card_expiry TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS policy_benefits (
            benefit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            category TEXT,
            sum_assured REAL,
            outpatient_limit REAL,
            has_227_clause TEXT,
            receipt_type TEXT,
            clause_details TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies (policy_id)
        )
        """)
        
        cursor = conn.execute("PRAGMA table_info(policy_benefits)")
        columns = [info[1] for info in cursor.fetchall()]
        if "outpatient_limit" not in columns:
            conn.execute("ALTER TABLE policy_benefits ADD COLUMN outpatient_limit REAL DEFAULT 0.0")
        if "has_227_clause" not in columns:
            conn.execute("ALTER TABLE policy_benefits ADD COLUMN has_227_clause TEXT DEFAULT '否'")
        if "receipt_type" not in columns:
            conn.execute("ALTER TABLE policy_benefits ADD COLUMN receipt_type TEXT DEFAULT '可副本'")
        if "clause_details" not in columns:
            conn.execute("ALTER TABLE policy_benefits ADD COLUMN clause_details TEXT DEFAULT ''")
            
        conn.commit()

init_and_migrate_db()

def get_total_policy_count():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM policies")
        return cur.fetchone()[0]

# ==================== 側邊欄：客製化專屬品牌識別 ====================
with st.sidebar:
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            padding: 18px 14px;
            border-radius: 12px;
            border: 1px solid #334155;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 12px;
            text-align: center;
        ">
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC; letter-spacing: 0.5px; line-height: 1.4;">
                🏛️ 澄璞財務顧問工作室
            </div>
            <div style="
                display: inline-block;
                background: linear-gradient(90deg, #D97706, #F59E0B);
                color: #FFFFFF;
                font-size: 0.82rem;
                font-weight: 600;
                padding: 2px 10px;
                border-radius: 20px;
                margin-top: 6px;
                margin-bottom: 10px;
                letter-spacing: 0.5px;
            ">
                JennyHsieh CFP®
            </div>
            <div style="
                border-top: 1px dashed #475569;
                padding-top: 8px;
                font-size: 0.88rem;
                color: #94A3B8;
                font-weight: 500;
                letter-spacing: 1px;
            ">
                有「筱」陪伴 ｜ 攜手「筑」夢
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 體驗版提示徽章
    total_existing = get_total_policy_count()
    st.info(f"💡 **系統體驗版**\n- 目前已建檔保單：**{total_existing} / {MAX_DEMO_POLICIES}** 筆\n- 體驗版開放上限為 3 筆")

    # 一鍵重置清空體驗資料庫
    if total_existing > 0:
        if st.button("🔄 一鍵清空／重置體驗資料庫"):
            with get_conn() as conn:
                conn.execute("DELETE FROM policy_benefits")
                conn.execute("DELETE FROM policies")
                conn.execute("DELETE FROM clients")
                conn.commit()
            st.success("✅ 體驗資料已清空，可重新輸入 3 筆！")
            st.rerun()

    api_key = st.text_input("🔑 Gemini API Key (選填/智慧條款檢索)", type="password")

    menu = st.radio("功能模組導航", [
        "📝 壽險/全險種批次建檔 (體驗版限3筆)",
        "🚗 新增車險 (市場常用/自訂空白框)",
        "📊 精準條款健診與理賠情境試算",
        "🔔 續期/車險到期排程儀表板",
        "👥 客戶名單管理"
    ])

# ==================== 模組 1: 壽險/全險種動態批次建檔 ====================
if menu == "📝 壽險/全險種批次建檔 (體驗版限3筆)":
    st.header("📝 壽險／全險種建檔（體驗版限定最多 3 筆保單）")
    conn = get_conn()
    clients = pd.read_sql_query("SELECT client_id, name FROM clients", conn)
    current_count = get_total_policy_count()

    tab_batch, tab_edit, tab_del = st.tabs([
        "➕ 批次建立客戶保單與條款",
        "✏️ 編輯現有保單",
        "🗑️ 刪除保單"
    ])

    with tab_batch:
        if current_count >= MAX_DEMO_POLICIES:
            st.warning(f"🔒 **體驗版額度已滿（{current_count}/{MAX_DEMO_POLICIES} 筆）**\n\n目前已達到試用體驗上限 3 筆保單。如需解鎖無限保單建檔、家庭整合模型與全功能健診模組，請洽 **Jenny CFP®**。")
            st.info("💡 提示：您可點擊左側「🔄 一鍵清空／重置體驗資料庫」或「🗑️ 刪除保單」分頁刪除資料後重新試用。")
        else:
            remaining = MAX_DEMO_POLICIES - current_count
            st.success(f"✨ 體驗版目前尚可建立 **{remaining}** 筆保單。")
            
            st.subheader("1. 選擇或輸入客戶資訊")
            if not clients.empty:
                c_mode = st.radio("客戶來源：", ["✍️ 直接打新客戶名字", "🔍 選擇現有客戶"], horizontal=True, key="life_c_mode")
            else:
                c_mode = "✍️ 直接打新客戶名字"

            c_id = None
            new_c_name, new_c_phone, new_c_family = "", "", ""
            if c_mode == "✍️ 直接打新客戶名字":
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_c_name = st.text_input("客戶姓名 *", key="life_new_name")
                with col2:
                    new_c_phone = st.text_input("聯絡電話", key="life_new_phone")
                with col3:
                    new_c_family = st.text_input("家庭群組代號", key="life_new_fam")
            else:
                c_opts = dict(zip(clients['name'] + " (ID: " + clients['client_id'].astype(str) + ")", clients['client_id']))
                sel_k = st.selectbox("選擇現有客戶：", list(c_opts.keys()), key="life_sel_client")
                c_id = c_opts[sel_k]

            st.markdown("---")
            st.subheader("2. 填寫保單與附約資料")

            if "policy_form_count" not in st.session_state:
                st.session_state.policy_form_count = 1

            col_btn1, col_btn2, _ = st.columns([2, 2, 6])
            with col_btn1:
                if st.session_state.policy_form_count < remaining:
                    if st.button("➕ 增加一張附約／保單"):
                        st.session_state.policy_form_count += 1
                        st.rerun()
                else:
                    st.button("➕ 已達體驗新增上限", disabled=True)
            with col_btn2:
                if st.session_state.policy_form_count > 1:
                    if st.button("➖ 減少一張"):
                        st.session_state.policy_form_count -= 1
                        st.rerun()

            st.write(f"目前將為該客戶建立 **{st.session_state.policy_form_count}** 張保單／附約項目：")

            with st.form("batch_policies_form"):
                policies_data = []

                for i in range(st.session_state.policy_form_count):
                    st.markdown(f"#### 📄 保單／附約項目 #{i+1}")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        company = st.text_input(f"保險公司 * (#{i+1})", key=f"comp_{i}", placeholder="例：全球人壽 / 國泰人壽 / 富邦人壽 / 南山人壽")
                        policy_no = st.text_input(f"保單號碼 * (#{i+1})", key=f"pno_{i}", placeholder="例：0008899123")
                        policy_name = st.text_input(f"主附約名稱 * (#{i+1})", key=f"pname_{i}", placeholder="例：實在醫靠醫療健康附約 / 美利發增額終身壽險")
                        policy_type = st.selectbox(f"險種屬性 (#{i+1})", [
                            "醫療實支", "壽險保障", "儲蓄/分紅/年金", "重大傷病", "癌症一次金", "日額/定額醫療", "個人意外險", "失能照護"
                        ], key=f"ptype_{i}")
                    with col_p2:
                        expiry_date = st.date_input(f"滿期日 / 續期應繳日 * (#{i+1})", key=f"exp_{i}")
                        premium = st.number_input(f"年度保費 (元) (#{i+1})", min_value=0, step=1000, key=f"prem_{i}")
                        payment_method = st.selectbox(f"繳費方式 (#{i+1})", ["活存轉帳", "信用卡", "自行繳款", "躉繳", "已繳費期滿"], key=f"paym_{i}")
                        card_expiry = st.text_input(f"信用卡到期年月 (選填) (#{i+1})", placeholder="MM/YY", key=f"card_{i}")

                    st.markdown(f"**🎯 條款細節與保障額度配置 (#{i+1})**")
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        category = st.selectbox(f"健診歸屬類別 (#{i+1})", [
                            "實支醫療", "壽險責任", "資產儲蓄", "重大傷病", "防癌一次金", "日額定額", "意外傷害", "失能照護"
                        ], key=f"cat_{i}")
                        sum_assured = st.number_input(f"主要保額 / 儲蓄滿期金 (萬元) * (#{i+1})", min_value=0.0, step=10.0, key=f"sum_{i}")
                        outpatient_limit = st.number_input(f"門診手術/雜費限額 (萬元) (實支必填) (#{i+1})", min_value=0.0, step=1.0, key=f"out_{i}")
                    with col_t2:
                        has_227 = st.selectbox(f"限制 2-2-7 手術？ (#{i+1})", ["否", "是", "不適用"], key=f"h227_{i}")
                        receipt_type = st.selectbox(f"理賠收據規範 (#{i+1})", ["可副本", "限正本", "不適用"], key=f"rec_{i}")
                        clause_details = st.text_area(f"詳細條款 / 利率 / 儲蓄解約金備註 (#{i+1})", placeholder="例：住院雜費20萬/門診手術4萬/無2-2-7限制 或 預定利率2.5%/第10年預估解約金50萬", key=f"det_{i}", height=70)

                    st.markdown("---")
                    policies_data.append({
                        "company": company, "policy_no": policy_no, "policy_name": policy_name,
                        "policy_type": policy_type, "expiry_date": expiry_date, "premium": premium,
                        "payment_method": payment_method, "card_expiry": card_expiry,
                        "category": category, "sum_assured": sum_assured, "outpatient_limit": outpatient_limit,
                        "has_227": has_227, "receipt_type": receipt_type, "clause_details": clause_details
                    })

                submit_all = st.form_submit_button("🚀 一鍵批次儲存該客戶所有保單與附約")
                if submit_all:
                    if c_mode == "✍️ 直接打新客戶名字":
                        if not new_c_name.strip():
                            st.error("請輸入客戶姓名！")
                            st.stop()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO clients (name, phone, family_id) VALUES (?, ?, ?)", (new_c_name.strip(), new_c_phone.strip(), new_c_family.strip()))
                        c_id = cur.lastrowid

                    saved_count = 0
                    for p in policies_data:
                        if p["company"].strip() and p["policy_name"].strip():
                            cur = conn.cursor()
                            cur.execute("""
                            INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, expiry_date, premium, payment_method, card_expiry)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (c_id, p["company"].strip(), p["policy_no"].strip(), p["policy_name"].strip(), p["policy_type"], p["expiry_date"].strftime("%Y-%m-%d"), p["premium"], p["payment_method"], p["card_expiry"].strip()))
                            new_pid = cur.lastrowid

                            cur.execute("""
                            INSERT INTO policy_benefits (policy_id, category, sum_assured, outpatient_limit, has_227_clause, receipt_type, clause_details)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (new_pid, p["category"], p["sum_assured"], p["outpatient_limit"], p["has_227"], p["receipt_type"], p["clause_details"].strip()))
                            saved_count += 1

                    conn.commit()
                    st.session_state.policy_form_count = 1
                    st.success(f"🎉 成功為客戶建立 {saved_count} 張保單／附約！")
                    st.rerun()

    # ====== 編輯保單分頁 ======
    with tab_edit:
        q_all = """
        SELECT p.policy_id, p.client_id, c.name AS client_name, p.company, p.policy_no, 
               p.policy_name, p.policy_type, p.expiry_date, p.premium, p.payment_method, p.card_expiry,
               b.benefit_id, b.category, b.sum_assured, b.outpatient_limit, b.has_227_clause, b.receipt_type, b.clause_details
        FROM policies p
        JOIN clients c ON p.client_id = c.client_id
        LEFT JOIN policy_benefits b ON p.policy_id = b.policy_id
        """
        edit_df = pd.read_sql_query(q_all, conn)

        if edit_df.empty:
            st.info("尚無保單資料可編輯。")
        else:
            p_map = dict(zip(
                edit_df['client_name'] + " ｜ " + edit_df['company'] + " - " + edit_df['policy_name'] + " (" + edit_df['policy_no'] + ")",
                edit_df['policy_id']
            ))
            sel_p_label = st.selectbox("選擇要編輯的保單：", list(p_map.keys()))
            target_pid = p_map[sel_p_label]
            row_data = edit_df[edit_df['policy_id'] == target_pid].iloc[0]

            with st.form("edit_precision_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_name = st.text_input("客戶姓名", value=row_data['client_name'])
                    edit_company = st.text_input("保險公司", value=row_data['company'])
                    edit_pol_no = st.text_input("保單/車牌號碼", value=row_data['policy_no'])
                with col_e2:
                    edit_pol_name = st.text_input("主附約名稱", value=row_data['policy_name'])
                    edit_type = st.text_input("險種屬性", value=row_data['policy_type'] or "")
                    edit_prem = st.number_input("年度保費", value=int(row_data['premium'] or 0), step=1000)

                col_e3, col_e4 = st.columns(2)
                with col_e3:
                    edit_cat = st.text_input("保障類別", value=row_data['category'] or "")
                    edit_sum = st.number_input("主要保額 (萬)", value=float(row_data['sum_assured'] or 0.0), step=10.0)
                    edit_out_lim = st.number_input("門診手術限額 (萬)", value=float(row_data['outpatient_limit'] or 0.0), step=1.0)
                with col_e4:
                    has_227_val = row_data['has_227_clause'] if row_data['has_227_clause'] in ["否", "是", "不適用"] else "否"
                    rec_val = row_data['receipt_type'] if row_data['receipt_type'] in ["可副本", "限正本", "不適用"] else "可副本"
                    edit_227 = st.selectbox("限制 2-2-7 手術", ["否", "是", "不適用"], index=["否", "是", "不適用"].index(has_227_val))
                    edit_rec = st.selectbox("收據規範", ["可副本", "限正本", "不適用"], index=["可副本", "限正本", "不適用"].index(rec_val))
                    edit_details = st.text_area("詳細條款與備註", value=row_data['clause_details'] or "", height=100)

                if st.form_submit_button("💾 儲存修改"):
                    conn.execute("UPDATE clients SET name = ? WHERE client_id = ?", (edit_name.strip(), int(row_data['client_id'])))
                    conn.execute("""
                    UPDATE policies SET company=?, policy_no=?, policy_name=?, policy_type=?, premium=?
                    WHERE policy_id=?
                    """, (edit_company.strip(), edit_pol_no.strip(), edit_pol_name.strip(), edit_type.strip(), edit_prem, target_pid))
                    
                    if pd.notna(row_data['benefit_id']):
                        conn.execute("""
                        UPDATE policy_benefits SET category=?, sum_assured=?, outpatient_limit=?, has_227_clause=?, receipt_type=?, clause_details=?
                        WHERE policy_id=?
                        """, (edit_cat.strip(), edit_sum, edit_out_lim, edit_227, edit_rec, edit_details.strip(), target_pid))
                    conn.commit()
                    st.success("🎉 修改儲存成功！")
                    st.rerun()

    # ====== 刪除保單分頁 ======
    with tab_del:
        if not edit_df.empty:
            del_opts = dict(zip(edit_df['client_name'] + " - " + edit_df['company'] + " (" + edit_df['policy_name'] + ")", edit_df['policy_id']))
            del_choice = st.selectbox("選擇要刪除的保單", list(del_opts.keys()))
            del_id = del_opts[del_choice]
            if st.button("⚠️ 確認刪除該張保單", type="primary"):
                conn.execute("DELETE FROM policy_benefits WHERE policy_id = ?", (del_id,))
                conn.execute("DELETE FROM policies WHERE policy_id = ?", (del_id,))
                conn.commit()
                st.warning("保單已刪除！")
                st.rerun()

    conn.close()

# ==================== 模組 2: 車險專用建檔 ====================
elif menu == "🚗 新增車險 (市場常用/自訂空白框)":
    st.header("🚗 車險投保與續保管理建檔")
    conn = get_conn()
    clients = pd.read_sql_query("SELECT client_id, name FROM clients", conn)
    current_count = get_total_policy_count()

    if current_count >= MAX_DEMO_POLICIES:
        st.warning(f"🔒 **體驗版額度已滿（{current_count}/{MAX_DEMO_POLICIES} 筆）**\n\n目前已達到試用體驗上限 3 筆保單。如需解鎖車險車籍庫與無限制排程，請洽 **Jenny CFP®**。")
        st.info("💡 提示：您可點擊左側「🔄 一鍵清空／重置體驗資料庫」刪除資料後重新試用。")
    else:
        if not clients.empty:
            c_mode = st.radio("客戶來源：", ["✍️ 直接打新客戶名字", "🔍 選擇現有客戶"], horizontal=True, key="car_c_mode")
        else:
            c_mode = "✍️ 直接打新客戶名字"

        c_id = None
        new_c_name, new_c_phone, new_c_family = "", "", ""
        if c_mode == "✍️ 直接打新客戶名字":
            col1, col2, col3 = st.columns(3)
            with col1:
                new_c_name = st.text_input("客戶姓名 *", key="car_new_name")
            with col2:
                new_c_phone = st.text_input("聯絡電話", key="car_new_phone")
            with col3:
                new_c_family = st.text_input("家庭群組代號", key="car_new_fam")
        else:
            c_opts = dict(zip(clients['name'] + " (ID: " + clients['client_id'].astype(str) + ")", clients['client_id']))
            sel_k = st.selectbox("選擇現有客戶：", list(c_opts.keys()), key="car_sel_client")
            c_id = c_opts[sel_k]

        market_car_options = [
            "汽車乙式全險 (車體險+第三責任+超額險+駕傷險)",
            "汽車丙式超值型 (丙式車體+第三責任+超額險+駕傷險)",
            "汽車責任防護型 (第三責任險+超額1000萬+駕傷險)",
            "機車完整防護型 (強制險+第三責任+超額險+駕傷險)",
            "機車基本防護型 (強制險+駕駛人傷害險)",
            "自訂專案"
        ]
        car_plan_choice = st.selectbox("車險保障方案：", market_car_options, key="car_plan_sel")

        with st.form("standalone_car_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                company = st.text_input("產險公司 *", placeholder="例：富邦產險 / 新安東京 / 國泰產險")
                policy_no = st.text_input("車牌號碼 / 保單號碼 *", placeholder="例：ABC-1234 或 0500-24AUTO")
                if car_plan_choice == "自訂專案":
                    final_plan_name = st.text_input("自訂專案名稱 *", placeholder="請輸入專案名稱")
                else:
                    final_plan_name = car_plan_choice
            with col_c2:
                expiry_date = st.date_input("滿期日 / 續保到期日 *")
                premium = st.number_input("年度總保費 (元)", min_value=0, step=500, value=3000)
                payment_method = st.text_input("繳費方式", value="信用卡")
                card_expiry = st.text_input("信用卡到期年月 (選填)", placeholder="MM/YY")

            st.markdown("---")
            custom_car_details = st.text_area(
                "投保內容明細 (強制險、第三責任、超額險、駕傷險等)：", 
                placeholder="例如：\n1. 強制險\n2. 第三人責任險：體傷500萬/財損100萬\n3. 超額責任險：1000萬\n4. 駕駛人傷害險：200萬", 
                height=140
            )
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                super_limit = st.number_input("健診統計額度 (萬元)", value=1000.0, step=100.0)
            with col_cr2:
                car_notes = st.text_input("車籍 / 備註 (選填)", placeholder="例：車種 Toyota RAV4")

            submit_car = st.form_submit_button("🚀 一鍵建立車險保單與續保提醒")
            if submit_car:
                if c_mode == "✍️ 直接打新客戶名字":
                    if not new_c_name.strip():
                        st.error("請輸入客戶姓名！")
                        st.stop()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO clients (name, phone, family_id) VALUES (?, ?, ?)", (new_c_name.strip(), new_c_phone.strip(), new_c_family.strip()))
                    c_id = cur.lastrowid

                if not company.strip() or not policy_no.strip() or not final_plan_name.strip():
                    st.error("請填寫產險公司、車牌號碼與專案名稱！")
                    st.stop()

                cur = conn.cursor()
                cur.execute("""
                INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, expiry_date, premium, payment_method, card_expiry)
                VALUES (?, ?, ?, ?, '車險', ?, ?, ?, ?)
                """, (c_id, company.strip(), policy_no.strip(), final_plan_name.strip(), expiry_date.strftime("%Y-%m-%d"), premium, payment_method.strip(), card_expiry.strip()))
                new_pid = cur.lastrowid

                full_clause_txt = f"{custom_car_details}\n備註：{car_notes}".strip()
                cur.execute("""
                INSERT INTO policy_benefits (policy_id, category, sum_assured, outpatient_limit, has_227_clause, receipt_type, clause_details)
                VALUES (?, '責任/財損', ?, 0, '不適用', '不適用', ?)
                """, (new_pid, super_limit, full_clause_txt))
                conn.commit()
                st.success(f"✅ 車險【{policy_no}】建立成功！已加入到期排程掃描！")
                st.rerun()
    conn.close()

# ==================== 模組 3: 條款健診與精準情境分析 ====================
elif menu == "📊 精準條款健診與理賠情境試算":
    st.header("📊 客戶保單條款深度健診與精準缺口分析 (體驗版)")
    conn = get_conn()
    clients = pd.read_sql_query("SELECT client_id, name FROM clients", conn)

    if clients.empty:
        st.warning("⚠️ 目前無客戶資料，請先新增保單與條款。")
    else:
        client_dict = dict(zip(clients['name'] + " (ID: " + clients['client_id'].astype(str) + ")", clients['client_id']))
        selected_label = st.selectbox("請選擇要進行精準分析的客戶：", list(client_dict.keys()))
        selected_cid = client_dict[selected_label]
        selected_name = selected_label.split(" (ID:")[0]

        df_benefits = pd.read_sql_query(f"""
        SELECT p.company AS '保險公司', p.policy_name AS '主附約名稱', p.policy_type AS '險種',
               b.category AS '保障類別', b.sum_assured AS '主要保額(萬)', 
               b.outpatient_limit AS '門診手術限額(萬)',
               b.has_227_clause AS '限制2-2-7手術',
               b.receipt_type AS '收據規範',
               b.clause_details AS '詳細條款與理賠定義'
        FROM policy_benefits b
        JOIN policies p ON b.policy_id = p.policy_id
        WHERE p.client_id = {selected_cid}
        """, conn)

        if df_benefits.empty:
            st.info("該客戶尚無條款細項資料。")
        else:
            st.subheader("1. 條款核心參數一覽表")
            st.dataframe(df_benefits, use_container_width=True)

            st.subheader("2. 🔍 條款風險與爭議防呆預警")
            warnings = []
            
            for _, row in df_benefits.iterrows():
                if "實支" in str(row['保障類別']) or "醫療" in str(row['險種']):
                    if row['限制2-2-7手術'] == "是":
                        warnings.append(f"⚠️ **【2-2-7 條款限制】** {row['保險公司']} - {row['主附約名稱']}：限制健保 2-2-7 手術章節，門診 2-2-6 處置（如息肉切除、雷射）恐遭拒賠。")
                    
                    if pd.notna(row['門診手術限額(萬)']) and 0 < row['門診手術限額(萬)'] < 5:
                        warnings.append(f"⚠️ **【門診手術額度過低】** {row['保險公司']} - {row['主附約名稱']}：門診手術限額僅 **{row['門診手術限額(萬)']} 萬**，微創自費手術將產生巨額自付缺口！")
                    
                    if row['收據規範'] == "限正本":
                        warnings.append(f"📌 **【收據限制】** {row['保險公司']} - {row['主附約名稱']}：要求**正本收據**，限制後續雙實支加保空間。")

            if warnings:
                for w in warnings:
                    st.error(w)
            else:
                st.success("✅ 條款結構優良！未檢測出明顯的門診手術限額過低或 2-2-7 隱藏限制。")

            st.subheader("3. 💡 常見自費醫療理賠情境精準試算")
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.markdown("##### 🏥 情境 A：微創門診手術（自費 15 萬）")
                med_df = df_benefits[df_benefits['保障類別'].str.contains("實支", na=False)]
                if not med_df.empty:
                    total_outpatient = med_df['門診手術限額(萬)'].fillna(med_df['主要保額(萬)']).sum()
                    st.write(f"- 客戶名下實支醫療門診理賠上限合計：**{total_outpatient:.1f} 萬元**")
                    if total_outpatient < 15:
                        st.markdown(f"<span style='color:red;'>❌ 預計自費缺口：**{15 - total_outpatient:.1f} 萬元**</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color:green;'>✅ 門診手術額度充裕，全額覆蓋。</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:red;'>❌ 無實支醫療保障，需全額自費 15 萬元。</span>", unsafe_allow_html=True)

            with col_s2:
                st.markdown("##### 🎗️ 情境 B：確診重大傷病（健保重大傷病卡核發）")
                ci_df = df_benefits[df_benefits['保障類別'].str.contains("重大傷病|防癌|一次金", na=False)]
                total_ci = ci_df['主要保額(萬)'].sum() if not ci_df.empty else 0.0
                st.write(f"- 確診當下可立即動用自由現金：**{total_ci:.1f} 萬元**")
                if total_ci < 100:
                    st.markdown(f"<span style='color:red;'>⚠️ 目前防護缺口：**{max(0.0, 100 - total_ci):.1f} 萬元**</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:green;'>✅ 重大傷病金足夠防禦 2 年以上家庭生活支出。</span>", unsafe_allow_html=True)

            st.markdown("---")
            df_policies = pd.read_sql_query(f"""
            SELECT company AS '保險公司', policy_no AS '保單號碼', policy_name AS '險種名稱', 
                   policy_type AS '類別', expiry_date AS '滿期/應繳日', premium AS '保費', payment_method AS '繳費方式' 
            FROM policies WHERE client_id = {selected_cid}
            """, conn)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_policies.to_excel(writer, sheet_name='保單清單與到期', index=False)
                df_benefits.to_excel(writer, sheet_name='精準條款健診與缺口', index=False)
            excel_data = output.getvalue()

            st.download_button(
                label=f"📥 下載【{selected_name}】精準條款健診 Excel 報告",
                data=excel_data,
                file_name=f"精準條款健診報告_{selected_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    conn.close()

# ==================== 模組 4: 到期排程儀表板 ====================
elif menu == "🔔 續期/車險到期排程儀表板":
    st.header("🔔 續期／車險到期排程儀表板 (T-45 / T-30 / T-7)")
    conn = get_conn()
    df = pd.read_sql_query("""
    SELECT p.policy_id, c.name AS '客戶姓名', c.phone AS '電話', p.company AS '保險公司', 
           p.policy_name AS '險種名稱', p.policy_type AS '險種分類', 
           p.expiry_date AS '到期/應繳日', p.premium AS '保費', p.payment_method AS '繳費方式'
    FROM policies p
    JOIN clients c ON p.client_id = c.client_id
    """, conn)
    conn.close()

    if df.empty:
        st.info("💡 目前尚外保單資料。")
    else:
        today = datetime.now().date()
        df['到期/應繳日'] = pd.to_datetime(df['到期/應繳日']).dt.date
        df['剩餘天數'] = (df['到期/應繳日'] - today).apply(lambda x: x.days)

        expiring = df[(df['剩餘天數'] >= 0) & (df['剩餘天數'] <= 45)].sort_values('剩餘天數')
        col1, col2, col3 = st.columns(3)
        col1.metric("🚨 T-7 緊急追蹤", f"{len(df[(df['剩餘天數'] >= 0) & (df['剩餘天數'] <= 7)])} 筆")
        col2.metric("📢 T-30 續保通知", f"{len(df[(df['剩餘天數'] > 7) & (df['剩餘天數'] <= 30)])} 筆")
        col3.metric("📝 T-45 試算準備", f"{len(df[(df['剩餘天數'] > 30) & (df['剩餘天數'] <= 45)])} 筆")

        st.subheader("📋 45 天內即將到期保單清單")
        if expiring.empty:
            st.success("🎉 未來 45 天內無即將到期保單！")
        else:
            st.dataframe(expiring, use_container_width=True)

# ==================== 模組 5: 客戶名單管理 ====================
elif menu == "👥 客戶名單管理":
    st.header("👥 客戶名單總覽")
    conn = get_conn()
    all_clients = pd.read_sql_query("SELECT client_id AS '客戶ID', name AS '姓名', phone AS '電話', family_id AS '家庭編號' FROM clients", conn)
    st.dataframe(all_clients, use_container_width=True)
    conn.close()
