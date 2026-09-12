"""
Executes tool calls by invoking the real backend logic.
Each function returns a dict that gets sent back to Grok.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.models import (
    User, Student, Teacher, Course, Enrollment,
    TeacherCourse, Timetable, AttendanceSession, AttendanceRecord,
)
from app.security import hash_password


# =========================================================
# ADMIN EXECUTORS
# =========================================================
def exec_create_student(db: Session, args: dict) -> dict:
    if db.query(User).filter(User.email == args["email"]).first():
        return {"error": "Email already exists"}
    if db.query(Student).filter(Student.roll_number == args["roll_number"]).first():
        return {"error": "Roll number already exists"}

    user = User(
        email=args["email"],
        password_hash=hash_password(args["password"]),
        full_name=args["full_name"],
        role="student",
    )
    db.add(user)
    db.flush()

    student = Student(
        user_id=user.id,
        roll_number=args["roll_number"],
        batch_year=args["batch_year"],
    )
    db.add(student)
    db.commit()
    return {"success": True, "user_id": user.id, "message": f"Student {args['full_name']} created"}


def exec_create_teacher(db: Session, args: dict) -> dict:
    if db.query(User).filter(User.email == args["email"]).first():
        return {"error": "Email already exists"}
    if db.query(Teacher).filter(Teacher.employee_code == args["employee_code"]).first():
        return {"error": "Employee code already exists"}

    user = User(
        email=args["email"],
        password_hash=hash_password(args["password"]),
        full_name=args["full_name"],
        role="teacher",
    )
    db.add(user)
    db.flush()

    teacher = Teacher(
        user_id=user.id,
        employee_code=args["employee_code"],
        designation=args.get("designation", "Lecturer"),
    )
    db.add(teacher)
    db.commit()
    return {"success": True, "user_id": user.id, "message": f"Teacher {args['full_name']} created"}


def exec_add_course(db: Session, args: dict) -> dict:
    if db.query(Course).filter(Course.code == args["code"]).first():
        return {"error": "Course code already exists"}

    course = Course(
        code=args["code"],
        title=args["title"],
        credits=args["credits"],
    )
    db.add(course)
    db.commit()
    return {"success": True, "course_id": course.id, "message": f"Course {args['code']} added"}


# =========================================================
# TEACHER EXECUTORS
# =========================================================
def exec_get_my_courses_teacher(db: Session, current_user: User) -> dict:
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        return {"error": "Teacher profile not found"}

    tcs = db.query(TeacherCourse).filter(TeacherCourse.teacher_id == teacher.id).all()
    courses = []
    for tc in tcs:
        course = db.query(Course).filter(Course.id == tc.course_id).first()
        if course:
            enrolled = db.query(func.count(Enrollment.id)).filter(
                Enrollment.course_id == course.id, Enrollment.status == "active"
            ).scalar()
            courses.append({
                "code": course.code,
                "title": course.title,
                "credits": course.credits,
                "enrolled_students": enrolled,
            })
    return {"courses": courses, "count": len(courses)}


def exec_get_course_students(db: Session, current_user: User, args: dict) -> dict:
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        return {"error": "Teacher profile not found"}

    course = db.query(Course).filter(Course.code == args["course_code"]).first()
    if not course:
        return {"error": f"Course {args['course_code']} not found"}

    tc = db.query(TeacherCourse).filter(
        TeacherCourse.teacher_id == teacher.id,
        TeacherCourse.course_id == course.id,
    ).first()
    if not tc:
        return {"error": "You are not assigned to this course"}

    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course.id,
        Enrollment.status == "active"
    ).all()

    students = []

    for e in enrollments:
        s = db.query(Student).filter(Student.id == e.student_id).first()
        u = db.query(User).filter(User.id == s.user_id).first()

        sessions = db.query(AttendanceSession.id).filter(
            AttendanceSession.course_id == course.id
        ).subquery()

        total = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.student_id == s.id,
            AttendanceRecord.session_id.in_(sessions),
        ).scalar()

        present = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.student_id == s.id,
            AttendanceRecord.session_id.in_(sessions),
            AttendanceRecord.status == "present",
        ).scalar()

        attendance_percentage = (
            round((present / total) * 100, 1)
            if total
            else 0.0
        )

        students.append({
            "roll_number": s.roll_number,
            "full_name": u.full_name,
            "attendance_percentage": attendance_percentage,
        })

    return {"students": students, "count": len(students)}


# =========================================================
# STUDENT EXECUTORS
# =========================================================
def exec_get_my_attendance(db: Session, current_user: User) -> dict:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return {"error": "Student profile not found"}

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "active"
    ).all()

    summary = []
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        sessions = db.query(AttendanceSession.id).filter(
            AttendanceSession.course_id == course.id
        ).subquery()
        total = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.session_id.in_(sessions),
        ).scalar()
        present = db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.session_id.in_(sessions),
            AttendanceRecord.status == "present",
        ).scalar()
        pct = round((present / total) * 100, 1) if total else 0.0
        summary.append({
            "course_code": course.code,
            "course_title": course.title,
            "present": present,
            "total": total,
            "percentage": pct,
        })
    return {"courses": summary}


def exec_get_my_timetable(db: Session, current_user: User) -> dict:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return {"error": "Student profile not found"}

    course_ids = [e.course_id for e in db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "active"
    ).all()]

    if not course_ids:
        return {"timetable": []}

    slots = db.query(Timetable).filter(Timetable.course_id.in_(course_ids)).all()
    result = []
    for t in slots:
        course = db.query(Course).filter(Course.id == t.course_id).first()
        result.append({
            "day": t.day_of_week,
            "start": str(t.start_time),
            "end": str(t.end_time),
            "course": course.code,
            "room": t.room,
        })
    return {"timetable": result}


def exec_get_my_courses_student(db: Session, current_user: User) -> dict:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return {"error": "Student profile not found"}

    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student.id, Enrollment.status == "active"
    ).all()
    courses = []
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        if course:
            courses.append({
                "code": course.code,
                "title": course.title,
                "credits": course.credits,
            })
    return {"courses": courses}

# =========================================================
# ADMIN EXECUTORS — LIST & DELETE
# =========================================================
def exec_list_users(db: Session, args: dict) -> dict:
    """List students or teachers for the admin to review."""
    role = args.get("role", "student")

    if role == "student":
        students = db.query(Student).all()
        rows = []
        for s in students:
            u = db.query(User).filter(User.id == s.user_id).first()
            if u:
                rows.append({
                    "roll_number": s.roll_number,
                    "full_name": u.full_name,
                    "email": u.email,
                })
        return {
            "role": "student",
            "count": len(rows),
            "users": rows,
            "hint": "Format each as: • Name (roll) — email",
        }

    if role == "teacher":
        teachers = db.query(Teacher).all()
        rows = []
        for t in teachers:
            u = db.query(User).filter(User.id == t.user_id).first()
            if u:
                rows.append({
                    "employee_code": t.employee_code,
                    "full_name": u.full_name,
                    "email": u.email,
                    "designation": t.designation,
                })
        return {
            "role": "teacher",
            "count": len(rows),
            "users": rows,
            "hint": "Format each as: • Name (code) — email · designation",
        }

    return {"error": f"Unknown role: {role}"}


def exec_delete_user(db: Session, args: dict) -> dict:
    """Delete a student or teacher by email, roll number, or employee code."""
    identifier = (args.get("identifier") or "").strip()
    confirm = args.get("confirm")

    if not identifier:
        return {"error": "No identifier provided"}
    if not confirm:
        return {
            "error": "Deletion not confirmed. Ask the admin to confirm before deleting."
        }

    # Try email first
    user = db.query(User).filter(User.email == identifier).first()

    # Try roll number (student)
    if not user:
        student = db.query(Student).filter(Student.roll_number == identifier).first()
        if student:
            user = db.query(User).filter(User.id == student.user_id).first()

    # Try employee code (teacher)
    if not user:
        teacher = db.query(Teacher).filter(Teacher.employee_code == identifier).first()
        if teacher:
            user = db.query(User).filter(User.id == teacher.user_id).first()

    if not user:
        return {"error": f"No user found matching '{identifier}'"}

    if user.role == "admin":
        return {"error": "Refusing to delete an admin account"}

    # Capture for the response before deletion
    deleted_name = user.full_name
    deleted_email = user.email
    deleted_role = user.role

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": f"Deleted {deleted_role} '{deleted_name}' ({deleted_email})",
    }
