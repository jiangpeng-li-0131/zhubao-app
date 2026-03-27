import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components  # [新增] 用于注入高级界面的工具库

# ================= 页面配置 =================
# [美化 1] 网页标签图标改成了猪鼻子 🐽
st.set_page_config(page_title="猪宝成长记账本", layout="centered", page_icon="🐽")

# [美化 2] 注入代码：强行告诉苹果手机，使用我们上传的图片作为桌面图标
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
# [美化 3] 侧边栏变得极简，不再显示设置项
with st.sidebar:
    st.title("🐽 家庭财务终端")
    st.markdown("---")
    menu = st.radio("导航菜单", ["📊 资产大盘看板", "📝 每月常规审计", "🛠️ 强制平账/修正", "📜 历史流水查询"])

# ================= 模块 1: 资产大盘看板 =================
if menu == "📊 资产大盘看板":
    
    # [美化 4] 将汇率设置做成了可折叠的小抽屉，放在看板最上方
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

    # [新增核心逻辑] 动态颜色函数：负数显示为醒目的红色
    def get_color(val, default_color):
        return "#e63946" if val < 0 else default_color

    # 计算总数
    j_personal = balances.get('Jacob', 0)
    a_personal = balances.get('Amanda', 0)
    j_zhu = balances.get('猪宝成长基金(Jacob代持)', 0)
    a_zhu = balances.get('猪宝成长基金(Amanda代持)', 0)
    total_zhu = j_zhu + a_zhu
    total_family = j_personal + a_personal + total_zhu

    # [美化 5] 使用高级 HTML 样式渲染的彩色数据卡片
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 30px;">
            <p style="margin: 0; font-size: 16px; opacity: 0.8; text-transform: uppercase; letter-spacing: 2px;">家庭总资产净值 (Total Net Worth)</p>
            <h1 style="margin: 10px 0 0 0; font-size: 3rem; font-weight: 800;">{display_currency(total_family)}</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🍼 猪宝成长基金 (共同账户)")
    
    # [动态 UI] 如果基金总额为负，背景变成清冷灰+红色警告边框；正数则保持猛男粉
    bg_style = "background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); border-left: 5px solid #ff758c;" if total_zhu >= 0 else "background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-left: 5px solid #e63946;"

    st.markdown(f"""
        <div style="{bg_style} padding: 20px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; font-size: 14px; color: #555; font-weight: 600;">基金总余额</p>
                    <h2 style="margin: 5px 0 0 0; color: {get_color(total_zhu, '#333')};">{display_currency(total_zhu)}</h2>
                </div>
                <div style="text-align: right;">
                    <p style="margin: 0; font-size: 13px; color: #555;">Jacob 银行卡代持: <br><b style="color: {get_color(j_zhu, '#555')};">{display_currency(j_zhu)}</b></p>
                    <p style="margin: 10px 0 0 0; font-size: 13px; color: #555;">Amanda 银行卡代持: <br><b style="color: {get_color(a_zhu, '#555')};">{display_currency(a_zhu)}</b></p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👤 个人流动资金")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #6c757d; font-weight: 600;">Jacob 个人账本</p>
                <h3 style="margin: 10px 0 0 0; color: {get_color(j_personal, '#212529')};">{display_currency(j_personal)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; text-align: center;">
                <p style="margin: 0; font-size: 14px; color: #6c757d; font-weight: 600;">Amanda 个人账本</p>
                <h3 style="margin: 10px 0 0 0; color: {get_color(a_personal, '#212529')};">{display_currency(a_personal)}</h3>
            </div>
        """, unsafe_allow_html=True)
        
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

    j_to_zhubao = j_income - j_to_personal
    a_to_zhubao = a_income - a_to_personal
    j_zhubao_net = j_to_zhubao - j_zhubao_expense
    a_zhubao_net = a_to_zhubao - a_zhubao_expense
    
    st.markdown("---")
    st.markdown("### 📊 本月结算核对预览")
    
    col_j, col_a = st.columns(2)
    with col_j:
        st.write("👨🏻 **Jacob 的账户变动**")
        st.write(f"📥 存入个人: SGD {j_to_personal:,.2f}")
        st.write(f"📥 划入代持: SGD {j_to_zhubao:,.2f}")
        st.write(f"📤 推算开销: SGD {j_zhubao_expense:,.2f}")
        
        j_color = "#28a745" if j_zhubao_net >= 0 else "#dc3545"
        j_sign = "+" if j_zhubao_net >= 0 else ""
        st.markdown(f"**本月代持基金净增减: <br><span style='color:{j_color}; font-size:20px;'>{j_sign}SGD {j_zhubao_net:,.2f}</span>**", unsafe_allow_html=True)

    with col_a:
        st.write("👩🏻 **Amanda 的账户变动**")
        st.write(f"📥 存入个人: SGD {a_to_personal:,.2f}")
        st.write(f"📥 划入代持: SGD {a_to_zhubao:,.2f}")
        st.write(f"📤 推算开销: SGD {a_zhubao_expense:,.2f}")
        
        a_color = "#28a745" if a_zhubao_net >= 0 else "#dc3545"
        a_sign = "+" if a_zhubao_net >= 0 else ""
        st.markdown(f"**本月代持基金净增减: <br><span style='color:{a_color}; font-size:20px;'>{a_sign}SGD {a_zhubao_net:,.2f}</span>**", unsafe_allow_html=True)
    
    if st.button("✅ 确认数据无误，同步至云端"):
        with st.spinner('🚀 正在将账目加密同步至 Google 云端... \n (由于免费服务器限制，保存后可能会出现短暂的断开连接。请放心，数据瞬间即安全入库！稍等片刻刷新即可)'):
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
        filter_acc = st.multiselect(
            "筛选账本", 
            ["Jacob", "Amanda", "猪宝成长基金(Jacob代持)", "猪宝成长基金(Amanda代持)"], 
            default=[]
        )
        
        df_display = df_transactions.iloc[::-1].copy()
        if filter_acc:
            df_display = df_display[df_display['account'].isin(filter_acc)]
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🗑️ 撤销流水记录")
        st.warning("⚠️ 删除流水后，系统会自动将该笔金额从云端的对应账本中「反向核算」回去。")
        
        df_trans_with_idx = df_transactions.reset_index()
        df_trans_with_idx_reverse = df_trans_with_idx.iloc[::-1]
        
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
                
                df_trans_new = df_trans_with_idx[df_trans_with_idx['index'] != del_idx].drop(columns=['index'])
                
                df_balances_new = df_balances.copy()
                b_idx = df_balances_new.index[df_balances_new['account'] == acc].tolist()
                if b_idx:
                    df_balances_new.loc[b_idx[0], 'balance'] -= amt
                
                conn.update(worksheet="transactions", data=df_trans_new)
                conn.update(worksheet="balances", data=df_balances_new)
                
            st.success(f"✅ 成功撤回！已删除该记录，并将 SGD {amt} 从 {acc} 的云端账本中反向调平。")
            st.rerun()
            
    else:
        st.write("暂无流水记录。")