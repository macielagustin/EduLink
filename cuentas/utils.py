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

# cuentas/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def enviar_email_notificacion(destinatario, asunto, template_html, contexto):
    """
    Envía un email utilizando una plantilla HTML.
    """
    if not destinatario:
        return
    html_mensaje = render_to_string(template_html, contexto)
    texto_mensaje = strip_tags(html_mensaje)
    send_mail(
        subject=asunto,
        message=texto_mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[destinatario],
        html_message=html_mensaje,
        fail_silently=False,
    )