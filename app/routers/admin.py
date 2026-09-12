from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.deps import require_roles
from app.models import User, Student, Teacher, Course, Department, TeacherCourse
from app.schemas import (
    StudentCreate, TeacherCreate, CourseCreate,
    UserDetail, CourseOut, DepartmentOut,
    AssignTeacherRequest,StudentUpdate, TeacherUpdate,
)
from app.security import hash_password

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles("admin"))],   # 🔒 every route requires admin
)


# ---------- USERS ----------

@router.get("/users", response_model=List[UserDetail])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


# ---------- STUDENTS ----------

@router.post("/students", response_model=UserDetail, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already exists")
    if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
        raise HTTPException(400, "Roll number already exists")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="student",
        phone=payload.phone,
    )
    db.add(user)
    db.flush()   # get user.id

    student = Student(
        user_id=user.id,
        roll_number=payload.roll_number,
        department_id=payload.department_id,
        batch_year=payload.batch_year,
        current_semester=payload.current_semester,
    )
    db.add(student)
    db.commit()
    db.refresh(user)
    return user


# ---------- TEACHERS ----------

@router.post("/teachers", response_model=UserDetail, status_code=201)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already exists")
    if db.query(Teacher).filter(Teacher.employee_code == payload.employee_code).first():
        raise HTTPException(400, "Employee code already exists")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="teacher",
        phone=payload.phone,
    )
    db.add(user)
    db.flush()

    teacher = Teacher(
        user_id=user.id,
        employee_code=payload.employee_code,
        department_id=payload.department_id,
        designation=payload.designation,
    )
    db.add(teacher)
    db.commit()
    db.refresh(user)
    return user


# ---------- COURSES ----------

@router.get("/courses", response_model=List[CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.code).all()


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise HTTPException(400, "Course code already exists")

    course = Course(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        credits=payload.credits,
        department_id=payload.department_id,
        semester=payload.semester,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# ---------- DEPARTMENTS ----------

@router.get("/departments", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).order_by(Department.name).all()


# ---------- ASSIGN TEACHER TO COURSE ----------

@router.post("/assign-teacher", status_code=201)
def assign_teacher(payload: AssignTeacherRequest, db: Session = Depends(get_db)):
    exists = (
        db.query(TeacherCourse)
        .filter(
            TeacherCourse.teacher_id == payload.teacher_id,
            TeacherCourse.course_id == payload.course_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(400, "Teacher already assigned to this course")

    if not db.query(Teacher).filter(Teacher.id == payload.teacher_id).first():
        raise HTTPException(404, "Teacher not found")
    if not db.query(Course).filter(Course.id == payload.course_id).first():
        raise HTTPException(404, "Course not found")

    db.add(TeacherCourse(teacher_id=payload.teacher_id, course_id=payload.course_id))
    db.commit()
    return {"message": "Teacher assigned successfully"}

# ---------- GET ONE USER ----------

@router.get("/users/{user_id}", response_model=UserDetail)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


# ---------- UPDATE STUDENT ----------

@router.put("/students/{user_id}", response_model=UserDetail)
def update_student(user_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not user:
        raise HTTPException(404, "Student not found")

    # Update base user fields
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)

    # Update student-specific fields
    student = db.query(Student).filter(Student.user_id == user_id).first()
    if student:
        if payload.roll_number is not None:
            # Check uniqueness
            existing = db.query(Student).filter(
                Student.roll_number == payload.roll_number,
                Student.id != student.id,
            ).first()
            if existing:
                raise HTTPException(400, "Roll number already in use")
            student.roll_number = payload.roll_number
        if payload.department_id is not None:
            student.department_id = payload.department_id
        if payload.batch_year is not None:
            student.batch_year = payload.batch_year
        if payload.current_semester is not None:
            student.current_semester = payload.current_semester
        if payload.cgpa is not None:
            student.cgpa = payload.cgpa

    db.commit()
    db.refresh(user)
    return user


# ---------- UPDATE TEACHER ----------

@router.put("/teachers/{user_id}", response_model=UserDetail)
def update_teacher(user_id: int, payload: TeacherUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role == "teacher").first()
    if not user:
        raise HTTPException(404, "Teacher not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)

    teacher = db.query(Teacher).filter(Teacher.user_id == user_id).first()
    if teacher:
        if payload.employee_code is not None:
            existing = db.query(Teacher).filter(
                Teacher.employee_code == payload.employee_code,
                Teacher.id != teacher.id,
            ).first()
            if existing:
                raise HTTPException(400, "Employee code already in use")
            teacher.employee_code = payload.employee_code
        if payload.department_id is not None:
            teacher.department_id = payload.department_id
        if payload.designation is not None:
            teacher.designation = payload.designation

    db.commit()
    db.refresh(user)
    return user


# ---------- DELETE USER (student or teacher) ----------

@router.delete("/users/{user_id}", status_code=200)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "admin":
        raise HTTPException(403, "Cannot delete admin accounts")

    # CASCADE will remove student/teacher/enrollments
    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted"}