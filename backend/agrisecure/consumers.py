"""
WebSocket Consumers for AgriSecure Real-Time Updates
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Dashboard real-time updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Join dashboard group
        self.group_name = 'dashboard_updates'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial data
        initial_data = await self.get_dashboard_data()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': initial_data
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client"""
        try:
            data = json.loads(text_data)
            
            # Client can request refresh
            if data.get('action') == 'refresh':
                dashboard_data = await self.get_dashboard_data()
                await self.send(text_data=json.dumps({
                    'type': 'dashboard_update',
                    'data': dashboard_data
                }))
        except json.JSONDecodeError:
            pass
    
    async def dashboard_update(self, event):
        """Receive update from group and send to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Get dashboard data from database"""
        from apps.nodes.models import Node
        from apps.security.models import Alarm, SystemArmState
        from apps.sensors.models import SensorReading
        
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


class AlarmsConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for Alarms page real-time updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Join alarms group
        self.group_name = 'alarms_updates'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial stats
        stats = await self.get_alarms_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': stats
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client"""
        try:
            data = json.loads(text_data)
            
            # Client can request refresh
            if data.get('action') == 'refresh':
                stats = await self.get_alarms_stats()
                await self.send(text_data=json.dumps({
                    'type': 'stats_update',
                    'stats': stats
                }))
            elif data.get('action') == 'refresh_table':
                # Client requests full table refresh
                await self.send(text_data=json.dumps({
                    'type': 'table_refresh',
                    'message': 'refresh_required'
                }))
        except json.JSONDecodeError:
            pass
    
    async def alarm_new(self, event):
        """New alarm notification"""
        await self.send(text_data=json.dumps({
            'type': 'alarm_new',
            'alarm': event['alarm']
        }))
    
    async def alarm_update(self, event):
        """Alarm status update notification"""
        await self.send(text_data=json.dumps({
            'type': 'alarm_update',
            'alarm_id': event['alarm_id'],
            'status': event['status']
        }))
    
    async def stats_update(self, event):
        """Stats update from group"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))
    
    @database_sync_to_async
    def get_alarms_stats(self):
        """Get alarms statistics"""
        from apps.security.models import Alarm
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
