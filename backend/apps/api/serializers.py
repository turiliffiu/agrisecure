"""
AgriSecure IoT System - API Serializers

Serializers per Django REST Framework
"""

from rest_framework import serializers
from apps.nodes.models import Node, NodeHeartbeat, NodeEvent
from apps.sensors.models import SensorReading, SensorAggregate, SensorAlert
from apps.security.models import SecurityEvent, Alarm, SystemArmState, SecurityZone


# ===========================================
# Node Serializers
# ===========================================

class NodeListSerializer(serializers.ModelSerializer):
    """Serializer per lista nodi (leggero)"""
    battery_status = serializers.ReadOnlyField()
    is_online = serializers.ReadOnlyField()
    
    class Meta:
        model = Node
        fields = [
            'id', 'node_id', 'name', 'node_type', 'status',
            'last_seen', 'battery_percentage', 'battery_status',
            'is_online', 'rssi', 'is_armed'
        ]


class NodeDetailSerializer(serializers.ModelSerializer):
    """Serializer per dettaglio nodo"""
    battery_status = serializers.ReadOnlyField()
    is_online = serializers.ReadOnlyField()
    gateway_id = serializers.CharField(source='gateway.node_id', read_only=True)
    
    class Meta:
        model = Node
        fields = '__all__'
        read_only_fields = [
            'last_seen', 'uptime_seconds', 'boot_count',
            'battery_voltage', 'battery_percentage', 'is_charging',
            'solar_voltage', 'rssi', 'mesh_neighbors',
            'created_at', 'updated_at'
        ]


class NodeHeartbeatSerializer(serializers.ModelSerializer):
    """Serializer per heartbeat"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    
    class Meta:
        model = NodeHeartbeat
        fields = [
            'id', 'node_id', 'timestamp', 'uptime_seconds',
            'free_heap_kb', 'rssi', 'battery_percentage', 'mesh_neighbors'
        ]


class NodeEventSerializer(serializers.ModelSerializer):
    """Serializer per eventi nodo"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    
    class Meta:
        model = NodeEvent
        fields = [
            'id', 'node_id', 'timestamp', 'event_type', 'message', 'data'
        ]


# ===========================================
# Sensor Serializers
# ===========================================

class SensorReadingSerializer(serializers.ModelSerializer):
    """Serializer per letture sensori"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = SensorReading
        fields = [
            'id', 'node_id', 'node_name', 'timestamp',
            'temperature', 'humidity', 'pressure',
            'light_lux', 'soil_moisture_percent', 'soil_moisture_raw'
        ]


class SensorReadingCreateSerializer(serializers.ModelSerializer):
    """Serializer per creazione letture (da API esterna)"""
    node_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = SensorReading
        fields = [
            'node_id', 'timestamp', 'temperature', 'humidity', 'pressure',
            'light_lux', 'soil_moisture_percent', 'soil_moisture_raw'
        ]
    
    def create(self, validated_data):
        node_id = validated_data.pop('node_id')
        node = Node.objects.get(node_id=node_id)
        return SensorReading.objects.create(node=node, **validated_data)


class SensorAggregateSerializer(serializers.ModelSerializer):
    """Serializer per dati aggregati"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    
    class Meta:
        model = SensorAggregate
        fields = [
            'id', 'node_id', 'aggregate_type', 'period_start', 'period_end',
            'reading_count',
            'temperature_min', 'temperature_max', 'temperature_avg',
            'humidity_min', 'humidity_max', 'humidity_avg',
            'soil_min', 'soil_max', 'soil_avg',
            'light_min', 'light_max', 'light_avg'
        ]


class SensorAlertSerializer(serializers.ModelSerializer):
    """Serializer per alert sensori"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    
    class Meta:
        model = SensorAlert
        fields = [
            'id', 'node_id', 'node_name', 'timestamp',
            'alert_type', 'severity', 'value', 'threshold', 'message',
            'is_acknowledged', 'acknowledged_at', 'acknowledged_by',
            'is_resolved', 'resolved_at'
        ]


# ===========================================
# Security Serializers
# ===========================================

class SecurityEventSerializer(serializers.ModelSerializer):
    """Serializer per eventi sicurezza"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    has_alarm = serializers.SerializerMethodField()
    
    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'node_id', 'node_name', 'timestamp',
            'classification', 'priority',
            'pir_main', 'pir_backup', 'motion_confirmed',
            'tamper_detected', 'confidence', 'duration_ms',
            'has_alarm'
        ]
    
    def get_has_alarm(self, obj):
        return hasattr(obj, 'alarm')


class AlarmListSerializer(serializers.ModelSerializer):
    """Serializer per lista allarmi"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    response_time = serializers.ReadOnlyField(source='response_time_seconds')
    
    class Meta:
        model = Alarm
        fields = [
            'id', 'node_id', 'node_name', 'triggered_at',
            'status', 'priority', 'classification',
            'siren_activated', 'lights_activated',
            'acknowledged_at', 'acknowledged_by',
            'response_time'
        ]


class AlarmDetailSerializer(serializers.ModelSerializer):
    """Serializer per dettaglio allarme"""
    node_id = serializers.CharField(source='node.node_id', read_only=True)
    node_name = serializers.CharField(source='node.name', read_only=True)
    event = SecurityEventSerializer(read_only=True)
    response_time = serializers.ReadOnlyField(source='response_time_seconds')
    
    class Meta:
        model = Alarm
        fields = '__all__'


class AlarmActionSerializer(serializers.Serializer):
    """Serializer per azioni su allarmi"""
    action = serializers.ChoiceField(choices=['acknowledge', 'resolve', 'false_positive'])
    notes = serializers.CharField(required=False, allow_blank=True)


class SystemArmStateSerializer(serializers.ModelSerializer):
    """Serializer per stato armamento"""
    
    class Meta:
        model = SystemArmState
        fields = [
            'id', 'timestamp', 'mode', 'previous_mode',
            'changed_by', 'change_source', 'notes'
        ]


class ArmSystemSerializer(serializers.Serializer):
    """Serializer per armare/disarmare sistema"""
    mode = serializers.ChoiceField(choices=SystemArmState.ArmMode.choices)
    nodes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista node_id da armare/disarmare (vuoto = tutti)"
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class SecurityZoneSerializer(serializers.ModelSerializer):
    """Serializer per zone sicurezza"""
    nodes = NodeListSerializer(many=True, read_only=True)
    node_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = SecurityZone
        fields = [
            'id', 'name', 'description', 'nodes', 'node_ids',
            'is_active', 'is_armed',
            'alarm_delay_seconds', 'entry_delay_seconds',
            'notify_on_alarm', 'notify_channels'
        ]


# ===========================================
# Dashboard Serializers
# ===========================================

class DashboardSummarySerializer(serializers.Serializer):
    """Serializer per riepilogo dashboard"""
    total_nodes = serializers.IntegerField()
    nodes_online = serializers.IntegerField()
    nodes_offline = serializers.IntegerField()
    nodes_warning = serializers.IntegerField()
    
    active_alarms = serializers.IntegerField()
    alarms_today = serializers.IntegerField()
    
    system_armed = serializers.BooleanField()
    arm_mode = serializers.CharField()
    
    latest_temperature = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    latest_humidity = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    latest_soil_moisture = serializers.IntegerField(allow_null=True)
    
    battery_warnings = serializers.IntegerField()


class ChartDataSerializer(serializers.Serializer):
    """Serializer per dati grafici"""
    timestamps = serializers.ListField(child=serializers.DateTimeField())
    datasets = serializers.DictField()
