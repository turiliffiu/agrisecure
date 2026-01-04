"""
AgriSecure IoT System - Models per Nodi IoT

Definisce i modelli per la gestione dei nodi della rete mesh:
- Gateway (connettività 4G)
- Nodi Ambientali (sensori clima/suolo)
- Nodi Sicurezza (PIR, allarmi)
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class NodeType(models.TextChoices):
    """Tipi di nodo supportati"""
    GATEWAY = 'GW', 'Gateway'
    AMBIENT = 'AMB', 'Ambientale'
    SECURITY = 'SEC', 'Sicurezza'


class NodeStatus(models.TextChoices):
    """Stati possibili di un nodo"""
    ONLINE = 'online', 'Online'
    OFFLINE = 'offline', 'Offline'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Errore'
    MAINTENANCE = 'maintenance', 'Manutenzione'


class Node(models.Model):
    """
    Modello principale per un nodo IoT
    """
    # Identificazione
    node_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="ID univoco del nodo (es. GW-001, AMB-001)"
    )
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        help_text="MAC address del nodo"
    )
    name = models.CharField(
        max_length=100,
        help_text="Nome descrittivo del nodo"
    )
    description = models.TextField(
        blank=True,
        help_text="Descrizione e note sul nodo"
    )
    
    # Tipo e stato
    node_type = models.CharField(
        max_length=3,
        choices=NodeType.choices,
        default=NodeType.AMBIENT
    )
    status = models.CharField(
        max_length=15,
        choices=NodeStatus.choices,
        default=NodeStatus.OFFLINE
    )
    is_armed = models.BooleanField(
        default=True,
        help_text="Sistema di sicurezza armato (solo per nodi SEC)"
    )
    
    # Posizione
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descrizione posizione (es. 'Angolo nord-est')"
    )
    
    # Firmware
    firmware_version = models.CharField(
        max_length=20,
        blank=True,
        default='1.0.0'
    )
    
    # Statistiche runtime
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultimo heartbeat ricevuto"
    )
    uptime_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Secondi dall'ultimo riavvio"
    )
    boot_count = models.PositiveIntegerField(
        default=0,
        help_text="Numero di riavvii"
    )
    
    # Batteria
    battery_voltage = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tensione batteria in V"
    )
    battery_percentage = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentuale carica batteria"
    )
    is_charging = models.BooleanField(
        default=False,
        help_text="Batteria in carica (pannello solare)"
    )
    solar_voltage = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tensione pannello solare in V"
    )
    
    # Connettività mesh
    rssi = models.SmallIntegerField(
        null=True,
        blank=True,
        help_text="Potenza segnale WiFi/mesh (dBm)"
    )
    mesh_neighbors = models.PositiveSmallIntegerField(
        default=0,
        help_text="Numero di nodi vicini nella mesh"
    )
    gateway = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connected_nodes',
        limit_choices_to={'node_type': NodeType.GATEWAY},
        help_text="Gateway di riferimento"
    )
    
    # Configurazione
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configurazione JSON del nodo"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'nodes'
        ordering = ['node_type', 'node_id']
        verbose_name = 'Nodo'
        verbose_name_plural = 'Nodi'
        indexes = [
            models.Index(fields=['node_type', 'status']),
            models.Index(fields=['last_seen']),
        ]
    
    def __str__(self):
        return f"{self.node_id} - {self.name}"
    
    @property
    def is_online(self):
        """Verifica se il nodo è online (heartbeat recente)"""
        if not self.last_seen:
            return False
        from django.conf import settings
        timeout = settings.AGRISECURE.get('NODE_TIMEOUT_CRITICAL', 7200)
        return (timezone.now() - self.last_seen).total_seconds() < timeout
    
    @property
    def battery_status(self):
        """Stato batteria: critical, low, normal, charging"""
        if self.is_charging:
            return 'charging'
        if self.battery_percentage is None:
            return 'unknown'
        if self.battery_percentage <= 10:
            return 'critical'
        if self.battery_percentage <= 20:
            return 'low'
        return 'normal'
    
    def update_status(self):
        """Aggiorna lo stato del nodo basandosi sui dati"""
        from django.conf import settings
        
        if not self.last_seen:
            self.status = NodeStatus.OFFLINE
        else:
            seconds_since_seen = (timezone.now() - self.last_seen).total_seconds()
            timeout_warning = settings.AGRISECURE.get('NODE_TIMEOUT_WARNING', 3600)
            timeout_critical = settings.AGRISECURE.get('NODE_TIMEOUT_CRITICAL', 7200)
            
            if seconds_since_seen > timeout_critical:
                self.status = NodeStatus.OFFLINE
            elif seconds_since_seen > timeout_warning:
                self.status = NodeStatus.WARNING
            elif self.battery_status == 'critical':
                self.status = NodeStatus.WARNING
            else:
                self.status = NodeStatus.ONLINE
        
        self.save(update_fields=['status', 'updated_at'])


class NodeHeartbeat(models.Model):
    """
    Storico heartbeat dei nodi (TimescaleDB hypertable)
    """
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='heartbeats'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # Dati heartbeat
    uptime_seconds = models.PositiveIntegerField(default=0)
    free_heap_kb = models.PositiveIntegerField(default=0)
    rssi = models.SmallIntegerField(null=True)
    battery_percentage = models.PositiveSmallIntegerField(null=True)
    mesh_neighbors = models.PositiveSmallIntegerField(default=0)
    status_code = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        db_table = 'node_heartbeats'
        ordering = ['-timestamp']
        verbose_name = 'Heartbeat'
        verbose_name_plural = 'Heartbeats'
        indexes = [
            models.Index(fields=['node', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} @ {self.timestamp}"


class NodeEvent(models.Model):
    """
    Eventi di sistema dei nodi (boot, errori, OTA, etc.)
    """
    class EventType(models.TextChoices):
        BOOT = 'boot', 'Avvio'
        SHUTDOWN = 'shutdown', 'Spegnimento'
        ERROR = 'error', 'Errore'
        WARNING = 'warning', 'Warning'
        OTA_START = 'ota_start', 'OTA Avviato'
        OTA_SUCCESS = 'ota_success', 'OTA Completato'
        OTA_FAIL = 'ota_fail', 'OTA Fallito'
        CONFIG_CHANGE = 'config', 'Cambio Configurazione'
        BATTERY_LOW = 'batt_low', 'Batteria Bassa'
        BATTERY_CRITICAL = 'batt_crit', 'Batteria Critica'
        OFFLINE = 'offline', 'Offline'
        ONLINE = 'online', 'Online'
    
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='events'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices
    )
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'node_events'
        ordering = ['-timestamp']
        verbose_name = 'Evento Nodo'
        verbose_name_plural = 'Eventi Nodi'
        indexes = [
            models.Index(fields=['node', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} - {self.event_type} @ {self.timestamp}"
