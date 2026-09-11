from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, Time,
    ForeignKey, Numeric, DateTime, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False)   # admin | teacher | student
    phone = Column(String(20))
    avatar_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    roll_number = Column(String(30), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    batch_year = Column(Integer, nullable=False)
    current_semester = Column(Integer, default=1)
    cgpa = Column(Numeric(3, 2), default=0.00)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="student")


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_code = Column(String(30), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    designation = Column(String(60))
    joined_at = Column(Date)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="teacher")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text)
    credits = Column(Integer, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    semester = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class TeacherCourse(Base):
    __tablename__ = "teacher_courses"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("teacher_id", "course_id"),)


class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, server_default=func.now())
    status = Column(String(20), default="active")
    grade = Column(String(5))
    __table_args__ = (UniqueConstraint("student_id", "course_id"),)


class Timetable(Base):
    __tablename__ = "timetable"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(10), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String(30))
    semester = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(Integer, primary_key=True)
    timetable_id = Column(Integer, ForeignKey("timetable.id", ondelete="SET NULL"))
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    topic = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(10), nullable=False)  # present | absent | late | excused
    marked_at = Column(DateTime, server_default=func.now())
    note = Column(String(200))
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    audience = Column(String(20), default="all")
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    published_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)


class ChatLog(Base):
    __tablename__ = "chat_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False)  # 'user' | 'bot'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())