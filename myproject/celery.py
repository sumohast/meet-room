import os
from celery import Celery

# تنظیم متغیر محیطی پیش‌فرض برای تنظیمات جنگو برای برنامه Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')

# استفاده از یک رشته در اینجا به این معنی است که worker نیازی به serialize کردن
# شیء پیکربندی به فرزندان ندارد.
# namespace='CELERY' به این معنی است که تمام کلیدهای پیکربندی مربوط به Celery
# باید با پیشوند 'CELERY_' شروع شوند.
app.config_from_object('django.conf:settings', namespace='CELERY')

# بارگذاری خودکار ماژول‌های tasks.py از تمام برنامه‌های ثبت شده جنگو
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')