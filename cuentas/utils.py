from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

def enviar_email(destinatario, asunto, mensaje_texto, mensaje_html=None):
    """
    Envía un correo que puede incluir HTML.
    """
    email = EmailMultiAlternatives(
        subject=asunto,
        body=mensaje_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    if mensaje_html:
        email.attach_alternative(mensaje_html, "text/html")
    email.send()