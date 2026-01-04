"""
AgriSecure IoT System - Celery Configuration
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrisecure.settings')

# Create Celery app
app = Celery('agrisecure')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all apps
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    # Verifica salute nodi ogni 5 minuti
    'check-node-health': {
        'task': 'apps.notifications.tasks.check_node_health',
        'schedule': 300.0,  # 5 minuti
    },
    
    # Report giornaliero alle 8:00
    'daily-report': {
        'task': 'apps.notifications.tasks.send_daily_report',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Pulizia dati vecchi ogni domenica alle 3:00
    'cleanup-old-data': {
        'task': 'apps.notifications.tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    
    # Aggregazione dati sensori ogni ora
    'aggregate-sensor-data': {
        'task': 'apps.sensors.tasks.aggregate_hourly_data',
        'schedule': crontab(minute=5),  # 5 minuti dopo ogni ora
    },
}

app.conf.timezone = 'Europe/Rome'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
