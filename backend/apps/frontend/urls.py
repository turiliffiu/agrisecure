"""
AgriSecure Frontend URLs
URL routing per la dashboard
"""
from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Nodes
    path('nodes/', views.nodes_list, name='nodes'),
    path('nodes/<int:node_id>/', views.node_detail, name='node_detail'),
    path('nodes/<int:node_id>/command/', views.node_command, name='node_command'),
    
    # Sensors
    path('sensors/', views.sensors, name='sensors'),
    path('sensors/alerts/<int:alert_id>/ack/', views.sensor_alert_acknowledge, name='sensor_alert_ack'),
    path('sensors/alerts/<int:alert_id>/resolve/', views.sensor_alert_resolve, name='sensor_alert_resolve'),
    
    # Security
    path('alarms/', views.alarms, name='alarms'),
    path('alarms/<int:alarm_id>/<str:action>/', views.alarm_action, name='alarm_action'),
    path('arm/', views.arm_system, name='arm'),
    path('arm/action/', views.arm_action, name='arm_action'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/restart/', views.restart_services, name='restart_services'),
    path('settings/cleanup/', views.cleanup_data, name='cleanup_data'),
]
