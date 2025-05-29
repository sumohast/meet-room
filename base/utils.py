# base/utils.py
import threading
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailThread(threading.Thread):
    def __init__(self, subject, message_content, recipient_list, reservation_id=None):
        self.subject = subject
        self.message_content = message_content
        self.recipient_list = recipient_list
        self.reservation_id = reservation_id # برای لاگ کردن
        threading.Thread.__init__(self)

    def run(self):
        if not self.recipient_list:
            logger.warning(f"EmailThread for reservation_id {self.reservation_id}: No recipients. Skipping.")
            return

        try:
            send_mail(
                self.subject,
                self.message_content,
                settings.DEFAULT_FROM_EMAIL,
                self.recipient_list,
                fail_silently=False
            )
            logger.info(f"EmailThread for reservation_id {self.reservation_id}: Successfully sent to {', '.join(self.recipient_list)}")
        except Exception as e:
            logger.error(f"EmailThread for reservation_id {self.reservation_id}: ERROR sending email to {', '.join(self.recipient_list)}: {str(e)}")

def send_email_in_background(subject, message_content, recipient_list, reservation_id=None):
    """
    تابعی برای شروع ارسال ایمیل در یک ترد جداگانه.
    """
    EmailThread(subject, message_content, recipient_list, reservation_id=reservation_id).start()