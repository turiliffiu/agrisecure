"""
AgriSecure Frontend Views
Dashboard views per il sistema di monitoraggio IoT
"""
import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.conf import settings

from apps.nodes.models import Node, Heartbeat
from apps.sensors.models import SensorReading, SensorAlert
from apps.security.models import SecurityEvent, Alarm, ArmState


# ============================================================
# Authentication Views
# ============================================================

def login_view(request):
    """Pagina di login"""
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('frontend:dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Logout utente"""
    logout(request)
    return redirect('frontend:login')


# ============================================================
# Dashboard Views
# ============================================================

@login_required
def dashboard(request):
    """Dashboard principale"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Statistiche nodi
    nodes = Node.objects.all()
    total_nodes = nodes.count()
    nodes_online = nodes.filter(status='online').count()
    nodes_offline = nodes.filter(status='offline').count()
    
    # Allarmi
    active_alarms = Alarm.objects.filter(status__in=['active', 'acknowledged']).count()
    alarms_today = Alarm.objects.filter(triggered_at__gte=today_start).count()
    recent_alarms = Alarm.objects.filter(
        status__in=['active', 'acknowledged']
    ).select_related('node').order_by('-triggered_at')[:5]
    
    # Stato armamento
    arm_state = ArmState.objects.order_by('-changed_at').first()
    system_armed = arm_state and arm_state.mode != 'disarmed' if arm_state else False
    arm_mode = arm_state.mode if arm_state else None
    
    # Ultime letture sensori
    latest_reading = SensorReading.objects.order_by('-timestamp').first()
    latest_temperature = latest_reading.temperature if latest_reading else None
    latest_humidity = latest_reading.humidity if latest_reading else None
    latest_soil = latest_reading.soil_moisture if latest_reading else None
    
    # Batterie basse
    battery_warnings = nodes.filter(battery_level__lt=20, battery_level__isnull=False).count()
    
    # Dati per il grafico (ultime 24 ore)
    chart_data = get_chart_data(hours=24)
    
    context = {
        'total_nodes': total_nodes,
        'nodes_online': nodes_online,
        'nodes_offline': nodes_offline,
        'active_alarms': active_alarms,
        'alarms_today': alarms_today,
        'recent_alarms': recent_alarms,
        'system_armed': system_armed,
        'arm_mode': arm_mode,
        'latest_temperature': latest_temperature,
        'latest_humidity': latest_humidity,
        'latest_soil': latest_soil,
        'battery_warnings': battery_warnings,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'dashboard/index.html', context)


def get_chart_data(hours=24, node_id=None):
    """Genera dati per i grafici"""
    now = timezone.now()
    since = now - timedelta(hours=hours)
    
    readings = SensorReading.objects.filter(timestamp__gte=since)
    if node_id:
        readings = readings.filter(node__node_id=node_id)
    
    readings = readings.order_by('timestamp')
    
    # Raggruppa per ora
    hourly_data = {}
    for reading in readings:
        hour_key = reading.timestamp.strftime('%H:%M')
        if hour_key not in hourly_data:
            hourly_data[hour_key] = {'temps': [], 'hums': [], 'soils': []}
        
        if reading.temperature:
            hourly_data[hour_key]['temps'].append(float(reading.temperature))
        if reading.humidity:
            hourly_data[hour_key]['hums'].append(float(reading.humidity))
        if reading.soil_moisture:
            hourly_data[hour_key]['soils'].append(float(reading.soil_moisture))
    
    labels = sorted(hourly_data.keys())
    temperature = []
    humidity = []
    soil = []
    
    for label in labels:
        data = hourly_data[label]
        temperature.append(sum(data['temps']) / len(data['temps']) if data['temps'] else None)
        humidity.append(sum(data['hums']) / len(data['hums']) if data['hums'] else None)
        soil.append(sum(data['soils']) / len(data['soils']) if data['soils'] else None)
    
    return {
        'labels': labels,
        'temperature': temperature,
        'humidity': humidity,
        'soil': soil,
    }


# ============================================================
# Nodes Views
# ============================================================

@login_required
def nodes_list(request):
    """Lista nodi"""
    nodes = Node.objects.all()
    
    # Filtri
    search = request.GET.get('search', '')
    node_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    
    if search:
        nodes = nodes.filter(
            Q(name__icontains=search) | Q(node_id__icontains=search)
        )
    if node_type:
        nodes = nodes.filter(node_type=node_type)
    if status:
        nodes = nodes.filter(status=status)
    
    # Statistiche
    all_nodes = Node.objects.all()
    
    context = {
        'nodes': nodes.order_by('-status', 'name'),
        'total_nodes': all_nodes.count(),
        'nodes_online': all_nodes.filter(status='online').count(),
        'nodes_offline': all_nodes.filter(status='offline').count(),
        'nodes_warning': all_nodes.filter(status='warning').count(),
    }
    
    return render(request, 'nodes/list.html', context)


@login_required
def node_detail(request, node_id):
    """Dettaglio singolo nodo"""
    node = get_object_or_404(Node, id=node_id)
    
    # Ultime letture (per nodi ambient)
    latest_readings = []
    chart_data = {'labels': [], 'datasets': []}
    
    if node.node_type == 'ambient':
        latest_readings = SensorReading.objects.filter(
            node=node
        ).order_by('-timestamp')[:20]
        
        # Dati grafico
        raw_data = get_chart_data(hours=24, node_id=node.node_id)
        chart_data = {
            'labels': raw_data['labels'],
            'datasets': [
                {
                    'label': 'Temperatura (°C)',
                    'data': raw_data['temperature'],
                    'borderColor': '#ef4444',
                    'fill': False,
                },
                {
                    'label': 'Umidità (%)',
                    'data': raw_data['humidity'],
                    'borderColor': '#3b82f6',
                    'fill': False,
                },
            ]
        }
    
    context = {
        'node': node,
        'latest_readings': latest_readings,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'nodes/detail.html', context)


@login_required
def node_command(request, node_id):
    """Invia comando a un nodo"""
    if request.method == 'POST':
        node = get_object_or_404(Node, id=node_id)
        command = request.POST.get('command', '')
        
        if command:
            # TODO: Implementare invio comando via MQTT
            from apps.core.mqtt_publisher import mqtt_publish
            try:
                mqtt_publish(f'agrisecure/{node.node_id}/command', {
                    'command': command,
                    'timestamp': timezone.now().isoformat()
                })
                messages.success(request, f'Comando "{command}" inviato a {node.name or node.node_id}')
            except Exception as e:
                messages.error(request, f'Errore invio comando: {str(e)}')
        
        return redirect('frontend:node_detail', node_id=node_id)
    
    return redirect('frontend:nodes')


# ============================================================
# Sensors Views
# ============================================================

@login_required
def sensors(request):
    """Pagina sensori"""
    hours = int(request.GET.get('hours', 24))
    node_id = request.GET.get('node', '')
    
    # Ultima lettura
    latest = SensorReading.objects.order_by('-timestamp').first()
    
    # Nodi ambientali
    ambient_nodes = Node.objects.filter(node_type='ambient')
    
    # Dati grafico
    chart_data = get_chart_data(hours=hours, node_id=node_id if node_id else None)
    
    # Alert attivi
    alerts = SensorAlert.objects.filter(is_resolved=False).order_by('-created_at')
    
    context = {
        'latest': latest,
        'ambient_nodes': ambient_nodes,
        'chart_data': json.dumps(chart_data),
        'alerts': alerts,
    }
    
    return render(request, 'sensors/index.html', context)


@login_required
def sensor_alert_acknowledge(request, alert_id):
    """Acknowledge alert sensore"""
    if request.method == 'POST':
        alert = get_object_or_404(SensorAlert, id=alert_id)
        alert.is_acknowledged = True
        alert.acknowledged_at = timezone.now()
        alert.save()
        messages.success(request, 'Alert preso in carico')
    return redirect('frontend:sensors')


@login_required
def sensor_alert_resolve(request, alert_id):
    """Risolvi alert sensore"""
    if request.method == 'POST':
        alert = get_object_or_404(SensorAlert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        messages.success(request, 'Alert risolto')
    return redirect('frontend:sensors')


# ============================================================
# Security Views
# ============================================================

@login_required
def alarms(request):
    """Lista allarmi"""
    alarms_qs = Alarm.objects.select_related('node').order_by('-triggered_at')
    
    # Filtri
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    
    if status:
        alarms_qs = alarms_qs.filter(status=status)
    if priority:
        alarms_qs = alarms_qs.filter(priority=priority)
    
    # Paginazione
    paginator = Paginator(alarms_qs, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    
    # Statistiche
    all_alarms = Alarm.objects.all()
    stats = {
        'active': all_alarms.filter(status='active').count(),
        'acknowledged': all_alarms.filter(status='acknowledged').count(),
        'resolved': all_alarms.filter(
            status='resolved',
            triggered_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'false_positive_rate': 0,  # TODO: calcolare
    }
    
    context = {
        'alarms': page_obj,
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'security/alarms.html', context)


@login_required
def alarm_action(request, alarm_id, action):
    """Esegui azione su allarme"""
    if request.method == 'POST':
        alarm = get_object_or_404(Alarm, id=alarm_id)
        
        if action == 'acknowledge':
            alarm.status = 'acknowledged'
            alarm.acknowledged_at = timezone.now()
            alarm.acknowledged_by = request.user.username
            messages.success(request, 'Allarme preso in carico')
        
        elif action == 'resolve':
            alarm.status = 'resolved'
            alarm.resolved_at = timezone.now()
            messages.success(request, 'Allarme risolto')
        
        elif action == 'false_positive':
            alarm.status = 'resolved'
            alarm.resolved_at = timezone.now()
            alarm.is_false_positive = True
            messages.success(request, 'Allarme segnato come falso positivo')
        
        alarm.save()
    
    return redirect('frontend:alarms')


@login_required
def arm_system(request):
    """Pagina armamento sistema"""
    arm_state = ArmState.objects.order_by('-changed_at').first()
    is_armed = arm_state and arm_state.mode != 'disarmed' if arm_state else False
    
    security_nodes = Node.objects.filter(node_type='security')
    armed_nodes = []
    
    if is_armed and arm_state and arm_state.armed_nodes:
        armed_node_ids = arm_state.armed_nodes
        armed_nodes = Node.objects.filter(node_id__in=armed_node_ids)
    
    context = {
        'is_armed': is_armed,
        'current_state': arm_state,
        'security_nodes': security_nodes,
        'armed_nodes': armed_nodes,
    }
    
    return render(request, 'security/arm.html', context)


@login_required
def arm_action(request):
    """Arma/Disarma sistema"""
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'arm':
            mode = request.POST.get('mode', 'away')
            nodes = request.POST.getlist('nodes', [])
            notes = request.POST.get('notes', '')
            
            # Crea nuovo stato
            ArmState.objects.create(
                mode=mode,
                armed_nodes=nodes,
                changed_by=request.user.username,
                notes=notes
            )
            
            # Invia comando ai nodi
            from apps.core.mqtt_publisher import mqtt_publish
            for node_id in nodes:
                try:
                    mqtt_publish(f'agrisecure/{node_id}/command', {
                        'command': 'arm',
                        'mode': mode,
                        'timestamp': timezone.now().isoformat()
                    })
                except:
                    pass
            
            messages.success(request, 'Sistema armato con successo')
        
        elif action == 'disarm':
            # Crea stato disarmato
            ArmState.objects.create(
                mode='disarmed',
                armed_nodes=[],
                changed_by=request.user.username
            )
            
            # Invia comando di disarmo a tutti i nodi security
            from apps.core.mqtt_publisher import mqtt_publish
            for node in Node.objects.filter(node_type='security'):
                try:
                    mqtt_publish(f'agrisecure/{node.node_id}/command', {
                        'command': 'disarm',
                        'timestamp': timezone.now().isoformat()
                    })
                except:
                    pass
            
            messages.success(request, 'Sistema disarmato')
    
    return redirect('frontend:arm')


# ============================================================
# Settings Views
# ============================================================

@login_required
def settings_view(request):
    """Pagina impostazioni"""
    # Verifica configurazioni
    telegram_configured = bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', None))
    email_configured = bool(getattr(settings, 'EMAIL_HOST_USER', None))
    
    # Info sistema
    total_nodes = Node.objects.count()
    last_reading = SensorReading.objects.order_by('-timestamp').first()
    last_data_update = last_reading.timestamp if last_reading else None
    
    # Stato MQTT
    mqtt_status = True  # TODO: verificare connessione reale
    
    context = {
        'telegram_configured': telegram_configured,
        'email_configured': email_configured,
        'mqtt_status': mqtt_status,
        'total_nodes': total_nodes,
        'last_data_update': last_data_update,
    }
    
    return render(request, 'settings/index.html', context)


@login_required
def restart_services(request):
    """Riavvia servizi (solo admin)"""
    if request.method == 'POST' and request.user.is_superuser:
        import subprocess
        try:
            subprocess.run(['systemctl', 'restart', 'agrisecure-celery'], check=True)
            subprocess.run(['systemctl', 'restart', 'agrisecure-mqtt'], check=True)
            messages.success(request, 'Servizi riavviati con successo')
        except Exception as e:
            messages.error(request, f'Errore riavvio: {str(e)}')
    else:
        messages.error(request, 'Permessi insufficienti')
    
    return redirect('frontend:settings')


@login_required
def cleanup_data(request):
    """Pulisci dati vecchi (solo admin)"""
    if request.method == 'POST' and request.user.is_superuser:
        threshold = timezone.now() - timedelta(days=30)
        deleted, _ = SensorReading.objects.filter(timestamp__lt=threshold).delete()
        messages.success(request, f'Eliminate {deleted} letture vecchie')
    else:
        messages.error(request, 'Permessi insufficienti')
    
    return redirect('frontend:settings')
