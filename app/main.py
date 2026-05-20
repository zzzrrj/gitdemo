import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="学生会物资借用管理系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 数据库配置 ====================
engine = create_engine('sqlite:///material.db', connect_args={'check_same_thread': False})
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


# ==================== 数据模型（增强版） ====================
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    student_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Integer, default=0)  # 0学生,1社团负责人,2超级管理员
    department = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    icon = Column(String(50), default="📦")
    sort_order = Column(Integer, default=0)


class Material(Base):
    __tablename__ = 'materials'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer)
    total_quantity = Column(Integer, default=1)
    available_quantity = Column(Integer, default=1)
    location = Column(String(100))
    image_url = Column(String(500))
    status = Column(Integer, default=1)  # 0下架,1正常
    warning_threshold = Column(Integer, default=0)
    description = Column(Text)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class BorrowApplication(Base):
    __tablename__ = 'borrow_applications'
    id = Column(Integer, primary_key=True)
    application_no = Column(String(32), unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    material_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)
    purpose = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Integer, default=0)  # 0待审批,1已通过,2已拒绝,3已归还,4逾期
    approver_id = Column(Integer)
    approve_remark = Column(String(255))
    actual_return_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ReturnRecord(Base):
    __tablename__ = 'return_records'
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, nullable=False)
    return_quantity = Column(Integer, default=1)
    damage_desc = Column(String(500))
    handled_by = Column(Integer)
    return_time = Column(DateTime, default=datetime.now)


class OperationLog(Base):
    __tablename__ = 'operation_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    operation = Column(String(100))
    target_id = Column(Integer)
    detail = Column(Text)
    ip = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


# ==================== 创建所有表 ====================
Base.metadata.create_all(engine)


# ==================== 工具函数 ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def generate_application_no() -> str:
    return f"BR{datetime.now().strftime('%Y%m%d%H%M%S')}{datetime.now().microsecond // 1000:03d}"


def log_operation(user_id: int, operation: str, target_id: int = None, detail: str = None):
    log = OperationLog(
        user_id=user_id,
        operation=operation,
        target_id=target_id,
        detail=detail
    )
    session.add(log)
    session.commit()


def get_current_user() -> Optional[User]:
    if 'user_id' in st.session_state:
        return session.query(User).filter(User.id == st.session_state.user_id).first()
    return None


def login(student_id: str, password: str) -> bool:
    user = session.query(User).filter(User.student_id == student_id).first()
    if user and check_password(password, user.password):
        user.last_login = datetime.now()
        session.commit()
        st.session_state.user_id = user.id
        log_operation(user.id, "登录")
        return True
    return False


def get_material_with_category(material: Material):
    """获取物资及其分类名"""
    category = session.query(Category).filter(Category.id == material.category_id).first()
    return {
        'id': material.id,
        'name': material.name,
        'category': category.name if category else '未分类',
        'category_icon': category.icon if category else '📦',
        'total_quantity': material.total_quantity,
        'available_quantity': material.available_quantity,
        'location': material.location,
        'status': material.status,
        'description': material.description
    }


# ==================== 初始化数据 ====================
def init_data():
    # 初始化分类
    if session.query(Category).count() == 0:
        categories = [
            Category(name="相机", icon="📷", sort_order=1),
            Category(name="帐篷", icon="🏕️", sort_order=2),
            Category(name="展板", icon="📋", sort_order=3),
            Category(name="音响", icon="🔊", sort_order=4),
            Category(name="桌椅", icon="🪑", sort_order=5),
            Category(name="其他", icon="📦", sort_order=99),
        ]
        for c in categories:
            session.add(c)
        session.commit()

    # 获取分类ID
    cat_map = {c.name: c.id for c in session.query(Category).all()}

    # 初始化用户
    if session.query(User).count() == 0:
        users = [
            User(student_id='admin', name='系统管理员', password=hash_password('123456'),
                 role=2, department='学生会', phone='13800000000'),
            User(student_id='2024001', name='张三', password=hash_password('123456'),
                 role=0, department='摄影社', phone='13800000001'),
            User(student_id='2024002', name='李四', password=hash_password('123456'),
                 role=1, department='学生会', phone='13800000002'),
            User(student_id='2024003', name='王五', password=hash_password('123456'),
                 role=0, department='舞蹈社', phone='13800000003'),
        ]
        for u in users:
            session.add(u)
        session.commit()

    # 初始化物资
    if session.query(Material).count() == 0:
        materials = [
            Material(name='佳能EOS 200D', category_id=cat_map.get('相机', 1),
                     total_quantity=3, available_quantity=3, location='器材室A01',
                     warning_threshold=1, description='入门级单反相机，适合活动拍摄'),
            Material(name='索尼A6400', category_id=cat_map.get('相机', 1),
                     total_quantity=2, available_quantity=2, location='器材室A02',
                     warning_threshold=1, description='专业微单，4K视频拍摄'),
            Material(name='3人帐篷', category_id=cat_map.get('帐篷', 2),
                     total_quantity=5, available_quantity=5, location='仓储区B01',
                     warning_threshold=2, description='户外露营帐篷，含防潮垫'),
            Material(name='折叠展板90x120', category_id=cat_map.get('展板', 3),
                     total_quantity=10, available_quantity=10, location='仓储区C01',
                     warning_threshold=3, description='可折叠展示板，双面可用'),
            Material(name='便携音响', category_id=cat_map.get('音响', 4),
                     total_quantity=4, available_quantity=4, location='器材室A03',
                     warning_threshold=1, description='蓝牙音响，续航8小时'),
            Material(name='折叠桌椅套装', category_id=cat_map.get('桌椅', 5),
                     total_quantity=6, available_quantity=6, location='仓储区D01',
                     warning_threshold=2, description='一桌四椅，方便携带'),
            Material(name='手持稳定器', category_id=cat_map.get('相机', 1),
                     total_quantity=2, available_quantity=2, location='器材室A04',
                     warning_threshold=1, description='手机/相机两用稳定器'),
        ]
        for m in materials:
            session.add(m)
        session.commit()


init_data()


# ==================== 业务服务类 ====================
class MaterialService:
    @staticmethod
    def get_all_materials(category_id: int = None, keyword: str = None) -> List:
        query = session.query(Material).filter(Material.status == 1)
        if category_id:
            query = query.filter(Material.category_id == category_id)
        if keyword:
            query = query.filter(Material.name.contains(keyword))
        return [get_material_with_category(m) for m in query.all()]

    @staticmethod
    def get_low_stock_materials():
        """获取库存预警物资"""
        return session.query(Material).filter(
            Material.available_quantity <= Material.warning_threshold,
            Material.status == 1
        ).all()

    @staticmethod
    def add_material(data: dict, user_id: int) -> bool:
        try:
            material = Material(
                name=data['name'],
                category_id=data['category_id'],
                total_quantity=data['total_quantity'],
                available_quantity=data['total_quantity'],
                location=data.get('location', ''),
                warning_threshold=data.get('warning_threshold', 0),
                description=data.get('description', ''),
                created_by=user_id
            )
            session.add(material)
            session.commit()
            log_operation(user_id, "添加物资", material.id, f"添加物资：{data['name']}")
            return True
        except Exception as e:
            session.rollback()
            return False

    @staticmethod
    def update_material(material_id: int, data: dict, user_id: int) -> bool:
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            if material:
                for key, value in data.items():
                    if hasattr(material, key) and value is not None:
                        setattr(material, key, value)
                session.commit()
                log_operation(user_id, "编辑物资", material_id)
                return True
        except Exception as e:
            session.rollback()
        return False


class BorrowService:
    @staticmethod
    def apply_borrow(user_id: int, material_id: int, quantity: int,
                     purpose: str, start_time: datetime, end_time: datetime) -> tuple:
        """返回 (成功标志, 消息)"""
        material = session.query(Material).filter(Material.id == material_id).first()
        if not material:
            return False, "物资不存在"
        if material.available_quantity < quantity:
            return False, f"库存不足，当前可用：{material.available_quantity}"
        if start_time >= end_time:
            return False, "开始时间必须早于结束时间"
        if start_time < datetime.now():
            return False, "开始时间不能早于当前时间"

        try:
            application = BorrowApplication(
                application_no=generate_application_no(),
                user_id=user_id,
                material_id=material_id,
                quantity=quantity,
                purpose=purpose,
                start_time=start_time,
                end_time=end_time,
                status=0
            )
            session.add(application)
            # 预扣库存
            material.available_quantity -= quantity
            session.commit()
            log_operation(user_id, "申请借用", application.id, f"申请 {material.name} x{quantity}")
            return True, f"申请成功！单号：{application.application_no}"
        except Exception as e:
            session.rollback()
            return False, f"申请失败：{str(e)}"

    @staticmethod
    def approve_application(application_id: int, approver_id: int,
                            approved: bool, remark: str = None) -> tuple:
        application = session.query(BorrowApplication).filter(
            BorrowApplication.id == application_id
        ).first()
        if not application:
            return False, "申请不存在"
        if application.status != 0:
            return False, "该申请已被处理"

        try:
            if approved:
                application.status = 1
                msg = "审批通过"
            else:
                application.status = 2
                application.approve_remark = remark
                # 拒绝时恢复库存
                material = session.query(Material).filter(
                    Material.id == application.material_id
                ).first()
                if material:
                    material.available_quantity += application.quantity
                msg = "已拒绝"

            application.approver_id = approver_id
            session.commit()
            log_operation(approver_id, "审批借用", application_id,
                          f"{msg} - {remark if remark else ''}")
            return True, msg
        except Exception as e:
            session.rollback()
            return False, f"操作失败：{str(e)}"

    @staticmethod
    def return_material(application_id: int, user_id: int,
                        damage_desc: str = None) -> tuple:
        application = session.query(BorrowApplication).filter(
            BorrowApplication.id == application_id
        ).first()
        if not application:
            return False, "申请不存在"
        if application.status != 1:
            return False, "只有已通过的申请才能归还"
        if application.actual_return_time:
            return False, "已归还过"

        try:
            application.status = 3
            application.actual_return_time = datetime.now()

            # 恢复库存
            material = session.query(Material).filter(
                Material.id == application.material_id
            ).first()
            if material:
                material.available_quantity += application.quantity

            # 记录归还详情
            return_record = ReturnRecord(
                application_id=application_id,
                return_quantity=application.quantity,
                damage_desc=damage_desc,
                handled_by=user_id
            )
            session.add(return_record)
            session.commit()

            log_operation(user_id, "归还物资", application_id,
                          f"归还 {material.name if material else ''} x{application.quantity}")
            return True, "归还成功"
        except Exception as e:
            session.rollback()
            return False, f"归还失败：{str(e)}"

    @staticmethod
    def check_overdue():
        """检查并更新逾期申请"""
        overdue_apps = session.query(BorrowApplication).filter(
            BorrowApplication.status == 1,
            BorrowApplication.end_time < datetime.now(),
            BorrowApplication.actual_return_time.is_(None)
        ).all()

        for app in overdue_apps:
            app.status = 4
        session.commit()
        return len(overdue_apps)


class StatisticsService:
    @staticmethod
    def get_dashboard_stats():
        """获取看板统计数据"""
        total_materials = session.query(Material).count()
        total_borrows = session.query(BorrowApplication).count()
        pending_count = session.query(BorrowApplication).filter(
            BorrowApplication.status == 0
        ).count()
        active_borrows = session.query(BorrowApplication).filter(
            BorrowApplication.status == 1,
            BorrowApplication.actual_return_time.is_(None)
        ).count()
        overdue_count = session.query(BorrowApplication).filter(
            BorrowApplication.status == 4
        ).count()
        low_stock = len(MaterialService.get_low_stock_materials())

        return {
            'total_materials': total_materials,
            'total_borrows': total_borrows,
            'pending': pending_count,
            'active': active_borrows,
            'overdue': overdue_count,
            'low_stock': low_stock
        }

    @staticmethod
    def get_borrow_trend(days: int = 7):
        """获取借用趋势数据"""
        start_date = datetime.now() - timedelta(days=days)
        results = session.query(
            func.date(BorrowApplication.created_at).label('date'),
            func.count(BorrowApplication.id).label('count')
        ).filter(
            BorrowApplication.created_at >= start_date
        ).group_by(
            func.date(BorrowApplication.created_at)
        ).all()

        dates = [r[0] for r in results]
        counts = [r[1] for r in results]
        return dates, counts

    @staticmethod
    def get_category_stats():
        """获取各分类借用统计"""
        results = session.query(
            Category.name,
            Category.icon,
            func.count(BorrowApplication.id).label('borrow_count')
        ).join(
            Material, Material.category_id == Category.id
        ).join(
            BorrowApplication, BorrowApplication.material_id == Material.id
        ).group_by(
            Category.id
        ).all()

        return results

    @staticmethod
    def get_top_borrowed_materials(limit: int = 5):
        """获取借用最多的物资"""
        results = session.query(
            Material.name,
            func.sum(BorrowApplication.quantity).label('total_borrowed')
        ).join(
            BorrowApplication, BorrowApplication.material_id == Material.id
        ).group_by(
            Material.id
        ).order_by(
            func.sum(BorrowApplication.quantity).desc()
        ).limit(limit).all()

        return results


# ==================== UI页面 ====================

def login_page():
    st.markdown("""
        <style>
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            max-width: 450px;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.image("https://img.icons8.com/fluency/96/box.png", width=80)
        st.title("📦 学生会物资借用管理系统")
        st.markdown("---")

        with st.form("login_form"):
            student_id = st.text_input("📚 学号", placeholder="请输入学号")
            password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
            submitted = st.form_submit_button("登录", use_container_width=True)

            if submitted:
                if login(student_id, password):
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("学号或密码错误")

        st.markdown("---")
        st.caption("测试账号：")
        st.caption("• 管理员：admin / 123456")
        st.caption("• 学生：2024001 / 123456")
        st.caption("• 负责人：2024002 / 123456")
        st.markdown('</div>', unsafe_allow_html=True)


def student_page():
    user = get_current_user()

    # 侧边栏
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/student-center.png", width=60)
        st.markdown(f"### 👤 {user.name}")
        st.markdown(f"📚 {user.student_id} | {user.department or '未设置部门'}")
        st.markdown("---")

        menu = st.radio(
            "功能导航",
            ["🏠 物资大厅", "📝 我的申请", "📋 借用记录", "ℹ️ 个人资料"],
            index=0
        )

        if st.button("🚪 退出登录", use_container_width=True):
            del st.session_state['user_id']
            st.rerun()

    # 检查逾期
    BorrowService.check_overdue()

    if menu == "🏠 物资大厅":
        material_page()
    elif menu == "📝 我的申请":
        my_applications_page(user.id)
    elif menu == "📋 借用记录":
        borrow_history_page(user.id)
    else:
        profile_page(user)


def material_page():
    st.title("🏠 物资大厅")

    # 搜索和筛选
    col1, col2 = st.columns([3, 1])
    with col1:
        keyword = st.text_input("🔍 搜索物资", placeholder="输入物资名称...")
    with col2:
        categories = [("全部", 0)] + [(c.name, c.id) for c in session.query(Category).all()]
        selected_cat_name = st.selectbox("📂 分类筛选", [c[0] for c in categories])
        selected_cat_id = next((c[1] for c in categories if c[0] == selected_cat_name), 0)

    # 库存预警提示
    low_stock = MaterialService.get_low_stock_materials()
    if low_stock:
        st.warning(f"⚠️ 有 {len(low_stock)} 种物资库存不足，请管理员及时补充！")

    # 获取物资列表
    materials = MaterialService.get_all_materials(
        category_id=selected_cat_id if selected_cat_id != 0 else None,
        keyword=keyword if keyword else None
    )

    # 卡片展示
    cols_per_row = 3
    for i in range(0, len(materials), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(materials):
                m = materials[i + j]
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {m['category_icon']} {m['name']}")
                        st.caption(f"分类：{m['category']} | 位置：{m['location']}")
                        st.markdown(f"**可用数量：** `{m['available_quantity']} / {m['total_quantity']}`")
                        if m['description']:
                            st.caption(f"📝 {m['description'][:50]}")

                        progress = m['available_quantity'] / m['total_quantity'] if m['total_quantity'] > 0 else 0
                        st.progress(progress, text=f"可用率 {progress * 100:.0f}%")

                        if m['available_quantity'] > 0:
                            if st.button("📝 申请借用", key=f"apply_{m['id']}"):
                                st.session_state['apply_material_id'] = m['id']
                                st.rerun()
                        else:
                            st.button("❌ 暂不可用", disabled=True, key=f"disabled_{m['id']}")

    # 申请弹窗
    if 'apply_material_id' in st.session_state:
        apply_dialog(st.session_state['apply_material_id'])


def apply_dialog(material_id: int):
    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        del st.session_state['apply_material_id']
        return

    with st.form("apply_form"):
        st.subheader(f"申请借用：{material.name}")

        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("借用数量", min_value=1, max_value=material.available_quantity, value=1)
        with col2:
            purpose = st.text_area("借用用途", placeholder="请说明借用用途（如：社团招新活动）")

        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("开始日期", min_value=datetime.now().date())
            start_time = st.time_input("开始时间", value=datetime.now().time())
        with col4:
            end_date = st.date_input("预计归还日期", min_value=start_date)
            end_time = st.time_input("预计归还时间", value=datetime.now().time())

        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)

        submitted = st.form_submit_button("提交申请", use_container_width=True)
        cancel = st.form_submit_button("取消", use_container_width=True)

        if submitted:
            if not purpose.strip():
                st.error("请填写借用用途")
            else:
                success, msg = BorrowService.apply_borrow(
                    get_current_user().id, material_id, quantity,
                    purpose, start_datetime, end_datetime
                )
                if success:
                    st.success(msg)
                    del st.session_state['apply_material_id']
                    st.rerun()
                else:
                    st.error(msg)

        if cancel:
            del st.session_state['apply_material_id']
            st.rerun()


def my_applications_page(user_id: int):
    st.title("📝 我的申请")

    applications = session.query(BorrowApplication).filter(
        BorrowApplication.user_id == user_id
    ).order_by(BorrowApplication.created_at.desc()).all()

    status_map = {
        0: ("⏳ 待审批", "🟡"),
        1: ("✅ 已通过", "🟢"),
        2: ("❌ 已拒绝", "🔴"),
        3: ("🔁 已归还", "⚪"),
        4: ("⚠️ 逾期", "🔴")
    }

    for app in applications:
        material = session.query(Material).filter(Material.id == app.material_id).first()
        status_text, status_color = status_map.get(app.status, ("未知", "⚪"))

        with st.expander(
                f"{status_color} {app.application_no} - {material.name if material else '未知'} x{app.quantity} - {status_text}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**用途：** {app.purpose}")
                st.markdown(
                    f"**借用时间：** {app.start_time.strftime('%Y-%m-%d %H:%M')} 至 {app.end_time.strftime('%Y-%m-%d %H:%M')}")
            with col2:
                if app.approve_remark:
                    st.info(f"审批备注：{app.approve_remark}")
                if app.actual_return_time:
                    st.success(f"实际归还：{app.actual_return_time.strftime('%Y-%m-%d %H:%M')}")

            # 归还按钮
            if app.status == 1 and not app.actual_return_time:
                if st.button("🔁 归还物资", key=f"return_{app.id}"):
                    success, msg = BorrowService.return_material(app.id, user_id, None)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def borrow_history_page(user_id: int):
    st.title("📋 历史借用记录")

    applications = session.query(BorrowApplication).filter(
        BorrowApplication.user_id == user_id
    ).order_by(BorrowApplication.created_at.desc()).all()

    data = []
    for app in applications:
        material = session.query(Material).filter(Material.id == app.material_id).first()
        data.append({
            "单号": app.application_no,
            "物资名称": material.name if material else "未知",
            "数量": app.quantity,
            "用途": app.purpose[:30] + "..." if len(app.purpose) > 30 else app.purpose,
            "状态": ["待审批", "已通过", "已拒绝", "已归还", "逾期"][app.status],
            "申请时间": app.created_at.strftime("%Y-%m-%d %H:%M")
        })

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无借用记录")


def admin_page():
    user = get_current_user()

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/admin-settings-male.png", width=60)
        st.markdown(f"### 👑 {user.name}")
        st.markdown(f"角色：{'超级管理员' if user.role == 2 else '社团负责人'}")
        st.markdown("---")

        menu = st.radio(
            "管理功能",
            ["📊 数据看板", "⏳ 待审批申请", "📦 物资管理", "👥 用户管理", "📜 所有借用记录", "📈 统计分析"],
            index=0
        )

        if st.button("🚪 退出登录", use_container_width=True):
            del st.session_state['user_id']
            st.rerun()

    BorrowService.check_overdue()

    if menu == "📊 数据看板":
        dashboard_page()
    elif menu == "⏳ 待审批申请":
        pending_approvals_page()
    elif menu == "📦 物资管理":
        material_manage_page()
    elif menu == "👥 用户管理":
        user_manage_page()
    elif menu == "📜 所有借用记录":
        all_borrows_page()
    else:
        statistics_page()


def dashboard_page():
    st.title("📊 数据看板")

    stats = StatisticsService.get_dashboard_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📦 物资总数", stats['total_materials'])
    with col2:
        st.metric("📝 总借用次数", stats['total_borrows'])
    with col3:
        st.metric("⏳ 待审批", stats['pending'], delta="需处理" if stats['pending'] > 0 else None)
    with col4:
        st.metric("🔁 借用中", stats['active'])
    with col5:
        st.metric("⚠️ 逾期未还", stats['overdue'], delta="⚠️ 紧急" if stats['overdue'] > 0 else None)

    # 库存预警
    low_stock = MaterialService.get_low_stock_materials()
    if low_stock:
        with st.expander("⚠️ 库存预警物资", expanded=True):
            for m in low_stock:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{m.name}**")
                with col2:
                    st.write(f"可用：{m.available_quantity} / {m.total_quantity}")
                with col3:
                    st.warning(f"低于阈值 {m.warning_threshold}")

    # 借用趋势图
    st.subheader("📈 近7天借用趋势")
    dates, counts = StatisticsService.get_borrow_trend(7)
    if dates:
        fig = px.line(x=dates, y=counts, markers=True, labels={'x': '日期', 'y': '申请数量'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")


def pending_approvals_page():
    st.title("⏳ 待审批申请")

    pending = session.query(BorrowApplication).filter(
        BorrowApplication.status == 0
    ).order_by(BorrowApplication.created_at).all()

    if not pending:
        st.success("暂无待审批申请")
        return

    for app in pending:
        student = session.query(User).filter(User.id == app.user_id).first()
        material = session.query(Material).filter(Material.id == app.material_id).first()

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**单号：** {app.application_no}")
                st.markdown(f"**申请人：** {student.name} ({student.student_id})")
                st.markdown(f"**物资：** {material.name} x{app.quantity}")
            with col2:
                st.markdown(f"**用途：** {app.purpose}")
                st.markdown(
                    f"**借用时间：** {app.start_time.strftime('%m-%d %H:%M')} 至 {app.end_time.strftime('%m-%d %H:%M')}")
            with col3:
                if st.button("✅ 通过", key=f"approve_{app.id}"):
                    success, msg = BorrowService.approve_application(app.id, get_current_user().id, True)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                remark = st.text_input("拒绝理由", key=f"remark_{app.id}", placeholder="选填")
                if st.button("❌ 拒绝", key=f"reject_{app.id}"):
                    success, msg = BorrowService.approve_application(app.id, get_current_user().id, False, remark)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def material_manage_page():
    st.title("📦 物资管理")

    # 添加物资表单
    with st.expander("➕ 添加新物资", expanded=False):
        with st.form("add_material_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("物资名称*")
                categories = {c.name: c.id for c in session.query(Category).all()}
                category = st.selectbox("分类*", list(categories.keys()))
            with col2:
                total_quantity = st.number_input("总数量*", min_value=1, value=1)
                location = st.text_input("存放位置")

            warning_threshold = st.number_input("库存预警阈值", min_value=0, value=0)
            description = st.text_area("物资描述")

            submitted = st.form_submit_button("添加物资")
            if submitted and name:
                success = MaterialService.add_material({
                    'name': name,
                    'category_id': categories[category],
                    'total_quantity': total_quantity,
                    'location': location,
                    'warning_threshold': warning_threshold,
                    'description': description
                }, get_current_user().id)
                if success:
                    st.success("添加成功")
                    st.rerun()
                else:
                    st.error("添加失败")

    # 物资列表管理
    st.subheader("📋 物资列表")
    materials = session.query(Material).order_by(Material.created_at.desc()).all()

    for m in materials:
        category = session.query(Category).filter(Category.id == m.category_id).first()
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.markdown(f"**{m.name}**")
                st.caption(f"分类：{category.name if category else '未知'}")
            with col2:
                new_total = st.number_input("总数量", value=m.total_quantity, key=f"total_{m.id}",
                                            label_visibility="collapsed")
                if new_total != m.total_quantity:
                    diff = new_total - m.total_quantity
                    m.total_quantity = new_total
                    m.available_quantity += diff
                    session.commit()
                    st.rerun()
                st.caption(f"可用：{m.available_quantity}")
            with col3:
                new_location = st.text_input("位置", value=m.location or "", key=f"loc_{m.id}",
                                             label_visibility="collapsed")
                if new_location != m.location:
                    m.location = new_location
                    session.commit()
                    st.rerun()
            with col4:
                if st.button("🗑️ 删除", key=f"del_{m.id}"):
                    session.delete(m)
                    session.commit()
                    st.rerun()

            if m.description:
                st.caption(f"📝 {m.description}")


def user_manage_page():
    st.title("👥 用户管理")

    users = session.query(User).all()
    data = []
    for u in users:
        role_text = ["学生", "社团负责人", "超级管理员"][u.role] if u.role <= 2 else "未知"
        data.append({
            "ID": u.id,
            "学号": u.student_id,
            "姓名": u.name,
            "角色": role_text,
            "部门": u.department or "-",
            "电话": u.phone or "-",
            "最后登录": u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "-"
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 添加用户
    with st.expander("➕ 添加用户"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_student_id = st.text_input("学号*")
                new_name = st.text_input("姓名*")
                new_role = st.selectbox("角色", ["学生", "社团负责人", "超级管理员"])
            with col2:
                new_password = st.text_input("密码*", type="password")
                new_department = st.text_input("部门")
                new_phone = st.text_input("电话")

            submitted = st.form_submit_button("添加用户")
            if submitted and new_student_id and new_name and new_password:
                role_map = {"学生": 0, "社团负责人": 1, "超级管理员": 2}
                new_user = User(
                    student_id=new_student_id,
                    name=new_name,
                    password=hash_password(new_password),
                    role=role_map[new_role],
                    department=new_department,
                    phone=new_phone
                )
                session.add(new_user)
                session.commit()
                st.success("添加成功")
                st.rerun()


def all_borrows_page():
    st.title("📜 所有借用记录")

    applications = session.query(BorrowApplication).order_by(BorrowApplication.created_at.desc()).all()

    data = []
    for app in applications:
        student = session.query(User).filter(User.id == app.user_id).first()
        material = session.query(Material).filter(Material.id == app.material_id).first()
        data.append({
            "单号": app.application_no,
            "申请人": f"{student.name} ({student.student_id})" if student else "-",
            "物资": material.name if material else "-",
            "数量": app.quantity,
            "用途": app.purpose[:50] + "..." if len(app.purpose) > 50 else app.purpose,
            "状态": ["待审批", "已通过", "已拒绝", "已归还", "逾期"][app.status],
            "申请时间": app.created_at.strftime("%Y-%m-%d %H:%M")
        })

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 导出按钮
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 导出Excel", csv, "borrow_records.csv", "text/csv")


def statistics_page():
    st.title("📈 统计分析")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 各分类借用统计")
        cat_stats = StatisticsService.get_category_stats()
        if cat_stats:
            fig = px.pie(values=[c[2] for c in cat_stats],
                         names=[f"{c[1]} {c[0]}" for c in cat_stats],
                         title="借用分布")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏆 最热门物资")
        top_materials = StatisticsService.get_top_borrowed_materials(5)
        if top_materials:
            fig = px.bar(x=[m[1] for m in top_materials],
                         y=[m[0] for m in top_materials],
                         orientation='h',
                         title="借用次数Top5")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def profile_page(user: User):
    st.title("ℹ️ 个人资料")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("姓名", value=user.name)
            department = st.text_input("部门", value=user.department or "")
        with col2:
            phone = st.text_input("电话", value=user.phone or "")
            email = st.text_input("邮箱", value=user.email or "")

        submitted = st.form_submit_button("保存修改")
        if submitted:
            user.name = name
            user.department = department
            user.phone = phone
            user.email = email
            session.commit()
            st.success("保存成功")
            st.rerun()

    st.divider()

    # 修改密码
    with st.expander("🔐 修改密码"):
        with st.form("password_form"):
            old_pwd = st.text_input("原密码", type="password")
            new_pwd = st.text_input("新密码", type="password")
            confirm_pwd = st.text_input("确认新密码", type="password")

            if st.form_submit_button("修改密码"):
                if not check_password(old_pwd, user.password):
                    st.error("原密码错误")
                elif len(new_pwd) < 6:
                    st.error("新密码长度至少6位")
                elif new_pwd != confirm_pwd:
                    st.error("两次输入的新密码不一致")
                else:
                    user.password = hash_password(new_pwd)
                    session.commit()
                    st.success("密码修改成功，请重新登录")
                    del st.session_state['user_id']
                    st.rerun()


# ==================== 主程序 ====================
def main():
    if 'user_id' not in st.session_state:
        login_page()
    else:
        user = get_current_user()
        if user and user.role >= 1:
            admin_page()
        else:
            student_page()


if __name__ == "__main__":
    main()