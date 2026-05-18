from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime, timedelta
import threading

borrow_bp = Blueprint('borrow', __name__)

# 简单的库存锁（生产环境应用Redis）
material_locks = {}

def get_lock(material_id):
    """获取物资锁"""
    if material_id not in material_locks:
        material_locks[material_id] = threading.Lock()
    return material_locks[material_id]

def generate_application_no():
    """生成唯一申请单号：BR + 年月日时分秒 + 毫秒 + 随机数"""
    now = datetime.now()
    base = now.strftime('%Y%m%d%H%M%S')
    ms = f"{now.microsecond // 1000:03d}"
    import random
    rand = f"{random.randint(0, 99):02d}"
    return f"BR{base}{ms}{rand}"

def check_overdue():
    """检查并标记逾期申请"""
    conn = get_db()
    now = datetime.now().isoformat()
    # 标记逾期：已通过(status=1)且结束时间小于当前时间且未归还
    conn.execute("""
        UPDATE borrow_applications 
        SET status = 4 
        WHERE status = 1 
        AND actual_return_time IS NULL 
        AND end_time < ?
    """, (now,))
    conn.commit()
    conn.close()

@borrow_bp.route('/borrow/apply', methods=['POST'])
def apply_borrow():
    """提交借用申请（带库存锁防超卖）"""
    data = request.json
    
    # === 参数校验 ===
    required_fields = ['user_id', 'material_id', 'quantity', 'purpose']
    for field in required_fields:
        if field not in data:
            return jsonify({'code': 400, 'message': f'缺少参数: {field}'})
    
    user_id = data['user_id']
    material_id = data['material_id']
    quantity = data['quantity']
    purpose = data['purpose'].strip()
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    # 数量校验
    if quantity <= 0:
        return jsonify({'code': 400, 'message': '借用数量必须大于0'})
    
    if quantity > 100:
        return jsonify({'code': 400, 'message': '单次借用数量不能超过100'})
    
    # 用途校验
    if not purpose:
        return jsonify({'code': 400, 'message': '请填写借用用途'})
    
    if len(purpose) > 500:
        return jsonify({'code': 400, 'message': '用途描述不能超过500字'})
    
    # 时间校验
    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            now = datetime.now()
            
            if start >= end:
                return jsonify({'code': 400, 'message': '开始时间必须早于结束时间'})
            
            if start < now:
                return jsonify({'code': 400, 'message': '开始时间不能早于当前时间'})
            
            if end > now + timedelta(days=30):
                return jsonify({'code': 400, 'message': '借用期限不能超过30天'})
        except ValueError:
            return jsonify({'code': 400, 'message': '时间格式错误'})
    
    # === 使用锁防止超卖 ===
    lock = get_lock(material_id)
    with lock:
        conn = get_db()
        
        # 检查物资是否存在
        material = conn.execute(
            "SELECT id, name, available_quantity, total_quantity FROM materials WHERE id=?", 
            (material_id,)
        ).fetchone()
        
        if not material:
            conn.close()
            return jsonify({'code': 404, 'message': '物资不存在'})
        
        # 检查库存
        if material['available_quantity'] < quantity:
            conn.close()
            return jsonify({
                'code': 400, 
                'message': f'库存不足，当前可用：{material["available_quantity"]}，你申请：{quantity}'
            })
        
        # 生成唯一单号
        app_no = generate_application_no()
        
        # 创建申请记录
        try:
            conn.execute("""
                INSERT INTO borrow_applications 
                (application_no, user_id, material_id, quantity, purpose, 
                 start_time, end_time, status, created_at) 
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                app_no, user_id, material_id, quantity, purpose,
                start_time, end_time, 0, datetime.now().isoformat()
            ))
            
            # 扣减库存
            conn.execute(
                "UPDATE materials SET available_quantity = available_quantity - ? WHERE id=?", 
                (quantity, material_id)
            )
            conn.commit()
            
            return jsonify({
                'code': 200, 
                'message': '申请成功',
                'data': {
                    'application_no': app_no,
                    'material_name': material['name'],
                    'quantity': quantity,
                    'status': '待审批'
                }
            })
        except Exception as e:
            conn.rollback()
            return jsonify({'code': 500, 'message': f'申请失败：{str(e)}'})
        finally:
            conn.close()

@borrow_bp.route('/borrow/my/<int:user_id>', methods=['GET'])
def get_my_applications(user_id):
    """获取我的借用申请（增强版：包含状态文本和可操作判断）"""
    # 先检查逾期
    check_overdue()
    
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, m.name as material_name, m.category
        FROM borrow_applications a 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.user_id=? 
        ORDER BY a.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    
    status_map = {
        0: {'text': '待审批', 'type': 'warning'},
        1: {'text': '已通过', 'type': 'success'},
        2: {'text': '已拒绝', 'type': 'danger'},
        3: {'text': '已归还', 'type': 'info'},
        4: {'text': '逾期', 'type': 'danger'}
    }
    
    result = []
    for a in apps:
        app_dict = dict(a)
        app_dict['status_text'] = status_map.get(a['status'], {'text': '未知'})['text']
        app_dict['status_type'] = status_map.get(a['status'], {'type': 'info'})['type']
        # 判断是否可以归还（已通过且未归还且未逾期）
        app_dict['can_return'] = (a['status'] == 1 and a['actual_return_time'] is None)
        result.append(app_dict)
    
    return jsonify({'code': 200, 'data': result})

@borrow_bp.route('/borrow/pending', methods=['GET'])
def get_pending():
    """获取待审批申请（负责人/管理员用）"""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, u.name as user_name, u.student_id, u.department, 
               m.name as material_name, m.category
        FROM borrow_applications a 
        JOIN users u ON a.user_id = u.id 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.status=0 
        ORDER BY a.created_at ASC
    """).fetchall()
    conn.close()
    
    result = []
    for a in apps:
        app_dict = dict(a)
        # 格式化时间显示
        if a['start_time']:
            app_dict['start_time_display'] = a['start_time'][:16] if len(a['start_time']) > 16 else a['start_time']
        if a['end_time']:
            app_dict['end_time_display'] = a['end_time'][:16] if len(a['end_time']) > 16 else a['end_time']
        result.append(app_dict)
    
    return jsonify({'code': 200, 'data': result})

@borrow_bp.route('/borrow/approve/<int:id>', methods=['POST'])
def approve_borrow(id):
    """审批申请（1通过, 2拒绝）"""
    data = request.json
    status = data.get('status')
    remark = data.get('remark', '').strip()
    
    if status not in [1, 2]:
        return jsonify({'code': 400, 'message': '无效的审批状态'})
    
    # 拒绝时必须填写理由
    if status == 2 and not remark:
        return jsonify({'code': 400, 'message': '拒绝时请填写理由'})
    
    conn = get_db()
    
    # 获取申请信息
    application = conn.execute("""
        SELECT a.*, m.name as material_name 
        FROM borrow_applications a 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.id=?
    """, (id,)).fetchone()
    
    if not application:
        conn.close()
        return jsonify({'code': 404, 'message': '申请不存在'})
    
    if application['status'] != 0:
        conn.close()
        return jsonify({'code': 400, 'message': f'该申请已被处理，当前状态：{application["status"]}'})
    
    try:
        if status == 2:  # 拒绝，恢复库存
            conn.execute(
                "UPDATE materials SET available_quantity = available_quantity + ? WHERE id=?", 
                (application['quantity'], application['material_id'])
            )
        
        # 更新申请状态
        conn.execute("""
            UPDATE borrow_applications 
            SET status=?, approve_remark=?, updated_at=? 
            WHERE id=?
        """, (status, remark, datetime.now().isoformat(), id))
        conn.commit()
        
        return jsonify({
            'code': 200, 
            'message': '审批通过' if status == 1 else '已拒绝',
            'data': {
                'application_no': application['application_no'],
                'material_name': application['material_name'],
                'quantity': application['quantity']
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'})
    finally:
        conn.close()

@borrow_bp.route('/borrow/return/<int:id>', methods=['POST'])
def return_material(id):
    """归还物资"""
    conn = get_db()
    
    # 获取申请信息
    application = conn.execute("""
        SELECT a.*, m.name as material_name, m.id as material_id
        FROM borrow_applications a 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.id=?
    """, (id,)).fetchone()
    
    if not application:
        conn.close()
        return jsonify({'code': 404, 'message': '借用记录不存在'})
    
    if application['status'] != 1:
        status_msg = {0: '待审批', 2: '已拒绝', 3: '已归还', 4: '逾期'}.get(application['status'], '未知')
        conn.close()
        return jsonify({'code': 400, 'message': f'当前状态为"{status_msg}"，无法归还'})
    
    if application['actual_return_time']:
        conn.close()
        return jsonify({'code': 400, 'message': '该物资已归还过'})
    
    try:
        # 恢复库存
        conn.execute(
            "UPDATE materials SET available_quantity = available_quantity + ? WHERE id=?", 
            (application['quantity'], application['material_id'])
        )
        
        # 更新申请状态
        conn.execute("""
            UPDATE borrow_applications 
            SET status=3, actual_return_time=?, updated_at=? 
            WHERE id=?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), id))
        conn.commit()
        
        return jsonify({
            'code': 200, 
            'message': '归还成功',
            'data': {
                'application_no': application['application_no'],
                'material_name': application['material_name'],
                'quantity': application['quantity']
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'message': f'归还失败：{str(e)}'})
    finally:
        conn.close()

@borrow_bp.route('/borrow/all', methods=['GET'])
def get_all_applications():
    """获取所有借用记录（管理员用）"""
    check_overdue()
    
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    status = request.args.get('status', type=int)
    
    offset = (page - 1) * size
    
    conn = get_db()
    
    # 构建查询
    query = """
        SELECT a.*, u.name as user_name, u.student_id, m.name as material_name 
        FROM borrow_applications a 
        JOIN users u ON a.user_id = u.id 
        JOIN materials m ON a.material_id = m.id 
        WHERE 1=1
    """
    params = []
    
    if status is not None:
        query += " AND a.status = ?"
        params.append(status)
    
    query += " ORDER BY a.created_at DESC LIMIT ? OFFSET ?"
    params.extend([size, offset])
    
    apps = conn.execute(query, params).fetchall()
    
    # 获取总数
    count_query = "SELECT COUNT(*) FROM borrow_applications"
    if status is not None:
        count_query += f" WHERE status = {status}"
    total = conn.execute(count_query).fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'code': 200, 
        'data': [dict(a) for a in apps],
        'pagination': {'page': page, 'size': size, 'total': total, 'pages': (total + size - 1) // size}
    })

@borrow_bp.route('/borrow/detail/<int:id>', methods=['GET'])
def get_application_detail(id):
    """获取申请详情"""
    conn = get_db()
    app = conn.execute("""
        SELECT a.*, u.name as user_name, u.student_id, u.department, u.phone,
               m.name as material_name, m.category, m.location
        FROM borrow_applications a 
        JOIN users u ON a.user_id = u.id 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.id=?
    """, (id,)).fetchone()
    conn.close()
    
    if not app:
        return jsonify({'code': 404, 'message': '记录不存在'})
    
    return jsonify({'code': 200, 'data': dict(app)})