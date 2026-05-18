import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="统计模块 - 数据看板", page_icon="📊", layout="wide")

conn = sqlite3.connect('material.db', check_same_thread=False)
c = conn.cursor()

# 获取统计数据
def get_stats():
    c.execute("SELECT COUNT(*) FROM materials")
    total_materials = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM borrow_applications")
    total_borrows = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=0")
    pending = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=1 AND actual_return_time IS NULL")
    active = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=4 OR (status=1 AND julianday('now') - julianday(end_time) > 0)")
    overdue = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    return {
        "total_materials": total_materials,
        "total_borrows": total_borrows,
        "pending": pending,
        "active": active,
        "overdue": overdue,
        "total_users": total_users
    }

# 获取借用趋势
def get_trend(days=7):
    c.execute("""SELECT date(created_at) as date, COUNT(*) as count
                 FROM borrow_applications
                 WHERE created_at >= date('now', ?)
                 GROUP BY date(created_at)
                 ORDER BY date""", (f'-{days} days',))
    return c.fetchall()

# 获取分类统计
def get_category_stats():
    c.execute("""SELECT m.category, COUNT(*) as count
                 FROM borrow_applications a
                 JOIN materials m ON a.material_id = m.id
                 GROUP BY m.category""")
    return c.fetchall()

# 获取热门物资
def get_top_materials(limit=5):
    c.execute("""SELECT m.name, SUM(a.quantity) as total
                 FROM borrow_applications a
                 JOIN materials m ON a.material_id = m.id
                 GROUP BY m.id
                 ORDER BY total DESC
                 LIMIT ?""", (limit,))
    return c.fetchall()

st.title("📊 数据统计看板")
st.markdown("物资借用系统的数据分析和可视化")

# 指标卡片
stats = get_stats()

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("📦 物资总数", stats["total_materials"])
with col2:
    st.metric("📝 总借用次数", stats["total_borrows"])
with col3:
    st.metric("⏳ 待审批", stats["pending"], delta="需处理" if stats["pending"] > 0 else None)
with col4:
    st.metric("🔁 借用中", stats["active"])
with col5:
    st.metric("⚠️ 逾期", stats["overdue"], delta="⚠️" if stats["overdue"] > 0 else None)
with col6:
    st.metric("👥 用户数", stats["total_users"])

st.divider()

# 图表区域
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 借用趋势")
    trend = get_trend(7)
    if trend:
        df_trend = pd.DataFrame(trend, columns=["日期", "数量"])
        fig = px.line(df_trend, x="日期", y="数量", markers=True, title="近7天借用申请量")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

with col2:
    st.subheader("🏷️ 分类统计")
    cat_stats = get_category_stats()
    if cat_stats:
        df_cat = pd.DataFrame(cat_stats, columns=["分类", "借用次数"])
        fig = px.pie(df_cat, values="借用次数", names="分类", title="各分类借用占比")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

# 第二行图表
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 最热门物资")
    top = get_top_materials(5)
    if top:
        df_top = pd.DataFrame(top, columns=["物资名称", "借用次数"])
        fig = px.bar(df_top, x="借用次数", y="物资名称", orientation='h', title="借用次数Top5")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

with col2:
    st.subheader("📊 库存概览")
    c.execute("SELECT name, available_quantity, total_quantity FROM materials")
    materials = c.fetchall()
    if materials:
        df_inv = pd.DataFrame(materials, columns=["物资名称", "可用", "总量"])
        df_inv["可用率"] = df_inv["可用"] / df_inv["总量"] * 100
        fig = px.bar(df_inv, x="物资名称", y="可用率", title="物资可用率", color="可用率", range_y=[0, 100])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

st.divider()

# 详细数据表格
with st.expander("📋 详细借用记录"):
    c.execute("""SELECT a.application_no, u.name as user, m.name as material, a.quantity, a.purpose, a.start_time, a.end_time,
                        CASE a.status
                            WHEN 0 THEN '待审批'
                            WHEN 1 THEN '已通过'
                            WHEN 2 THEN '已拒绝'
                            WHEN 3 THEN '已归还'
                            ELSE '逾期'
                        END as status
                 FROM borrow_applications a
                 JOIN users u ON a.user_id = u.id
                 JOIN materials m ON a.material_id = m.id
                 ORDER BY a.created_at DESC
                 LIMIT 50""")
    records = c.fetchall()
    if records:
        df = pd.DataFrame(records, columns=["单号", "申请人", "物资", "数量", "用途", "开始时间", "结束时间", "状态"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无借用记录")