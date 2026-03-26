import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ================= 页面配置 =================
st.set_page_config(page_title="猪宝成长记账本", layout="centered", page_icon="🐷")

# 建立与 Google Sheets 的连接 (云端核心)
conn = st.connection("gsheets", type=GSheetsConnection)

# ================= 数据库操作 =================
def load_data():
    try:
        df_balances = conn.read(worksheet="balances", ttl=0)
        df_trans = conn.read(worksheet="transactions", ttl=0)
    except Exception as e:
        st.error("无法连接到 Google Sheets。请检查后台配置或稍后再试。")
        st.stop()
        
    # 初始化4个账本 (双轨制核心)
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
    
    # 更新余额
    idx = df_balances.index[df_balances['account'] == account].tolist()
    if idx:
        df_balances.loc[idx[0], 'balance'] += amount
    else:
        new_row = pd.DataFrame({"account": [account], "balance": [amount]})
        df_balances = pd.concat([df_balances, new_row], ignore_index=True)
        
    # 记录流水
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_trans = pd.DataFrame([{
        "date": date_str, "account": account, "type": type_str, 
        "amount": amount, "description": description
    }])
    df_trans = pd.concat([df_trans, new_trans], ignore_index=True)
    
    # 写回云端
    conn.update(worksheet="balances", data=df_balances)
    conn.update(worksheet="transactions", data=df_trans)

# ================= 全局数据加载 =================
df_balances, df_transactions = load_data()
balances = df_balances.set_index('account')['balance'].to_dict()

# ================= 侧边栏与导航 =================
with st.sidebar:
    st.title("⚙️ 系统设置")
    exchange_rate = st.number_input("设置 SGD 到 RMB 汇率", value=5.35, step=0.01)
    view_mode = st.radio("显示货币", ["SGD (新加坡元)", "RMB (人民币)"])
    st.markdown("---")
    menu = st.radio("导航", ["📊 资产看板", "📝 每月常规审计", "🛠️ 强制平账/修正", "📜 历史流水查询"])

def display_currency(amount):
    if "RMB" in view_mode:
        return f"¥ {amount * exchange_rate:,.2f}"
    return f"$ {amount:,.2f}"

# ================= 模块 1: 资产看板 =================
if menu == "📊 资产看板":
    st.title("🐷 猪宝成长基金 & 个人账本")
    
    col1, col2 = st.columns(2)
    col1.metric("Jacob 个人账本", display_currency(balances.get('Jacob', 0)))
    col2.metric("Amanda 个人账本", display_currency(balances.get('Amanda', 0)))
    
    st.markdown("### 🍼 家庭共同账户 (猪宝成长基金)")
    j_zhu = balances.get('猪宝成长基金(Jacob代持)', 0)
    a_zhu = balances.get('猪宝成长基金(Amanda代持)', 0)
    total_zhu = j_zhu + a_zhu
    
    st.metric("总计金额", display_currency(total_zhu))
    
    st.caption("🔍 资金分布明细：")
    sub_col1, sub_col2 = st.columns(2)
    sub_col1.info(f"Jacob 银行卡代持:\n\n**{display_currency(j_zhu)}**")
    sub_col2.info(f"Amanda 银行卡代持:\n\n**{display_currency(a_zhu)}**")

# ================= 模块 2: 每月常规审计 =================
elif menu == "📝 每月常规审计":
    st.title("📝 每月 7 号财务审计")
    st.info("程序将分别计算各自名下银行卡的流水差额，精准扣除各自代持的猪宝基金。")
    
    audit_month = st.date_input("选择审计月份", value=datetime.today())
    
    st.subheader("1. 💰 收入与个人分配 (SGD)")
    col1, col2 = st.columns(2)
    with col1:
        j_income = st.number_input("Jacob 总收入", min_value=0.0, step=100.0)
        j_to_personal = st.number_input("Jacob 截留至个人", min_value=0.0, step=100.0)
    with col2:
        a_income = st.number_input("Amanda 总收入", min_value=0.0, step=100.0)
        a_to_personal = st.number_input("Amanda 截留至个人", min_value=0.0, step=100.0)
        
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
    
    st.subheader("3. ⚖️ 个人特殊支出剔除")
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
    
    st.markdown("---")
    st.markdown("### 📊 本月结算核对预览")
    
    col_j, col_a = st.columns(2)
    with col_j:
        st.write("👨🏻 **Jacob 的账户推算**")
        st.write(f"推算流水花销: SGD {j_raw_expense:,.2f}")
        st.write(f"剔除个人开销: SGD {j_special:,.2f}")
        st.markdown(f"**从Jacob代持扣除: <br><span style='color:red; font-size:20px;'>SGD {j_zhubao_expense:,.2f}</span>**", unsafe_allow_html=True)

    with col_a:
        st.write("👩🏻 **Amanda 的账户推算**")
        st.write(f"推算流水花销: SGD {a_raw_expense:,.2f}")
        st.write(f"剔除个人开销: SGD {a_special:,.2f}")
        st.markdown(f"**从Amanda代持扣除: <br><span style='color:red; font-size:20px;'>SGD {a_zhubao_expense:,.2f}</span>**", unsafe_allow_html=True)
    
    if st.button("✅ 确认数据无误，同步至云端"):
        with st.spinner('正在同步至 Google Sheets，请稍候...'):
            j_details = [f"{row['银行名称']}(D:{row['Deposit_存入']},W:{row['Withdrawal_支出']})" for _, row in edited_banks.iterrows() if row['所有人'] == 'Jacob' and str(row['银行名称']).strip()]
            a_details = [f"{row['银行名称']}(D:{row['Deposit_存入']},W:{row['Withdrawal_支出']})" for _, row in edited_banks.iterrows() if row['所有人'] == 'Amanda' and str(row['银行名称']).strip()]
            
            if j_to_personal > 0: update_balance('Jacob', j_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
            if a_to_personal > 0: update_balance('Amanda', a_to_personal, '收入', f'{audit_month.strftime("%Y-%m")} 薪资存入')
            
            for _, row in edited_personal.iterrows():
                if row['金额'] > 0 and str(row['事由']).strip() != "":
                    update_balance(row['支出人'], -row['金额'], '支出', f"{audit_month.strftime('%Y-%m')} 个人开销: {row['事由']}")
            
            j_to_zhubao = j_income - j_to_personal
            a_to_zhubao = a_income - a_to_personal
            
            if j_to_zhubao > 0: update_balance('猪宝成长基金(Jacob代持)', j_to_zhubao, '收入', f'{audit_month.strftime("%Y-%m")} 薪资划入')
            if a_to_zhubao > 0: update_balance('猪宝成长基金(Amanda代持)', a_to_zhubao, '收入', f'{audit_month.strftime("%Y-%m")} 薪资划入')
            
            if j_zhubao_expense != 0: update_balance('猪宝成长基金(Jacob代持)', -j_zhubao_expense, '支出', f"{audit_month.strftime('%Y-%m')}日常开销 [{'|'.join(j_details)}]")
            if a_zhubao_expense != 0: update_balance('猪宝成长基金(Amanda代持)', -a_zhubao_expense, '支出', f"{audit_month.strftime('%Y-%m')}日常开销 [{'|'.join(a_details)}]")
            
            st.session_state.pop("bank_statements", None)
            st.session_state.pop("personal_expenses", None)
            
        st.success("🎉 本月审计结算完成！双轨账本已同步更新并归档。")
        st.rerun()

# ================= 模块 4: 强制平账 =================
elif menu == "🛠️ 强制平账/修正":
    st.title("🛠️ 强制修改余额")
    st.info("💡 提示：用于校准你们各自银行卡的真实余额。")
    acc_to_fix = st.selectbox("选择要修改的账本", ["Jacob", "Amanda", "猪宝成长基金(Jacob代持)", "猪宝成长基金(Amanda代持)"])
    current_b = balances.get(acc_to_fix, 0.0)
    st.write(f"当前账面余额: **SGD {current_b:,.2f}**")
    new_balance = st.number_input("输入实际正确余额 (SGD)", value=float(current_b), step=100.0)
    
    if new_balance != current_b:
        diff = new_balance - current_b
        st.warning(f"系统将生成一笔 SGD {diff:,.2f} 的平账记录。")
        confirm = st.checkbox("我已反复核实，确认强制修改当前余额。")
        if confirm and st.button("🚨 确认执行覆盖"):
            with st.spinner('正在同步至云端...'):
                update_balance(acc_to_fix, diff, '系统平账', '人工强制修改余额')
            st.success("余额已修正！")
            st.rerun()

# ================= 模块 5: 历史流水与撤回 =================
elif menu == "📜 历史流水查询":
    st.title("📜 账本流水与回溯")
    
    if not df_transactions.empty:
        # 功能一：清空默认筛选，完整展示
        filter_acc = st.multiselect(
            "筛选账本", 
            ["Jacob", "Amanda", "猪宝成长基金(Jacob代持)", "猪宝成长基金(Amanda代持)"], 
            default=[]
        )
        
        # 按照倒序显示最新流水
        df_display = df_transactions.iloc[::-1].copy()
        if filter_acc:
            df_display = df_display[df_display['account'].isin(filter_acc)]
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # 功能二：安全的下拉撤销功能 (Google Sheets 架构)
        st.markdown("---")
        st.subheader("🗑️ 撤销流水记录")
        st.warning("⚠️ 删除流水后，系统会自动将该笔金额从云端的对应账本中「反向核算」回去，保证账目绝对平衡。")
        
        # 为了唯一识别云端行，我们引入原 DataFrame 的内部索引(index)
        df_trans_with_idx = df_transactions.reset_index()
        df_trans_with_idx_reverse = df_trans_with_idx.iloc[::-1] # 保持下拉菜单也是倒序排列
        
        def format_record(idx):
            row = df_trans_with_idx[df_trans_with_idx['index'] == idx].iloc[0]
            return f"{row['date']} | {row['account']} | 金额: {row['amount']} | 事由: {row['description']}"
            
        del_idx = st.selectbox(
            "请选择要彻底撤回的流水记录：", 
            options=df_trans_with_idx_reverse['index'].tolist(),
            format_func=format_record
        )
        
        if st.button("🚨 确认删除并回算余额"):
            with st.spinner('正在云端执行撤回并反向核算余额，请稍候...'):
                row_to_delete = df_trans_with_idx[df_trans_with_idx['index'] == del_idx].iloc[0]
                acc = row_to_delete['account']
                amt = float(row_to_delete['amount'])
                
                # 1. 剔除选中的这行，准备写回新的流水表
                df_trans_new = df_trans_with_idx[df_trans_with_idx['index'] != del_idx].drop(columns=['index'])
                
                # 2. 从余额表中执行反向加减法
                df_balances_new = df_balances.copy()
                b_idx = df_balances_new.index[df_balances_new['account'] == acc].tolist()
                if b_idx:
                    df_balances_new.loc[b_idx[0], 'balance'] -= amt
                
                # 3. 双重更新覆盖云端数据
                conn.update(worksheet="transactions", data=df_trans_new)
                conn.update(worksheet="balances", data=df_balances_new)
                
            st.success(f"✅ 成功撤回！已删除该记录，并将 SGD {amt} 从 {acc} 的云端账本中反向调平。")
            st.rerun()
            
    else:
        st.write("暂无流水记录。")
