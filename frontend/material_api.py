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