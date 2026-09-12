from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


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