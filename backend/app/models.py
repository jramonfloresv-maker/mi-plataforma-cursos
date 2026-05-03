from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    CONVERTED = "converted"
    LOST = "lost"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    courses_teaching = relationship("Course", back_populates="instructor")
    purchases = relationship("Purchase", back_populates="user")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    instructor_id = Column(Integer, ForeignKey("users.id"))
    thumbnail = Column(String, nullable=True)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # NUEVOS CAMPOS
    audiencia = Column(Text, nullable=True)
    modalidad = Column(String, default="online")

    instructor = relationship("User", back_populates="courses_teaching")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="course")

    # NUEVOS CAMPOS PARA CURSOS EN VIVO
    course_type = Column(String, default="recorded")  # "recorded" o "live"
    platform = Column(String, nullable=True)  # "zoom", "teams", "meet"
    live_dates = Column(Text, nullable=True)  # JSON con fechas: ["2026-05-10 18:00", "2026-05-17 18:00"]
    duration_hours = Column(Integer, default=0)  # Horas totales del curso
    sessions_count = Column(Integer, default=0)  # Número de sesiones
    next_session = Column(DateTime, nullable=True)  # Próxima fecha/hora
    meeting_link = Column(String, nullable=True)  # Enlace de Zoom/Teams (solo visible para compradores)
    recording_available = Column(Boolean, default=True)  # Si hay grabación disponible
    # Dentro de la clase Course, después de los campos existentes
    course_version = Column(String, default="recorded")  # recorded, live, sandbox
    sandbox_url = Column(String, nullable=True)  # URL del entorno de práctica
    mentor_hours = Column(Integer, default=0)  # Horas de mentoría incluidas
    projects_count = Column(Integer, default=0)  # Números de proyectos prácticos
    includes_certificate = Column(Boolean, default=True)
    includes_dc3 = Column(Boolean, default=False)
    # NUEVO CAMPO PARA VIDEO PROMOCIONAL
    video_promocional = Column(String, nullable=True)  # URL del video promocional


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    order = Column(Integer)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    video_url = Column(String, nullable=True)
    order = Column(Integer)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"))

    module = relationship("Module", back_populates="lessons")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    amount = Column(Float)
    status = Column(String)
    payment_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="purchases")
    course = relationship("Course", back_populates="purchases")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    source = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_contact = Column(DateTime(timezone=True), nullable=True)


# ==================== MODELOS PARA PROYECTOS KANBAN ====================

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación con usuario
    owner = relationship("User", backref="projects")
    # Relación con tareas
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(Integer, default=2)  # 1=Alta, 2=Media, 3=Baja
    order = Column(Integer, default=0)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id])