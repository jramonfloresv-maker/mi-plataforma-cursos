from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/crm", tags=["CRM - Gestión de Leads"])


# ==================== CREAR LEAD ====================
@router.post("/leads/", response_model=schemas.LeadResponse)
def create_lead(
        lead: schemas.LeadCreate,
        db: Session = Depends(get_db)
):
    """
    Capturar un nuevo lead (cliente potencial)
    Útil para formularios de landing page, newsletter, etc.
    """
    # Verificar si ya existe un lead con ese email
    existing_lead = db.query(models.Lead).filter(models.Lead.email == lead.email).first()
    if existing_lead:
        raise HTTPException(status_code=400, detail="Ya existe un lead con este email")

    # Crear nuevo lead
    db_lead = models.Lead(
        email=lead.email,
        name=lead.name,
        phone=lead.phone,
        source=lead.source,
        status=models.LeadStatus.NEW,
        created_at=datetime.utcnow()
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    return db_lead


# ==================== LISTAR LEADS ====================
@router.get("/leads/", response_model=List[schemas.LeadResponse])
def list_leads(
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Listar todos los leads (solo usuarios autenticados)
    Puedes filtrar por estado: new, contacted, interested, converted, lost
    """
    query = db.query(models.Lead)

    if status:
        query = query.filter(models.Lead.status == status)

    leads = query.offset(skip).limit(limit).all()
    return leads


# ==================== OBTENER LEAD POR ID ====================
@router.get("/leads/{lead_id}", response_model=schemas.LeadResponse)
def get_lead(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtener detalles de un lead específico
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return lead


# ==================== ACTUALIZAR LEAD ====================
@router.put("/leads/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(
        lead_id: int,
        lead_update: schemas.LeadCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Actualizar información de un lead
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    # Actualizar campos
    lead.email = lead_update.email
    lead.name = lead_update.name
    lead.phone = lead_update.phone
    lead.source = lead_update.source

    db.commit()
    db.refresh(lead)
    return lead


# ==================== ACTUALIZAR ESTADO DEL LEAD ====================
@router.patch("/leads/{lead_id}/status")
def update_lead_status(
        lead_id: int,
        status: str = Query(..., regex="^(new|contacted|interested|converted|lost)$"),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Cambiar el estado de un lead
    Estados válidos: new, contacted, interested, converted, lost
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    lead.status = status
    lead.last_contact = datetime.utcnow()
    db.commit()

    return {
        "message": f"Lead actualizado a '{status}'",
        "lead_id": lead_id,
        "new_status": status
    }


# ==================== ELIMINAR LEAD ====================
@router.delete("/leads/{lead_id}")
def delete_lead(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Eliminar un lead (solo administradores)
    """
    # Solo admins pueden eliminar leads
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar leads")

    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    db.delete(lead)
    db.commit()

    return {"message": "Lead eliminado exitosamente"}


# ==================== CONVERTIR LEAD EN CLIENTE ====================
@router.post("/leads/{lead_id}/convert")
def convert_lead_to_customer(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Marcar un lead como convertido (cuando realiza una compra)
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    # Verificar si ya existe un usuario con ese email
    existing_user = db.query(models.User).filter(models.User.email == lead.email).first()

    lead.status = models.LeadStatus.CONVERTED
    lead.last_contact = datetime.utcnow()
    db.commit()

    return {
        "message": "Lead marcado como convertido",
        "lead_id": lead_id,
        "customer_email": lead.email,
        "user_exists": existing_user is not None
    }


# ==================== ESTADÍSTICAS DE LEADS ====================
@router.get("/stats/leads")
def get_lead_stats(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtener estadísticas de leads (cuántos hay en cada estado)
    """
    stats = {}
    for status in models.LeadStatus:
        count = db.query(models.Lead).filter(models.Lead.status == status).count()
        stats[status.value] = count

    total = db.query(models.Lead).count()
    stats["total"] = total

    # Calcular tasa de conversión
    converted = stats.get("converted", 0)
    conversion_rate = (converted / total * 100) if total > 0 else 0
    stats["conversion_rate"] = round(conversion_rate, 2)

    return stats


# ==================== LEADS RECIENTES ====================
@router.get("/recent/leads")
def get_recent_leads(
        hours: int = Query(24, description="Últimas X horas"),
        limit: int = Query(10, description="Cantidad máxima"),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Obtener leads de las últimas horas
    """
    from datetime import timedelta
    time_threshold = datetime.utcnow() - timedelta(hours=hours)

    leads = db.query(models.Lead).filter(
        models.Lead.created_at >= time_threshold
    ).order_by(models.Lead.created_at.desc()).limit(limit).all()

    return {
        "since_hours": hours,
        "count": len(leads),
        "leads": leads
    }


# ==================== AGENTE IA DE VENTAS ====================

@router.get("/ai/analyze-lead/{lead_id}")
async def ai_analyze_lead(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Analizar un lead con IA y obtener recomendaciones de venta
    """
    from ..ai_agent import analyze_lead_with_ai

    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    analysis = await analyze_lead_with_ai(lead, db)
    return {
        "lead_id": lead_id,
        "lead_email": lead.email,
        "analysis": analysis
    }


@router.get("/ai/evaluate-new-leads")
async def ai_evaluate_new_leads(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Evaluar todos los leads nuevos con IA
    """
    from ..ai_agent import evaluate_new_leads

    results = await evaluate_new_leads(db)
    return {
        "total_evaluated": len(results),
        "results": results
    }


@router.post("/ai/send-followup/{lead_id}")
async def ai_send_followup(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Enviar seguimiento automático a un lead basado en análisis IA
    """
    from ..ai_agent import send_auto_followup

    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    result = await send_auto_followup(lead, db)
    return result


@router.get("/ai/recommend-course/{lead_id}")
async def ai_recommend_course(
        lead_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Recomendar el mejor curso para un lead usando IA
    """
    from ..ai_agent import recommend_course_for_lead

    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    recommendation = await recommend_course_for_lead(lead, db)
    return recommendation