from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
import stripe
import os
from ..database import get_db
from .. import models, schemas, auth

# Importar las funciones de email
from backend.app.utils.email import enviar_correo, email_confirmacion_compra

router = APIRouter(prefix="/payments", tags=["Pagos"])

# Configurar Stripe con la clave secreta
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN = os.getenv("DOMAIN", "http://localhost:8000")


# ==================== CREAR SESIÓN DE PAGO ====================
@router.post("/create-checkout/{course_id}")
def create_checkout_session(
        course_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """
    Crear una sesión de pago de Stripe para comprar un curso
    Retorna la URL de checkout a donde redirigir al usuario
    """

    # 1. Obtener el curso de la base de datos
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # 2. Verificar que el usuario no haya comprado ya el curso
    existing_purchase = db.query(models.Purchase).filter(
        models.Purchase.user_id == current_user.id,
        models.Purchase.course_id == course_id,
        models.Purchase.status == "completed"
    ).first()

    if existing_purchase:
        raise HTTPException(status_code=400, detail="Ya has comprado este curso")

    try:
        # 3. Crear la sesión de checkout en Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": course.title,
                            "description": course.description[:200] if course.description else "",
                        },
                        "unit_amount": int(course.price * 100),  # Stripe usa centavos
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=f"{DOMAIN}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{DOMAIN}/payments/cancel",
            metadata={
                "course_id": str(course_id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "course_title": course.title,
                "course_price": str(course.price)
            },
            customer_email=current_user.email,
        )

        return {
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url,
            "message": "Sesión de pago creada exitosamente"
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==================== VERIFICAR ESTADO DE SESIÓN ====================
@router.get("/session-status/{session_id}")
def get_session_status(
        session_id: str,
        db: Session = Depends(get_db)
):
    """
    Verificar el estado de una sesión de pago
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Buscar si ya existe la compra en nuestra base de datos
        purchase = db.query(models.Purchase).filter(
            models.Purchase.payment_id == session_id
        ).first()

        return {
            "session_id": session_id,
            "status": session.payment_status,
            "customer_email": session.customer_details.email if session.customer_details else None,
            "purchase_exists": purchase is not None,
            "purchase_status": purchase.status if purchase else None
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


# ==================== WEBHOOK DE STRIPE ====================
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook que Stripe llama cuando hay eventos de pago
    (pago completado, fallido, etc.)
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Si no hay webhook secret configurado, procesamos igual (solo para pruebas)
    if not webhook_secret:
        print("⚠️ STRIPE_WEBHOOK_SECRET no configurado. Procesando sin verificar firma...")
        try:
            import json
            event = json.loads(payload)
        except:
            raise HTTPException(status_code=400, detail="Payload inválido")
    else:
        # Verificar que el webhook viene realmente de Stripe
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Payload inválido")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=401, detail="Firma inválida")

    # Procesar según el tipo de evento
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_successful_payment(session, db)

    return {"status": "success"}


# ==================== FUNCIÓN AUXILIAR PARA PAGO EXITOSO ====================
async def handle_successful_payment(session: dict, db: Session):
    """
    Procesar un pago exitoso:
    1. Guardar la compra en la base de datos
    2. Dar acceso al curso al usuario
    3. Enviar email de confirmación de compra
    """
    metadata = session.get("metadata", {})
    course_id = int(metadata.get("course_id", 0))
    user_id = int(metadata.get("user_id", 0))
    customer_email = session.get("customer_details", {}).get("email")

    # Buscar el usuario por ID o email
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user and customer_email:
        user = db.query(models.User).filter(models.User.email == customer_email).first()

    if not user:
        print(f"⚠️ Usuario no encontrado para pago: {session['id']}")
        return

    # Verificar que el curso existe
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        print(f"⚠️ Curso {course_id} no encontrado")
        return

    # Verificar que no exista ya una compra
    existing = db.query(models.Purchase).filter(
        models.Purchase.payment_id == session["id"]
    ).first()

    if existing:
        print(f"ℹ️ Compra ya registrada: {session['id']}")
        return

    # Crear el registro de compra
    purchase = models.Purchase(
        user_id=user.id,
        course_id=course_id,
        amount=float(metadata.get("course_price", 0)),
        status="completed",
        payment_id=session["id"]
    )
    db.add(purchase)
    db.commit()

    print(f"✅ Pago registrado: Usuario {user.email} compró curso {course.title}")

    # ========== NUEVO: Enviar email de confirmación de compra ==========
    try:
        destinatario = {"name": user.name, "email": user.email}
        asunto = f"✅ Confirmación de compra: {course.title}"
        contenido_html = email_confirmacion_compra(user.name, course.title, course.price)
        enviar_correo(destinatario, asunto, contenido_html)
        print(f"📧 Email de confirmación enviado a {user.email}")
    except Exception as e:
        print(f"❌ Error al enviar email de confirmación: {e}")

    # Aquí puedes agregar lógica adicional:
    # - Activar acceso premium
    # - Registrar en sistema de analytics, etc.


# ==================== ENDPOINTS PARA PRUEBAS ====================
@router.get("/test-payment")
def test_payment_config():
    """
    Endpoint para verificar que Stripe está configurado correctamente
    """
    try:
        # Intentar hacer una llamada simple a Stripe
        stripe.Product.list(limit=1)
        return {
            "stripe_configured": True,
            "message": "Stripe está configurado correctamente",
            "api_version": stripe.api_version
        }
    except stripe.error.AuthenticationError:
        return {
            "stripe_configured": False,
            "error": "Clave API inválida. Revisa tu STRIPE_SECRET_KEY en .env"
        }
    except Exception as e:
        return {
            "stripe_configured": False,
            "error": str(e)
        }


# ==================== PÁGINAS DE ÉXITO Y CANCELACIÓN ====================
@router.get("/success")
def payment_success(session_id: str, db: Session = Depends(get_db)):
    """
    Página de éxito después de un pago completado
    """
    # Verificar el estado de la sesión
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Buscar la compra en nuestra base de datos
        purchase = db.query(models.Purchase).filter(
            models.Purchase.payment_id == session_id
        ).first()

        if purchase:
            course = db.query(models.Course).filter(
                models.Course.id == purchase.course_id
            ).first()

            return {
                "status": "success",
                "message": "¡Pago completado exitosamente!",
                "course_title": course.title if course else "Curso",
                "session_id": session_id,
                "customer_email": session.customer_details.email if session.customer_details else None
            }
        else:
            return {
                "status": "pending",
                "message": "Procesando pago... vuelve a intentar en unos segundos",
                "session_id": session_id
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error verificando pago: {str(e)}"
        }


@router.get("/cancel")
def payment_cancel():
    """
    Página cuando el usuario cancela el pago
    """
    return {
        "status": "canceled",
        "message": "El pago fue cancelado. Puedes intentar nuevamente cuando quieras."
    }