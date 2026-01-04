"""
AgriSecure IoT System - Models per Dati Sensori

Definisce i modelli per i dati dei sensori ambientali:
- Temperature, Umidità, Pressione (BME280)
- Luminosità (BH1750)
- Umidità suolo (sensore capacitivo)

Usa TimescaleDB per ottimizzare le query su serie temporali.
"""

from django.db import models
from django.utils import timezone
from apps.nodes.models import Node


class SensorReading(models.Model):
    """
    Lettura sensori ambientali (TimescaleDB hypertable)
    
    Questa tabella viene convertita in hypertable per performance ottimali
    su grandi volumi di dati temporali.
    """
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='sensor_readings'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # BME280 - Clima
    temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Temperatura in °C"
    )
    humidity = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Umidità relativa in %"
    )
    pressure = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pressione atmosferica in hPa"
    )
    
    # BH1750 - Luminosità
    light_lux = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Luminosità in lux"
    )
    
    # Sensore suolo
    soil_moisture_raw = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Valore ADC grezzo (0-4095)"
    )
    soil_moisture_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Umidità suolo in %"
    )
    
    # Batteria (opzionale, per correlazioni)
    battery_voltage = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'sensor_readings'
        ordering = ['-timestamp']
        verbose_name = 'Lettura Sensore'
        verbose_name_plural = 'Letture Sensori'
        indexes = [
            models.Index(fields=['node', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} @ {self.timestamp}"
    
    @property
    def is_temperature_critical(self):
        """Verifica se temperatura fuori range critico"""
        from django.conf import settings
        thresholds = settings.AGRISECURE.get('ALARM_THRESHOLDS', {})
        if self.temperature is None:
            return False
        temp = float(self.temperature)
        return temp < thresholds.get('TEMPERATURE_MIN', -5) or \
               temp > thresholds.get('TEMPERATURE_MAX', 45)
    
    @property
    def is_soil_dry(self):
        """Verifica se suolo troppo secco"""
        from django.conf import settings
        thresholds = settings.AGRISECURE.get('ALARM_THRESHOLDS', {})
        if self.soil_moisture_percent is None:
            return False
        return self.soil_moisture_percent < thresholds.get('SOIL_MOISTURE_MIN', 15)


class SensorAggregate(models.Model):
    """
    Dati aggregati per periodo (ora, giorno, settimana, mese)
    
    Usato per dashboard e grafici storici senza query su milioni di righe.
    """
    class AggregateType(models.TextChoices):
        HOURLY = 'hourly', 'Orario'
        DAILY = 'daily', 'Giornaliero'
        WEEKLY = 'weekly', 'Settimanale'
        MONTHLY = 'monthly', 'Mensile'
    
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='sensor_aggregates'
    )
    aggregate_type = models.CharField(
        max_length=10,
        choices=AggregateType.choices
    )
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField()
    
    # Conteggi
    reading_count = models.PositiveIntegerField(default=0)
    
    # Temperatura
    temperature_min = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    temperature_max = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    temperature_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Umidità aria
    humidity_min = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    humidity_max = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    humidity_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Pressione
    pressure_min = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    pressure_max = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    pressure_avg = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    
    # Luminosità
    light_min = models.PositiveIntegerField(null=True)
    light_max = models.PositiveIntegerField(null=True)
    light_avg = models.PositiveIntegerField(null=True)
    
    # Suolo
    soil_min = models.PositiveSmallIntegerField(null=True)
    soil_max = models.PositiveSmallIntegerField(null=True)
    soil_avg = models.PositiveSmallIntegerField(null=True)
    
    class Meta:
        db_table = 'sensor_aggregates'
        ordering = ['-period_start']
        verbose_name = 'Aggregato Sensori'
        verbose_name_plural = 'Aggregati Sensori'
        unique_together = ['node', 'aggregate_type', 'period_start']
        indexes = [
            models.Index(fields=['node', 'aggregate_type', '-period_start']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} - {self.aggregate_type} @ {self.period_start}"


class SensorAlert(models.Model):
    """
    Alert generati dai sensori quando valori escono dai range
    """
    class AlertType(models.TextChoices):
        TEMPERATURE_LOW = 'temp_low', 'Temperatura Bassa'
        TEMPERATURE_HIGH = 'temp_high', 'Temperatura Alta'
        HUMIDITY_LOW = 'hum_low', 'Umidità Bassa'
        HUMIDITY_HIGH = 'hum_high', 'Umidità Alta'
        SOIL_DRY = 'soil_dry', 'Suolo Secco'
        SOIL_WET = 'soil_wet', 'Suolo Bagnato'
        SENSOR_OFFLINE = 'sensor_off', 'Sensore Offline'
        SENSOR_ERROR = 'sensor_err', 'Errore Sensore'
    
    class AlertSeverity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critico'
    
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='sensor_alerts'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices
    )
    severity = models.CharField(
        max_length=10,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING
    )
    
    # Valori che hanno triggerato l'alert
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        help_text="Valore che ha triggerato l'alert"
    )
    threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        help_text="Soglia superata"
    )
    
    message = models.TextField(blank=True)
    
    # Gestione
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=100, blank=True)
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notifiche inviate
    notification_sent = models.BooleanField(default=False)
    notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Canali su cui è stata inviata la notifica"
    )
    
    class Meta:
        db_table = 'sensor_alerts'
        ordering = ['-timestamp']
        verbose_name = 'Alert Sensore'
        verbose_name_plural = 'Alert Sensori'
        indexes = [
            models.Index(fields=['node', '-timestamp']),
            models.Index(fields=['alert_type', 'is_resolved']),
            models.Index(fields=['-timestamp', 'severity']),
        ]
    
    def __str__(self):
        return f"{self.node.node_id} - {self.alert_type} @ {self.timestamp}"
    
    def acknowledge(self, by_user='system'):
        """Marca l'alert come preso in carico"""
        self.is_acknowledged = True
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = by_user
        self.save(update_fields=['is_acknowledged', 'acknowledged_at', 'acknowledged_by'])
    
    def resolve(self):
        """Marca l'alert come risolto"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save(update_fields=['is_resolved', 'resolved_at'])
