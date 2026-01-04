"""
AgriSecure IoT System - Notification Tasks

Task Celery per invio notifiche asincrone:
- Push notifications (Firebase)
- SMS (Twilio)
- Email
- Telegram
"""

import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

import requests

logger = logging.getLogger('agrisecure')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_alarm_notification(self, alarm_id):
    """
    Invia notifiche per un allarme critico
    """
    from apps.security.models import Alarm
    
    try:
        alarm = Alarm.objects.select_related('node', 'event').get(id=alarm_id)
    except Alarm.DoesNotExist:
        logger.error(f"Allarme {alarm_id} non trovato")
        return
    
    logger.info(f"Invio notifiche per allarme {alarm_id}")
    
    channels_sent = []
    
    # Prepara messaggio
    message = _format_alarm_message(alarm)
    
    # Push notification
    try:
        if _send_push_notification(alarm, message):
            channels_sent.append('push')
    except Exception as e:
        logger.error(f"Errore push notification: {e}")
    
    # Telegram
    try:
        if _send_telegram_notification(alarm, message):
            channels_sent.append('telegram')
    except Exception as e:
        logger.error(f"Errore Telegram: {e}")
    
    # SMS (solo per allarmi critici)
    if alarm.priority == 'critical':
        try:
            if _send_sms_notification(alarm, message):
                channels_sent.append('sms')
        except Exception as e:
            logger.error(f"Errore SMS: {e}")
    
    # Email
    try:
        if _send_email_notification(alarm, message):
            channels_sent.append('email')
    except Exception as e:
        logger.error(f"Errore email: {e}")
    
    # Aggiorna allarme
    alarm.notification_sent = True
    alarm.notifications_sent = channels_sent
    alarm.save(update_fields=['notification_sent', 'notifications_sent'])
    
    logger.info(f"Notifiche inviate su: {channels_sent}")
    return channels_sent


def _format_alarm_message(alarm):
    """Formatta messaggio allarme"""
    classification_names = {
        'person': '🚨 PERSONA RILEVATA',
        'tamper': '⚠️ MANOMISSIONE',
        'animal_lg': '🦊 Animale grande',
        'unknown': '❓ Movimento sconosciuto',
    }
    
    title = classification_names.get(alarm.classification, 'Allarme')
    
    message = {
        'title': title,
        'body': f"Nodo: {alarm.node.name} ({alarm.node.node_id})\n"
                f"Ora: {alarm.triggered_at.strftime('%H:%M:%S')}\n"
                f"Priorità: {alarm.priority.upper()}",
        'data': {
            'alarm_id': alarm.id,
            'node_id': alarm.node.node_id,
            'classification': alarm.classification,
            'priority': alarm.priority,
        }
    }
    
    return message


def _send_push_notification(alarm, message):
    """Invia push notification via Firebase"""
    from push_notifications.models import GCMDevice
    
    fcm_key = settings.PUSH_NOTIFICATIONS_SETTINGS.get('FCM_API_KEY')
    if not fcm_key:
        logger.warning("FCM_API_KEY non configurata")
        return False
    
    devices = GCMDevice.objects.filter(active=True)
    if not devices.exists():
        logger.warning("Nessun dispositivo registrato per push")
        return False
    
    devices.send_message(
        message['body'],
        title=message['title'],
        extra=message['data']
    )
    
    return True


def _send_telegram_notification(alarm, message):
    """Invia notifica Telegram"""
    config = settings.TELEGRAM_CONFIG
    
    if not config.get('BOT_TOKEN') or not config.get('CHAT_ID'):
        logger.warning("Telegram non configurato")
        return False
    
    text = f"*{message['title']}*\n\n{message['body']}"
    
    url = f"https://api.telegram.org/bot{config['BOT_TOKEN']}/sendMessage"
    payload = {
        'chat_id': config['CHAT_ID'],
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    response = requests.post(url, json=payload, timeout=10)
    
    if response.status_code == 200:
        logger.info("Notifica Telegram inviata")
        return True
    else:
        logger.error(f"Errore Telegram: {response.text}")
        return False


def _send_sms_notification(alarm, message):
    """Invia SMS via Twilio"""
    config = settings.TWILIO_CONFIG
    
    if not config.get('ACCOUNT_SID') or not config.get('AUTH_TOKEN'):
        logger.warning("Twilio non configurato")
        return False
    
    from twilio.rest import Client
    
    client = Client(config['ACCOUNT_SID'], config['AUTH_TOKEN'])
    
    # Numeri destinatari (da configurare)
    recipients = settings.AGRISECURE.get('SMS_RECIPIENTS', [])
    
    if not recipients:
        logger.warning("Nessun destinatario SMS configurato")
        return False
    
    sms_text = f"{message['title']}\n{message['body']}"
    
    for phone in recipients:
        try:
            client.messages.create(
                body=sms_text[:160],  # Limite SMS
                from_=config['FROM_NUMBER'],
                to=phone
            )
            logger.info(f"SMS inviato a {phone}")
        except Exception as e:
            logger.error(f"Errore SMS a {phone}: {e}")
    
    return True


def _send_email_notification(alarm, message):
    """Invia email di notifica"""
    recipients = settings.AGRISECURE.get('EMAIL_RECIPIENTS', [])
    
    if not recipients:
        logger.warning("Nessun destinatario email configurato")
        return False
    
    subject = f"[AgriSecure] {message['title']}"
    
    # Render template HTML
    html_content = render_to_string('notifications/alarm_email.html', {
        'alarm': alarm,
        'message': message,
    })
    
    text_content = f"{message['title']}\n\n{message['body']}"
    
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_content,
            fail_silently=False,
        )
        logger.info(f"Email inviata a {len(recipients)} destinatari")
        return True
    except Exception as e:
        logger.error(f"Errore invio email: {e}")
        return False


@shared_task
def send_daily_report():
    """
    Task schedulato: report giornaliero
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.nodes.models import Node
    from apps.sensors.models import SensorReading, SensorAlert
    from apps.security.models import Alarm
    
    yesterday = timezone.now() - timedelta(days=1)
    
    # Statistiche
    stats = {
        'date': yesterday.date(),
        'nodes_active': Node.objects.filter(is_active=True).count(),
        'readings_count': SensorReading.objects.filter(
            timestamp__date=yesterday.date()
        ).count(),
        'alerts_count': SensorAlert.objects.filter(
            timestamp__date=yesterday.date()
        ).count(),
        'alarms_count': Alarm.objects.filter(
            triggered_at__date=yesterday.date()
        ).count(),
    }
    
    # Temperature min/max
    temp_stats = SensorReading.objects.filter(
        timestamp__date=yesterday.date(),
        temperature__isnull=False
    ).aggregate(
        min_temp=Min('temperature'),
        max_temp=Max('temperature'),
        avg_temp=Avg('temperature')
    )
    stats.update(temp_stats)
    
    # Invia report
    recipients = settings.AGRISECURE.get('REPORT_RECIPIENTS', [])
    if recipients:
        html_content = render_to_string('notifications/daily_report.html', {
            'stats': stats
        })
        
        send_mail(
            subject=f"[AgriSecure] Report Giornaliero - {stats['date']}",
            message=str(stats),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_content,
        )
    
    logger.info(f"Report giornaliero generato: {stats}")
    return stats


@shared_task
def check_node_health():
    """
    Task schedulato: verifica salute nodi
    """
    from django.utils import timezone
    from apps.nodes.models import Node, NodeStatus, NodeEvent
    
    timeout_warning = settings.AGRISECURE.get('NODE_TIMEOUT_WARNING', 3600)
    timeout_critical = settings.AGRISECURE.get('NODE_TIMEOUT_CRITICAL', 7200)
    now = timezone.now()
    
    offline_nodes = []
    warning_nodes = []
    
    for node in Node.objects.filter(is_active=True):
        if not node.last_seen:
            continue
        
        seconds_since = (now - node.last_seen).total_seconds()
        
        if seconds_since > timeout_critical and node.status != NodeStatus.OFFLINE:
            node.status = NodeStatus.OFFLINE
            node.save(update_fields=['status'])
            offline_nodes.append(node)
            
            NodeEvent.objects.create(
                node=node,
                event_type=NodeEvent.EventType.OFFLINE,
                message=f"Nodo offline da {int(seconds_since/60)} minuti"
            )
            
        elif seconds_since > timeout_warning and node.status == NodeStatus.ONLINE:
            node.status = NodeStatus.WARNING
            node.save(update_fields=['status'])
            warning_nodes.append(node)
    
    # Notifica se ci sono nodi offline
    if offline_nodes:
        _notify_offline_nodes(offline_nodes)
    
    return {
        'offline': [n.node_id for n in offline_nodes],
        'warning': [n.node_id for n in warning_nodes]
    }


def _notify_offline_nodes(nodes):
    """Notifica nodi offline"""
    message = {
        'title': '⚠️ Nodi Offline',
        'body': f"{len(nodes)} nodi non rispondono:\n" + 
                "\n".join([f"- {n.node_id}: {n.name}" for n in nodes]),
        'data': {'type': 'node_offline'}
    }
    
    # Telegram
    config = settings.TELEGRAM_CONFIG
    if config.get('BOT_TOKEN') and config.get('CHAT_ID'):
        url = f"https://api.telegram.org/bot{config['BOT_TOKEN']}/sendMessage"
        requests.post(url, json={
            'chat_id': config['CHAT_ID'],
            'text': f"*{message['title']}*\n\n{message['body']}",
            'parse_mode': 'Markdown'
        }, timeout=10)


@shared_task
def cleanup_old_data():
    """
    Task schedulato: pulizia dati vecchi
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.sensors.models import SensorReading
    from apps.nodes.models import NodeHeartbeat
    
    retention = settings.AGRISECURE.get('DATA_RETENTION_DAYS', {})
    
    # Pulizia letture sensori
    sensor_days = retention.get('SENSOR_DATA', 365)
    cutoff = timezone.now() - timedelta(days=sensor_days)
    deleted_sensors = SensorReading.objects.filter(timestamp__lt=cutoff).delete()
    
    # Pulizia heartbeat (più aggressiva)
    heartbeat_days = 30
    cutoff = timezone.now() - timedelta(days=heartbeat_days)
    deleted_heartbeats = NodeHeartbeat.objects.filter(timestamp__lt=cutoff).delete()
    
    logger.info(f"Cleanup: {deleted_sensors[0]} letture, {deleted_heartbeats[0]} heartbeats")
    
    return {
        'sensor_readings_deleted': deleted_sensors[0],
        'heartbeats_deleted': deleted_heartbeats[0]
    }
