from flask import Blueprint, jsonify
from database import get_db

statistics_bp = Blueprint('statistics', __name__)

@statistics_bp.route('/statistics/dashboard', methods=['GET'])
def get_dashboard():
    """获取看板统计数据"""
    conn = get_db()
    
    total_materials = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    total_borrows = conn.execute("SELECT COUNT(*) FROM borrow_applications").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=0").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=1").fetchone()[0]
    returned = conn.execute("SELECT COUNT(*) FROM borrow_applications WHERE status=3").fetchone()[0]
    
    # 各分类物资数量
    categories = conn.execute("""
        SELECT category, COUNT(*) as count 
        FROM materials 
        GROUP BY category
    """).fetchall()
    
    conn.close()
    
    return jsonify({'code': 200, 'data': {
        'total_materials': total_materials,
        'total_borrows': total_borrows,
        'pending': pending,
        'approved': approved,
        'returned': returned,
        'categories': [dict(c) for c in categories]
    }})

@statistics_bp.route('/statistics/trend', methods=['GET'])
def get_trend():
    """获取借用趋势（近7天）"""
    conn = get_db()
    trend = conn.execute("""
        SELECT date(created_at) as date, COUNT(*) as count
        FROM borrow_applications
        WHERE created_at >= date('now', '-7 days')
        GROUP BY date(created_at)
        ORDER BY date
    """).fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(t) for t in trend]})

@statistics_bp.route('/statistics/popular', methods=['GET'])
def get_popular_materials():
    """获取热门物资Top5"""
    conn = get_db()
    popular = conn.execute("""
        SELECT m.name, COUNT(*) as borrow_count
        FROM borrow_applications a
        JOIN materials m ON a.material_id = m.id
        GROUP BY m.id
        ORDER BY borrow_count DESC
        LIMIT 5
    """).fetchall()
    conn.close()
    return jsonify({'code': 200, 'data': [dict(p) for p in popular]})