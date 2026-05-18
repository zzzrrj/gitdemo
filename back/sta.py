from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

borrow_bp = Blueprint('borrow', __name__)

def generate_application_no():
    """生成申请单号"""
    return f"BR{datetime.now().strftime('%Y%m%d%H%M%S')}"

@borrow_bp.route('/borrow/apply', methods=['POST'])
def apply_borrow():
    """提交借用申请"""
    data = request.json
    app_no = generate_application_no()
    conn = get_db()
    
    # 检查库存
    material = conn.execute(
        "SELECT available_quantity FROM materials WHERE id=?", 
        (data['material_id'],)
    ).fetchone()
    
    if not material or material['available_quantity'] < data['quantity']:
        conn.close()
        return jsonify({'code': 400, 'message': '库存不足'})
    
    # 扣减库存
    conn.execute(
        "UPDATE materials SET available_quantity = available_quantity - ? WHERE id=?", 
        (data['quantity'], data['material_id'])
    )
    conn.execute(
        """INSERT INTO borrow_applications 
           (application_no, user_id, material_id, quantity, purpose, created_at) 
           VALUES (?,?,?,?,?,?)""",
        (app_no, data['user_id'], data['material_id'], data['quantity'], 
         data['purpose'], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({'code': 200, 'message': '申请成功', 'data': {'application_no': app_no}})

@borrow_bp.route('/borrow/my/<int:user_id>', methods=['GET'])
def get_my_applications(user_id):
    """获取我的借用申请"""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, m.name as material_name 
        FROM borrow_applications a 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.user_id=? 
        ORDER BY a.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(a) for a in apps]})

@borrow_bp.route('/borrow/pending', methods=['GET'])
def get_pending():
    """获取待审批申请（负责人/管理员用）"""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, u.name as user_name, u.student_id, m.name as material_name 
        FROM borrow_applications a 
        JOIN users u ON a.user_id = u.id 
        JOIN materials m ON a.material_id = m.id 
        WHERE a.status=0 
        ORDER BY a.created_at
    """).fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(a) for a in apps]})

@borrow_bp.route('/borrow/approve/<int:id>', methods=['POST'])
def approve_borrow(id):
    """审批申请（1通过, 2拒绝）"""
    data = request.json
    conn = get_db()
    
    if data['status'] == 2:  # 拒绝，恢复库存
        app = conn.execute(
            "SELECT material_id, quantity FROM borrow_applications WHERE id=?", 
            (id,)
        ).fetchone()
        conn.execute(
            "UPDATE materials SET available_quantity = available_quantity + ? WHERE id=?", 
            (app['quantity'], app['material_id'])
        )
    
    conn.execute("UPDATE borrow_applications SET status=? WHERE id=?", (data['status'], id))
    conn.commit()
    conn.close()
    return jsonify({'code': 200, 'message': '操作成功'})

@borrow_bp.route('/borrow/return/<int:id>', methods=['POST'])
def return_material(id):
    """归还物资"""
    conn = get_db()
    app = conn.execute(
        "SELECT material_id, quantity FROM borrow_applications WHERE id=?", 
        (id,)
    ).fetchone()
    
    if app:
        # 恢复库存
        conn.execute(
            "UPDATE materials SET available_quantity = available_quantity + ? WHERE id=?", 
            (app['quantity'], app['material_id'])
        )
        # 更新申请状态
        conn.execute(
            "UPDATE borrow_applications SET status=3 WHERE id=?", 
            (id,)
        )
        conn.commit()
    
    conn.close()
    return jsonify({'code': 200, 'message': '归还成功'})

@borrow_bp.route('/borrow/all', methods=['GET'])
def get_all_applications():
    """获取所有借用记录（管理员用）"""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, u.name as user_name, m.name as material_name 
        FROM borrow_applications a 
        JOIN users u ON a.user_id = u.id 
        JOIN materials m ON a.material_id = m.id 
        ORDER BY a.created_at DESC
    """).fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(a) for a in apps]})