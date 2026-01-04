"""
AgriSecure IoT System - API Views

ViewSets e Views per le API REST
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Min, Max, Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.nodes.models import Node, NodeStatus, NodeHeartbeat, NodeEvent
from apps.sensors.models import SensorReading, SensorAggregate, SensorAlert
from apps.security.models import (
    SecurityEvent, Alarm, SystemArmState, SecurityZone, IntrusionClass
)
from .serializers import (
    NodeListSerializer, NodeDetailSerializer, NodeHeartbeatSerializer, NodeEventSerializer,
    SensorReadingSerializer, SensorReadingCreateSerializer, 
    SensorAggregateSerializer, SensorAlertSerializer,
    SecurityEventSerializer, AlarmListSerializer, AlarmDetailSerializer,
    AlarmActionSerializer, SystemArmStateSerializer, ArmSystemSerializer,
    SecurityZoneSerializer, DashboardSummarySerializer
)


# ===========================================
# Node ViewSets
# ===========================================

class NodeViewSet(viewsets.ModelViewSet):
    """
    API endpoint per gestione nodi IoT
    """
    queryset = Node.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['node_type', 'status', 'is_armed']
    search_fields = ['node_id', 'name', 'description']
    ordering_fields = ['node_id', 'last_seen', 'status', 'battery_percentage']
    ordering = ['node_type', 'node_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NodeListSerializer
        return NodeDetailSerializer
    
    @action(detail=True, methods=['get'])
    def heartbeats(self, request, pk=None):
        """Storico heartbeat del nodo"""
        node = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        heartbeats = NodeHeartbeat.objects.filter(
            node=node,
            timestamp__gte=since
        ).order_by('-timestamp')[:100]
        
        serializer = NodeHeartbeatSerializer(heartbeats, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Eventi del nodo"""
        node = self.get_object()
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        
        events = NodeEvent.objects.filter(
            node=node,
            timestamp__gte=since
        ).order_by('-timestamp')[:50]
        
        serializer = NodeEventSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_command(self, request, pk=None):
        """Invia comando al nodo via MQTT"""
        node = self.get_object()
        command = request.data.get('command')
        
        if not command:
            return Response(
                {'error': 'Comando richiesto'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Pubblica comando su MQTT
        from apps.core.mqtt_publisher import publish_command
        success = publish_command(node.node_id, command, request.data.get('params', {}))
        
        if success:
            return Response({'status': 'Comando inviato'})
        return Response(
            {'error': 'Errore invio comando'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===========================================
# Sensor ViewSets
# ===========================================

class SensorReadingViewSet(viewsets.ModelViewSet):
    """
    API endpoint per letture sensori
    """
    queryset = SensorReading.objects.select_related('node')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['node__node_id']
    ordering = ['-timestamp']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SensorReadingCreateSerializer
        return SensorReadingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro per range temporale
        hours = self.request.query_params.get('hours')
        if hours:
            since = timezone.now() - timedelta(hours=int(hours))
            queryset = queryset.filter(timestamp__gte=since)
        
        return queryset[:500]  # Limita risultati
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Ultime letture per ogni nodo"""
        from django.db.models import Subquery, OuterRef
        
        # Subquery per ultima lettura per nodo
        latest_ids = SensorReading.objects.filter(
            node=OuterRef('node')
        ).order_by('-timestamp').values('id')[:1]
        
        readings = SensorReading.objects.filter(
            id__in=Subquery(
                SensorReading.objects.filter(
                    node__node_type='AMB'
                ).values('node').annotate(
                    latest_id=Max('id')
                ).values('latest_id')
            )
        ).select_related('node')
        
        serializer = SensorReadingSerializer(readings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def chart_data(self, request):
        """Dati per grafici"""
        node_id = request.query_params.get('node_id')
        hours = int(request.query_params.get('hours', 24))
        
        if not node_id:
            return Response(
                {'error': 'node_id richiesto'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        since = timezone.now() - timedelta(hours=hours)
        readings = SensorReading.objects.filter(
            node__node_id=node_id,
            timestamp__gte=since
        ).order_by('timestamp').values(
            'timestamp', 'temperature', 'humidity', 
            'pressure', 'light_lux', 'soil_moisture_percent'
        )
        
        # Formatta per Chart.js
        data = {
            'labels': [],
            'temperature': [],
            'humidity': [],
            'pressure': [],
            'light': [],
            'soil': []
        }
        
        for r in readings:
            data['labels'].append(r['timestamp'].isoformat())
            data['temperature'].append(float(r['temperature']) if r['temperature'] else None)
            data['humidity'].append(float(r['humidity']) if r['humidity'] else None)
            data['pressure'].append(float(r['pressure']) if r['pressure'] else None)
            data['light'].append(r['light_lux'])
            data['soil'].append(r['soil_moisture_percent'])
        
        return Response(data)


class SensorAlertViewSet(viewsets.ModelViewSet):
    """
    API endpoint per alert sensori
    """
    queryset = SensorAlert.objects.select_related('node')
    serializer_class = SensorAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['node__node_id', 'alert_type', 'severity', 'is_resolved']
    ordering = ['-timestamp']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Prendi in carico alert"""
        alert = self.get_object()
        alert.acknowledge(by_user=request.user.username)
        return Response({'status': 'Alert acknowledged'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Risolvi alert"""
        alert = self.get_object()
        alert.resolve()
        return Response({'status': 'Alert resolved'})


# ===========================================
# Security ViewSets
# ===========================================

class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint per eventi sicurezza (sola lettura)
    """
    queryset = SecurityEvent.objects.select_related('node')
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['node__node_id', 'classification', 'priority']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro temporale
        days = self.request.query_params.get('days', 7)
        since = timezone.now() - timedelta(days=int(days))
        queryset = queryset.filter(timestamp__gte=since)
        
        return queryset[:200]


class AlarmViewSet(viewsets.ModelViewSet):
    """
    API endpoint per allarmi
    """
    queryset = Alarm.objects.select_related('node', 'event')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['node__node_id', 'status', 'priority', 'classification']
    ordering = ['-triggered_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AlarmListSerializer
        return AlarmDetailSerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Lista allarmi attivi"""
        alarms = self.queryset.filter(
            status__in=['active', 'acknowledged']
        ).order_by('-priority', '-triggered_at')
        
        serializer = AlarmListSerializer(alarms, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Esegui azione su allarme"""
        alarm = self.get_object()
        serializer = AlarmActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        if action_type == 'acknowledge':
            alarm.acknowledge(by_user=request.user.username)
        elif action_type == 'resolve':
            alarm.resolve(notes=notes)
        elif action_type == 'false_positive':
            alarm.resolve(notes=notes, as_false_positive=True)
        
        return Response({'status': f'Alarm {action_type}d'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiche allarmi"""
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        
        alarms = Alarm.objects.filter(triggered_at__gte=since)
        
        stats = {
            'total': alarms.count(),
            'by_status': dict(alarms.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'by_priority': dict(alarms.values('priority').annotate(count=Count('id')).values_list('priority', 'count')),
            'by_classification': dict(alarms.values('classification').annotate(count=Count('id')).values_list('classification', 'count')),
            'avg_response_time': None,
            'false_positive_rate': 0
        }
        
        # Tempo medio risposta
        acknowledged = alarms.filter(acknowledged_at__isnull=False)
        if acknowledged.exists():
            from django.db.models import F, ExpressionWrapper, DurationField
            avg_response = acknowledged.annotate(
                response_time=ExpressionWrapper(
                    F('acknowledged_at') - F('triggered_at'),
                    output_field=DurationField()
                )
            ).aggregate(avg=Avg('response_time'))
            if avg_response['avg']:
                stats['avg_response_time'] = avg_response['avg'].total_seconds()
        
        # Tasso falsi positivi
        resolved = alarms.filter(status__in=['resolved', 'false_pos'])
        if resolved.count() > 0:
            false_pos = alarms.filter(status='false_pos').count()
            stats['false_positive_rate'] = round(false_pos / resolved.count() * 100, 1)
        
        return Response(stats)


class SystemArmViewSet(viewsets.ViewSet):
    """
    API endpoint per gestione armamento sistema
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Stato corrente e storico armamento"""
        current_mode = SystemArmState.get_current_mode()
        
        # Ultimi 10 cambi stato
        history = SystemArmState.objects.order_by('-timestamp')[:10]
        
        return Response({
            'current_mode': current_mode,
            'is_armed': current_mode != 'disarmed',
            'history': SystemArmStateSerializer(history, many=True).data
        })
    
    def create(self, request):
        """Cambia stato armamento"""
        serializer = ArmSystemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mode = serializer.validated_data['mode']
        node_ids = serializer.validated_data.get('nodes', [])
        notes = serializer.validated_data.get('notes', '')
        
        # Stato precedente
        previous_mode = SystemArmState.get_current_mode()
        
        # Crea nuovo stato
        arm_state = SystemArmState.objects.create(
            mode=mode,
            previous_mode=previous_mode,
            changed_by=request.user.username,
            change_source='api',
            notes=notes
        )
        
        # Aggiorna nodi
        if node_ids:
            nodes = Node.objects.filter(node_id__in=node_ids, node_type='SEC')
        else:
            nodes = Node.objects.filter(node_type='SEC')
        
        is_armed = mode != 'disarmed'
        nodes.update(is_armed=is_armed)
        arm_state.nodes_affected.set(nodes)
        
        # Invia comando ai nodi via MQTT
        from apps.core.mqtt_publisher import publish_arm_command
        publish_arm_command(mode, [n.node_id for n in nodes])
        
        return Response({
            'status': 'success',
            'mode': mode,
            'nodes_affected': nodes.count()
        })


class SecurityZoneViewSet(viewsets.ModelViewSet):
    """
    API endpoint per zone sicurezza
    """
    queryset = SecurityZone.objects.prefetch_related('nodes')
    serializer_class = SecurityZoneSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def arm(self, request, pk=None):
        """Arma zona"""
        zone = self.get_object()
        zone.is_armed = True
        zone.save()
        zone.nodes.update(is_armed=True)
        return Response({'status': 'Zone armed'})
    
    @action(detail=True, methods=['post'])
    def disarm(self, request, pk=None):
        """Disarma zona"""
        zone = self.get_object()
        zone.is_armed = False
        zone.save()
        zone.nodes.update(is_armed=False)
        return Response({'status': 'Zone disarmed'})


# ===========================================
# Dashboard Views
# ===========================================

class DashboardSummaryView(views.APIView):
    """
    Riepilogo dashboard principale
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Conteggi nodi
        nodes = Node.objects.filter(is_active=True)
        total_nodes = nodes.count()
        nodes_online = nodes.filter(status=NodeStatus.ONLINE).count()
        nodes_offline = nodes.filter(status=NodeStatus.OFFLINE).count()
        nodes_warning = nodes.filter(status=NodeStatus.WARNING).count()
        
        # Allarmi
        active_alarms = Alarm.objects.filter(status__in=['active', 'acknowledged']).count()
        alarms_today = Alarm.objects.filter(triggered_at__gte=today_start).count()
        
        # Stato armamento
        arm_mode = SystemArmState.get_current_mode()
        
        # Ultime letture sensori
        latest_reading = SensorReading.objects.order_by('-timestamp').first()
        
        # Batterie basse
        battery_warnings = nodes.filter(
            battery_percentage__isnull=False,
            battery_percentage__lte=20
        ).count()
        
        data = {
            'total_nodes': total_nodes,
            'nodes_online': nodes_online,
            'nodes_offline': nodes_offline,
            'nodes_warning': nodes_warning,
            'active_alarms': active_alarms,
            'alarms_today': alarms_today,
            'system_armed': arm_mode != 'disarmed',
            'arm_mode': arm_mode,
            'latest_temperature': latest_reading.temperature if latest_reading else None,
            'latest_humidity': latest_reading.humidity if latest_reading else None,
            'latest_soil_moisture': latest_reading.soil_moisture_percent if latest_reading else None,
            'battery_warnings': battery_warnings,
        }
        
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)


class DashboardChartsView(views.APIView):
    """
    Dati per grafici dashboard
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        # Aggregazione oraria sensori
        from django.db.models.functions import TruncHour
        
        hourly_data = SensorReading.objects.filter(
            timestamp__gte=since
        ).annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            avg_temp=Avg('temperature'),
            avg_humidity=Avg('humidity'),
            avg_soil=Avg('soil_moisture_percent'),
            reading_count=Count('id')
        ).order_by('hour')
        
        # Eventi sicurezza per ora
        security_hourly = SecurityEvent.objects.filter(
            timestamp__gte=since
        ).annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return Response({
            'sensor_data': list(hourly_data),
            'security_events': list(security_hourly)
        })
