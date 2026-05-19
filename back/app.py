from flask import Flask
from flask_cors import CORS

# 导入四个模块的蓝图
from user_api import user_bp
from material_api import material_bp
from borrow_api import borrow_bp
from statistics_api import statistics_bp

app = Flask(__name__)
CORS(app)

# 注册蓝图（统一前缀 /api）
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(material_bp, url_prefix='/api')
app.register_blueprint(borrow_bp, url_prefix='/api')
app.register_blueprint(statistics_bp, url_prefix='/api')

@app.route('/')
def index():
    return jsonify({'message': '物资管理系统API已启动', 'status': 'running'})

if __name__ == '__main__':
    app.run(debug=True, port=8080)