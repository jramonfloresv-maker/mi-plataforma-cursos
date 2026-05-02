from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw

from .database import engine, Base, get_db
from . import models, schemas, auth
from .routes import courses, payments, crm, projects, videos, videos_capcut

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mi Plataforma de Cursos")

# === CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS (CORREGIDA) ===
# Esta es la ÚNICA línea que monta la ruta /static
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# === CONFIGURACIÓN DE LA APLICACIÓN ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTERS DE LA API ===
app.include_router(courses.router)
app.include_router(payments.router)
app.include_router(crm.router)
app.include_router(projects.router)
app.include_router(videos.router)
app.include_router(videos_capcut.router)

# === CONFIGURACIÓN DE PLANTILLAS ===
templates = Jinja2Templates(directory="backend/app/templates")

# === CARPETAS PARA FLYERS Y VIDEOS ===
FLYERS_DIR = "backend/static/flyers"
os.makedirs(FLYERS_DIR, exist_ok=True)

VIDEOS_DIR = "backend/static/videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)


# === RUTAS DE LA APLICACIÓN ===

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    # Construir la ruta al archivo index.html
    import os
    file_path = os.path.join("backend", "app", "templates", "index.html")
    if not os.path.exists(file_path):
        return HTMLResponse(content=f"<h1>Error</h1><p>No se encuentra index.html en {file_path}</p>", status_code=404)
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/")
def root():
    return {"message": "API funcionando 🚀", "status": "online"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================== AUTENTICACIÓN ====================
@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, name=user.name, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "Usuario creado exitosamente", "user_id": db_user.id, "email": db_user.email}


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id, "user_name": user.name}


@app.get("/users/me")
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    }


@app.get("/test-db")
def test_database(db: Session = Depends(get_db)):
    try:
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
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden generar flyers")

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Crear imagen
    img = Image.new('RGB', (1200, 630), color='#1a1a2e')
    draw = ImageDraw.Draw(img)

    white = (255, 255, 255)
    purple = (102, 126, 234)
    yellow = (255, 193, 7)
    gray = (200, 200, 200)

    def draw_text(draw, text, position, color, font_size):
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        draw.text(position, text, fill=color, font=font)

    for i in range(150):
        color_value = int(102 + (i * 0.3))
        draw.rectangle([0, i, 1200, i + 1], fill=(color_value, 126, 234))

    draw_text(draw, course.title.upper(), (60, 50), yellow, 42)
    desc = course.description[:120] + "..." if len(
        course.description or "") > 120 else course.description or "Curso de alta calidad"
    draw_text(draw, desc, (60, 130), white, 24)
    draw_text(draw, f"${course.price} MXN", (60, 220), purple, 48)
    draw_text(draw, "¡OFERTA ESPECIAL!", (60, 280), yellow, 28)
    draw_text(draw, "📅 Próximas fechas", (60, 360), white, 20)
    draw_text(draw, "Abril - Mayo 2026", (80, 400), gray, 18)
    modalidad = "🔴 CURSO EN VIVO" if course.course_type == 'live' else "📹 CURSO GRABADO"
    draw_text(draw, modalidad, (60, 460), purple, 20)
    draw_text(draw, "📞 CONTACTO", (60, 480), white, 22)
    draw_text(draw, "📱 WhatsApp: +52 1 234 567 890", (60, 520), gray, 20)
    draw_text(draw, "✉️ Email: info@eduplatform.com", (60, 560), gray, 18)
    draw_text(draw, "🌐 www.eduplatform.com", (60, 590), gray, 16)

    draw.ellipse([980, 450, 1150, 620], outline=purple, width=3)
    draw_text(draw, "EduPlatform", (1020, 530), white, 20)

    filename = f"flyer_course_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(FLYERS_DIR, filename)
    img.save(filepath)

    return FileResponse(filepath, media_type="image/png", filename=filename,
                        headers={"Content-Disposition": f"attachment; filename={filename}"})