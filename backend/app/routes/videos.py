from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import replicate
import os
import httpx
from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/videos", tags=["Generador de Videos IA"])

# Configurar API key
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

# Modelos disponibles en Replicate
MODELOS_VIDEO = {
    "stable_video": "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
    "kling": "kling-ai/kling-v1:abc123def456",
    "pika": "pika-labs/pika-v1:xyz789"
}


@router.get("/modelos")
async def get_modelos_disponibles():
    """Obtener lista de modelos de video disponibles"""
    return {
        "modelos": [
            {"id": "stable_video", "nombre": "Stable Video Diffusion", "duracion_max": "2 segundos",
             "costo": "créditos"},
            {"id": "kling", "nombre": "Kling AI", "duracion_max": "10 segundos", "costo": "créditos"},
            {"id": "pika", "nombre": "Pika Labs", "duracion_max": "4 segundos", "costo": "créditos"}
        ]
    }


@router.post("/generar/{course_id}")
async def generar_video_promocional(
        course_id: int,
        modelo: str = "stable_video",
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Generar video promocional para un curso usando IA
    Solo administradores pueden usar esta función
    """

    # Verificar que sea administrador
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden generar videos")

    # Obtener el curso
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Verificar que hay API key
    if not REPLICATE_API_KEY:
        raise HTTPException(status_code=500, detail="API key de Replicate no configurada")

    try:
        # Configurar cliente de Replicate
        client = replicate.Client(api_token=REPLICATE_API_KEY)

        # Generar prompt basado en el curso
        prompt = f"""
        Video promocional para el curso "{course.title}".
        {course.description[:200] if course.description else ''}
        Precio: ${course.price}
        Duración: {course.duration_hours or 30} horas
        Incluye certificación y acceso 24/7.
        Estilo: profesional, moderno, educativo, atractivo.
        """

        # Seleccionar modelo según parámetro
        modelo_id = MODELOS_VIDEO.get(modelo, MODELOS_VIDEO["stable_video"])

        # Ejecutar el modelo
        output = client.run(
            modelo_id,
            input={
                "prompt": prompt,
                "video_length": "14_frames_with_svd_xt",  # para stable video
                "sizing_strategy": "maintain_aspect_ratio",
                "num_frames": 14,
                "fps": 7
            }
        )

        # El output puede ser una URL o un archivo
        video_url = output if isinstance(output, str) else output[0] if output else None

        # Guardar en la base de datos (opcional)
        # Aquí puedes agregar el video al curso

        return {
            "success": True,
            "course_id": course_id,
            "course_title": course.title,
            "video_url": video_url,
            "modelo_used": modelo,
            "message": "Video generado exitosamente"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando video: {str(e)}")


@router.post("/generar-texto-a-video")
async def generar_video_desde_texto(
        request: dict,
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Generar un video corto a partir de un texto personalizado
    Útil para promociones rápidas en redes sociales
    """

    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")

    texto = request.get("texto", "")
    duracion = request.get("duracion", 5)  # segundos

    if not texto:
        raise HTTPException(status_code=400, detail="Se requiere texto para generar el video")

    try:
        client = replicate.Client(api_token=REPLICATE_API_KEY)

        output = client.run(
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={
                "prompt": f"Video para redes sociales: {texto}",
                "video_length": "14_frames_with_svd_xt"
            }
        )

        return {
            "success": True,
            "video_url": output,
            "texto": texto,
            "message": "Video generado correctamente"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")