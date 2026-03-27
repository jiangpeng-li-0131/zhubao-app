import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# ================= 页面配置 =================
st.set_page_config(page_title="猪宝成长记账本", layout="centered", page_icon="🐽")

components.html(
    """
    <script>
        try {
            const link = window.parent.document.createElement('link');
            link.rel = 'apple-touch-icon';
            link.href = 'https://em-content.zobj.net/source/apple/391/pig-nose_1f43d.png';
            window.parent.document.head.appendChild(link);
        } catch (e) { }
    </script>
    """,
    height=0, width=0
)

# [UI 核心升级] 全局 CSS 注入：统一字体、圆角、悬浮动效与统一风格
st.markdown("""
<style>
    /* 引入现代圆润字体 */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Nunito', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    
    /* 美化原生按钮 */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    
    /* 美化数据表格外框 */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        border: 1px solid #f0f2f6;
    }
    
    /* 自定义统一的标题颜色 */
    h1, h2, h3 {
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)


# 建立与 Google Sheets 的连接 (云端核心)
conn = st.connection("gsheets", type=GSheetsConnection)

# ================= 数据库操作 (逻辑保持不变，绝对安全) =================
def load_data():
    try:
        df_balances = conn.read(worksheet="balances", ttl=0)
        df_trans = conn.read(worksheet="transactions", ttl=0)
    except Exception as e:
        st.error("无法连接到 Google Sheets。请检查后台配置或稍后再试。")
        st.stop()
        
    accounts = ['Jacob', 'Amanda', '猪宝成长基金(Jacob代持)', '猪宝成长基金(Amanda代持)']
    if df_balances.empty or not all(acc in df_balances['account'].values for acc in accounts):
        existing_accs = df_balances['account'].values if not df_balances.empty else []
        new_rows = []
        for acc in accounts:
            if acc not in existing_accs:
                new_rows.append({"account": acc, "balance": 0.0})
        if new_rows:
            df_balances = pd.concat([df_balances, pd.DataFrame(new_rows)], ignore_index=True)
            conn.update(worksheet="balances", data=df_balances)
            
    if df_trans.empty:
        df_trans = pd.DataFrame(columns=["date", "account", "type", "amount", "description"])
        conn.update(worksheet="transactions", data=df_trans)
        
    return df_balances, df_trans

def update_balance(account, amount, type_str, description):
    df_balances, df_trans = load_data()
    
    idx = df_balances.index[df_balances['account'] == account].tolist()
    if idx:
        df_balances.loc[idx[0], 'balance'] += amount
    else:
        new_row = pd.DataFrame({"account": [account], "balance": [amount]})
        df_balances = pd.concat([df_balances, new_row], ignore_index=True)
        
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_trans = pd.DataFrame([{
        "date": date_str, "account": account, "type": type_str, 
        "amount": amount, "description": description
    }])
    df_trans = pd.concat([df_trans, new_trans], ignore_index=True)
    
    conn.update(worksheet="balances", data=df_balances)
    conn.update(worksheet="transactions", data=df_trans)

# ================= 全局数据加载 =================
df_balances, df_transactions = load_data()
balances = df_balances.set_index('account')['balance'].to_dict()

# ================= 侧边栏与导航 =================
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-size: 2rem;'>🐽</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #555; margin-bottom: 20px;'>猪宝财务终端</h3>", unsafe_allow_html=True)
    menu = st.radio("导航菜单", ["📊 资产大盘看板", "📝 每月常规审计", "🛠️ 强制平账与修正", "📜 历史流水与撤销"])

# ================= 模块 1: 资产大盘看板 =================
if menu == "📊 资产大盘看板":
    
    with st.expander("⚙️ 视图与汇率设置 (仅影响当前大盘展示)"):
        col_set1, col_set2 = st.columns(2)
        with col_set1:
            exchange_rate = st.number_input("SGD 到 RMB 汇率设定", value=5.35, step=0.01)
        with col_set2:
            view_mode = st.radio("全局显示货币", ["SGD (新加坡元)", "RMB (人民币)"], horizontal=True)

    def display_currency(amount):
        if "RMB" in view_mode:
            return f"¥ {amount * exchange_rate:,.2f}"
        return f"$ {amount:,.2f}"

    def get_color(val, default_color):
        return "#e63946" if val < 0 else default_color

    j_personal = balances.get('Jacob', 0)
    a_personal = balances.get('Amanda', 0)
    j_zhu = balances.get('猪宝成长基金(Jacob代持)', 0)
    a_zhu = balances.get('猪宝成长基金(Amanda代持)', 0)
    total_zhu = j_zhu + a_zhu
    total_family = j_personal + a_personal + total_zhu

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 35px; border-radius: 20px; text-align: center; color: white; box-shadow: 0 10px 25px rgba(30,60,114,0.3); margin-bottom: 35px;">
            <p style="margin: 0; font-size: 14px; opacity: 0.8; text-transform: uppercase; letter-spacing: 3px; font-weight: 600;">家庭总资产净值 (Net Worth)</p>
            <h1 style="margin: 10px 0 0 0; font-size: 3.2rem; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">{display_currency(total_family)}</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🍼 猪宝成长基金")
    bg_style = "background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); border-left: 6px solid #ff758c;" if total_zhu >= 0 else "background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-left: 6px solid #e63946;"

    st.markdown(f"""
        <div style="{bg_style} padding: 25px; border-radius: 16px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; font-size: 15px; color: #555; font-weight: 700;">基金总余额</p>
                    <h2 style="margin: 5px 0 0 0; color: {get_color(total_zhu, '#2c3e50')}; font-weight: 800; font-size: 2.2rem;">{display_currency(total_zhu)}</h2>
                </div>
                <div style="text-align: right;">
                    <p style="margin: 0; font-size: 14px; color: #666; font-weight: 600;">Jacob 代持: <br><b style="color: {get_color(j_zhu, '#444')}; font-size: 1.1rem;">{display_currency(j_zhu)}</b></p>
                    <p style="margin: 10px 0 0 0; font-size: 14px; color: #666; font-weight: 600;">Amanda 代持: <br><b style="color: {get_color(a_zhu, '#444')}; font-size: 1.1rem;">{display_currency(a_zhu)}</b></p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👤 个人流动资金")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 25px; border-radius: 16px; border: 1px solid #f0f2f6; box-shadow: 0 4px 15px rgba(0,0,0,0.03); text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #888; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Jacob 个人账本</p>
                <h3 style="margin: 15px 0 0 0; color: {get_color(j_personal, '#2c3e50')}; font-weight: 800;">{display_currency(j_personal)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 25px; border-radius: 16px; border: 1px solid #f0f2f6; box-shadow: 0 4px 15px rgba(0,0,0,0.03); text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #888; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Amanda 个人账本</p>
                <h3 style="margin: 15px 0 0 0; color: {get_color(a_personal, '#2c3e50')}; font-weight: 800;">{display_currency(a_personal)}</h3>
            </div>
        """, unsafe_allow_html=True)
        
# ================= 模块 2: 每月常规审计 =================
elif menu == "📝 每月常规审计":
    st.title("📝 常规财务审计")
    st.markdown("<p style='color: #666; font-size: 15px;'>分别计算各自名下银行卡的流水差额，精准扣除各自代持的猪宝基金。</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    audit_month = st.date_input("📅 设定当前审计归档月份", value=datetime.today())
    st.markdown("---")
    
    st.markdown("#### 1. 💰 收入与个人分配")
    col1, col2 = st.columns(2)
    with col1:
        j_income = st.number_input("Jacob 总收入 (SGD)", min_value=0.0, step=100.0)
        j_to_personal = st.number_input("Jacob 截留至个人 (SGD)", min_value=0.0, step=100.0)
    with col2:
        a_income = st.number_input("Amanda 总收入 (SGD)", min_value=0.0, step=100.0)
        a_to_personal = st.number_input("Amanda 截留至个人 (SGD)", min_value=0.0, step=100.0)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 2. 🏦 银行对账单明细录入")
    if "bank_statements" not in st.session_state:
        st.session_state.bank_statements = pd.DataFrame(
            {"所有人": ["Jacob", "Jacob", "Jacob", "Jacob", "Amanda", "Amanda", "Amanda"], "银行名称": ["OCBC", "UOB", "DBS", "ICBC", "OCBC", "DBS", "BOC"], "Deposit_存入": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "Withdrawal_支出": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
        )
    edited_banks = st.data_editor(
        st.session_state.bank_statements,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "所有人": st.column_config.SelectboxColumn("所有人", options=["Jacob", "Amanda"], required=True),
            "银行名称": st.column_config.TextColumn("银行名称", required=True),
            "Deposit_存入": st.column_config.NumberColumn("Deposit (+) (SGD)", min_value=0.0, format="%.2f"),
            "Withdrawal_支出": st.column_config.NumberColumn("Withdrawal (-) (SGD)", min_value=0.0, format="%.2f")
        }
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 3. ⚖️ 剔除个人特殊开销")
    if "personal_expenses" not in st.session_state:
        st.session_state.personal_expenses = pd.DataFrame(
            {"支出人": ["Jacob", "Amanda"], "金额": [0.0, 0.0], "事由": ["无", "无"]}
        )
    edited_personal = st.data_editor(
        st.session_state.personal_expenses,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "支出人": st.column_config.SelectboxColumn("支出人", options=["Jacob", "Amanda"], required=True),
            "金额": st.column_config.NumberColumn("金额 (SGD)", min_value=0.0, format="%.2f"),
            "事由": st.column_config.TextColumn("事由", required=True)
        }
    )
    
    # === 核心双轨逻辑计算区 ===
    j_deposit = edited_banks[edited_banks['所有人'] == 'Jacob']['Deposit_存入'].sum()
    j_withdrawal = edited_banks[edited_banks['所有人'] == 'Jacob']['Withdrawal_支出'].sum()
    j_net_change = j_deposit - j_withdrawal
    
    a_deposit = edited_banks[edited_banks['所有人'] == 'Amanda']['Deposit_存入'].sum()
    a_withdrawal = edited_banks[edited_banks['所有人'] == 'Amanda']['Withdrawal_支出'].sum()
    a_net_change = a_deposit - a_withdrawal
    
    j_raw_expense = j_income - j_net_change
    a_raw_expense = a_income - a_net_change
    
    j_special = edited_personal[edited_personal['支出人'] == 'Jacob']['金额'].sum()
    a_special = edited_personal[edited_personal['支出人'] == 'Amanda']['金额'].sum()
    
    j_zhubao_expense = j_raw_expense - j_special
    a_zhubao_expense = a_raw_expense - a_special

    j_to_zhubao = j_income - j_to_personal
    a_to_zhubao = a_income - a_to_personal
    j_zhubao_net = j_to_zhubao - j_zhubao_expense
    a_zhubao_net = a_to_zhubao - a_zhubao_expense
    
    st.markdown("---")
    st.markdown("### 📊 结算核对单 (Preview)")
    
    # [UI 升级] 将预览区域改造成精致的电子回单卡片风格
    col_j, col_a = st.columns(2)
    with col_j:
        j_color = "#28a745" if j_zhubao_net >= 0 else "#e63946"
        j_sign = "+" if j_zhubao_net >= 0 else ""
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #f0f2f6; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                <h4 style="margin-top:0; color:#2c3e50; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;">👨🏻 Jacob 资金流 (SGD)</h4>
                <p style="margin:10px 0 5px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📥 存入个人账本:</span> <b>{j_to_personal:,.2f}</b></p>
                <p style="margin:5px 0 5px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📥 划入代持基金:</span> <b>{j_to_zhubao:,.2f}</b></p>
                <p style="margin:5px 0 15px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📤 推算基金开销:</span> <b>{j_zhubao_expense:,.2f}</b></p>
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center;">
                    <p style="margin:0; font-size: 13px; color:#888;">代持基金本月净变动</p>
                    <h3 style="margin:5px 0 0 0; color:{j_color};">{j_sign}{j_zhubao_net:,.2f}</h3>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_a:
        a_color = "#28a745" if a_zhubao_net >= 0 else "#e63946"
        a_sign = "+" if a_zhubao_net >= 0 else ""
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #f0f2f6; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                <h4 style="margin-top:0; color:#2c3e50; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;">👩🏻 Amanda 资金流 (SGD)</h4>
                <p style="margin:10px 0 5px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📥 存入个人账本:</span> <b>{a_to_personal:,.2f}</b></p>
                <p style="margin:5px 0 5px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📥 划入代持基金:</span> <b>{a_to_zhubao:,.2f}</b></p>
                <p style="margin:5px 0 15px 0; color:#666; font-size: 14px; display: flex; justify-content: space-between;"><span>📤 推算基金开销:</span> <b>{a_zhubao_expense:,.2f}</b></p>
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center;">
                    <p style="margin:0; font-size: 13px; color:#888;">代持基金本月净变动</p>
                    <h3 style="margin:5px 0 0 0; color:{a_color};">{a_sign}{a_zhubao_net:,.2f}</h3>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ 确认上述对账无误，安全写入云端", type="primary", use_container_width=True):
        with st.spinner('🚀 正在将账目加密同步至 Google 云端... \n (若遇短暂白屏属云端保护机制，数据已瞬间入库，稍后刷新即可)'):
            j_details = [f"{row['银行名称']}(D:{row['Deposit_存入']},W:{row['Withdrawal_支出']})" for _, row in edited_banks.iterrows() if row['所有人'] == 'Jacob' and str(row['银行名称']).strip()]
            a_details = [f"{row['银行名称']}(D:{row['Deposit_存入']},W:{row['Withdrawal_支出']})" for _, row in edited_banks.iterrows() if row['所有人'] == 'Amanda' and str(row['银行名称']).strip()]
            
            if j_to_personal > 0: update_balance('Jacob', j_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
            if a_to_personal > 0: update_balance('Amanda', a_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
            
            for _, row in edited_personal.iterrows():
                if row['金额'] > 0 and str(row['事由']).strip() != "":
                    update_balance(row['支出人'], -row['金额'], '支出', f"{audit_month.strftime('%Y-%m')} 个人开销: {row['事由']}")
            
            if j_to_zhubao > 0: update_balance('猪宝成长基金(Jacob代持)', j_to_zhubao, '收入', f'{audit_month.strftime("%Y-%m")} 薪资划入')
            if a_to_zhubao > 0: update_balance('猪宝成长基金(Amanda代持)', a_to_zhubao, '收入', f'{audit_month.strftime("%Y-%m")} 薪资划入')
            
            if j_zhubao_expense != 0: update_balance('猪宝成长基金(Jacob代持)', -j_zhubao_expense, '支出', f"{audit_month.strftime('%Y-%m')}日常开销 [{'|'.join(j_details)}]")
            if a_zhubao_expense != 0: update_balance('猪宝成长基金(Amanda代持)', -a_zhubao_expense, '支出', f"{audit_month.strftime('%Y-%m')}日常开销 [{'|'.join(a_details)}]")
            
            st.session_state.pop("bank_statements", None)
            st.session_state.pop("personal_expenses", None)
            
        st.success("🎉 审计结算圆满完成！底层账本已更新。")
        st.rerun()

# ================= 模块 3: 强制平账 =================
elif menu == "🛠️ 强制平账与修正":
    st.title("🛠️ 强制余额校准")
    st.markdown("<p style='color: #666; font-size: 15px;'>用于对齐真实银行卡的绝对余额，系统将自动计算差额并生成修正流水。</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    acc_to_fix = st.selectbox("📌 目标账本", ["Jacob", "Amanda", "猪宝成长基金(Jacob代持)", "猪宝成长基金(Amanda代持)"])
    current_b = balances.get(acc_to_fix, 0.0)
    
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #1e3c72; margin-bottom: 20px;">
            <p style="margin:0; color:#555;">系统账面余额: <b style="font-size: 1.2rem; color:#2c3e50;">SGD {current_b:,.2f}</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    new_balance = st.number_input("✍️ 录入实际正确余额 (SGD)", value=float(current_b), step=100.0)
    
    if new_balance != current_b:
        diff = new_balance - current_b
        st.warning(f"⚠️ 系统侦测到差异，将自动补录一笔 SGD {diff:,.2f} 的平账流水以平衡账本。")
        confirm = st.checkbox("确认操作无误")
        if confirm and st.button("🚨 强制覆盖同步", type="primary"):
            with st.spinner('正在同步至云端...'):
                update_balance(acc_to_fix, diff, '系统平账', '人工强制修改余额')
            st.success("✅ 余额对齐成功！")
            st.rerun()

# ================= 模块 4: 历史流水与撤回 =================
elif menu == "📜 历史流水与撤销":
    st.title("📜 底层流水追溯")
    st.markdown("<p style='color: #666; font-size: 15px;'>透明展示所有的资金流动轨迹。支持安全回滚与反向核算。</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    if not df_transactions.empty:
        filter_acc = st.multiselect(
            "🔍 筛选特定账本", 
            ["Jacob", "Amanda", "猪宝成长基金(Jacob代持)", "猪宝成长基金(Amanda代持)"], 
            default=[]
        )
        
        df_display = df_transactions.iloc[::-1].copy()
        if filter_acc:
            df_display = df_display[df_display['account'].isin(filter_acc)]
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.markdown("### 🗑️ 撤销错误记录")
        st.info("💡 选中记录删除后，系统不仅会将其从流水表剔除，还会自动把这笔钱从云端余额里「反向加减」回去。")
        
        df_trans_with_idx = df_transactions.reset_index()
        df_trans_with_idx_reverse = df_trans_with_idx.iloc[::-1]
        
        def format_record(idx):
            row = df_trans_with_idx[df_trans_with_idx['index'] == idx].iloc[0]
            return f"[{row['date']}] {row['account']} | {row['type']} {row['amount']} | {row['description']}"
            
        del_idx = st.selectbox(
            "选择需要回滚的流水：", 
            options=df_trans_with_idx_reverse['index'].tolist(),
            format_func=format_record
        )
        
        if st.button("🚨 确认删除并回算账本", type="primary"):
            with st.spinner('正在云端执行撤回与双表反向核算，请稍候...'):
                row_to_delete = df_trans_with_idx[df_trans_with_idx['index'] == del_idx].iloc[0]
                acc = row_to_delete['account']
                amt = float(row_to_delete['amount'])
                
                df_trans_new = df_trans_with_idx[df_trans_with_idx['index'] != del_idx].drop(columns=['index'])
                
                df_balances_new = df_balances.copy()
                b_idx = df_balances_new.index[df_balances_new['account'] == acc].tolist()
                if b_idx:
                    df_balances_new.loc[b_idx[0], 'balance'] -= amt
                
                conn.update(worksheet="transactions", data=df_trans_new)
                conn.update(worksheet="balances", data=df_balances_new)
                
            st.success(f"✅ 回滚成功！记录已抹除，SGD {amt} 已从 {acc} 的系统余额中安全调平。")
            st.rerun()
            
    else:
        st.info("📭 系统当前处于初始状态，暂无任何资金流水产生。")