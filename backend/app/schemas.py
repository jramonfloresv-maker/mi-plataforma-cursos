from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    title: str
    description: str
    price: float
    thumbnail: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: int
    instructor_id: int
    published: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None


class LeadResponse(LeadCreate):
    id: int
    status: str
    created_at: datetime
    last_contact: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== MÓDULOS Y LECCIONES ====================
class LessonBase(BaseModel):
    title: str
    content: str
    video_url: Optional[str] = None
    order: int


class LessonResponse(LessonBase):
    id: int

    class Config:
        from_attributes = True


class ModuleBase(BaseModel):
    title: str
    order: int
    lessons: List[LessonBase] = []


class ModuleResponse(ModuleBase):
    id: int
    lessons: List[LessonResponse]

    class Config:
        from_attributes = True


# Actualizar CourseResponse para incluir módulos
class CourseResponse(CourseBase):
    id: int
    instructor_id: int
    published: bool
    created_at: datetime
    modules: List[ModuleResponse] = []

    class Config:
        from_attributes = True


class CourseCreate(CourseBase):
    modules: List[ModuleBase] = []

# ==================== PAYMENT SCHEMAS ====================
class CheckoutSessionCreate(BaseModel):
    course_id: int

class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    message: str

class PaymentWebhookResponse(BaseModel):
    status: str

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    customer_email: Optional[str]
    purchase_exists: bool
    purchase_status: Optional[str]


# ==================== PROJECTS SCHEMAS ====================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: int = 2
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    id: int
    order: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True