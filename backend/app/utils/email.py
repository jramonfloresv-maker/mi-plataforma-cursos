# backend/app/utils/email.py
import sib_api_v3_sdk
from sib_api_v3_sdk import SendSmtpEmail, SendSmtpEmailTo, SendSmtpEmailSender
import os

# Configuración del cliente de Brevo
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')  # <- Toma la variable de Render

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))


def enviar_correo(destinatario, asunto, contenido_html):
    """
    Función genérica para enviar correos usando Brevo.
    """
    sender = {"name": "EduPlatform", "email": "floval_2000@yahoo.com"}
    to = [{"email": destinatario['email'], "name": destinatario['name']}]

    send_smtp_email = SendSmtpEmail(
        to=to,
        sender=sender,
        subject=asunto,
        html_content=contenido_html
    )

    print(f"📧 Preparando envío a: {destinatario['email']}")
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"✅ CORREO ENVIADO. ID de Brevo: {api_response}")
        return True
    except Exception as e:
        # Este es el mensaje de error que necesitamos ver
        print(f"❌ ERROR DETALLADO DE BREVO: {e}")
        # Si el error tiene cuerpo, lo imprimimos también
        if hasattr(e, 'body'):
            print(f"   Cuerpo del error: {e.body}")
        return False


# Ejemplo de contenido HTML para el email de bienvenida
def email_bienvenida(nombre_usuario):
    return f"""
    <html>
        <body>
            <h1>¡Bienvenido a EduPlatform, {nombre_usuario}!</h1>
            <p>Nos alegra que te hayas unido a nuestra comunidad de aprendizaje.</p>
            <p>Estamos aquí para ayudarte a transformar tu futuro.</p>
            <br>
            <p>El equipo de EduPlatform</p>
        </body>
    </html>
    """

def email_confirmacion_compra(nombre_usuario, curso_titulo, curso_precio):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h1 style="color: #667eea;">¡Gracias por tu compra, {nombre_usuario}!</h1>
            <p>Has adquirido el curso:</p>
            <h2>{curso_titulo}</h2>
            <p><strong>Precio pagado:</strong> ${curso_precio}</p>
            <p>Ya puedes acceder al curso desde tu <a href="https://mi-plataforma-cursos-7g5k.onrender.com/dashboard">panel de control</a>.</p>
            <br>
            <p>El equipo de EduPlatform</p>
        </body>
    </html>
    """