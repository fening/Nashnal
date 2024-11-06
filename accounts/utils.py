# accounts/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def send_templated_email(template_prefix, context, subject, recipient_list):
    """
    Send an email using HTML and text templates.
    """
    try:
        # Render HTML and text versions
        html_template = f"{template_prefix}_email.html"
        text_template = f"{template_prefix}_email.txt"
        
        html_content = render_to_string(html_template, context)
        text_content = render_to_string(text_template, context)
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        logger.info(f"Successfully sent email to {', '.join(recipient_list)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {', '.join(recipient_list)}: {str(e)}")
        return False

def send_registration_invitation(invitation, request):
    """
    Send a registration invitation email.
    """
    # Build the registration URL
    registration_url = request.build_absolute_uri(
        reverse('complete_registration', args=[str(invitation.token)])
    )
    
    context = {
        'invitation': invitation,
        'registration_url': registration_url,
    }
    
    return send_templated_email(
        template_prefix='registration/invitation',
        context=context,
        subject='Complete Your TimeSheet App Registration',
        recipient_list=[invitation.email]
    )

def send_invitation_reminder(invitation, request):
    """
    Send a reminder email for pending registration invitations.
    """
    registration_url = request.build_absolute_uri(
        reverse('complete_registration', args=[str(invitation.token)])
    )
    
    context = {
        'invitation': invitation,
        'registration_url': registration_url,
        'is_reminder': True,
        'expires_in_days': (invitation.expires_at - timezone.now()).days
    }
    
    return send_templated_email(
        template_prefix='registration/invitation_reminder',
        context=context,
        subject='Reminder: Complete Your TimeSheet App Registration',
        recipient_list=[invitation.email]
    )

def send_invitation_cancelled_notification(invitation):
    """
    Send a notification when an invitation is cancelled.
    """
    context = {
        'invitation': invitation,
    }
    
    return send_templated_email(
        template_prefix='registration/invitation_cancelled',
        context=context,
        subject='TimeSheet App Registration Invitation Cancelled',
        recipient_list=[invitation.email]
    )