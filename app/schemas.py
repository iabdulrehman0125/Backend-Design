from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List          
from datetime import datetime, date, time  

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        


TokenResponse.model_rebuild()
# ============ ADMIN SCHEMAS ============

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = Field(..., pattern="^(admin|teacher|student)$")
    phone: Optional[str] = None


class StudentCreate(UserCreate):
    role: str = "student"
    roll_number: str
    department_id: Optional[int] = None
    batch_year: int
    current_semester: int = 1


class TeacherCreate(UserCreate):
    role: str = "teacher"
    employee_code: str
    department_id: Optional[int] = None
    designation: Optional[str] = None


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    credits: int = Field(..., ge=1, le=6)
    department_id: Optional[int] = None
    semester: Optional[int] = None


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    credits: int
    department_id: Optional[int] = None
    semester: Optional[int] = None

    class Config:
        from_attributes = True


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: int
    user_id: int
    roll_number: str
    department_id: Optional[int] = None
    batch_year: int
    current_semester: int
    cgpa: float

    class Config:
        from_attributes = True


class TeacherOut(BaseModel):
    id: int
    user_id: int
    employee_code: str
    department_id: Optional[int] = None
    designation: Optional[str] = None

    class Config:
        from_attributes = True


class UserDetail(UserOut):
    student: Optional[StudentOut] = None
    teacher: Optional[TeacherOut] = None


class AssignTeacherRequest(BaseModel):
    teacher_id: int
    course_id: int
    
# ============ UPDATE SCHEMAS ============

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class StudentUpdate(UserUpdate):
    roll_number: Optional[str] = None
    department_id: Optional[int] = None
    batch_year: Optional[int] = None
    current_semester: Optional[int] = None
    cgpa: Optional[float] = None


class TeacherUpdate(UserUpdate):
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    
# ============ TEACHER SCHEMAS ============

class StudentInCourseOut(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    email: EmailStr
    roll_number: str
    batch_year: int
    attendance_percentage: float
    total_sessions: int
    present_count: int


class TeacherCourseOut(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    credits: int
    semester: Optional[int] = None
    department: Optional[str] = None
    enrolled_students: int
    sessions_held: int


class AttendanceSessionCreate(BaseModel):
    course_id: int
    session_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    topic: Optional[str] = None
    timetable_id: Optional[int] = None


class AttendanceItem(BaseModel):
    student_id: int
    status: str = Field(..., pattern="^(present|absent|late|excused)$")


class AttendanceMarkBulk(BaseModel):
    records: List[AttendanceItem]


class TimetableOut(BaseModel):
    id: int
    course_code: str
    course_title: str
    day_of_week: str
    start_time: str
    end_time: str
    room: Optional[str] = None