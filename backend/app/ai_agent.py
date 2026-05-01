import openai
import os
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from . import models

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


# ==================== ANALIZAR LEAD CON IA ====================
async def analyze_lead_with_ai(lead: models.Lead, db: Session) -> Dict[str, Any]:
    """
    Analiza un lead usando IA y devuelve recomendaciones de venta
    """

    # Si no hay API key, usar modo simulado
    if not openai.api_key:
        return simulate_lead_analysis(lead)

    # Buscar cursos disponibles para recomendar
    courses = db.query(models.Course).filter(models.Course.published == True).all()
    courses_info = "\n".join([f"- {c.title}: ${c.price} - {c.description[:100]}" for c in courses])

    prompt = f"""
    Eres un agente de ventas experto en cursos online.

    Información del lead:
    - Nombre: {lead.name or 'Desconocido'}
    - Email: {lead.email}
    - Teléfono: {lead.phone or 'No disponible'}
    - Estado actual: {lead.status}
    - Fecha de registro: {lead.created_at}

    Cursos disponibles:
    {courses_info or 'No hay cursos disponibles aún'}

    Analiza este lead y responde SOLO en formato JSON con estos campos:
    {{
        "intent_score": "número del 0 al 100 (probabilidad de compra)",
        "recommended_course": "nombre del curso que más le interesaría",
        "next_action": "email | call | whatsapp | wait",
        "suggested_message": "mensaje personalizado para contactarlo",
        "reasoning": "breve explicación de tu análisis"
    }}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )

        import json
        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Error con OpenAI: {e}")
        return simulate_lead_analysis(lead)


def simulate_lead_analysis(lead: models.Lead) -> Dict[str, Any]:
    """
    Simulación de análisis cuando no hay API key
    """
    # Lógica simple basada en el nombre/email
    name = (lead.name or lead.email).lower()

    # Determinar puntuación basada en keywords
    score = 50  # base
    if "python" in name or "curso" in name or "aprender" in name:
        score += 20
    if "gratis" in name or "free" in name:
        score -= 10
    if lead.phone:
        score += 10  # tiene teléfono = más comprometido

    # Recomendar curso (el primero disponible)
    recommended = "Curso de Prueba"

    # Determinar acción
    if score > 70:
        next_action = "email"
        message = f"Hola {lead.name or lead.email}, veo que te interesa aprender. Tengo un curso que podría interesarte. ¿Te gustaría más información?"
    elif score > 40:
        next_action = "wait"
        message = "Seguiré monitoreando su interés."
    else:
        next_action = "wait"
        message = "Lead con bajo interés, esperar."

    return {
        "intent_score": score,
        "recommended_course": recommended,
        "next_action": next_action,
        "suggested_message": message,
        "reasoning": f"Análisis basado en datos del lead. Puntuación: {score}"
    }


# ==================== EVALUAR LEADES NUEVOS ====================
async def evaluate_new_leads(db: Session) -> list:
    """
    Evalúa todos los leads nuevos y devuelve recomendaciones
    """
    new_leads = db.query(models.Lead).filter(
        models.Lead.status == models.LeadStatus.NEW
    ).all()

    results = []
    for lead in new_leads:
        analysis = await analyze_lead_with_ai(lead, db)
        results.append({
            "lead_id": lead.id,
            "lead_email": lead.email,
            "analysis": analysis
        })

    return results


# ==================== RECOMENDAR CURSO PARA LEAD ====================
async def recommend_course_for_lead(lead: models.Lead, db: Session):
    """
    Recomienda el mejor curso para un lead específico
    """
    analysis = await analyze_lead_with_ai(lead, db)

    # Buscar el curso recomendado en la base de datos
    recommended_course = db.query(models.Course).filter(
        models.Course.title == analysis.get("recommended_course", "")
    ).first()

    return {
        "lead_id": lead.id,
        "lead_email": lead.email,
        "intent_score": analysis.get("intent_score", 0),
        "recommended_course_id": recommended_course.id if recommended_course else None,
        "recommended_course_title": analysis.get("recommended_course"),
        "suggested_message": analysis.get("suggested_message"),
        "next_action": analysis.get("next_action")
    }


# ==================== ENVIAR SEGUIMIENTO AUTOMÁTICO ====================
async def send_auto_followup(lead: models.Lead, db: Session):
    """
    Envía un email de seguimiento automático basado en análisis IA
    """
    analysis = await analyze_lead_with_ai(lead, db)

    if analysis.get("next_action") == "email":
        # Aquí integrarías con SendGrid, Mailgun, etc.
        print(f"📧 Enviando email a {lead.email}")
        print(f"   Mensaje: {analysis.get('suggested_message')}")

        # Actualizar lead
        lead.last_contact = datetime.utcnow()
        lead.status = models.LeadStatus.CONTACTED
        db.commit()

        return {
            "status": "email_sent",
            "lead_id": lead.id,
            "message": analysis.get("suggested_message")
        }

    return {
        "status": "no_action",
        "lead_id": lead.id,
        "suggested_action": analysis.get("next_action")
    }