from flask import Blueprint, request, jsonify
from database import get_db
import hashlib

user_bp = Blueprint('user', __name__)

@user_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    hashed = hashlib.sha256(data['password'].encode()).hexdigest()
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE student_id=? AND password=?", 
        (data['student_id'], hashed)
    ).fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'code': 200, 
            'data': {
                'id': user['id'], 
                'name': user['name'], 
                'student_id': user['student_id'],
                'role': user['role']
            }
        })
    return jsonify({'code': 401, 'message': '学号或密码错误'})

@user_bp.route('/users', methods=['GET'])
def get_users():
    """获取所有用户（管理员用）"""
    conn = get_db()
    users = conn.execute("SELECT id, student_id, name, role, department FROM users").fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(u) for u in users]})

@user_bp.route('/user/<int:id>', methods=['GET'])
def get_user(id):
    """获取单个用户信息"""
    conn = get_db()
    user = conn.execute("SELECT id, student_id, name, role, department FROM users WHERE id=?", (id,)).fetchone()
    conn.close()
    if user:
        return jsonify({'code': 200, 'data': dict(user)})
    return jsonify({'code': 404, 'message': '用户'})

material_bp = Blueprint('material', __name__)

@material_bp.route('/materials', methods=['GET'])
def get_materials():
    """获取物资列表（支持分类筛选和关键词搜索）"""
    category = request.args.get('category')
    keyword = request.args.get('keyword')
    conn = get_db()
    
    if category:
        materials = conn.execute(
            "SELECT * FROM materials WHERE category=?", 
            (category,)
        ).fetchall()
    elif keyword:
        materials = conn.execute(
            "SELECT * FROM materials WHERE name LIKE ?", 
            (f'%{keyword}%',)
        ).fetchall()
    else:
        materials = conn.execute("SELECT * FROM materials").fetchall()
    
    conn.close()
    return jsonify({'code': 200, 'data': [dict(m) for m in materials]})

@material_bp.route('/materials/<int:id>', methods=['GET'])
def get_material(id):
    """获取单个物资详情"""
    conn = get_db()
    material = conn.execute("SELECT * FROM materials WHERE id=?", (id,)).fetchone()
    conn.close()
    if material:
        return jsonify({'code': 200, 'data': dict(material)})
    return jsonify({'code': 404, 'message': '物资不存在'})

@material_bp.route('/categories', methods=['GET'])
def get_categories():
    """获取所有物资分类"""
    conn = get_db()
    categories = conn.execute("SELECT DISTINCT category FROM materials").fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [c['category'] for c in categories]})
