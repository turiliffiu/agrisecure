"""
MQTT to WebSocket Bridge
Listens to MQTT messages and sends real-time updates via WebSocket
"""
import os
import sys
import django
import asyncio
import paho.mqtt.client as mqtt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Setup Django
sys.path.insert(0, '/opt/agrisecure/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrisecure.settings')
django.setup()

from apps.security.models import Alarm
from apps.nodes.models import Node
from django.utils import timezone


class MQTTWebSocketBridge:
    """Bridge between MQTT and WebSocket for real-time updates"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            print("✅ Connected to MQTT broker")
            # Subscribe to relevant topics
            client.subscribe("agrisecure/+/security/#")
            client.subscribe("agrisecure/+/sensors/#")
            client.subscribe("agrisecure/+/status")
        else:
            print(f"❌ MQTT connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        topic = msg.topic
        
        try:
            # Handle security events (alarms)
            if "/security/" in topic:
                self.handle_security_event(topic, msg.payload)

            # Handle sensor data
            elif "/sensors/" in topic:
                self.handle_sensor_data(topic, msg.payload)

            # Handle heartbeats
            elif "/status" in topic:
                self.handle_heartbeat(topic, msg.payload)


        except Exception as e:
            print(f"❌ Error handling message: {e}")
    
    def handle_security_event(self, topic, payload):
        """Handle security events and send WebSocket update"""
        print(f"🚨 Security event on {topic}")
        
        # Send update to alarms WebSocket group
        async_to_sync(self.channel_layer.group_send)(
            'alarms_updates',
            {
                'type': 'stats_update',
                'stats': self.get_alarm_stats()
            }
        )
        
        # Also update dashboard
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': self.get_dashboard_data()
            }
        )
    
    def handle_sensor_data(self, topic, payload):
        """Handle sensor data and send WebSocket update"""
        print(f"📊 Sensor data on {topic}")
        
        # Send update to dashboard
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': self.get_dashboard_data()
            }
        )
    
    def handle_heartbeat(self, topic, payload):
        """Handle node heartbeat and send WebSocket update"""
        # Update dashboard node stats
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': self.get_dashboard_data()
            }
        )
    
    def get_alarm_stats(self):
        """Get alarm statistics"""
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        stats = {
            'active': Alarm.objects.filter(status='active').count(),
            'acknowledged': Alarm.objects.filter(status='acknowledged').count(),
            'resolved': Alarm.objects.filter(
                status='resolved',
                resolved_at__gte=thirty_days_ago
            ).count(),
        }
        
        # Calculate false positive rate
        total = Alarm.objects.filter(triggered_at__gte=thirty_days_ago).count()
        if total > 0:
            false_positives = Alarm.objects.filter(
                triggered_at__gte=thirty_days_ago,
                status='false_pos'
            ).count()
            stats['false_positive_rate'] = round((false_positives / total) * 100, 1)
        else:
            stats['false_positive_rate'] = 0
        
        return stats
    
    def get_dashboard_data(self):
        """Get dashboard data"""
        from apps.sensors.models import SensorReading
        from apps.security.models import SystemArmState
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Node stats
        nodes = Node.objects.all()
        total_nodes = nodes.count()
        nodes_online = nodes.filter(status='online').count()
        nodes_offline = nodes.filter(status='offline').count()
        
        # Alarm stats
        active_alarms = Alarm.objects.filter(status__in=['active', 'acknowledged']).count()
        alarms_today = Alarm.objects.filter(triggered_at__gte=today_start).count()
        
        # Recent alarms
        recent_alarms = []
        for alarm in Alarm.objects.filter(
            status__in=['active', 'acknowledged']
        ).select_related('node').order_by('-triggered_at')[:5]:
            recent_alarms.append({
                'id': alarm.id,
                'priority': alarm.priority,
                'classification': alarm.classification,
                'node_name': alarm.node.name if alarm.node.name else alarm.node.node_id,
                'triggered_at': alarm.triggered_at.strftime('%d/%m/%Y %H:%M'),
                'status': alarm.status,
            })
        
        # Arm state
        arm_state = SystemArmState.objects.order_by('-timestamp').first()
        system_armed = arm_state and arm_state.mode != 'disarmed' if arm_state else False
        arm_mode = arm_state.mode if arm_state else None
        
        # Latest sensor readings
        latest_reading = SensorReading.objects.order_by('-timestamp').first()
        latest_temperature = float(latest_reading.temperature) if latest_reading and latest_reading.temperature else None
        latest_humidity = float(latest_reading.humidity) if latest_reading and latest_reading.humidity else None
        latest_soil = float(latest_reading.soil_moisture_percent) if latest_reading and latest_reading.soil_moisture_percent else None
        
        # Battery warnings
        battery_warnings = nodes.filter(
            battery_percentage__lt=20,
            battery_percentage__isnull=False
        ).count()
        
        return {
            'nodes': {
                'total': total_nodes,
                'online': nodes_online,
                'offline': nodes_offline,
            },
            'alarms': {
                'active': active_alarms,
                'today': alarms_today,
                'recent': recent_alarms,
            },
            'system': {
                'armed': system_armed,
                'arm_mode': arm_mode,
            },
            'sensors': {
                'temperature': latest_temperature,
                'humidity': latest_humidity,
                'soil_moisture': latest_soil,
            },
            'battery_warnings': battery_warnings,
            'timestamp': now.isoformat(),
        }
    
    def start(self):
        """Start the MQTT bridge"""
        print("🚀 Starting MQTT to WebSocket bridge...")
        print("📡 Connecting to MQTT broker at localhost:1883")
        
        try:
            self.mqtt_client.connect("localhost", 1883, 60)
            print("✅ MQTT bridge running")
            print("🔌 Listening for MQTT messages...")
            self.mqtt_client.loop_forever()
        except Exception as e:
            print(f"❌ Error starting bridge: {e}")
            sys.exit(1)


if __name__ == "__main__":
    bridge = MQTTWebSocketBridge()
    bridge.start()
