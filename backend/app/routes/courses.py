from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from .. import models, schemas, auth

from fastapi import UploadFile, File, Form
import shutil
import os

import os
#BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


#VIDEOS_DIR = os.path.join(BASE_DIR, "static", "videos")
#os.makedirs(VIDEOS_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
VIDEOS_DIR = os.path.join(BASE_DIR, "backend", "static", "videos")

router = APIRouter(prefix="/courses", tags=["Cursos"])


# ==================== CREAR CURSO ====================
@router.post("/", response_model=schemas.CourseResponse)
def create_course(
        course: schemas.CourseCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Crear un nuevo curso (solo instructores)"""

    # Verificar si es instructor o admin
    if current_user.role not in [models.UserRole.INSTRUCTOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Solo los instructores pueden crear cursos")

    # Crear el curso
    db_course = models.Course(
        title=course.title,
        description=course.description,
        price=course.price,
        thumbnail=course.thumbnail,
        instructor_id=current_user.id
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)

    return db_course


# ==================== LISTAR CURSOS ====================
@router.get("/", response_model=List[schemas.CourseResponse])
def list_courses(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """Listar todos los cursos publicados"""
    courses = db.query(models.Course).filter(
        models.Course.published == True
    ).offset(skip).limit(limit).all()
    return courses




@router.get("/videos_list")
async def get_videos_list(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Obtener lista de todos los cursos que tienen video (solo administradores)"""

    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    courses = db.query(models.Course).filter(
        models.Course.video_promocional.isnot(None)
    ).all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "video_url": c.video_promocional,
            "price": c.price
        }
        for c in courses
    ]


# ==================== MIS CURSOS (como instructor) ====================
@router.get("/my-courses", response_model=List[schemas.CourseResponse])
def get_my_courses(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Obtener los cursos que ha creado el instructor"""
    courses = db.query(models.Course).filter(
        models.Course.instructor_id == current_user.id
    ).all()
    return courses


import traceback


@router.post("/upload_video/{course_id}")
async def upload_video(
        course_id: int,
        video: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # Verificar que sea administrador
        if current_user.role != models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Solo administradores pueden subir videos")

        # Obtener el curso
        course = db.query(models.Course).filter(models.Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Curso no encontrado")

        # Validar tipo de archivo
        if not video.filename.endswith(('.mp4', '.webm', '.mov')):
            raise HTTPException(status_code=400, detail="Formato no soportado. Use MP4, WEBM o MOV")

        # Crear nombre único para el archivo
        import uuid
        extension = video.filename.split('.')[-1]
        nombre_archivo = f"curso_{course_id}_{uuid.uuid4().hex[:8]}.{extension}"

        # Ruta completa
        import os
        VIDEOS_DIR = "backend/static/videos"
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        ruta_archivo = os.path.join(VIDEOS_DIR, nombre_archivo)

        # Guardar el archivo
        with open(ruta_archivo, "wb") as buffer:
            content = await video.read()
            buffer.write(content)

        # Guardar la URL en la base de datos
        video_url = f"/static/videos/{nombre_archivo}"
        course.video_promocional = video_url
        db.commit()

        return {
            "success": True,
            "message": "Video subido exitosamente",
            "video_url": video_url,
            "course_id": course_id,
            "course_title": course.title
        }

    except Exception as e:
        print("=" * 60)
        print("ERROR AL SUBIR VIDEO:")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
@router.delete("/delete_video/{course_id}")
async def delete_video(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Eliminar video promocional de un curso (solo administradores)"""

    # Verificar que sea administrador
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar videos")

    # Obtener el curso
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Verificar que tiene un video
    if not course.video_promocional:
        raise HTTPException(status_code=404, detail="El curso no tiene video promocional")

    # Obtener la ruta del archivo
    video_path = os.path.join("backend/static", course.video_promocional.replace("/static/", ""))

    # Eliminar el archivo físico si existe
    if os.path.exists(video_path):
        os.remove(video_path)

    # Eliminar la referencia en la base de datos
    course.video_promocional = None
    db.commit()

    return {
        "success": True,
        "message": "Video eliminado exitosamente",
        "course_id": course_id
    }

# ==================== VER CURSO ESPECÍFICO ====================
@router.get("/{course_id}", response_model=schemas.CourseResponse)
def get_course(
        course_id: int,
        db: Session = Depends(get_db)
):
    """Obtener un curso específico"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


# ==================== PUBLICAR CURSO ====================
@router.patch("/{course_id}/publish")
def publish_course(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Publicar un curso (solo el instructor dueño)"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if course.instructor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="No eres el instructor de este curso")

    course.published = True
    db.commit()
    return {"message": "Curso publicado exitosamente", "course_id": course_id}


# ==================== ELIMINAR CURSO ====================
@router.delete("/{course_id}")
def delete_course(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Eliminar un curso (solo instructor dueño o admin)"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if course.instructor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="No autorizado")

    db.delete(course)
    db.commit()
    return {"message": "Curso eliminado exitosamente"}


@router.get("/{course_id}/live-info")
def get_live_course_info(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    """Obtener información del curso en vivo (fechas, enlace si es comprador)"""

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Curso no encontrado")

    import json
    live_dates = json.loads(course.live_dates) if course.live_dates else []

    # Verificar si el usuario ha comprado el curso
    has_purchased = False
    if current_user:
        purchase = db.query(models.Purchase).filter(
            models.Purchase.user_id == current_user.id,
            models.Purchase.course_id == course_id,
            models.Purchase.status == "completed"
        ).first()
        has_purchased = purchase is not None

    response = {
        "course_type": course.course_type,
        "platform": course.platform,
        "live_dates": live_dates,
        "duration_hours": course.duration_hours,
        "sessions_count": course.sessions_count,
        "next_session": course.next_session,
        "has_purchased": has_purchased
    }

    # Solo mostrar enlace si el usuario compró el curso
    if has_purchased and course.meeting_link:
        response["meeting_link"] = course.meeting_link

    return response


# ==================== SUBIR VIDEO PROMOCIONAL ====================

# Crear carpeta para videos si no existe
# Crear carpeta para videos si no existe (ruta absoluta)








