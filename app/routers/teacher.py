from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import List, Optional

from app.database import get_db
from app.deps import require_roles
from app.schemas import (
    TeacherCourseOut,
    StudentInCourseOut,
    AttendanceSessionCreate,
    AttendanceMarkBulk,
    TimetableOut,
    UserOut,
)
from app.schemas import (
    TeacherDashboardOut, TeacherCourseOut, StudentInCourseOut,
    AttendanceSessionCreate, AttendanceMarkBulk, AttendanceSessionOut,
    TimetableOut, UserOut,
)

router = APIRouter(
    prefix="/api/teacher",
    tags=["teacher"],
    dependencies=[Depends(require_roles("teacher"))],
)


# =========================================================
# HELPER — get current teacher record
# =========================================================
def _current_teacher(db: Session, current_user: User) -> Teacher:
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(404, "Teacher profile not found")
    return teacher


# =========================================================
# DASHBOARD
# =========================================================
@router.get("/dashboard")
def teacher_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)

    # Courses taught
    course_ids = [
        tc.course_id
        for tc in db.query(TeacherCourse).filter(TeacherCourse.teacher_id == teacher.id).all()
    ]

    total_courses = len(course_ids)

    # Unique students across all courses
    if course_ids:
        student_ids = {
            e.student_id
            for e in db.query(Enrollment).filter(Enrollment.course_id.in_(course_ids)).all()
        }
    else:
        student_ids = set()
    total_students = len(student_ids)

    # Attendance stats for this teacher
    sessions = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.teacher_id == teacher.id)
        .all()
    )
    session_ids = [s.id for s in sessions]
    total_sessions = len(sessions)

    if session_ids:
        all_records = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.session_id.in_(session_ids))
            .all()
        )
        total_records = len(all_records)
        present_records = sum(1 for r in all_records if r.status == "present")
        avg_attendance = round((present_records / total_records) * 100, 1) if total_records else 0.0
    else:
        avg_attendance = 0.0

    # Upcoming timetable (today)
    today = date.today().strftime("%A").lower()
    today_classes = (
        db.query(Timetable)
        .filter(Timetable.teacher_id == teacher.id, Timetable.day_of_week == today)
        .order_by(Timetable.start_time)
        .all()
    )

    upcoming = []
    for t in today_classes:
        course = db.query(Course).filter(Course.id == t.course_id).first()
        upcoming.append({
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "start_time": str(t.start_time),
            "end_time": str(t.end_time),
            "room": t.room,
        })

    # Recent sessions (last 5)
    recent = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.teacher_id == teacher.id)
        .order_by(AttendanceSession.session_date.desc(), AttendanceSession.id.desc())
        .limit(5)
        .all()
    )
    recent_list = []
    for s in recent:
        course = db.query(Course).filter(Course.id == s.course_id).first()
        count = (
            db.query(func.count(AttendanceRecord.id))
            .filter(AttendanceRecord.session_id == s.id)
            .scalar()
        )
        present = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.session_id == s.id,
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        recent_list.append({
            "id": s.id,
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "session_date": str(s.session_date),
            "topic": s.topic,
            "total_marked": count,
            "present_count": present,
        })

    return {
        "teacher_name": current_user.full_name,
        "designation": teacher.designation,
        "total_students": total_students,
        "total_courses": total_courses,
        "total_sessions": total_sessions,
        "average_attendance": avg_attendance,
        "today_classes": upcoming,
        "recent_sessions": recent_list,
    }


# =========================================================
# MY COURSES
# =========================================================
@router.get("/courses")
def my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)
    tcs = db.query(TeacherCourse).filter(TeacherCourse.teacher_id == teacher.id).all()

    result = []
    for tc in tcs:
        course = db.query(Course).filter(Course.id == tc.course_id).first()
        if not course:
            continue
        # Enrolled students count
        enrolled = (
            db.query(func.count(Enrollment.id))
            .filter(Enrollment.course_id == course.id, Enrollment.status == "active")
            .scalar()
        )
        # Sessions count
        sessions = (
            db.query(func.count(AttendanceSession.id))
            .filter(
                AttendanceSession.course_id == course.id,
                AttendanceSession.teacher_id == teacher.id,
            )
            .scalar()
        )
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
            "enrolled_students": enrolled,
            "sessions_held": sessions,
        })
    return result


# =========================================================
# STUDENTS IN A COURSE
# =========================================================
@router.get("/courses/{course_id}/students")
def course_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)
    tc = (
        db.query(TeacherCourse)
        .filter(
            TeacherCourse.teacher_id == teacher.id,
            TeacherCourse.course_id == course_id,
        )
        .first()
    )
    if not tc:
        raise HTTPException(403, "You are not assigned to this course")

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.status == "active")
        .all()
    )

    result = []
    for e in enrollments:
        student = db.query(Student).filter(Student.id == e.student_id).first()
        if not student:
            continue
        user = db.query(User).filter(User.id == student.user_id).first()
        if not user:
            continue

        # Attendance percentage for this student in this course
        course_sessions = (
            db.query(AttendanceSession.id)
            .filter(AttendanceSession.course_id == course_id)
            .subquery()
        )
        total = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(course_sessions),
            )
            .scalar()
        )
        present = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(course_sessions),
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        pct = round((present / total) * 100, 1) if total else 0.0

        result.append({
            "student_id": student.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "roll_number": student.roll_number,
            "batch_year": student.batch_year,
            "attendance_percentage": pct,
            "total_sessions": total,
            "present_count": present,
        })
    return result


# =========================================================
# TIMETABLE
# =========================================================
@router.get("/timetable")
def my_timetable(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)
    slots = (
        db.query(Timetable)
        .filter(Timetable.teacher_id == teacher.id)
        .order_by(Timetable.day_of_week, Timetable.start_time)
        .all()
    )
    result = []
    for t in slots:
        course = db.query(Course).filter(Course.id == t.course_id).first()
        result.append({
            "id": t.id,
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "day_of_week": t.day_of_week,
            "start_time": str(t.start_time),
            "end_time": str(t.end_time),
            "room": t.room,
        })
    return result


# =========================================================
# ATTENDANCE — CREATE SESSION
# =========================================================
@router.post("/attendance/sessions", status_code=201)
def create_attendance_session(
    payload: AttendanceSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)

    # Verify teacher assigned to course
    tc = (
        db.query(TeacherCourse)
        .filter(
            TeacherCourse.teacher_id == teacher.id,
            TeacherCourse.course_id == payload.course_id,
        )
        .first()
    )
    if not tc:
        raise HTTPException(403, "You are not assigned to this course")

    session = AttendanceSession(
        course_id=payload.course_id,
        teacher_id=teacher.id,
        session_date=payload.session_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        topic=payload.topic,
        timetable_id=payload.timetable_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Auto-create "absent" placeholder records so teacher can flip to present
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == payload.course_id, Enrollment.status == "active")
        .all()
    )
    for e in enrollments:
        db.add(
            AttendanceRecord(
                session_id=session.id,
                student_id=e.student_id,
                status="absent",
            )
        )
    db.commit()

    return {"id": session.id, "message": "Session created, mark attendance now"}


# =========================================================
# ATTENDANCE — MARK BULK
# =========================================================
@router.post("/attendance/sessions/{session_id}/mark")
def mark_attendance(
    session_id: int,
    payload: AttendanceMarkBulk,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)
    session = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.id == session_id,
            AttendanceSession.teacher_id == teacher.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(404, "Session not found or not yours")

    updated = 0
    for item in payload.records:
        rec = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == item.student_id,
            )
            .first()
        )
        if rec:
            rec.status = item.status
            updated += 1
        else:
            db.add(
                AttendanceRecord(
                    session_id=session_id,
                    student_id=item.student_id,
                    status=item.status,
                )
            )
            updated += 1
    db.commit()
    return {"message": f"Attendance saved for {updated} students"}


# =========================================================
# ATTENDANCE — LIST MY SESSIONS
# =========================================================
@router.get("/attendance/sessions")
def list_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    teacher = _current_teacher(db, current_user)
    sessions = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.teacher_id == teacher.id)
        .order_by(AttendanceSession.session_date.desc(), AttendanceSession.id.desc())
        .all()
    )
    result = []
    for s in sessions:
        course = db.query(Course).filter(Course.id == s.course_id).first()
        present = (
            db.query(func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.session_id == s.id,
                AttendanceRecord.status == "present",
            )
            .scalar()
        )
        total = (
            db.query(func.count(AttendanceRecord.id))
            .filter(AttendanceRecord.session_id == s.id)
            .scalar()
        )
        result.append({
            "id": s.id,
            "course_code": course.code if course else "—",
            "course_title": course.title if course else "—",
            "session_date": str(s.session_date),
            "topic": s.topic,
            "present": present,
            "total": total,
        })
    return result


# =========================================================
# ANNOUNCEMENTS — view all (teacher can see student-facing too)
# =========================================================
@router.get("/announcements")
def teacher_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("teacher")),
):
    from app.models import Announcement
    items = (
        db.query(Announcement)
        .filter(Announcement.audience.in_(["all", "teachers"]))
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