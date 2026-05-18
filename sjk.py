import sqlite3

conn = sqlite3.connect('material.db')
c = conn.cursor()

# 创建物资表
c.execute('''CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    total_quantity INTEGER DEFAULT 0,
    available_quantity INTEGER DEFAULT 0
)''')

# 创建用户表
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)''')

# 创建借用申请表
c.execute('''CREATE TABLE IF NOT EXISTS borrow_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_no TEXT UNIQUE,
    user_id INTEGER,
    material_id INTEGER,
    quantity INTEGER,
    purpose TEXT,
    start_time TEXT,
    end_time TEXT,
    actual_return_time TEXT,
    status INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(material_id) REFERENCES materials(id)
)''')

# 插入演示数据（可选）
c.execute("INSERT OR IGNORE INTO materials (name, category, total_quantity, available_quantity) VALUES ('笔记本电脑', '电子设备', 10, 8)")
c.execute("INSERT OR IGNORE INTO materials (name, category, total_quantity, available_quantity) VALUES ('投影仪', '电子设备', 5, 3)")
c.execute("INSERT OR IGNORE INTO materials (name, category, total_quantity, available_quantity) VALUES ('课桌椅', '家具', 50, 42)")
c.execute("INSERT OR IGNORE INTO materials (name, category, total_quantity, available_quantity) VALUES ('白板', '文具', 20, 18)")

c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (1, '张三')")
c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (2, '李四')")

import datetime
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
c.execute("INSERT OR IGNORE INTO borrow_applications (application_no, user_id, material_id, quantity, purpose, start_time, end_time, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
          ('B001', 1, 1, 1, '项目演示', '2025-01-01', '2025-01-10', 1, now))
c.execute("INSERT OR IGNORE INTO borrow_applications (application_no, user_id, material_id, quantity, purpose, start_time, end_time, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
          ('B002', 2, 2, 1, '会议', '2025-03-01', '2025-03-05', 0, now))

conn.commit()
conn.close()
print("数据库表创建成功，并已插入示例数据！")