"""
AgriSecure IoT System - MQTT Subscriber

Management command Django che si connette al broker MQTT
e processa i messaggi in arrivo dai gateway IoT.

Usage:
    python manage.py mqtt_subscriber
"""

import json
import logging
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction

import paho.mqtt.client as mqtt

from apps.nodes.models import Node, NodeStatus, NodeType, NodeHeartbeat, NodeEvent
from apps.sensors.models import SensorReading, SensorAlert
from apps.security.models import SecurityEvent, Alarm, IntrusionClass, AlarmPriority

logger = logging.getLogger('mqtt')


class MQTTSubscriber:
    """
    Gestisce la connessione MQTT e il processing dei messaggi
    """
    
    def __init__(self):
        self.config = settings.MQTT_CONFIG
        self.client = None
        self.connected = False
        
    def connect(self):
        """Stabilisce connessione al broker MQTT"""
        self.client = mqtt.Client(
            client_id=f"agrisecure-backend-{timezone.now().timestamp()}"
        )
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Autenticazione
        if self.config['USER']:
            self.client.username_pw_set(
                self.config['USER'],
                self.config['PASSWORD']
            )
        
        # Connessione
        logger.info(f"Connessione a MQTT broker: {self.config['BROKER']}:{self.config['PORT']}")
        try:
            self.client.connect(
                self.config['BROKER'],
                self.config['PORT'],
                self.config['KEEPALIVE']
            )
            return True
        except Exception as e:
            logger.error(f"Errore connessione MQTT: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback connessione stabilita"""
        if rc == 0:
            self.connected = True
            logger.info("Connesso al broker MQTT")
            
            # Subscribe a tutti i topic agrisecure con wildcard ampio
            # Questo cattura: sensors, security, status e qualsiasi altro
            main_topic = "agrisecure/#"
            client.subscribe(main_topic, self.config['QOS'])
            logger.info(f"Sottoscritto a: {main_topic}")
        else:
            logger.error(f"Connessione MQTT fallita, codice: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback disconnessione"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Disconnessione inattesa dal broker MQTT: {rc}")
        else:
            logger.info("Disconnesso dal broker MQTT")
    
    def _on_message(self, client, userdata, msg):
        """Callback ricezione messaggio"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            logger.info(f"Messaggio ricevuto su {topic}: {list(payload.keys())}")
            
            # Routing basato su topic
            if '/sensors/' in topic:
                self._process_sensor_data(topic, payload)
            elif '/security/' in topic:
                self._process_security_event(topic, payload)
            elif '/status' in topic:
                self._process_status(topic, payload)
            else:
                logger.warning(f"Topic non gestito: {topic}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Errore parsing JSON: {e}")
        except Exception as e:
            logger.exception(f"Errore processing messaggio: {e}")
    
    @transaction.atomic
    def _process_sensor_data(self, topic, payload):
        """Processa dati sensori ambientali"""
        node_id = payload.get('node_id')
        if not node_id:
            logger.warning("Messaggio sensori senza node_id")
            return
        
        logger.info(f"Dati sensori da {node_id}")
        
        # Trova o crea nodo
        node, created = Node.objects.get_or_create(
            node_id=node_id,
            defaults={
                'name': f'Nodo {node_id}',
                'node_type': NodeType.AMBIENT,
            }
        )
        
        if created:
            logger.info(f"Nuovo nodo creato: {node_id}")
        
        # Aggiorna stato nodo
        node.last_seen = timezone.now()
        node.status = NodeStatus.ONLINE
        node.save(update_fields=['last_seen', 'status', 'updated_at'])
        
        # Crea lettura sensore
        reading = SensorReading.objects.create(
            node=node,
            timestamp=self._parse_timestamp(payload.get('timestamp')),
            temperature=self._to_decimal(payload.get('temperature')),
            humidity=self._to_decimal(payload.get('humidity')),
            pressure=self._to_decimal(payload.get('pressure')),
            light_lux=payload.get('light'),
            soil_moisture_raw=payload.get('soil_raw'),
            soil_moisture_percent=payload.get('soil_moisture'),
        )
        
        logger.info(f"Lettura salvata: T={reading.temperature}°C, H={reading.humidity}%")
        
        # Verifica soglie e genera alert se necessario
        self._check_sensor_alerts(node, reading)
    
    @transaction.atomic
    def _process_security_event(self, topic, payload):
        """Processa evento di sicurezza"""
        node_id = payload.get('node_id')
        if not node_id:
            logger.warning("Evento sicurezza senza node_id")
            return
        
        classification_raw = payload.get('classification', 'unknown')
        priority_raw = payload.get('priority', 'MEDIUM')
        
        logger.info(f"Evento sicurezza da {node_id}: {classification_raw} (priorità: {priority_raw})")
        
        # Trova o crea nodo
        node, created = Node.objects.get_or_create(
            node_id=node_id,
            defaults={
                'name': f'Nodo Sicurezza {node_id}',
                'node_type': NodeType.SECURITY,
            }
        )
        
        # Aggiorna stato nodo
        node.last_seen = timezone.now()
        node.status = NodeStatus.ONLINE
        node.save(update_fields=['last_seen', 'status', 'updated_at'])
        
        # Mappa classificazione - supporta sia valori numerici che stringhe
        class_map = {
            # Valori numerici
            0: IntrusionClass.NONE,
            1: IntrusionClass.PERSON,
            2: IntrusionClass.ANIMAL_LARGE,
            3: IntrusionClass.ANIMAL_SMALL,
            4: IntrusionClass.UNKNOWN,
            5: IntrusionClass.TAMPER,
            # Stringhe maiuscole
            'NONE': IntrusionClass.NONE,
            'PERSON': IntrusionClass.PERSON,
            'ANIMAL_LARGE': IntrusionClass.ANIMAL_LARGE,
            'ANIMAL_SMALL': IntrusionClass.ANIMAL_SMALL,
            'UNKNOWN': IntrusionClass.UNKNOWN,
            'TAMPER': IntrusionClass.TAMPER,
            # Stringhe minuscole (come invia il simulatore)
            'none': IntrusionClass.NONE,
            'person': IntrusionClass.PERSON,
            'animal_lg': IntrusionClass.ANIMAL_LARGE,
            'animal_sm': IntrusionClass.ANIMAL_SMALL,
            'unknown': IntrusionClass.UNKNOWN,
            'tamper': IntrusionClass.TAMPER,
        }
        intrusion_class = class_map.get(classification_raw, IntrusionClass.UNKNOWN)
        
        # Mappa priorità
        priority_map = {
            'CRITICAL': AlarmPriority.CRITICAL,
            'HIGH': AlarmPriority.HIGH,
            'MEDIUM': AlarmPriority.MEDIUM,
            'LOW': AlarmPriority.LOW,
            'WARNING': AlarmPriority.HIGH,
            'critical': AlarmPriority.CRITICAL,
            'high': AlarmPriority.HIGH,
            'medium': AlarmPriority.MEDIUM,
            'low': AlarmPriority.LOW,
        }
        alarm_priority = priority_map.get(priority_raw, AlarmPriority.MEDIUM)
        
        # Crea evento sicurezza
        event = SecurityEvent.objects.create(
            node=node,
            timestamp=self._parse_timestamp(payload.get('timestamp')),
            classification=intrusion_class,
            priority=alarm_priority,
            pir_main=payload.get('pir_main', False),
            pir_backup=payload.get('pir_backup', False),
            motion_confirmed=payload.get('pir_main', False) and payload.get('pir_backup', False),
            tamper_detected=payload.get('tamper', False),
            accel_x=self._to_decimal(payload.get('accel_x')),
            accel_y=self._to_decimal(payload.get('accel_y')),
            accel_z=self._to_decimal(payload.get('accel_z')),
            raw_data=payload,
        )
        
        logger.info(f"Evento sicurezza salvato: {event.id} - {intrusion_class}")
        
        # Se persona o tamper, crea allarme
        if intrusion_class in [IntrusionClass.PERSON, IntrusionClass.TAMPER]:
            alarm = Alarm.objects.create(
                event=event,
                node=node,
                triggered_at=event.timestamp,
                priority=AlarmPriority.CRITICAL,
                classification=intrusion_class,
                siren_activated=True,
                lights_activated=True,
            )
            
            logger.warning(f"!!! ALLARME CRITICO {alarm.id} !!! {intrusion_class} su {node_id}")
            
            # Trigger notifiche
            self._send_alarm_notifications(alarm)
        
        elif intrusion_class == IntrusionClass.ANIMAL_LARGE:
            alarm = Alarm.objects.create(
                event=event,
                node=node,
                triggered_at=event.timestamp,
                priority=AlarmPriority.HIGH,
                classification=intrusion_class,
                siren_activated=False,
                lights_activated=True,
            )
            logger.info(f"Warning: animale grande rilevato su {node_id}")
    
    @transaction.atomic
    def _process_status(self, topic, payload):
        """Processa status/heartbeat da nodo"""
        node_id = payload.get('node_id')
        if not node_id:
            return
        
        logger.debug(f"Status da {node_id}")
        
        # Mappa tipo nodo
        node_type_map = {
            'GATEWAY': NodeType.GATEWAY,
            'AMBIENT': NodeType.AMBIENT,
            'SECURITY': NodeType.SECURITY,
            'GW': NodeType.GATEWAY,
            'AMB': NodeType.AMBIENT,
            'SEC': NodeType.SECURITY,
        }
        
        # Trova nodo
        try:
            node = Node.objects.get(node_id=node_id)
        except Node.DoesNotExist:
            # Crea nodo se non esiste
            raw_type = payload.get('type', 'AMB')
            node = Node.objects.create(
                node_id=node_id,
                name=f'Nodo {node_id}',
                node_type=node_type_map.get(raw_type, NodeType.AMBIENT),
            )
            logger.info(f"Nuovo nodo creato da heartbeat: {node_id} ({raw_type})")
        
        # Aggiorna dati nodo
        node.last_seen = timezone.now()
        node.status = NodeStatus.ONLINE
        node.uptime_seconds = payload.get('uptime', 0)
        node.rssi = payload.get('rssi') or payload.get('signal')
        node.mesh_neighbors = payload.get('mesh_peers', 0)
        node.firmware_version = payload.get('firmware', node.firmware_version)
        
        if 'battery' in payload:
            node.battery_percentage = payload['battery']
        
        node.save()
        
        logger.debug(f"Nodo {node_id} aggiornato: status=online, battery={node.battery_percentage}")
        
        # Crea record heartbeat
        NodeHeartbeat.objects.create(
            node=node,
            uptime_seconds=payload.get('uptime', 0),
            free_heap_kb=payload.get('heap_free', 0) // 1024 if payload.get('heap_free') else 0,
            rssi=payload.get('rssi') or payload.get('signal'),
            battery_percentage=payload.get('battery'),
            mesh_neighbors=payload.get('mesh_peers', 0),
        )
    
    def _check_sensor_alerts(self, node, reading):
        """Verifica soglie sensori e genera alert"""
        thresholds = getattr(settings, 'AGRISECURE', {}).get('ALARM_THRESHOLDS', {})
        
        alerts_to_create = []
        
        # Temperatura
        if reading.temperature is not None:
            temp = float(reading.temperature)
            if temp < thresholds.get('TEMPERATURE_MIN', -5):
                alerts_to_create.append({
                    'alert_type': SensorAlert.AlertType.TEMPERATURE_LOW,
                    'severity': SensorAlert.AlertSeverity.CRITICAL,
                    'value': temp,
                    'threshold': thresholds.get('TEMPERATURE_MIN', -5),
                    'message': f"Temperatura critica: {temp}°C (rischio gelo)",
                })
            elif temp > thresholds.get('TEMPERATURE_MAX', 45):
                alerts_to_create.append({
                    'alert_type': SensorAlert.AlertType.TEMPERATURE_HIGH,
                    'severity': SensorAlert.AlertSeverity.WARNING,
                    'value': temp,
                    'threshold': thresholds.get('TEMPERATURE_MAX', 45),
                    'message': f"Temperatura elevata: {temp}°C",
                })
        
        # Umidità suolo
        if reading.soil_moisture_percent is not None:
            soil = reading.soil_moisture_percent
            if soil < thresholds.get('SOIL_MOISTURE_MIN', 15):
                alerts_to_create.append({
                    'alert_type': SensorAlert.AlertType.SOIL_DRY,
                    'severity': SensorAlert.AlertSeverity.WARNING,
                    'value': soil,
                    'threshold': thresholds.get('SOIL_MOISTURE_MIN', 15),
                    'message': f"Suolo troppo secco: {soil}%",
                })
        
        # Crea alert
        for alert_data in alerts_to_create:
            SensorAlert.objects.create(
                node=node,
                **alert_data
            )
            logger.warning(f"Alert creato: {alert_data['message']}")
    
    def _send_alarm_notifications(self, alarm):
        """Invia notifiche per allarme critico"""
        # Questo sarà gestito da Celery task
        try:
            from apps.notifications.tasks import send_alarm_notification
            send_alarm_notification.delay(alarm.id)
            logger.info(f"Notifica schedulata per allarme {alarm.id}")
        except Exception as e:
            logger.error(f"Errore invio notifica allarme: {e}")
    
    def _parse_timestamp(self, ts):
        """Converte timestamp in datetime"""
        if ts is None:
            return timezone.now()
        if isinstance(ts, (int, float)):
            # Unix timestamp (secondi o millisecondi)
            if ts > 1e12:  # Millisecondi
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=dt_timezone.utc)
        return timezone.now()
    
    def _to_decimal(self, value):
        """Converte valore in Decimal"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def run(self):
        """Avvia il loop principale"""
        if not self.connect():
            return
        
        logger.info("MQTT Subscriber avviato")
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Interruzione richiesta")
        finally:
            self.client.disconnect()
            logger.info("MQTT Subscriber terminato")


class Command(BaseCommand):
    help = 'Avvia il subscriber MQTT per ricevere dati dai gateway IoT'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Avvio MQTT Subscriber...'))
        subscriber = MQTTSubscriber()
        subscriber.run()
