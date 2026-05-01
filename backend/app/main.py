from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from .database import engine, Base, get_db
from . import models, schemas, auth
from .routes import courses, payments, crm, projects
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi import Request
from .routes import courses, payments, crm, projects, videos

from fastapi.staticfiles import StaticFiles

import os
from datetime import datetime
from PIL import Image, ImageDraw
from .routes import videos_capcut


# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mi Plataforma de Cursos")

# Servir archivos estáticos (CSS, JS, etc.)
#app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")

# Servir videos (asegurar que la ruta /videos funciona)
#app.mount("/videos", StaticFiles(directory="backend/static/videos"), name="videos")
#app.mount("/static/videos", StaticFiles(directory="backend/static/videos"), name="videos")
#app.mount("/static", StaticFiles(directory="backend/static"), name="static")

app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Incluir routers
app.include_router(courses.router)
app.include_router(payments.router)
app.include_router(crm.router)
app.include_router(projects.router)

app.include_router(videos.router)

app.include_router(videos_capcut.router)

# Servir archivos estáticos (CSS, JS, imágenes)
app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")
# Servir videos desde la carpeta static/videos
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
VIDEOS_DIR = "static/videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)

app.mount("/static/videos", StaticFiles(directory="static/videos"), name="videos")

# Configurar plantillas HTML
templates = Jinja2Templates(directory="backend/app/templates")

# Crear carpeta para flyers si no existe
FLYERS_DIR = "backend/static/flyers"
os.makedirs(FLYERS_DIR, exist_ok=True)

# Servir flyers generados
app.mount("/flyers", StaticFiles(directory="backend/static/flyers"), name="flyers")






# Ruta para el dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ==================== ENDPOINTS PÚBLICOS ====================

@app.get("/")
def root():
    return {"message": "API funcionando 🚀", "status": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================== AUTENTICACIÓN ====================

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registrar un nuevo usuario"""
    # Verificar si el email ya existe
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear nuevo usuario
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "Usuario creado exitosamente", "user_id": db_user.id, "email": db_user.email}


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Iniciar sesión y obtener token JWT"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id, "user_name": user.name}


# ==================== ENDPOINTS DE PRUEBA ====================

@app.get("/users/me")
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Obtener información del usuario autenticado"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    }


@app.get("/test-db")
def test_database(db: Session = Depends(get_db)):
    """Probar conexión a la base de datos"""
    try:
        # Intentar contar usuarios
        user_count = db.query(models.User).count()
        return {"status": "success", "message": "Conexión a BD exitosa", "user_count": user_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== GENERADOR DE FLYERS ====================

@app.get("/generate-flyer/{course_id}")
async def generate_flyer(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Genera un flyer promocional para un curso (solo administradores)"""

    # Verificar que sea administrador
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden generar flyers")

    # Obtener el curso
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Crear imagen de fondo
    img = Image.new('RGB', (1200, 630), color='#1a1a2e')
    draw = ImageDraw.Draw(img)

    # Colores
    white = (255, 255, 255)
    purple = (102, 126, 234)
    yellow = (255, 193, 7)
    gray = (200, 200, 200)

    # Función para dibujar texto con tamaño aproximado
    def draw_text(draw, text, position, color, font_size):
        try:
            # Intentar usar una fuente del sistema
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        draw.text(position, text, fill=color, font=font)

    # Dibujar fondo con gradiente (simplificado)
    for i in range(150):
        color_value = int(102 + (i * 0.3))
        draw.rectangle([0, i, 1200, i + 1], fill=(color_value, 126, 234))

    # Título
    draw_text(draw, course.title.upper(), (60, 50), yellow, 42)

    # Descripción
    desc = course.description[:120] + "..." if len(
        course.description or "") > 120 else course.description or "Curso de alta calidad"
    draw_text(draw, desc, (60, 130), white, 24)

    # Precio
    draw_text(draw, f"${course.price} MXN", (60, 220), purple, 48)
    draw_text(draw, "¡OFERTA ESPECIAL!", (60, 280), yellow, 28)

    # Fechas
    draw_text(draw, "📅 Próximas fechas", (60, 360), white, 20)
    draw_text(draw, "Abril - Mayo 2026", (80, 400), gray, 18)

    # Modalidad
    modalidad = "🔴 CURSO EN VIVO" if course.course_type == 'live' else "📹 CURSO GRABADO"
    draw_text(draw, modalidad, (60, 460), purple, 20)

    # WhatsApp y contacto
    # Sección de contacto (más completa)
    draw_text(draw, "📞 CONTACTO", (60, 480), white, 22)

    # Teléfono
    draw_text(draw, "📱 WhatsApp: +52 1 234 567 890", (60, 520), gray, 20)

    # Correo
    draw_text(draw, "✉️ Email: info@eduplatform.com", (60, 560), gray, 18)

    # Sitio web
    draw_text(draw, "🌐 www.eduplatform.com", (60, 590), gray, 16)

    # Logo decorativo
    draw.ellipse([980, 450, 1150, 620], outline=purple, width=3)
    draw_text(draw, "EduPlatform", (1020, 530), white, 20)

    # Guardar imagen
    filename = f"flyer_course_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(FLYERS_DIR, filename)
    img.save(filepath)

    return FileResponse(
        filepath,
        media_type="image/png",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )