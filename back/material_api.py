from flask import Blueprint, request, jsonify
from database import get_db

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