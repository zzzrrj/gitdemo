from flask import Blueprint, jsonify, request
from database import get_db
from datetime import datetime, timedelta

statistics_bp = Blueprint('statistics', __name__)

def safe_execute(db_query, params=(), fetch_one=False, fetch_all=False):
    """封装数据库操作，自动处理连接关闭与异常"""
    conn = get_db()
    try:
        cursor = conn.execute(db_query, params)
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e  # 抛出给上层统一处理
    finally:
        conn.close()

@statistics_bp.route('/statistics/dashboard', methods=['GET'])
def get_dashboard():
    """获取看板统计数据（合并查询 + 异常捕获）"""
    try:
        # 一次查询获取所有计数，使用 CASE WHEN 统计不同状态的申请
        query = """
            SELECT 
                (SELECT COUNT(*) FROM materials) AS total_materials,
                (SELECT COUNT(*) FROM borrow_applications WHERE status IN (1, 3)) AS total_borrows,
                (SELECT COUNT(*) FROM borrow_applications WHERE status = 0) AS pending,
                (SELECT COUNT(*) FROM borrow_applications WHERE status = 1) AS approved,
                (SELECT COUNT(*) FROM borrow_applications WHERE status = 3) AS returned
        """
        row = safe_execute(query, fetch_one=True)
        total_materials, total_borrows, pending, approved, returned = row

        # 各分类物资数量
        categories = safe_execute(
            "SELECT category, COUNT(*) as count FROM materials GROUP BY category",
            fetch_all=True
        )
        categories_list = [dict(cat) for cat in categories]

        return jsonify({
            'code': 200,
            'data': {
                'total_materials': total_materials,
                'total_borrows': total_borrows,
                'pending': pending,
                'approved': approved,
                'returned': returned,
                'categories': categories_list
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500

@statistics_bp.route('/statistics/trend', methods=['GET'])
def get_trend():
    """获取借用趋势（可指定天数，默认7天，只统计有效借用）"""
    try:
        days = request.args.get('days', default=7, type=int)
        if days <= 0:
            days = 7

        # 计算起始日期
        start_date = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
        # 查询有效借用（status=1已批准 或 3已归还）按日期分组
        query = """
            SELECT date(created_at) as date, COUNT(*) as count
            FROM borrow_applications
            WHERE status IN (1, 3) AND date(created_at) >= ?
            GROUP BY date(created_at)
            ORDER BY date
        """
        rows = safe_execute(query, (start_date,), fetch_all=True)
        data_map = {row[0]: row[1] for row in rows}

        # 补全缺失的日期（返回连续 days 天）
        trend_data = []
        current = datetime.now().date() - timedelta(days=days-1)
        for _ in range(days):
            date_str = current.strftime('%Y-%m-%d')
            trend_data.append({
                'date': date_str,
                'count': data_map.get(date_str, 0)
            })
            current += timedelta(days=1)

        return jsonify({'code': 200, 'data': trend_data})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500

@statistics_bp.route('/statistics/popular', methods=['GET'])
def get_popular_materials():
    """获取热门物资Top N（默认5，可指定，只统计有效借用）"""
    try:
        limit = request.args.get('limit', default=5, type=int)
        if limit <= 0:
            limit = 5

        query = """
            SELECT m.name, COUNT(*) as borrow_count
            FROM borrow_applications a
            JOIN materials m ON a.material_id = m.id
            WHERE a.status IN (1, 3)  -- 只统计已批准或已归还的借出
            GROUP BY m.id
            ORDER BY borrow_count DESC
            LIMIT ?
        """
        popular = safe_execute(query, (limit,), fetch_all=True)
        return jsonify({'code': 200, 'data': [dict(p) for p in popular]})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500