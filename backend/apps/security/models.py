"""
AgriSecure IoT System - Models per Sicurezza

Definisce i modelli per la gestione della sicurezza perimetrale:
- Eventi di movimento
- Allarmi intrusione
- Classificazione persona/animale
- Stato armamento sistema
"""

from django.db import models
from django.utils import timezone
from apps.nodes.models import Node


class IntrusionClass(models.TextChoices):
    """Classificazione dell'intrusione rilevata"""
    NONE = 'none', 'Nessuno'
    PERSON = 'person', 'Persona'
    ANIMAL_LARGE = 'animal_lg', 'Animale Grande'
    ANIMAL_SMALL = 'animal_sm', 'Animale Piccolo'
    UNKNOWN = 'unknown', 'Sconosciuto'
    TAMPER = 'tamper', 'Manomissione'


class AlarmPriority(models.TextChoices):
    """Priorità dell'allarme"""
    CRITICAL = 'critical', 'Critico'  # Persona o tamper
    HIGH = 'high', 'Alto'             # Animale grande
    MEDIUM = 'medium', 'Medio'        # Movimento generico
    LOW = 'low', 'Basso'              # Animale piccolo


class SecurityEvent(models.Model):
    """
    Evento di sicurezza rilevato dai nodi SEC
    
    Ogni attivazione dei sensori PIR genera un evento.
    """
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='security_events'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # Classificazione
    classification = models.CharField(
        max_length=15,
        choices=IntrusionClass.choices,
        default=IntrusionClass.UNKNOWN
    )
    priority = models.CharField(
        max_length=10,
        choices=AlarmPriority.choices,
        default=AlarmPriority.MEDIUM
    )
    
    # Dati sensori
    pir_main = models.BooleanField(
        default=False,
        help_text="PIR principale attivato"
    )
    pir_backup = models.BooleanField(
        default=False,
        help_text="PIR backup attivato"
    )
    motion_confirmed = models.BooleanField(
        default=False,
        help_text="Movimento confermato da entrambi i PIR"
    )
    
    # Accelerometro (tamper detection)
    tamper_detected = models.BooleanField(
        default=False,
        help_text="Manomissione rilevata"
    )
    accel_x = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True
    )
    accel_y = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True
    )
    accel_z = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True
    )
    
    # Dati supplementari
    confidence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Confidenza classificazione (0-100)"
    )
    duration_ms = models.PositiveIntegerField(
        default=0,
        help_text="Durata movimento in millisecondi"
    )
    
    # Raw data per debug/ML
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dati grezzi per analisi"
    )
    
    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']
        verbose_name = 'Evento Sicurezza'
        verbose_name_plural = 'Eventi Sicurezza'
        indexes = [
            models.Index(fields=['node', '-timestamp']),
            models.Index(fields=['classification', '-timestamp']),
            models.Index(fields=['priority', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} - {self.classification} @ {self.timestamp}"


class Alarm(models.Model):
    """
    Allarme generato da un evento di sicurezza
    
    Un allarme viene creato quando l'evento supera determinate soglie
    (es. classificazione PERSON o TAMPER).
    """
    class AlarmStatus(models.TextChoices):
        ACTIVE = 'active', 'Attivo'
        ACKNOWLEDGED = 'acknowledged', 'Preso in Carico'
        RESOLVED = 'resolved', 'Risolto'
        FALSE_POSITIVE = 'false_pos', 'Falso Positivo'
        IGNORED = 'ignored', 'Ignorato'
    
    # Evento che ha generato l'allarme
    event = models.OneToOneField(
        SecurityEvent,
        on_delete=models.CASCADE,
        related_name='alarm'
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='alarms'
    )
    
    # Timing
    triggered_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Stato
    status = models.CharField(
        max_length=15,
        choices=AlarmStatus.choices,
        default=AlarmStatus.ACTIVE
    )
    priority = models.CharField(
        max_length=10,
        choices=AlarmPriority.choices
    )
    classification = models.CharField(
        max_length=15,
        choices=IntrusionClass.choices
    )
    
    # Attuazione locale
    siren_activated = models.BooleanField(
        default=False,
        help_text="Sirena attivata localmente"
    )
    lights_activated = models.BooleanField(
        default=False,
        help_text="Luci allarme attivate"
    )
    actuation_duration = models.PositiveIntegerField(
        default=30,
        help_text="Durata attuazione in secondi"
    )
    
    # Gestione
    acknowledged_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Utente che ha preso in carico"
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Note sulla risoluzione"
    )
    
    # Notifiche
    notifications_sent = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista canali notifica usati"
    )
    
    class Meta:
        db_table = 'alarms'
        ordering = ['-triggered_at']
        verbose_name = 'Allarme'
        verbose_name_plural = 'Allarmi'
        indexes = [
            models.Index(fields=['status', '-triggered_at']),
            models.Index(fields=['node', '-triggered_at']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"Allarme {self.id} - {self.classification} @ {self.triggered_at}"
    
    @property
    def response_time_seconds(self):
        """Tempo di risposta in secondi (se acknowledged)"""
        if self.acknowledged_at:
            return (self.acknowledged_at - self.triggered_at).total_seconds()
        return None
    
    def acknowledge(self, by_user='system'):
        """Prende in carico l'allarme"""
        self.status = self.AlarmStatus.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = by_user
        self.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by'])
    
    def resolve(self, notes='', as_false_positive=False):
        """Risolve l'allarme"""
        if as_false_positive:
            self.status = self.AlarmStatus.FALSE_POSITIVE
        else:
            self.status = self.AlarmStatus.RESOLVED
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save(update_fields=['status', 'resolved_at', 'resolution_notes'])


class SystemArmState(models.Model):
    """
    Storico stato armamento del sistema
    """
    class ArmMode(models.TextChoices):
        ARMED = 'armed', 'Armato'
        DISARMED = 'disarmed', 'Disarmato'
        ARMED_STAY = 'armed_stay', 'Armato Casa'  # Solo perimetro
        ARMED_AWAY = 'armed_away', 'Armato Via'   # Tutto
    
    timestamp = models.DateTimeField(default=timezone.now)
    mode = models.CharField(
        max_length=15,
        choices=ArmMode.choices
    )
    previous_mode = models.CharField(
        max_length=15,
        choices=ArmMode.choices,
        blank=True
    )
    
    # Chi ha cambiato stato
    changed_by = models.CharField(
        max_length=100,
        help_text="Utente o sistema che ha cambiato stato"
    )
    change_source = models.CharField(
        max_length=50,
        default='app',
        help_text="Origine del cambio (app, api, schedule, system)"
    )
    
    # Nodi coinvolti
    nodes_affected = models.ManyToManyField(
        Node,
        related_name='arm_states',
        blank=True
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'system_arm_states'
        ordering = ['-timestamp']
        verbose_name = 'Stato Armamento'
        verbose_name_plural = 'Stati Armamento'
    
    def __str__(self):
        return f"{self.mode} @ {self.timestamp}"
    
    @classmethod
    def get_current_mode(cls):
        """Ottiene lo stato corrente del sistema"""
        latest = cls.objects.first()
        return latest.mode if latest else cls.ArmMode.DISARMED


class SecurityZone(models.Model):
    """
    Zone di sicurezza per gestione granulare
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Nodi appartenenti alla zona
    nodes = models.ManyToManyField(
        Node,
        related_name='security_zones',
        limit_choices_to={'node_type': 'SEC'}
    )
    
    # Configurazione
    is_active = models.BooleanField(default=True)
    is_armed = models.BooleanField(default=True)
    
    # Soglie personalizzate
    alarm_delay_seconds = models.PositiveSmallIntegerField(
        default=0,
        help_text="Ritardo prima di attivare allarme"
    )
    entry_delay_seconds = models.PositiveSmallIntegerField(
        default=30,
        help_text="Tempo per disarmare dopo ingresso"
    )
    
    # Notifiche
    notify_on_alarm = models.BooleanField(default=True)
    notify_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Canali notifica per questa zona"
    )
    
    class Meta:
        db_table = 'security_zones'
        verbose_name = 'Zona Sicurezza'
        verbose_name_plural = 'Zone Sicurezza'
    
    def __str__(self):
        return self.name
