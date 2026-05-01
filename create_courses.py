from backend.app.database import SessionLocal
from backend.app.models import Course, User
from datetime import datetime
import json

db = SessionLocal()

# Obtener el primer usuario como instructor
user = db.query(User).first()
if not user:
    print("❌ No hay usuarios. Regístrate primero en http://localhost:8000/dashboard")
    exit()

print(f"📚 Usuario instructor: {user.email}")

# Curso BASE
base_title = "Python Avanzado"

# 1. Versión GRABADA
course_recorded = Course(
    title=f"{base_title} - Autoaprendizaje (Grabado)",
    description="Acceso 24/7 a videos grabados, ejercicios prácticos y certificado de finalización.",
    price=49.99,
    instructor_id=user.id,
    published=True,
    course_type="recorded",
    course_version="recorded",
    duration_hours=40,
    projects_count=5,
    includes_certificate=True,
    includes_dc3=False,
    recording_available=True
)
db.add(course_recorded)
print("✅ Versión GRABADA creada")

# 2. Versión EN VIVO
course_live = Course(
    title=f"{base_title} - Clases en Vivo por Zoom",
    description="8 sesiones en vivo con instructor. Incluye grabaciones y certificado DC3.",
    price=129.99,
    instructor_id=user.id,
    published=True,
    course_type="live",
    course_version="live",
    platform="zoom",
    duration_hours=30,
    sessions_count=8,
    live_dates=json.dumps([
        "2026-05-10 18:00:00", "2026-05-17 18:00:00",
        "2026-05-24 18:00:00", "2026-05-31 18:00:00",
        "2026-06-07 18:00:00", "2026-06-14 18:00:00",
        "2026-06-21 18:00:00", "2026-06-28 18:00:00"
    ]),
    next_session=datetime(2026, 5, 10, 18, 0, 0),
    meeting_link="https://zoom.us/j/123456789",
    includes_certificate=True,
    includes_dc3=True,
    mentor_hours=8,
    projects_count=5
)
db.add(course_live)
print("✅ Versión EN VIVO creada")

# 3. Versión PLATAFORMA PRÁCTICA
course_sandbox = Course(
    title=f"{base_title} - Plataforma Práctica + Mentoría",
    description="Entorno sandbox, 20 proyectos guiados y mentoría personalizada.",
    price=199.99,
    instructor_id=user.id,
    published=True,
    course_type="sandbox",
    course_version="sandbox",
    duration_hours=60,
    projects_count=20,
    sandbox_url="https://sandbox.eduplatform.com/python-avanzado",
    includes_certificate=True,
    includes_dc3=True,
    mentor_hours=10,
    recording_available=True
)
db.add(course_sandbox)
print("✅ Versión PLATAFORMA PRÁCTICA creada")

db.commit()
db.close()

print("\n" + "="*50)
print("🎉 CURSOS CREADOS EXITOSAMENTE:")
print("="*50)