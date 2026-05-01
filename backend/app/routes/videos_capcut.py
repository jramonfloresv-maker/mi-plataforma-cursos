from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/videos/capcut", tags=["Generador de Videos CapCut"])

# URL del servidor CapCut (debe estar corriendo en otra terminal)
CAPCUT_API_URL = "http://127.0.0.1:9001"


@router.get("/estado")
async def verificar_estado():
    """Verificar si el servidor CapCut está funcionando"""
    try:
        response = requests.get(f"{CAPCUT_API_URL}/", timeout=3)
        if response.status_code == 200:
            return {"status": "online", "message": "Servidor CapCut funcionando"}
    except:
        return {"status": "offline", "message": "Servidor CapCut no disponible"}
    return {"status": "offline"}


@router.post("/generar/{course_id}")
async def generar_video(
        course_id: int,
        formato: str = "16:9",
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Generar video promocional para un curso"""

    # Solo administradores
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    # Obtener el curso
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Preparar datos para el servidor CapCut
    payload = {
        "titulo": course.title,
        "descripcion": course.description[:200] if course.description else "",
        "precio": f"${course.price}"
    }

    try:
        # Llamar al servidor CapCut
        response = requests.post(
            f"{CAPCUT_API_URL}/crear_video",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "course_id": course_id,
                "course_title": course.title,
                "video_url": None,
                "message": data.get("mensaje", "Video solicitado")
            }
        else:
            raise HTTPException(status_code=500, detail=f"Error CapCut: {response.text}")

    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Servidor CapCut no disponible")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")