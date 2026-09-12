from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import require_roles
from app.models import (
    User, Student, Course, Enrollment, Teacher,
    TeacherCourse, Timetable, AttendanceSession, AttendanceRecord,
    Department, Announcement,
)

router = APIRouter(
    prefix="/api/student",
    tags=["student"],
    dependencies=[Depends(require_roles("student"))],
)


# =========================================================
# HELPER
# =========================================================
def _current_student(db: Session, current_user: User) -> Student:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(404, "Student profile not found")
    return student


# =========================================================
# DASHBOARD
# =========================================================
@router.get("/dashboard")
def student_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    student = _current_student(db, current_user)

    # Enrolled courses
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.status == "active")
        .all()
    )
    course_ids = [e.course_id for e in enrollments]
    total_courses = len(course_ids)

    # Attendance stats
    if course_ids:
        sessions = (
            db.query(AttendanceSession.id)
            .filter(AttendanceSession.course_id.in_(course_ids))
            .subquery()
        )
        total_records = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
            )
            .scalar()
        )
        present_records = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        attendance_pct = round((present_records / total_records) * 100, 1) if total_records else 0.0
    else:
        total_records = 0
        present_records = 0
        attendance_pct = 0.0

    # Today's classes
    from datetime import date as dt
    today = dt.today().strftime("%A").lower()
    today_slots = (
        db.query(Timetable)
        .filter(
            Timetable.course_id.in_(course_ids) if course_ids else False,
            Timetable.day_of_week == today,
        )
        .order_by(Timetable.start_time)
        .all()
    )
    today_classes = []
    for t in today_slots:
        course = db.query(Course).filter(Course.id == t.course_id).first()
        teacher = db.query(Teacher).filter(Teacher.id == t.teacher_id).first()
        teacher_user = db.query(User).filter(User.id == teacher.user_id).first() if teacher else None
        today_classes.append({
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "start_time": str(t.start_time),
            "end_time": str(t.end_time),
            "room": t.room,
            "teacher": teacher_user.full_name if teacher_user else "—",
        })

    # Recent announcements for students
    announcements = (
        db.query(Announcement)
        .filter(Announcement.audience.in_(["all", "students"]))
        .order_by(Announcement.published_at.desc())
        .limit(3)
        .all()
    )
    recent_announcements = [
        {
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        }
        for a in announcements
    ]

    return {
        "student_name": current_user.full_name,
        "roll_number": student.roll_number,
        "batch_year": student.batch_year,
        "current_semester": student.current_semester,
        "cgpa": float(student.cgpa or 0),
        "total_courses": total_courses,
        "attendance_percentage": attendance_pct,
        "present_count": present_records,
        "total_sessions": total_records,
        "today_classes": today_classes,
        "recent_announcements": recent_announcements,
    }


# =========================================================
# MY COURSES
# =========================================================
@router.get("/courses")
def my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    student = _current_student(db, current_user)
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.status == "active")
        .all()
    )
    result = []
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        if not course:
            continue
        # Teacher
        tc = db.query(TeacherCourse).filter(TeacherCourse.course_id == course.id).first()
        teacher_user = None
        if tc:
            teacher = db.query(Teacher).filter(Teacher.id == tc.teacher_id).first()
            if teacher:
                teacher_user = db.query(User).filter(User.id == teacher.user_id).first()

        # Attendance % for this course
        sessions = (
            db.query(AttendanceSession.id)
            .filter(AttendanceSession.course_id == course.id)
            .subquery()
        )
        total = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
            )
            .scalar()
        )
        present = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        pct = round((present / total) * 100, 1) if total else 0.0

        dept = None
        if course.department_id:
            d = db.query(Department).filter(Department.id == course.department_id).first()
            dept = d.name if d else None

        result.append({
            "id": course.id,
            "code": course.code,
            "title": course.title,
            "description": course.description,
            "credits": course.credits,
            "semester": course.semester,
            "department": dept,
            "teacher_name": teacher_user.full_name if teacher_user else "—",
            "attendance_percentage": pct,
            "present_count": present,
            "total_sessions": total,
            "grade": e.grade,
        })
    return result


# =========================================================
# ATTENDANCE — MY RECORDS
# =========================================================
@router.get("/attendance")
def my_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    student = _current_student(db, current_user)

    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceRecord.marked_at.desc())
        .all()
    )

    result = []
    for r in records:
        session = db.query(AttendanceSession).filter(AttendanceSession.id == r.session_id).first()
        if not session:
            continue
        course = db.query(Course).filter(Course.id == session.course_id).first()
        result.append({
            "id": r.id,
            "session_date": str(session.session_date),
            "topic": session.topic,
            "status": r.status,
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
        })

    # Per-course summary
    summary = []
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.status == "active")
        .all()
    )
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        if not course:
            continue
        sessions = (
            db.query(AttendanceSession.id)
            .filter(AttendanceSession.course_id == course.id)
            .subquery()
        )
        total = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
            )
            .scalar()
        )
        present = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(sessions),
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        pct = round((present / total) * 100, 1) if total else 0.0
        summary.append({
            "course_code": course.code,
            "course_title": course.title,
            "present": present,
            "total": total,
            "percentage": pct,
        })

    return {"records": result, "summary": summary}


# =========================================================
# TIMETABLE
# =========================================================
@router.get("/timetable")
def my_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    student = _current_student(db, current_user)
    course_ids = [
        e.course_id
        for e in db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.status == "active")
        .all()
    ]

    if not course_ids:
        return []

    slots = (
        db.query(Timetable)
        .filter(Timetable.course_id.in_(course_ids))
        .order_by(Timetable.day_of_week, Timetable.start_time)
        .all()
    )
    result = []
    for t in slots:
        course = db.query(Course).filter(Course.id == t.course_id).first()
        teacher = db.query(Teacher).filter(Teacher.id == t.teacher_id).first()
        teacher_user = db.query(User).filter(User.id == teacher.user_id).first() if teacher else None
        result.append({
            "id": t.id,
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "day_of_week": t.day_of_week,
            "start_time": str(t.start_time),
            "end_time": str(t.end_time),
            "room": t.room,
            "teacher_name": teacher_user.full_name if teacher_user else "—",
        })
    return result


# =========================================================
# ANNOUNCEMENTS
# =========================================================
@router.get("/announcements")
def student_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    items = (
        db.query(Announcement)
        .filter(Announcement.audience.in_(["all", "students"]))
        .order_by(Announcement.published_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "audience": a.audience,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        }
        for a in items
    ]


# =========================================================
# PROFILE
# =========================================================
@router.get("/profile")
def student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    student = _current_student(db, current_user)
    dept = None
    if student.department_id:
        d = db.query(Department).filter(Department.id == student.department_id).first()
        dept = {"id": d.id, "name": d.name, "code": d.code} if d else None

    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "roll_number": student.roll_number,
        "batch_year": student.batch_year,
        "current_semester": student.current_semester,
        "cgpa": float(student.cgpa or 0),
        "department": dept,
    }