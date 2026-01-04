"""AgriSecure - Admin per Nodi IoT"""
from django.contrib import admin
from .models import Node, NodeHeartbeat, NodeEvent


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = [
        'node_id', 'name', 'node_type', 'status', 
        'last_seen', 'battery_percentage', 'rssi', 'is_armed'
    ]
    list_filter = ['node_type', 'status', 'is_armed', 'is_active']
    search_fields = ['node_id', 'name', 'description']
    readonly_fields = [
        'last_seen', 'uptime_seconds', 'boot_count',
        'battery_voltage', 'battery_percentage', 'is_charging',
        'solar_voltage', 'rssi', 'mesh_neighbors',
        'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Identificazione', {
            'fields': ('node_id', 'mac_address', 'name', 'description')
        }),
        ('Tipo e Stato', {
            'fields': ('node_type', 'status', 'is_armed', 'is_active')
        }),
        ('Posizione', {
            'fields': ('latitude', 'longitude', 'location_description')
        }),
        ('Runtime', {
            'fields': ('last_seen', 'uptime_seconds', 'boot_count', 'firmware_version'),
            'classes': ('collapse',)
        }),
        ('Batteria', {
            'fields': ('battery_voltage', 'battery_percentage', 'is_charging', 'solar_voltage'),
            'classes': ('collapse',)
        }),
        ('Connettività', {
            'fields': ('rssi', 'mesh_neighbors', 'gateway'),
            'classes': ('collapse',)
        }),
        ('Configurazione', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
    )


@admin.register(NodeHeartbeat)
class NodeHeartbeatAdmin(admin.ModelAdmin):
    list_display = ['node', 'timestamp', 'uptime_seconds', 'rssi', 'battery_percentage']
    list_filter = ['node__node_type', 'timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['node', 'timestamp', 'uptime_seconds', 'free_heap_kb', 'rssi', 'battery_percentage', 'mesh_neighbors']


@admin.register(NodeEvent)
class NodeEventAdmin(admin.ModelAdmin):
    list_display = ['node', 'timestamp', 'event_type', 'message']
    list_filter = ['event_type', 'timestamp', 'node__node_type']
    search_fields = ['node__node_id', 'message']
    date_hierarchy = 'timestamp'
