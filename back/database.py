import sqlite3
import hashlib

DB_PATH = 'material.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE,
        name TEXT,
        password TEXT,
        role INTEGER DEFAULT 0,
        department TEXT
    )''')
    
    # 物资表
    c.execute('''CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        total_quantity INTEGER DEFAULT 1,
        available_quantity INTEGER DEFAULT 1,
        location TEXT
    )''')
    
    # 借用申请表
    c.execute('''CREATE TABLE IF NOT EXISTS borrow_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_no TEXT,
        user_id INTEGER,
        material_id INTEGER,
        quantity INTEGER,
        purpose TEXT,
        status INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    
    # 初始化用户数据
    c.execute("SELECT * FROM users WHERE student_id='admin'")
    if not c.fetchone():
        users = [
            ('admin', '管理员', hashlib.sha256('123456'.encode()).hexdigest(), 2, '学生会'),
            ('2024001', '张三', hashlib.sha256('123456'.encode()).hexdigest(), 0, '摄影社'),
            ('2024002', '李四', hashlib.sha256('123456'.encode()).hexdigest(), 1, '学生会'),
        ]
        c.executemany("INSERT INTO users (student_id, name, password, role, department) VALUES (?,?,?,?,?)", users)
    
    # 初始化物资数据
    c.execute("SELECT * FROM materials")
    if not c.fetchone():
        materials = [
            ('佳能EOS 200D', '相机', 3, 3, '器材室A01'),
            ('索尼A6400', '相机', 2, 2, '器材室A02'),
            ('3人帐篷', '帐篷', 5, 5, '仓储区B01'),
            ('折叠展板', '展板', 10, 10, '仓储区C01'),
            ('便携音响', '音响', 4, 4, '器材室A03'),
            ('折叠桌椅套装', '桌椅', 6, 6, '仓储区D01'),
        ]
        c.executemany("INSERT INTO materials (name, category, total_quantity, available_quantity, location) VALUES (?,?,?,?,?)", materials)
    
    conn.commit()
    conn.close()

# 初始化数据库
init_db()