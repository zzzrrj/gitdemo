from flask import Flask, jsonify
from flask_cors import CORS
import sys

# 导入四个模块的蓝图
try:
    from user_api import user_bp
    from material_api import material_bp
    from borrow_api import borrow_bp
    from statistics_api import statistics_bp
except ImportError as e:
    print(f"❌ 蓝图导入失败: {e}")
    print("请确保以下文件存在: user_api.py, material_api.py, borrow_api.py, statistics_api.py")
    sys.exit(1)

# 验证蓝图是否成功导入
blueprints = {
    'user': user_bp,
    'material': material_bp,
    'borrow': borrow_bp,
    'statistics': statistics_bp
}

for name, bp in blueprints.items():
    if bp is None:
        print(f"❌ {name}_bp 为 None，请检查 {name}_api.py 中是否定义了 {name}_bp")
        sys.exit(1)

app = Flask(__name__)

# CORS 配置：允许前端开发服务器的地址
CORS(app, origins=[
    'http://localhost:5500',   # VS Code Live Server
    'http://127.0.0.1:5500',
    'http://localhost:8080',   # 前端直接打开
    'http://127.0.0.1:8080',
    'http://localhost:3000',   # Vue 开发服务器（备用）
], supports_credentials=True)

# 注册蓝图（统一前缀 /api）
for name, bp in blueprints.items():
    app.register_blueprint(bp, url_prefix='/api')
    print(f"✅ 已注册 {name} 模块蓝图")

@app.route('/')
def index():
    """根路径，返回API状态信息"""
    return jsonify({
        'message': '物资管理系统API已启动',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'user': '/api/login, /api/users',
            'material': '/api/materials, /api/categories',
            'borrow': '/api/borrow/apply, /api/borrow/pending, /api/borrow/approve/<id>',
            'statistics': '/api/statistics/dashboard, /api/statistics/trend'
        }
    })

@app.errorhandler(404)
def not_found(error):
    """处理404错误"""
    return jsonify({'code': 404, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("   📦 物资借用管理系统 - 后端服务")
    print("=" * 50)
    print(f"   启动地址: http://127.0.0.1:8080")
    print(f"   API文档:  http://127.0.0.1:8080")
    print("=" * 50)
    print("\n可用接口:")
    print("   POST   /api/login                    - 用户登录")
    print("   GET    /api/materials                - 获取物资列表")
    print("   GET    /api/categories               - 获取分类列表")
    print("   POST   /api/borrow/apply             - 提交借用申请")
    print("   GET    /api/borrow/my/<user_id>      - 获取我的申请")
    print("   GET    /api/borrow/pending           - 获取待审批列表")
    print("   POST   /api/borrow/approve/<id>      - 审批申请")
    print("   POST   /api/borrow/return/<id>       - 归还物资")
    print("   GET    /api/statistics/dashboard     - 获取看板数据")
    print("=" * 50 + "\n")
    
    try:
        app.run(debug=True, port=8080, host='0.0.0.0')
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 端口 8080 已被占用，请关闭占用程序或修改端口号")
        else:
            print(f"❌ 启动失败: {e}")
    except Exception as e:
        print(f"❌ 启动失败: {e}")