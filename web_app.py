import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, date
import io
import json

# 設定頁面標題與品牌圖示
st.set_page_config(
    page_title="澄璞財務顧問工作室 ｜ JennyHsieh CFP® (體驗版)", 
    page_icon="🏛️", 
    layout="wide"
)

# 徹底隱藏頂部選單、頁尾、部署按鈕以及右下角所有 Streamlit 官方浮動裝飾
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
MAX_DEMO_POLICIES = 3  # 體驗版保單筆數上限
REGULATION_CUTOFF_DATE = "2024-07-01"

COMPANY_PRODUCTS_DB = {
    "全球人壽": {
        "mains": ["QWX 終身壽險", "DCE 醫卡讚重大傷病終身健康保險", "QTL 幸福定期壽險", "XDJ 臻愛久久重大傷病定期健康保險", "XTG 臻愛久久防癌終身健康保險", "美利發增額終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["XHR 醫療費用健康保險附約", "XHD 實在醫靠醫療健康保險附約", "XHB 實在醫靠醫療健康保險附約", "XDE 醫護重大傷病健康保險附約", "XTC 臻幸福防癌定期健康保險附約", "MIR 傷害保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "台灣人壽": {
        "mains": ["T02H0 福滿人生終身壽險", "T08F0 傳富安心重大傷病定期健康保險", "OTL1 珍好命一年定期壽險", "T04V2 傳富滿滿終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["HNRC 新住院醫療保險附約", "HNRB 新住院醫療保險附約", "HNRD 自負額住院醫療健康保險附約", "CIR4 金安心卡順利重大傷病健康保險附約", "YCD 愛無慮防癌一次金保險附約", "YHB 新住院醫療定額健康保險附約", "SPAR 長安傷害保險附約", "BX0 實質效益傷害醫療保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "富邦人壽": {
        "mains": ["XWS 終身壽險", "XLT 金安順重大傷病定期健康保險", "SWB 鑫富利增額終身壽險", "EHI 享安心住院醫療定額主約", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["HS 新綜合住院醫療保險附約", "HSG 長順住院醫療健康保險附約", "HSN 佳順住院醫療健康保險附約", "HKR 防癌定期健康保險附約", "PCC 防癌終身健康保險附約", "ADC 日額意外傷害保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "國泰人壽": {
        "mains": ["L65 鑫彩終身壽險", "UB 鍾心滿滿重大傷病定期保險", "B65 增美利終身壽險", "L3 萬代福終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["CV 新真全意住院醫療健康保險附約", "CV1 真全意住院醫療健康保險附約", "CV2 實全心意住院醫療健康保險附約", "ZV 金骨力傷害保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "南山人壽": {
        "mains": ["NNPL 新終身壽險", "CAB 護您久久防癌終身健康保險", "1CR 康祥重大疾病終身健康保險", "美滿發增額終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["1HIR 住院醫療保險附約", "HS 住院醫療保險附約", "HSI 好醫靠住院醫療健康保險附約", "PAR 新人身意外傷害保險附約", "DHI 意外傷害日額附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "遠雄人壽": {
        "mains": ["FI1 傳富新世代終身壽險", "MB1 美滿富貴終身壽險", "FX7 終身壽險", "HG4 金好心終身健康保險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["RJ1 康富醫療健康保險附約", "RM1 永康醫療健康保險附約", "RM2 永康自負額醫療附約", "CJ1 愛家安心防癌健康保險附約", "XCD 一年定期防癌健康保險附約", "RHA 超好心傷害保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "新光人壽": {
        "mains": ["DNA 珍愛健康終身壽險", "E2 傳家寶終身壽險", "長金倍發終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["C1 安心住院醫療保險附約", "U1 好全方位傷害保險附約", "V1 好全方位傷害醫療保險附約(實支)", "✍️ 自行輸入其他附約/代碼"]
    },
    "凱基人壽(中國)": {
        "mains": ["LEGO 金康泰專案主約", "MAJOTA 傳富終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["LEGOTA 金康泰住院醫療健康保險附約", "MAJOTA 超康泰自負額住院醫療健康保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "安聯人壽": {
        "mains": ["WS 萬世福終身壽險", "WL 卓越人生變額萬能壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["TL0 一年定期壽險附約", "DR 一年定期重大疾病健康保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "宏泰人壽": {
        "mains": ["FCB 觀音防癌終身健康保險", "宏運發終身壽險", "✍️ 自行輸入其他商品/代碼"],
        "riders": ["HSA 薰衣草醫療健康保險附約", "✍️ 自行輸入其他附約/代碼"]
    },
    "其他保險公司": {
        "mains": ["✍️ 自行輸入其他商品/代碼"],
        "riders": ["✍️ 自行輸入其他附約/代碼"]
    }
}

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

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

def calculate_rider_expiry(birth_d, max_age):
    if not birth_d or max_age <= 0: return "終身/依主約"
    exp_year = birth_d.year + int(max_age)
    try:
        return date(exp_year, birth_d.month, birth_d.day).strftime("%Y-%m-%d")
    except ValueError:
        return date(exp_year, birth_d.month, 28).strftime("%Y-%m-%d")

def init_and_migrate_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, birth_date TEXT, phone TEXT, family_id TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS policies (policy_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, company TEXT NOT NULL, policy_no TEXT NOT NULL, policy_name TEXT NOT NULL, policy_type TEXT NOT NULL, is_main TEXT DEFAULT '👑 主約', pay_years INTEGER DEFAULT 20, pay_frequency TEXT DEFAULT '年繳', max_renew_age INTEGER DEFAULT 80, start_date TEXT, next_due_date TEXT, expiry_date TEXT, premium INTEGER, payment_method TEXT, card_expiry TEXT, FOREIGN KEY (client_id) REFERENCES clients (client_id))")
        c.execute("CREATE TABLE IF NOT EXISTS policy_benefits (benefit_id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER, category TEXT, sum_assured REAL, sum_assured_unit TEXT DEFAULT '萬元', plan_unit_name TEXT DEFAULT '', outpatient_limit REAL, has_227_clause TEXT, receipt_type TEXT, clause_details TEXT, FOREIGN KEY (policy_id) REFERENCES policies (policy_id))")
        conn.commit()

init_and_migrate_db()

def get_total_policy_count():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM policies")
        return cur.fetchone()[0]

with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px 14px; border-radius: 12px; text-align: center; margin-bottom: 15px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">🏛️ 澄璞財務顧問工作室</div>
            <div style="background: #D97706; color: #FFFFFF; font-size: 0.82rem; padding: 2px 10px; border-radius: 20px; display: inline-block; margin-top: 6px;">JennyHsieh CFP®</div>
            <div style="font-size: 0.8rem; color: #F59E0B; margin-top: 6px;">🔒 體驗版 (上限 3 筆保單)</div>
        </div>
    """, unsafe_allow_html=True)

    current_count = get_total_policy_count()
    st.info(f"📋 **目前已建檔保單**：`{current_count} / {MAX_DEMO_POLICIES} 筆`")

    if current_count > 0:
        if st.button("🔄 清空體驗資料庫"):
            with get_conn() as conn:
                conn.execute("DELETE FROM policy_benefits")
                conn.execute("DELETE FROM policies")
                conn.execute("DELETE FROM clients")
                conn.commit()
            st.success("✅ 已清空！")
            st.rerun()

    menu = st.radio("功能模組導航", [
        "📝 主約+附約體系建檔",
        "🚗 新增車險",
        "📊 精準條款健診",
        "🔔 續期/車險排程",
        "👥 客戶管理"
    ])

company_list = list(COMPANY_PRODUCTS_DB.keys())
all_ptypes = ["壽險保障", "儲蓄/分紅/年金", "醫療實支", "重大傷病", "癌症一次金", "日額/定額醫療", "個人意外險", "失能照護"]
all_cats = ["壽險責任", "資產儲蓄", "實支醫療", "重大傷病", "防癌一次金", "日額定額", "意外傷害", "失能照護"]
all_units = ["萬元 (保額/滿期金)", "計畫 (實支/XHD等)", "元/日 (日額/住院)", "單位 (手術/防癌)", "自訂"]
receipt_options = ["可副本", "限正本", "限正本(差額證明)", "不適用"]

if menu == "📝 主約+附約體系建檔":
    st.header("📝 保單主約 ＋ 附約體系精算建檔（體驗版）")
    conn = get_conn()
    clients = pd.read_sql_query("SELECT client_id, name, birth_date FROM clients", conn)
    current_count = get_total_policy_count()

    tab_batch, tab_add_rider, tab_edit, tab_del = st.tabs([
        "➕ 建立新保單(主約+附約)",
        "📎 為現有主約追加新附約",
        "✏️ 編輯現有保單",
        "🗑️ 刪除保單"
    ])

    with tab_batch:
        if current_count >= MAX_DEMO_POLICIES:
            st.warning(f"🔒 **體驗版額度已滿（{current_count}/{MAX_DEMO_POLICIES} 筆）**\n\n如需繼續測試，請點擊左側側邊欄的 **「🔄 清空體驗資料庫」** 按鈕清除現有資料。")
        else:
            st.info(f"✨ 體驗版目前尚可建立保單／附約項目額度。")
            c_mode = st.radio("客戶來源：", ["✍️ 直接打新客戶名字", "🔍 選擇現有客戶"], horizontal=True, key="life_c_mode") if not clients.empty else "✍️ 直接打新客戶名字"

            c_id = None
            selected_client_birth = date(1990, 1, 1)

            if c_mode == "✍️ 直接打新客戶名字":
                col1, col2, col3, col4 = st.columns([2.5, 2.5, 2.5, 2.5])
                with col1: new_c_name = st.text_input("客戶姓名 *", key="life_new_name")
                with col2:
                    birth_input = st.date_input("出生日期 *", value=date(1990, 1, 1), min_value=date(1920, 1, 1), max_value=date.today(), key="life_new_birth")
                    st.caption(f"🎂 目前年齡：**{calculate_age(birth_input)} 歲**")
                    selected_client_birth = birth_input
                with col3: new_c_phone = st.text_input("聯絡電話", key="life_new_phone")
                with col4: new_c_family = st.text_input("家庭群組代號", key="life_new_fam")
            else:
                c_opts = dict(zip(clients['name'] + " (ID: " + clients['client_id'].astype(str) + ")", clients['client_id']))
                sel_k = st.selectbox("選擇現有客戶：", list(c_opts.keys()), key="life_sel_client")
                c_id = c_opts[sel_k]
                client_row = clients[clients['client_id'] == c_id].iloc[0]
                if pd.notna(client_row['birth_date']):
                    selected_client_birth = pd.to_datetime(client_row['birth_date']).date()
                    st.info(f"👤 客戶：**{client_row['name']}** ｜ 生日：**{client_row['birth_date']}** ｜ 目前年齡：**{calculate_age(selected_client_birth)} 歲**")

            st.markdown("---")
            st.subheader("2. 填寫【保單主約】核心資料")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_comp_sel = st.selectbox("保險公司 *", company_list, key="main_comp_sel")
                main_company = st.text_input("請輸入其他保險公司名稱 *", key="main_comp_custom") if m_comp_sel == "其他保險公司" else m_comp_sel
                main_policy_no = st.text_input("保單號碼 *", placeholder="例：0008899123", key="main_pno")
                avail_mains = COMPANY_PRODUCTS_DB.get(m_comp_sel, {}).get("mains", ["✍️ 自行輸入其他商品/代碼"])
                main_pname_choice = st.selectbox("主約商品名稱 / 代碼 *", avail_mains, key=f"main_pchoice_{m_comp_sel}")
                main_policy_name = st.text_input("請手動輸入主約商品名稱/代碼 *", key="main_pname_custom") if main_pname_choice == "✍️ 自行輸入其他商品/代碼" else main_pname_choice
                main_policy_type = st.selectbox("主約險種屬性", all_ptypes, key="main_ptype")
            with col_m2:
                col_md1, col_md2 = st.columns(2)
                with col_md1:
                    main_start_date = st.date_input("投保生效日 (起保日) *", key="main_start_d")
                    main_pay_years = st.selectbox("主約繳費年期 *", [20, 10, 6, 15, 25, 30, 1, 0], format_func=lambda x: "躉繳" if x == 0 else f"{x} 年期", key="main_pyears")
                with col_md2:
                    main_pay_freq = st.selectbox("繳費頻率 *", ["年繳", "半年繳", "季繳", "月繳"], key="main_pfreq")
                    calculated_due = calculate_next_due_date(main_start_date, main_pay_freq, main_pay_years)
                    st.text_input("下次續期應繳日 (系統自動精算)", value=calculated_due, disabled=True, key="calc_due_disp")
                main_premium = st.number_input("全單總繳年度保費 (元)", min_value=0, step=1000, key="main_prem")
                main_paym = st.selectbox("繳費管道", ["活存轉帳", "信用卡", "自行繳款", "躉繳", "已繳費期滿"], key="main_paym")

            st.markdown("**🎯 主約保障額度與條款設定**")
            col_mt1, col_mt2 = st.columns(2)
            with col_mt1:
                main_cat = st.selectbox("主約健診歸屬類別", all_cats, key="main_cat")
                col_ma1, col_ma2 = st.columns(2)
                with col_ma1: main_sum = st.number_input("主約額度數值 *", min_value=0.0, step=1.0, value=10.0, key="main_sum")
                with col_ma2: main_unit = st.selectbox("計價單位", all_units, key="main_unit")
                main_plan_note = st.text_input("主約規格備註 (選填)", key="main_pnote")
                main_out_limit = st.number_input("門診手術限額 (萬元)", min_value=0.0, step=1.0, key="main_out")
            with col_mt2:
                main_h227 = st.selectbox("限制 2-2-7 手術？", ["不適用", "否", "是"], key="main_h227")
                main_rec = st.selectbox("理賠收據規範", receipt_options, index=3, key="main_rec")
                main_details = st.text_area("主約條款 / 利率 / 滿期解約金備註", key="main_det", height=100)

            st.markdown("---")
            if "rider_form_count" not in st.session_state: st.session_state.rider_form_count = 0
            col_r_hdr, col_r_btn1, col_r_btn2 = st.columns([5, 2.5, 2.5])
            with col_r_hdr: st.subheader(f"3. 依附於此主約的【附約項目】 (目前共 {st.session_state.rider_form_count} 項)")
            with col_r_btn1:
                if st.button("➕ 為此保單新增一張附約"): st.session_state.rider_form_count += 1; st.rerun()
            with col_r_btn2:
                if st.session_state.rider_form_count > 0:
                    if st.button("➖ 減少最後一筆附約"): st.session_state.rider_form_count -= 1; st.rerun()

            riders_data = []
            avail_riders = COMPANY_PRODUCTS_DB.get(m_comp_sel, {}).get("riders", ["✍️ 自行輸入其他附約/代碼"])
            for r in range(st.session_state.rider_form_count):
                with st.container():
                    st.markdown(f"#### 📎 附約項目 #{r+1}")
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        r_pname_choice = st.selectbox(f"附約名稱 / 代碼 * (#{r+1})", avail_riders, key=f"r_choice_{m_comp_sel}_{r}")
                        r_name = st.text_input(f"請手動輸入附約名稱/代碼 * (#{r+1})", key=f"r_name_custom_{r}") if r_pname_choice == "✍️ 自行輸入其他附約/代碼" else r_pname_choice
                        r_type = st.selectbox(f"險種屬性 (#{r+1})", all_ptypes, index=2, key=f"r_type_{r}")
                        r_cat = st.selectbox(f"健診歸屬類別 (#{r+1})", all_cats, index=2, key=f"r_cat_{r}")
                        col_ra1, col_ra2 = st.columns(2)
                        with col_ra1: r_sum = st.number_input(f"額度數值 * (#{r+1})", min_value=0.0, step=1.0, value=5.0, key=f"r_sum_{r}")
                        with col_ra2: r_unit = st.selectbox(f"計價單位 (#{r+1})", all_units, index=1, key=f"r_unit_{r}")
                    with col_r2:
                        col_rage1, col_rage2 = st.columns(2)
                        with col_rage1: r_max_age = st.number_input(f"最高續保年齡 (#{r+1})", min_value=0, max_value=110, value=80, key=f"r_mage_{r}")
                        with col_rage2:
                            r_calc_exp = calculate_rider_expiry(selected_client_birth, r_max_age)
                            st.text_input(f"保障終止日 (#{r+1})", value=r_calc_exp, disabled=True, key=f"r_exp_disp_{r}")
                        r_plan_note = st.text_input(f"計畫名稱/備註 (#{r+1})", key=f"r_pnote_{r}")
                        r_out_limit = st.number_input(f"門診限額(萬) (#{r+1})", min_value=0.0, step=1.0, value=5.5, key=f"r_out_{r}")
                        r_h227 = st.selectbox(f"限制 2-2-7？ (#{r+1})", ["否", "是", "不適用"], key=f"r_h227_{r}")
                        r_rec = st.selectbox(f"收據規範 (#{r+1})", receipt_options, key=f"r_rec_{r}")
                        r_details = st.text_area(f"條款備註 (#{r+1})", key=f"r_det_{r}", height=70)
                    riders_data.append({"policy_name": r_name, "policy_type": r_type, "category": r_cat, "max_renew_age": r_max_age, "expiry_date": r_calc_exp, "sum_assured": r_sum, "sum_assured_unit": r_unit, "plan_unit_name": r_plan_note, "outpatient_limit": r_out_limit, "has_227": r_h227, "receipt_type": r_rec, "clause_details": r_details})

            if st.button("🚀 一鍵儲存整張保單（主約 ＋ 所有附約）", type="primary"):
                total_to_add = 1 + len([x for x in riders_data if x["policy_name"].strip()])
                if (current_count + total_to_add) > MAX_DEMO_POLICIES:
                    st.error(f"❌ 儲存失敗！體驗版總上限為 {MAX_DEMO_POLICIES} 筆（目前已有 {current_count} 筆，本次欲新增 {total_to_add} 筆）。")
                else:
                    if c_mode == "✍️ 直接打新客戶名字":
                        if not new_c_name.strip(): st.error("請輸入客戶姓名！"); st.stop()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO clients (name, birth_date, phone, family_id) VALUES (?, ?, ?, ?)", (new_c_name.strip(), selected_client_birth.strftime("%Y-%m-%d"), new_c_phone.strip(), new_c_family.strip()))
                        c_id = cur.lastrowid

                    sdate_str = main_start_date.strftime("%Y-%m-%d")
                    m_next_due = calculate_next_due_date(main_start_date, main_pay_freq, main_pay_years)
                    m_exp_date = f"{main_start_date.year + main_pay_years}年滿期" if main_pay_years > 0 else "終身"

                    cur = conn.cursor()
                    cur.execute("INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, is_main, pay_years, pay_frequency, max_renew_age, start_date, next_due_date, expiry_date, premium, payment_method) VALUES (?, ?, ?, ?, ?, '👑 主約', ?, ?, 99, ?, ?, ?, ?, ?)", (c_id, main_company.strip(), main_policy_no.strip(), main_policy_name.strip(), main_policy_type, main_pay_years, main_pay_freq, sdate_str, m_next_due, str(m_exp_date), main_premium, main_paym))
                    main_pid = cur.lastrowid
                    cur.execute("INSERT INTO policy_benefits (policy_id, category, sum_assured, sum_assured_unit, plan_unit_name, outpatient_limit, has_227_clause, receipt_type, clause_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (main_pid, main_cat, main_sum, main_unit, main_plan_note.strip(), main_out_limit, main_h227, main_rec, main_details.strip()))

                    for r_item in riders_data:
                        if r_item["policy_name"].strip():
                            cur.execute("INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, is_main, pay_years, pay_frequency, max_renew_age, start_date, next_due_date, expiry_date, premium, payment_method) VALUES (?, ?, ?, ?, ?, '📎 附約', 1, ?, ?, ?, ?, ?, 0, ?)", (c_id, main_company.strip(), main_policy_no.strip(), r_item["policy_name"].strip(), r_item["policy_type"], main_pay_freq, r_item["max_renew_age"], sdate_str, m_next_due, r_item["expiry_date"], main_paym))
                            r_pid = cur.lastrowid
                            cur.execute("INSERT INTO policy_benefits (policy_id, category, sum_assured, sum_assured_unit, plan_unit_name, outpatient_limit, has_227_clause, receipt_type, clause_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (r_pid, r_item["category"], r_item["sum_assured"], r_item["sum_assured_unit"], r_item["plan_unit_name"].strip(), r_item["outpatient_limit"], r_item["has_227"], r_item["receipt_type"], r_item["clause_details"].strip()))
                    conn.commit()
                    st.session_state.rider_form_count = 0
                    st.success("🎉 保單建立成功！")
                    st.rerun()

    with tab_add_rider:
        st.subheader("📎 為現有主約追加新附約")
        main_policies_df = pd.read_sql_query("SELECT p.policy_id, p.client_id, c.name AS client_name, c.birth_date, p.company, p.policy_no, p.policy_name, p.start_date, p.pay_frequency, p.payment_method FROM policies p JOIN clients c ON p.client_id = c.client_id WHERE p.is_main = '👑 主約'", conn)
        if main_policies_df.empty: st.info("尚無主約保單。")
        elif current_count >= MAX_DEMO_POLICIES: st.warning("🔒 體驗版額度已滿（3筆）。")
        else:
            p_opts = dict(zip(main_policies_df['client_name'] + " ｜ " + main_policies_df['company'] + " - " + main_policies_df['policy_name'], main_policies_df['policy_id']))
            sel_target_p = st.selectbox("選擇主約保單：", list(p_opts.keys()))
            target_row = main_policies_df[main_policies_df['policy_id'] == p_opts[sel_target_p]].iloc[0]
            c_bdate = pd.to_datetime(target_row['birth_date']).date() if pd.notna(target_row['birth_date']) else date(1990, 1, 1)
            
            col_ar1, col_ar2 = st.columns(2)
            with col_ar1:
                add_r_name = st.text_input("追加附約名稱 *", placeholder="例：XHR 醫療附約")
                add_r_type = st.selectbox("險種屬性", all_ptypes, index=2)
                add_r_cat = st.selectbox("健診類別", all_cats, index=2)
                add_r_sum = st.number_input("額度數值", value=5.0)
                add_r_unit = st.selectbox("計價單位", all_units, index=1)
            with col_ar2:
                add_r_mage = st.number_input("最高續保年齡", value=80)
                add_r_exp = calculate_rider_expiry(c_bdate, add_r_mage)
                st.text_input("終止日", value=add_r_exp, disabled=True)
                add_r_pnote = st.text_input("計畫備註")
                add_r_out = st.number_input("門診限額(萬)", value=5.5)
                add_r_h227 = st.selectbox("限制 2-2-7？", ["否", "是", "不適用"])
                add_r_rec = st.selectbox("收據規範", receipt_options)
                add_r_details = st.text_area("條款備註", height=70)

            if st.button("🚀 確認追加此附約", type="primary"):
                if current_count + 1 > MAX_DEMO_POLICIES: st.error("❌ 體驗版總上限 3 筆！")
                else:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, is_main, pay_years, pay_frequency, max_renew_age, start_date, next_due_date, expiry_date, premium, payment_method) VALUES (?, ?, ?, ?, ?, '📎 附約', 1, ?, ?, ?, '', ?, 0, ?)", (int(target_row['client_id']), target_row['company'], target_row['policy_no'], add_r_name.strip(), add_r_type, target_row['pay_frequency'], add_r_mage, target_row['start_date'], add_r_exp, target_row['payment_method']))
                    new_r_pid = cur.lastrowid
                    cur.execute("INSERT INTO policy_benefits (policy_id, category, sum_assured, sum_assured_unit, plan_unit_name, outpatient_limit, has_227_clause, receipt_type, clause_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_r_pid, add_r_cat, add_r_sum, add_r_unit, add_r_pnote.strip(), add_r_out, add_r_h227, add_r_rec, add_r_details.strip()))
                    conn.commit()
                    st.success("🎉 追加成功！")
                    st.rerun()

    with tab_edit:
        q_all = "SELECT p.*, c.name AS client_name, c.birth_date, b.* FROM policies p JOIN clients c ON p.client_id = c.client_id LEFT JOIN policy_benefits b ON p.policy_id = b.policy_id"
        edit_df = pd.read_sql_query(q_all, conn)
        if edit_df.empty: st.info("尚無資料可編輯。")
        else:
            p_map = dict(zip(edit_df['client_name'] + " ｜ " + edit_df['company'] + " - " + edit_df['policy_name'], edit_df['policy_id']))
            sel_p = st.selectbox("選擇要編輯的項目：", list(p_map.keys()))
            row = edit_df[edit_df['policy_id'] == p_map[sel_p]].iloc[0]
            with st.form("edit_form"):
                e_name = st.text_input("客戶姓名", value=row['client_name'])
                e_comp = st.text_input("保險公司", value=row['company'])
                e_pno = st.text_input("保單號碼", value=row['policy_no'])
                e_pname = st.text_input("名稱", value=row['policy_name'])
                if st.form_submit_button("💾 儲存修改"):
                    conn.execute("UPDATE clients SET name = ? WHERE client_id = ?", (e_name.strip(), int(row['client_id'])))
                    conn.execute("UPDATE policies SET company = ?, policy_no = ?, policy_name = ? WHERE policy_id = ?", (e_comp.strip(), e_pno.strip(), e_pname.strip(), int(row['policy_id'])))
                    conn.commit()
                    st.success("修改成功！"); st.rerun()

    with tab_del:
        q_all = "SELECT p.*, c.name AS client_name FROM policies p JOIN clients c ON p.client_id = c.client_id"
        del_df = pd.read_sql_query(q_all, conn)
        if del_df.empty: st.info("無資料可刪除。")
        else:
            d_map = dict(zip(del_df['client_name'] + " - " + del_df['company'] + " (" + del_df['policy_name'] + ")", del_df['policy_id']))
            d_choice = st.selectbox("選擇刪除項目", list(d_map.keys()))
            if st.button("⚠️ 確認刪除", type="primary"):
                conn.execute("DELETE FROM policy_benefits WHERE policy_id = ?", (d_map[d_choice],))
                conn.execute("DELETE FROM policies WHERE policy_id = ?", (d_map[d_choice],))
                conn.commit()
                st.warning("已刪除！"); st.rerun()
    conn.close()

elif menu == "🚗 新增車險":
    st.header("🚗 車險投保管理")
    conn = get_conn()
    current_count = get_total_policy_count()
    if current_count >= MAX_DEMO_POLICIES:
        st.warning(f"🔒 體驗版額度已滿（{current_count}/{MAX_DEMO_POLICIES} 筆）。")
    else:
        clients = pd.read_sql_query("SELECT client_id, name, birth_date FROM clients", conn)
        c_mode = st.radio("客戶來源：", ["✍️ 直接打新客戶名字", "🔍 選擇現有客戶"], horizontal=True) if not clients.empty else "✍️ 直接打新客戶名字"
        c_id = None
        if c_mode == "✍️ 直接打新客戶名字":
            c_name = st.text_input("客戶姓名 *")
            c_bdate = st.date_input("出生日期", value=date(1990, 1, 1))
        else:
            c_opts = dict(zip(clients['name'], clients['client_id']))
            c_id = c_opts[st.selectbox("選擇客戶", list(c_opts.keys()))]

        with st.form("car_form"):
            company = st.text_input("產險公司 *", placeholder="例：富邦產險")
            policy_no = st.text_input("車牌/保單號碼 *")
            plan_name = st.text_input("專案名稱 *", value="汽車乙式全險")
            start_date = st.date_input("起保日", value=date.today())
            expiry_date = st.date_input("滿期日")
            premium = st.number_input("保費", value=30000)
            details = st.text_area("保障明細")
            if st.form_submit_button("🚀 建立車險"):
                if current_count + 1 > MAX_DEMO_POLICIES: st.error("❌ 超過體驗版上限！")
                else:
                    if c_mode == "✍️ 直接打新客戶名字":
                        cur = conn.cursor()
                        cur.execute("INSERT INTO clients (name, birth_date) VALUES (?, ?)", (c_name.strip(), c_bdate.strftime("%Y-%m-%d")))
                        c_id = cur.lastrowid
                    cur = conn.cursor()
                    cur.execute("INSERT INTO policies (client_id, company, policy_no, policy_name, policy_type, is_main, start_date, expiry_date, premium) VALUES (?, ?, ?, ?, '車險', '車險', ?, ?, ?)", (c_id, company.strip(), policy_no.strip(), plan_name.strip(), start_date.strftime("%Y-%m-%d"), expiry_date.strftime("%Y-%m-%d"), premium))
                    new_pid = cur.lastrowid
                    cur.execute("INSERT INTO policy_benefits (policy_id, category, sum_assured, clause_details) VALUES (?, '責任/財損', 1000, ?)", (new_pid, details))
                    conn.commit()
                    st.success("✅ 車險建立成功！"); st.rerun()
    conn.close()

elif menu == "📊 精準條款健診":
    st.header("📊 保單深度健診")
    conn = get_conn()
    clients = pd.read_sql_query("SELECT client_id, name FROM clients", conn)
    if clients.empty: st.info("目前無客戶資料。")
    else:
        c_dict = dict(zip(clients['name'], clients['client_id']))
        sel_c = st.selectbox("選擇客戶", list(c_dict.keys()))
        df = pd.read_sql_query(f"SELECT p.company, p.policy_no, p.is_main, p.policy_name, b.category, b.sum_assured FROM policies p JOIN policy_benefits b ON p.policy_id = b.policy_id WHERE p.client_id = {c_dict[sel_c]}", conn)
        if df.empty: st.info("該客戶尚無保單細項。")
        else: st.dataframe(df, use_container_width=True)
    conn.close()

elif menu == "🔔 續期/車險排程":
    st.header("🔔 續期與到期排程")
    conn = get_conn()
    df = pd.read_sql_query("SELECT p.*, c.name AS 客戶姓名, c.phone AS 電話 FROM policies p JOIN clients c ON p.client_id = c.client_id", conn)
    conn.close()
    if df.empty: st.info("目前無排程資料。")
    else: st.dataframe(df[['客戶姓名', '電話', 'company', 'policy_no', 'policy_name', 'expiry_date', 'premium']], use_container_width=True)

elif menu == "👥 客戶管理":
    st.header("👥 客戶名單總覽")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM clients", conn)
    conn.close()
    if df.empty: st.info("尚無客戶。")
    else: st.dataframe(df, use_container_width=True)
