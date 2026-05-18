from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

engine = create_engine('sqlite:///campus_activity.db', connect_args={'check_same_thread': False})
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    student_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Integer, default=0)  # 0学生, 1负责人, 2管理员
    department = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)

class Activity(Base):
    __tablename__ = 'activities'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    location = Column(String(200), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    max_participants = Column(Integer, default=50)
    registration_deadline = Column(DateTime, nullable=False)
    status = Column(Integer, default=1)  # 1进行中, 0已取消, 2已结束
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)

class Registration(Base):
    __tablename__ = 'registrations'
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activities.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(Integer, default=0)  # 0待确认, 1已确认, 2已取消
    remark = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)

class Checkin(Base):
    __tablename__ = 'checkins'
    id = Column(Integer, primary_key=True)
    registration_id = Column(Integer, ForeignKey('registrations.id'), unique=True)
    checkin_time = Column(DateTime, default=datetime.now)
    operator_id = Column(Integer, ForeignKey('users.id'))   # 签到操作人

Base.metadata.create_all(engine)