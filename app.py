import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ================= 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('zhubao_finance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS balances
                 (id INTEGER PRIMARY KEY, account TEXT, balance REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, account TEXT, type TEXT, amount REAL, description TEXT)''')
    
    accounts = ['Jacob', 'Amanda', '猪宝成长基金']
    for acc in accounts:
        c.execute("SELECT * FROM balances WHERE account=?", (acc,))
        if not c.fetchone():
            c.execute("INSERT INTO balances (account, balance) VALUES (?, 0)", (acc,))
    conn.commit()
    conn.close()

init_db()

# ================= 辅助函数 =================
def get_balances():
    conn = sqlite3.connect('zhubao_finance.db')
    df = pd.read_sql_query("SELECT account, balance FROM balances", conn)
    conn.close()
    return df.set_index('account')['balance'].to_dict()

def update_balance(account, amount, type_str, description):
    conn = sqlite3.connect('zhubao_finance.db')
    c = conn.cursor()
    c.execute("UPDATE balances SET balance = balance + ? WHERE account = ?", (amount, account))
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (date, account, type, amount, description) VALUES (?, ?, ?, ?, ?)",
              (date_str, account, type_str, amount, description))
    conn.commit()
    conn.close()

# ================= 页面配置与 UI =================
st.set_page_config(page_title="猪宝成长记账本", layout="centered", page_icon="🐷")

with st.sidebar:
    st.title("⚙️ 系统设置")
    exchange_rate = st.number_input("设置 SGD 到 RMB 汇率", value=5.35, step=0.01)
    view_mode = st.radio("显示货币", ["SGD (新加坡元)", "RMB (人民币)"])
    st.markdown("---")
    # 删除了独立的个人特殊支出页面
    menu = st.radio("导航", ["📊 资产看板", "📝 每月常规审计", "🛠️ 强制平账/修正", "📜 历史流水查询"])

def display_currency(amount):
    if "RMB" in view_mode:
        return f"¥ {amount * exchange_rate:,.2f}"
    return f"$ {amount:,.2f}"

balances = get_balances()

# ================= 模块 1: 资产看板 =================
if menu == "📊 资产看板":
    st.title("🐷 猪宝成长基金 & 个人账本")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Jacob 个人账本", display_currency(balances['Jacob']))
    col2.metric("Amanda 个人账本", display_currency(balances['Amanda']))
    
    st.markdown("### 🍼 家庭共同账户")
    st.metric("猪宝成长基金 (总计)", display_currency(balances['猪宝成长基金']))

# ================= 模块 2: 每月常规审计 =================
elif menu == "📝 每月常规审计":
    st.title("📝 每月 7 号财务审计")
    st.info("只需录入当月收入、银行流水及个人特殊开销，程序将全自动推算并结算三个账本。")
    
    audit_month = st.date_input("选择审计月份", value=datetime.today())
    
    st.subheader("1. 💰 收入与个人分配 (SGD)")
    col1, col2 = st.columns(2)
    with col1:
        j_income = st.number_input("Jacob 总收入", min_value=0.0, step=100.0)
        j_to_personal = st.number_input("Jacob 截留至个人账本", min_value=0.0, step=100.0)
    with col2:
        a_income = st.number_input("Amanda 总收入", min_value=0.0, step=100.0)
        a_to_personal = st.number_input("Amanda 截留至个人账本", min_value=0.0, step=100.0)
        
    st.subheader("2. 🏦 银行对账单明细录入")
    if "bank_statements" not in st.session_state:
        st.session_state.bank_statements = pd.DataFrame(
            {"所有人": ["Jacob", "Amanda"], "银行名称": ["DBS", "OCBC"], "Deposit_存入": [0.0, 0.0], "Withdrawal_支出": [0.0, 0.0]}
        )
    edited_banks = st.data_editor(
        st.session_state.bank_statements,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "所有人": st.column_config.SelectboxColumn("所有人", options=["Jacob", "Amanda"], required=True),
            "银行名称": st.column_config.TextColumn("银行名称", required=True),
            "Deposit_存入": st.column_config.NumberColumn("Deposit (+)", min_value=0.0, format="%.2f"),
            "Withdrawal_支出": st.column_config.NumberColumn("Withdrawal (-)", min_value=0.0, format="%.2f")
        }
    )
    
    st.subheader("3. ⚖️ 个人特殊支出剔除 (账单微调)")
    st.warning("如果本月产生了【仅归属个人】的开销（包含在上方银行 Withdrawal 中），请在此详细记录。程序会从家庭总开销中剔除，并自动从对应的个人账本扣款。")
    
    # 个人特殊支出动态表格
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
    
    # === 核心逻辑计算区 ===
    total_income = j_income + a_income
    total_deposit = edited_banks['Deposit_存入'].sum()
    total_withdrawal = edited_banks['Withdrawal_支出'].sum()
    
    # 计算个人特殊支出总和
    jacob_special = edited_personal[edited_personal['支出人'] == 'Jacob']['金额'].sum()
    amanda_special = edited_personal[edited_personal['支出人'] == 'Amanda']['金额'].sum()
    total_personal_expense = jacob_special + amanda_special
    
    # 推算支出
    net_bank_change = total_deposit - total_withdrawal
    calculated_raw_expense = total_income - net_bank_change
    final_zhubao_expense = calculated_raw_expense - total_personal_expense
    
    st.markdown("---")
    st.markdown("### 📊 本月结算预览")
    st.write(f"- 家庭总账面收入: **SGD {total_income:,.2f}**")
    st.write(f"- 银行账户总净变化 (存 - 取): **SGD {net_bank_change:,.2f}**")
    st.write(f"- 程序推算家庭总流水花销: **SGD {calculated_raw_expense:,.2f}**")
    if total_personal_expense > 0:
        st.write(f"- 💡 其中包含个人特殊开销: **SGD {total_personal_expense:,.2f}** (将分别从个人账本扣除)")
        
    st.markdown(f"**=> 最终将从猪宝成长基金扣除日常开销: <span style='color:red; font-size:24px;'>SGD {final_zhubao_expense:,.2f}</span>**", unsafe_allow_html=True)
    
    if st.button("✅ 确认数据无误，提交本月审计"):
        # 1. 记录银行明细字符串用于历史记录
        bank_details = []
        for index, row in edited_banks.iterrows():
            if pd.notna(row['银行名称']) and str(row['银行名称']).strip() != "":
                bank_details.append(f"{row['所有人']}-{row['银行名称']}(D:{row['Deposit_存入']}, W:{row['Withdrawal_支出']})")
        detail_str = " | ".join(bank_details)
        expense_desc = f"{audit_month.strftime('%Y-%m')}日常开销 [流水依据: {detail_str}]"
        
        # 2. 个人账本：存入薪资
        if j_to_personal > 0: update_balance('Jacob', j_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
        if a_to_personal > 0: update_balance('Amanda', a_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
        
        # 3. 个人账本：扣除特殊开销
        for index, row in edited_personal.iterrows():
            if row['金额'] > 0 and str(row['事由']).strip() != "":
                update_balance(row['支出人'], -row['金额'], '支出', f"{audit_month.strftime('%Y-%m')} 个人开销: {row['事由']}")
        
        # 4. 猪宝基金：存入与扣除
        total_zhubao_in = (j_income - j_to_personal) + (a_income - a_to_personal)
        if total_zhubao_in > 0: update_balance('猪宝成长基金', total_zhubao_in, '收入', f'{audit_month.strftime("%Y-%m")} 薪资划入')
        if final_zhubao_expense != 0: update_balance('猪宝成长基金', -final_zhubao_expense, '支出', expense_desc)
        
        st.success("🎉 本月审计结算完成！所有账本已同步更新并归档。")
        st.rerun()

# ================= 模块 4: 强制平账 =================
elif menu == "🛠️ 强制平账/修正":
    st.title("🛠️ 强制修改余额")
    acc_to_fix = st.selectbox("选择要修改的账本", ["Jacob", "Amanda", "猪宝成长基金"])
    current_b = balances[acc_to_fix]
    st.write(f"当前账面余额: **SGD {current_b:,.2f}**")
    new_balance = st.number_input("输入实际正确余额 (SGD)", value=float(current_b), step=100.0)
    
    if new_balance != current_b:
        diff = new_balance - current_b
        st.info(f"系统将生成一笔 SGD {diff:,.2f} 的一次性平账记录。")
        confirm = st.checkbox("我已反复核实，确认强制修改当前余额。")
        if confirm and st.button("🚨 确认执行覆盖"):
            update_balance(acc_to_fix, diff, '系统平账', '人工强制修改余额')
            st.success("余额已修正！")
            st.rerun()

# ================= 模块 5: 历史流水 =================
elif menu == "📜 历史流水查询":
    st.title("📜 账本流水与回溯")
    conn = sqlite3.connect('zhubao_finance.db')
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        filter_acc = st.multiselect("筛选账本", ["Jacob", "Amanda", "猪宝成长基金"], default=["猪宝成长基金"])
        if filter_acc:
            df = df[df['account'].isin(filter_acc)]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("暂无流水记录。")