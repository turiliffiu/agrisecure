#!/usr/bin/env python3
"""
AgriSecure IoT Simulator v4 - Enhanced Edition
===============================================
Simulatore completo per testare MQTT e Dashboard

Features:
- 20+ scenari di test
- Test automatici completi
- Modalità demo/presentazione
- Test stress e performance
- Output dettagliato e statistiche
- Validazione risposte MQTT
"""

import os
import sys
import json
import time
import random
import signal
import argparse
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict
import logging

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ Errore: paho-mqtt non installato")
    print("   pip install paho-mqtt")
    sys.exit(1)


# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('simulator.log')
    ]
)
logger = logging.getLogger('AgriSecure-Sim')


# ============================================================================
# Configurazione
# ============================================================================

@dataclass
class MQTTConfig:
    """Configurazione MQTT"""
    broker: str = "localhost"
    port: int = 1883
    username: str = "agrisecure"
    password: str = "mqtt_secure_password"
    base_topic: str = "agrisecure"
    qos: int = 1
    keepalive: int = 60


@dataclass
class SimConfig:
    """Configurazione simulatore"""
    heartbeat_interval: int = 30
    sensor_interval: int = 60
    security_check_interval: int = 5
    motion_probability: float = 0.02
    alarm_probability: float = 0.3
    
    # Intervalli per demo
    demo_step_duration: int = 10
    
    # Limiti sensori
    temp_min: float = -10.0
    temp_max: float = 45.0
    temp_normal_min: float = 15.0
    temp_normal_max: float = 30.0
    
    humidity_min: float = 20.0
    humidity_max: float = 95.0
    humidity_normal_min: float = 40.0
    humidity_normal_max: float = 80.0
    
    soil_min: int = 10
    soil_max: int = 80
    soil_critical: int = 15
    
    battery_critical: int = 10
    battery_low: int = 20
    battery_warning: int = 50


class NodeType(Enum):
    """Tipi di nodo"""
    GATEWAY = "GW"
    AMBIENT = "AMB"
    SECURITY = "SEC"


class NodeStatus(Enum):
    """Stati nodo"""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Classification(Enum):
    """Classificazione eventi sicurezza"""
    NONE = "none"
    PERSON = "person"
    ANIMAL_LARGE = "animal_lg"
    ANIMAL_SMALL = "animal_sm"
    UNKNOWN = "unknown"
    TAMPER = "tamper"


class Scenario(Enum):
    """Scenari disponibili"""
    NORMAL = "normal"
    SENSOR_ALERT_TEMP_HIGH = "temp_high"
    SENSOR_ALERT_TEMP_LOW = "temp_low"
    SENSOR_ALERT_HUMIDITY_HIGH = "humidity_high"
    SENSOR_ALERT_HUMIDITY_LOW = "humidity_low"
    SENSOR_ALERT_SOIL_DRY = "soil_dry"
    SECURITY_PERSON = "person_detected"
    SECURITY_ANIMAL_LARGE = "animal_large"
    SECURITY_ANIMAL_SMALL = "animal_small"
    SECURITY_TAMPER = "tamper_detected"
    BATTERY_CRITICAL = "battery_critical"
    BATTERY_LOW = "battery_low"
    NODE_OFFLINE = "node_offline"
    NODE_WARNING = "node_warning"
    MESH_DEGRADED = "mesh_degraded"
    ALARM_MULTIPLE = "alarm_multiple"
    STORM_SIMULATION = "storm"
    NIGHT_MODE = "night"
    GREENHOUSE_MODE = "greenhouse"
    FULL_TEST = "full_test"
    STRESS_TEST = "stress_test"


@dataclass
class SimNode:
    """Nodo simulato"""
    node_id: str
    node_type: NodeType
    name: str
    location: str = ""
    status: NodeStatus = NodeStatus.ONLINE
    
    # Hardware
    battery: int = 100
    battery_voltage: float = 4.2
    is_charging: bool = False
    solar_voltage: float = 0.0
    
    # Connettività
    rssi: int = -45
    mesh_peers: int = 2
    
    # Runtime
    uptime: int = 0
    boot_count: int = 1
    firmware_version: str = "1.0.0"
    
    # Sicurezza
    is_armed: bool = True
    
    # Sensori ambientali
    temperature: float = 22.0
    humidity: float = 65.0
    pressure: float = 1013.0
    light: int = 5000
    soil_moisture: int = 45
    soil_raw: int = 1800
    
    # Eventi sicurezza
    last_motion: Optional[datetime] = None
    motion_count: int = 0
    
    # Statistiche
    messages_sent: int = 0
    errors: int = 0
    
    def to_dict(self) -> dict:
        """Converti a dizionario"""
        return {
            'node_id': self.node_id,
            'type': self.node_type.value,
            'name': self.name,
            'status': self.status.value,
            'battery': self.battery,
            'temperature': self.temperature if self.node_type == NodeType.AMBIENT else None,
            'is_armed': self.is_armed if self.node_type == NodeType.SECURITY else None,
        }


@dataclass
class Statistics:
    """Statistiche simulatore"""
    heartbeats: int = 0
    sensor_readings: int = 0
    security_events: int = 0
    alarms: int = 0
    commands_received: int = 0
    
    # Breakdown per classificazione
    classifications: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Timing
    start_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        runtime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            'runtime_seconds': int(runtime),
            'heartbeats': self.heartbeats,
            'sensor_readings': self.sensor_readings,
            'security_events': self.security_events,
            'alarms': self.alarms,
            'commands_received': self.commands_received,
            'classifications': dict(self.classifications),
            'rate': {
                'heartbeats_per_min': round(self.heartbeats / (runtime / 60), 2) if runtime > 0 else 0,
                'events_per_min': round(self.security_events / (runtime / 60), 2) if runtime > 0 else 0,
            }
        }


# ============================================================================
# Simulatore Principale
# ============================================================================

class Simulator:
    """Simulatore IoT AgriSecure"""
    
    def __init__(self, mqtt_cfg: MQTTConfig = None, sim_cfg: SimConfig = None):
        self.mqtt_cfg = mqtt_cfg or MQTTConfig()
        self.sim_cfg = sim_cfg or SimConfig()
        
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.running = False
        self.lock = threading.Lock()
        
        self.current_scenario: Scenario = Scenario.NORMAL
        self.nodes: Dict[str, SimNode] = {}
        self.stats = Statistics()
        
        self._init_nodes()
        
        # Test suite results
        self.test_results: List[Tuple[str, bool, str]] = []
    
    def _init_nodes(self):
        """Inizializza nodi"""
        logger.info("Inizializzazione nodi...")
        
        self.nodes["GW-001"] = SimNode(
            "GW-001", NodeType.GATEWAY, "Gateway Principale",
            location="Ingresso terreno", battery=100, mesh_peers=6
        )
        
        self.nodes["AMB-001"] = SimNode(
            "AMB-001", NodeType.AMBIENT, "Sensore Campo Nord",
            location="Campo Nord", battery=85, temperature=21.5, humidity=62.0
        )
        
        self.nodes["AMB-002"] = SimNode(
            "AMB-002", NodeType.AMBIENT, "Sensore Campo Sud",
            location="Campo Sud", battery=72, temperature=23.0, humidity=58.0
        )
        
        self.nodes["AMB-003"] = SimNode(
            "AMB-003", NodeType.AMBIENT, "Sensore Serra",
            location="Serra", battery=90, temperature=28.0, humidity=80.0,
            is_charging=True, solar_voltage=5.2
        )
        
        self.nodes["SEC-001"] = SimNode(
            "SEC-001", NodeType.SECURITY, "Sicurezza Ingresso",
            location="Ingresso principale", battery=95, is_armed=True
        )
        
        self.nodes["SEC-002"] = SimNode(
            "SEC-002", NodeType.SECURITY, "Sicurezza Est",
            location="Perimetro Est", battery=88, is_armed=True
        )
        
        self.nodes["SEC-003"] = SimNode(
            "SEC-003", NodeType.SECURITY, "Sicurezza Ovest",
            location="Perimetro Ovest", battery=78, is_armed=True
        )
        
        logger.info(f"✅ {len(self.nodes)} nodi inizializzati")
    
    # ========================================================================
    # MQTT Connection & Callbacks
    # ========================================================================
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback connessione"""
        if rc == 0:
            self.connected = True
            logger.info(f"✅ Connesso a MQTT {self.mqtt_cfg.broker}:{self.mqtt_cfg.port}")
            
            # Sottoscrizione comandi
            topic = f"{self.mqtt_cfg.base_topic}/+/command"
            client.subscribe(topic)
            logger.info(f"📡 Sottoscritto a: {topic}")
        else:
            self.connected = False
            logger.error(f"❌ Connessione fallita: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback disconnessione"""
        self.connected = False
        if rc != 0:
            logger.warning(f"⚠️ Disconnesso inaspettatamente: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback messaggio ricevuto"""
        try:
            parts = msg.topic.split("/")
            if len(parts) >= 3 and parts[2] == "command":
                node_id = parts[1]
                cmd = json.loads(msg.payload.decode())
                self._handle_command(node_id, cmd)
        except Exception as e:
            logger.error(f"Errore processing comando: {e}")
    
    def _handle_command(self, node_id: str, cmd: dict):
        """Gestisce comando ricevuto"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Comando per nodo sconosciuto: {node_id}")
                return
            
            node = self.nodes[node_id]
            action = cmd.get("command", "")
            
            logger.info(f"📥 Comando {node_id}: {action}")
            self.stats.commands_received += 1
            
            if action == "reboot":
                node.uptime = 0
                node.boot_count += 1
                logger.info(f"  ↻ Reboot {node_id}")
            
            elif action == "arm":
                node.is_armed = True
                logger.info(f"  🔒 Armato {node_id}")
            
            elif action == "disarm":
                node.is_armed = False
                logger.info(f"  🔓 Disarmato {node_id}")
            
            elif action == "sleep":
                duration = cmd.get("duration", 60)
                logger.info(f"  💤 Sleep {node_id} per {duration}s")
            
            elif action == "update_config":
                config = cmd.get("config", {})
                logger.info(f"  ⚙️ Config update {node_id}: {config}")
            
            else:
                logger.warning(f"  ❓ Comando sconosciuto: {action}")
    
    def _publish(self, topic: str, data: dict, qos: int = None) -> bool:
        """Pubblica messaggio MQTT"""
        if not self.connected or not self.client:
            return False
        
        try:
            full_topic = f"{self.mqtt_cfg.base_topic}/{topic}"
            payload = json.dumps(data)
            qos = qos if qos is not None else self.mqtt_cfg.qos
            
            result = self.client.publish(full_topic, payload, qos=qos)
            result.wait_for_publish(timeout=5)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        
        except Exception as e:
            logger.error(f"❌ Errore publish {topic}: {e}")
            return False
    
    # ========================================================================
    # Message Senders
    # ========================================================================
    
    def _send_heartbeat(self, node: SimNode):
        """Invia heartbeat nodo"""
        data = {
            "node_id": node.node_id,
            "type": node.node_type.value,
            "timestamp": int(time.time()),
            "uptime": node.uptime,
            "battery": node.battery,
            "battery_voltage": round(node.battery_voltage, 2),
            "is_charging": node.is_charging,
            "solar_voltage": round(node.solar_voltage, 2) if node.is_charging else 0.0,
            "rssi": node.rssi,
            "mesh_peers": node.mesh_peers,
            "firmware": node.firmware_version,
            "boot_count": node.boot_count,
            "heap_free": random.randint(100000, 200000),
            "status": node.status.value,
        }
        
        if self._publish(f"{node.node_id}/status", data):
            self.stats.heartbeats += 1
            node.messages_sent += 1
        else:
            node.errors += 1
    
    def _send_sensors(self, node: SimNode):
        """Invia letture sensori"""
        if node.node_type != NodeType.AMBIENT:
            return
        
        data = {
            "node_id": node.node_id,
            "timestamp": int(time.time()),
            "temperature": round(node.temperature, 2),
            "humidity": round(node.humidity, 2),
            "pressure": round(node.pressure, 2),
            "light": node.light,
            "soil_moisture": node.soil_moisture,
            "soil_raw": node.soil_raw,
            "battery": node.battery,
        }
        
        if self._publish(f"{node.node_id}/sensors/ambient", data):
            self.stats.sensor_readings += 1
            node.messages_sent += 1
        else:
            node.errors += 1
    
    def _send_security_event(
        self,
        node: SimNode,
        classification: Classification,
        trigger_alarm: bool = False,
        confidence: int = None
    ):
        """Invia evento sicurezza"""
        if node.node_type != NodeType.SECURITY:
            return
        
        # Determina priorità
        if classification == Classification.PERSON:
            priority = "CRITICAL"
        elif classification == Classification.TAMPER:
            priority = "CRITICAL"
        elif classification == Classification.ANIMAL_LARGE:
            priority = "HIGH"
        elif classification == Classification.ANIMAL_SMALL:
            priority = "LOW"
        else:
            priority = "MEDIUM"
        
        # PIR patterns realistici per classificazione
        if classification == Classification.PERSON:
            pir_main = True
            pir_backup = random.random() > 0.2  # 80% backup attivo
            confidence = confidence or random.randint(85, 98)
        elif classification == Classification.ANIMAL_LARGE:
            pir_main = True
            pir_backup = random.random() > 0.5  # 50% backup
            confidence = confidence or random.randint(70, 85)
        elif classification == Classification.ANIMAL_SMALL:
            pir_main = random.random() > 0.3  # Intermittente
            pir_backup = False
            confidence = confidence or random.randint(50, 70)
        elif classification == Classification.TAMPER:
            pir_main = True
            pir_backup = True
            confidence = confidence or 99
        else:
            pir_main = True
            pir_backup = random.random() > 0.5
            confidence = confidence or random.randint(40, 60)
        
        # Accelerometro
        if classification == Classification.TAMPER:
            accel_x = round(random.uniform(-2.0, 2.0), 3)
            accel_y = round(random.uniform(-2.0, 2.0), 3)
            accel_z = round(random.uniform(-1.0, 2.0), 3)
        else:
            accel_x = round(random.uniform(-0.1, 0.1), 3)
            accel_y = round(random.uniform(-0.1, 0.1), 3)
            accel_z = round(random.uniform(0.95, 1.05), 3)
        
        data = {
            "node_id": node.node_id,
            "timestamp": int(time.time()),
            "classification": classification.value,
            "priority": priority,
            "confidence": confidence,
            "pir_main": pir_main,
            "pir_backup": pir_backup,
            "motion_confirmed": pir_main and pir_backup,
            "tamper": classification == Classification.TAMPER,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z,
            "duration_ms": random.randint(1000, 5000),
            "is_armed": node.is_armed,
        }
        
        if self._publish(f"{node.node_id}/security/event", data):
            self.stats.security_events += 1
            self.stats.classifications[classification.value] += 1
            node.messages_sent += 1
            node.last_motion = datetime.now()
            node.motion_count += 1
            
            if trigger_alarm and node.is_armed:
                self.stats.alarms += 1
                logger.warning(f"🚨 ALLARME: {node.node_id} - {classification.value}")
        else:
            node.errors += 1
    
    # ========================================================================
    # Simulation Logic
    # ========================================================================
    
    def _simulate_sensors(self, node: SimNode):
        """Simula evoluzione sensori"""
        if node.node_type != NodeType.AMBIENT:
            return
        
        hour = datetime.now().hour
        is_day = 6 <= hour <= 20
        
        # Temperatura
        if self.current_scenario == Scenario.SENSOR_ALERT_TEMP_HIGH:
            node.temperature = min(node.temperature + random.uniform(0.5, 1.0), 
                                  self.sim_cfg.temp_max)
        elif self.current_scenario == Scenario.SENSOR_ALERT_TEMP_LOW:
            node.temperature = max(node.temperature - random.uniform(0.5, 1.0),
                                  self.sim_cfg.temp_min)
        elif self.current_scenario == Scenario.GREENHOUSE_MODE:
            # Serra: temperatura più alta
            target = 28.0 + random.uniform(-2, 2)
            node.temperature += (target - node.temperature) * 0.1
        elif self.current_scenario == Scenario.STORM_SIMULATION:
            # Tempesta: temperatura cala
            node.temperature = max(node.temperature - random.uniform(0.2, 0.5), 10.0)
        else:
            # Normale: ciclo giornaliero
            temp_mod = 3.0 if 12 <= hour <= 16 else -2.0 if 0 <= hour <= 6 else 0
            target = 20.0 + temp_mod + random.uniform(-1, 1)
            node.temperature += (target - node.temperature) * 0.05
        
        # Umidità
        if self.current_scenario == Scenario.SENSOR_ALERT_HUMIDITY_HIGH:
            node.humidity = min(node.humidity + random.uniform(1.0, 2.0),
                               self.sim_cfg.humidity_max)
        elif self.current_scenario == Scenario.SENSOR_ALERT_HUMIDITY_LOW:
            node.humidity = max(node.humidity - random.uniform(1.0, 2.0),
                               self.sim_cfg.humidity_min)
        elif self.current_scenario == Scenario.STORM_SIMULATION:
            # Tempesta: umidità alta
            node.humidity = min(node.humidity + random.uniform(1, 3), 95)
        else:
            # Normale
            target = 65.0 if is_day else 75.0
            node.humidity += (target - node.humidity) * 0.05 + random.uniform(-1, 1)
        
        # Pressione atmosferica
        if self.current_scenario == Scenario.STORM_SIMULATION:
            # Tempesta: pressione bassa
            node.pressure = max(node.pressure - random.uniform(1, 3), 980)
        else:
            node.pressure += random.uniform(-1, 1)
            node.pressure = max(1000, min(1030, node.pressure))
        
        # Luminosità
        if self.current_scenario == Scenario.NIGHT_MODE or not is_day:
            target = random.randint(0, 100)
        else:
            target = random.randint(3000, 8000)
        node.light = int(node.light * 0.8 + target * 0.2)
        
        # Umidità suolo
        if self.current_scenario == Scenario.SENSOR_ALERT_SOIL_DRY:
            node.soil_moisture = max(node.soil_moisture - random.randint(1, 2),
                                    self.sim_cfg.soil_min)
        elif self.current_scenario == Scenario.STORM_SIMULATION:
            # Pioggia: suolo bagnato
            node.soil_moisture = min(node.soil_moisture + random.randint(2, 5), 80)
        else:
            node.soil_moisture += random.randint(-1, 0)
            node.soil_moisture = max(20, min(70, node.soil_moisture))
        
        # Converti % in raw ADC (inversely proportional)
        node.soil_raw = int(3000 - (node.soil_moisture * 30))
    
    def _simulate_battery(self, node: SimNode):
        """Simula batteria"""
        hour = datetime.now().hour
        is_day = 6 <= hour <= 18
        
        # Ricarica solare
        if is_day and node.status == NodeStatus.ONLINE:
            node.is_charging = True
            node.solar_voltage = random.uniform(4.8, 5.5)
            charge_rate = random.uniform(0.5, 1.5)
            node.battery = min(100, node.battery + charge_rate)
        else:
            node.is_charging = False
            node.solar_voltage = 0.0
        
        # Consumo batteria
        if self.current_scenario in [Scenario.BATTERY_CRITICAL, Scenario.BATTERY_LOW]:
            # Scarica più velocemente
            discharge_rate = random.uniform(2, 5)
        else:
            discharge_rate = random.uniform(0.1, 0.3)
        
        if not node.is_charging:
            node.battery = max(0, node.battery - discharge_rate)
        
        # Aggiorna voltage (4.2V = 100%, 3.0V = 0%)
        node.battery_voltage = 3.0 + (node.battery / 100) * 1.2
        
        # Aggiorna stato nodo
        if node.battery <= self.sim_cfg.battery_critical:
            node.status = NodeStatus.ERROR
        elif node.battery <= self.sim_cfg.battery_warning:
            node.status = NodeStatus.WARNING
        else:
            node.status = NodeStatus.ONLINE
    
    def _simulate_connectivity(self, node: SimNode):
        """Simula connettività"""
        if self.current_scenario == Scenario.NODE_OFFLINE:
            # Alcuni nodi offline
            if random.random() < 0.3:
                node.status = NodeStatus.OFFLINE
        
        elif self.current_scenario == Scenario.MESH_DEGRADED:
            # Mesh degradato
            node.mesh_peers = max(0, node.mesh_peers - random.randint(0, 2))
            node.rssi = min(-30, node.rssi - random.randint(5, 15))
        
        else:
            # Variazione normale RSSI
            node.rssi += random.randint(-5, 5)
            node.rssi = max(-90, min(-30, node.rssi))
            
            # Mesh peers variabile
            if random.random() < 0.1:
                node.mesh_peers = max(0, min(6, node.mesh_peers + random.choice([-1, 0, 1])))
    
    def _apply_scenario(self):
        """Applica scenario corrente ai nodi"""
        
        # Scenari sicurezza
        if self.current_scenario == Scenario.SECURITY_PERSON:
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY and random.random() < 0.3:
                    self._send_security_event(node, Classification.PERSON, trigger_alarm=True)
        
        elif self.current_scenario == Scenario.SECURITY_ANIMAL_LARGE:
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY and random.random() < 0.4:
                    self._send_security_event(node, Classification.ANIMAL_LARGE)
        
        elif self.current_scenario == Scenario.SECURITY_ANIMAL_SMALL:
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY and random.random() < 0.5:
                    self._send_security_event(node, Classification.ANIMAL_SMALL)
        
        elif self.current_scenario == Scenario.SECURITY_TAMPER:
            # Tamper su un nodo casuale
            sec_nodes = [n for n in self.nodes.values() if n.node_type == NodeType.SECURITY]
            if sec_nodes and random.random() < 0.2:
                node = random.choice(sec_nodes)
                self._send_security_event(node, Classification.TAMPER, trigger_alarm=True)
        
        elif self.current_scenario == Scenario.ALARM_MULTIPLE:
            # Allarmi multipli contemporanei
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY and random.random() < 0.6:
                    cls = random.choice([Classification.PERSON, Classification.PERSON, 
                                       Classification.ANIMAL_LARGE])
                    self._send_security_event(node, cls, trigger_alarm=True)
    
    # ========================================================================
    # Threading Loops
    # ========================================================================
    
    def _heartbeat_loop(self):
        """Loop heartbeat"""
        while self.running:
            with self.lock:
                for node in self.nodes.values():
                    if node.status != NodeStatus.OFFLINE:
                        node.uptime += self.sim_cfg.heartbeat_interval
                        self._send_heartbeat(node)
            
            time.sleep(self.sim_cfg.heartbeat_interval)
    
    def _sensor_loop(self):
        """Loop sensori"""
        while self.running:
            with self.lock:
                for node in self.nodes.values():
                    if node.status != NodeStatus.OFFLINE:
                        self._simulate_sensors(node)
                        self._simulate_battery(node)
                        self._simulate_connectivity(node)
                        
                        if node.node_type == NodeType.AMBIENT:
                            self._send_sensors(node)
            
            time.sleep(self.sim_cfg.sensor_interval)
    
    def _security_loop(self):
        """Loop sicurezza"""
        while self.running:
            with self.lock:
                self._apply_scenario()
                
                # Eventi random in modalità normale
                if self.current_scenario == Scenario.NORMAL:
                    for node in self.nodes.values():
                        if node.node_type == NodeType.SECURITY and node.status == NodeStatus.ONLINE:
                            if random.random() < self.sim_cfg.motion_probability:
                                cls = random.choices(
                                    [Classification.ANIMAL_SMALL, Classification.ANIMAL_LARGE,
                                     Classification.PERSON, Classification.UNKNOWN],
                                    weights=[0.5, 0.3, 0.1, 0.1]
                                )[0]
                                trigger = (cls == Classification.PERSON and 
                                         random.random() < self.sim_cfg.alarm_probability)
                                self._send_security_event(node, cls, trigger_alarm=trigger)
            
            time.sleep(self.sim_cfg.security_check_interval)
    
    # ========================================================================
    # Control Methods
    # ========================================================================
    
    def connect(self) -> bool:
        """Connetti a MQTT broker"""
        try:
            logger.info(f"🔌 Connessione a {self.mqtt_cfg.broker}:{self.mqtt_cfg.port}...")
            
            client_id = f"simulator-{random.randint(1000,9999)}"
            self.client = mqtt.Client(client_id=client_id)
            
            self.client.username_pw_set(self.mqtt_cfg.username, self.mqtt_cfg.password)
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            self.client.connect(
                self.mqtt_cfg.broker,
                self.mqtt_cfg.port,
                self.mqtt_cfg.keepalive
            )
            
            self.client.loop_start()
            
            # Attendi connessione
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if self.connected:
                logger.info("✅ Connessione MQTT stabilita")
            else:
                logger.error("❌ Timeout connessione MQTT")
            
            return self.connected
        
        except Exception as e:
            logger.error(f"❌ Errore connessione: {e}")
            return False
    
    def start(self) -> bool:
        """Avvia simulatore"""
        if not self.connected and not self.connect():
            return False
        
        self.running = True
        self.stats.start_time = datetime.now()
        
        # Invia heartbeat iniziale
        logger.info("📤 Invio heartbeat iniziale...")
        for node in self.nodes.values():
            self._send_heartbeat(node)
        
        # Avvia thread
        threading.Thread(target=self._heartbeat_loop, daemon=True, name="heartbeat").start()
        threading.Thread(target=self._sensor_loop, daemon=True, name="sensors").start()
        threading.Thread(target=self._security_loop, daemon=True, name="security").start()
        
        logger.info(f"▶️ Simulazione avviata - {len(self.nodes)} nodi")
        return True
    
    def stop(self):
        """Ferma simulatore"""
        logger.info("⏹️ Arresto simulatore...")
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        logger.info("✅ Simulatore fermato")
    
    def set_scenario(self, scenario: Scenario):
        """Imposta scenario"""
        with self.lock:
            # Reset stati
            for node in self.nodes.values():
                if node.status == NodeStatus.OFFLINE:
                    node.status = NodeStatus.ONLINE
            
            self.current_scenario = scenario
            logger.info(f"🎬 Scenario: {scenario.value}")
    
    # ========================================================================
    # Test Suite
    # ========================================================================
    
    def run_full_test_suite(self):
        """Esegue suite completa di test"""
        logger.info("\n" + "="*60)
        logger.info("🧪 AVVIO TEST SUITE COMPLETA")
        logger.info("="*60)
        
        test_scenarios = [
            (Scenario.NORMAL, "Operazione normale", 15),
            (Scenario.SENSOR_ALERT_TEMP_HIGH, "Temperatura alta", 20),
            (Scenario.SENSOR_ALERT_TEMP_LOW, "Temperatura bassa", 20),
            (Scenario.SENSOR_ALERT_HUMIDITY_HIGH, "Umidità alta", 20),
            (Scenario.SENSOR_ALERT_SOIL_DRY, "Suolo secco", 20),
            (Scenario.SECURITY_PERSON, "Rilevamento persona", 15),
            (Scenario.SECURITY_ANIMAL_LARGE, "Animale grande", 15),
            (Scenario.SECURITY_ANIMAL_SMALL, "Animale piccolo", 15),
            (Scenario.SECURITY_TAMPER, "Manomissione", 10),
            (Scenario.BATTERY_LOW, "Batteria scarica", 15),
            (Scenario.ALARM_MULTIPLE, "Allarmi multipli", 15),
            (Scenario.STORM_SIMULATION, "Simulazione tempesta", 20),
            (Scenario.NIGHT_MODE, "Modalità notturna", 15),
        ]
        
        for scenario, description, duration in test_scenarios:
            if not self.running:
                break
            
            logger.info(f"\n{'─'*60}")
            logger.info(f"🔬 Test: {description}")
            logger.info(f"{'─'*60}")
            
            self.set_scenario(scenario)
            time.sleep(duration)
            
            self.test_results.append((description, True, "OK"))
        
        # Reset a normale
        self.set_scenario(Scenario.NORMAL)
        
        logger.info("\n" + "="*60)
        logger.info("✅ TEST SUITE COMPLETATA")
        logger.info("="*60)
        self._print_test_results()
    
    def run_stress_test(self, duration: int = 60):
        """Test di stress - molti eventi contemporanei"""
        logger.info(f"\n⚡ STRESS TEST - {duration}s")
        logger.info("Generazione eventi ad alta frequenza...")
        
        start = time.time()
        event_count = 0
        
        while time.time() - start < duration and self.running:
            with self.lock:
                # Eventi sensori
                for node in [n for n in self.nodes.values() if n.node_type == NodeType.AMBIENT]:
                    self._send_sensors(node)
                    event_count += 1
                
                # Eventi sicurezza
                for node in [n for n in self.nodes.values() if n.node_type == NodeType.SECURITY]:
                    cls = random.choice(list(Classification))
                    self._send_security_event(node, cls)
                    event_count += 1
            
            time.sleep(0.5)
        
        logger.info(f"✅ Stress test completato: {event_count} eventi in {duration}s")
        logger.info(f"   Rate: {event_count/duration:.1f} eventi/secondo")
    
    # ========================================================================
    # Actions
    # ========================================================================
    
    def trigger_alarm(self, node_id: str = None, classification: Classification = None):
        """Trigger manuale allarme"""
        with self.lock:
            if node_id:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    if node.node_type == NodeType.SECURITY:
                        cls = classification or Classification.PERSON
                        self._send_security_event(node, cls, trigger_alarm=True)
                        logger.info(f"🚨 Allarme manuale: {node_id}")
                else:
                    logger.warning(f"Nodo non trovato: {node_id}")
            else:
                # Tutti i nodi sicurezza
                for node in self.nodes.values():
                    if node.node_type == NodeType.SECURITY:
                        cls = classification or Classification.PERSON
                        self._send_security_event(node, cls, trigger_alarm=True)
                logger.info("🚨 Allarme manuale su tutti i nodi sicurezza")
    
    def set_node_offline(self, node_id: str):
        """Porta nodo offline"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].status = NodeStatus.OFFLINE
                logger.info(f"🔴 Nodo offline: {node_id}")
    
    def set_node_online(self, node_id: str):
        """Porta nodo online"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].status = NodeStatus.ONLINE
                logger.info(f"🟢 Nodo online: {node_id}")
    
    def arm_all(self):
        """Arma tutti i nodi sicurezza"""
        with self.lock:
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY:
                    node.is_armed = True
            logger.info("🔒 Tutti i nodi armati")
    
    def disarm_all(self):
        """Disarma tutti i nodi sicurezza"""
        with self.lock:
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY:
                    node.is_armed = False
            logger.info("🔓 Tutti i nodi disarmati")
    
    # ========================================================================
    # Display & Reporting
    # ========================================================================
    
    def print_status(self):
        """Stampa stato completo"""
        print("\n" + "="*70)
        print(f"📊 STATO SIMULATORE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Connessione
        mqtt_status = "✅ Connesso" if self.connected else "❌ Disconnesso"
        print(f"MQTT: {mqtt_status} ({self.mqtt_cfg.broker}:{self.mqtt_cfg.port})")
        print(f"Scenario: {self.current_scenario.value}")
        
        # Statistiche
        print(f"\n📈 Statistiche:")
        stats = self.stats.to_dict()
        print(f"  Runtime: {stats['runtime_seconds']}s")
        print(f"  Heartbeats: {stats['heartbeats']}")
        print(f"  Letture sensori: {stats['sensor_readings']}")
        print(f"  Eventi sicurezza: {stats['security_events']}")
        print(f"  Allarmi: {stats['alarms']}")
        print(f"  Comandi ricevuti: {stats['commands_received']}")
        
        if stats['classifications']:
            print(f"\n  Classificazioni:")
            for cls, count in stats['classifications'].items():
                print(f"    {cls}: {count}")
        
        # Nodi
        print(f"\n📡 Nodi ({len(self.nodes)}):")
        for node_id, node in sorted(self.nodes.items()):
            icon = {
                NodeStatus.ONLINE: "🟢",
                NodeStatus.OFFLINE: "🔴",
                NodeStatus.WARNING: "🟡",
                NodeStatus.ERROR: "🔴",
                NodeStatus.MAINTENANCE: "🔧"
            }[node.status]
            
            type_icon = {
                NodeType.GATEWAY: "🌐",
                NodeType.AMBIENT: "🌡️",
                NodeType.SECURITY: "🛡️"
            }[node.node_type]
            
            info = f"{icon} {type_icon} {node_id}: {node.name}"
            info += f" | 🔋{node.battery}% ({node.battery_voltage:.1f}V)"
            
            if node.is_charging:
                info += f" ⚡"
            
            info += f" | 📶{node.rssi}dBm"
            
            if node.node_type == NodeType.AMBIENT:
                info += f" | 🌡️{node.temperature:.1f}°C 💧{node.humidity:.0f}% 🌱{node.soil_moisture}%"
            
            if node.node_type == NodeType.SECURITY:
                armed_icon = "🔒" if node.is_armed else "🔓"
                info += f" | {armed_icon}"
                if node.motion_count > 0:
                    info += f" | 👁️{node.motion_count} eventi"
            
            print(f"  {info}")
            print(f"    Loc: {node.location} | Msgs: {node.messages_sent} | Err: {node.errors}")
        
        print("="*70)
    
    def _print_test_results(self):
        """Stampa risultati test"""
        print("\n" + "="*60)
        print("📋 RISULTATI TEST")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            icon = "✅" if success else "❌"
            print(f"{icon} {test_name}: {message}")
        
        print(f"\n{'─'*60}")
        print(f"Totale: {passed}/{total} test passati ({100*passed/total:.0f}%)")
        print("="*60)
    
    def export_statistics(self, filename: str = "simulator_stats.json"):
        """Esporta statistiche in JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'scenario': self.current_scenario.value,
            'statistics': self.stats.to_dict(),
            'nodes': {nid: n.to_dict() for nid, n in self.nodes.items()},
            'test_results': [
                {'test': name, 'success': success, 'message': msg}
                for name, success, msg in self.test_results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"📊 Statistiche esportate: {filename}")


# ============================================================================
# Interactive Menu
# ============================================================================

def print_menu():
    """Stampa menu interattivo"""
    print("\n" + "─"*70)
    print("🎮 COMANDI DISPONIBILI")
    print("─"*70)
    print("📊 Status & Info:")
    print("  s, status       - Mostra stato completo")
    print("  stats           - Esporta statistiche JSON")
    print("\n🎬 Scenari:")
    print("  n, normal       - Operazione normale")
    print("  th, temp_high   - Temperatura alta")
    print("  tl, temp_low    - Temperatura bassa")
    print("  hh, hum_high    - Umidità alta")
    print("  sd, soil_dry    - Suolo secco")
    print("  p, person       - Rilevamento persona")
    print("  al, animal_lg   - Animale grande")
    print("  as, animal_sm   - Animale piccolo")
    print("  tm, tamper      - Manomissione")
    print("  bc, batt_crit   - Batteria critica")
    print("  bl, batt_low    - Batteria scarica")
    print("  off, offline    - Nodi offline")
    print("  md, mesh_deg    - Mesh degradato")
    print("  am, alarm_mult  - Allarmi multipli")
    print("  st, storm       - Tempesta")
    print("  nt, night       - Modalità notturna")
    print("  gh, greenhouse  - Modalità serra")
    print("\n🧪 Test:")
    print("  ft, full_test   - Test suite completa")
    print("  stress [secs]   - Stress test")
    print("\n🎯 Azioni:")
    print("  !, alarm        - Trigger allarme")
    print("  arm             - Arma tutti")
    print("  disarm          - Disarma tutti")
    print("\n❓ Altro:")
    print("  h, help         - Mostra questo menu")
    print("  q, quit         - Esci")
    print("─"*70)


def interactive_mode(sim: Simulator):
    """Modalità interattiva"""
    print_menu()
    
    while sim.running:
        try:
            cmd = input("\n🎮 > ").strip().lower()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Quit
            if cmd in ["q", "quit", "exit"]:
                break
            
            # Status
            elif cmd in ["s", "status"]:
                sim.print_status()
            
            elif cmd == "stats":
                sim.export_statistics()
                print("✅ Statistiche esportate in simulator_stats.json")
            
            # Scenari normali
            elif cmd in ["n", "normal"]:
                sim.set_scenario(Scenario.NORMAL)
            
            # Scenari temperatura
            elif cmd in ["th", "temp_high"]:
                sim.set_scenario(Scenario.SENSOR_ALERT_TEMP_HIGH)
            
            elif cmd in ["tl", "temp_low"]:
                sim.set_scenario(Scenario.SENSOR_ALERT_TEMP_LOW)
            
            # Scenari umidità
            elif cmd in ["hh", "hum_high"]:
                sim.set_scenario(Scenario.SENSOR_ALERT_HUMIDITY_HIGH)
            
            elif cmd in ["hl", "hum_low"]:
                sim.set_scenario(Scenario.SENSOR_ALERT_HUMIDITY_LOW)
            
            # Suolo
            elif cmd in ["sd", "soil_dry"]:
                sim.set_scenario(Scenario.SENSOR_ALERT_SOIL_DRY)
            
            # Sicurezza
            elif cmd in ["p", "person"]:
                sim.set_scenario(Scenario.SECURITY_PERSON)
            
            elif cmd in ["al", "animal_lg", "animal_large"]:
                sim.set_scenario(Scenario.SECURITY_ANIMAL_LARGE)
            
            elif cmd in ["as", "animal_sm", "animal_small"]:
                sim.set_scenario(Scenario.SECURITY_ANIMAL_SMALL)
            
            elif cmd in ["tm", "tamper"]:
                sim.set_scenario(Scenario.SECURITY_TAMPER)
            
            # Batteria
            elif cmd in ["bc", "batt_crit"]:
                sim.set_scenario(Scenario.BATTERY_CRITICAL)
            
            elif cmd in ["bl", "batt_low"]:
                sim.set_scenario(Scenario.BATTERY_LOW)
            
            # Connettività
            elif cmd in ["off", "offline"]:
                sim.set_scenario(Scenario.NODE_OFFLINE)
            
            elif cmd in ["md", "mesh_deg"]:
                sim.set_scenario(Scenario.MESH_DEGRADED)
            
            # Allarmi
            elif cmd in ["am", "alarm_mult"]:
                sim.set_scenario(Scenario.ALARM_MULTIPLE)
            
            # Ambiente
            elif cmd in ["st", "storm"]:
                sim.set_scenario(Scenario.STORM_SIMULATION)
            
            elif cmd in ["nt", "night"]:
                sim.set_scenario(Scenario.NIGHT_MODE)
            
            elif cmd in ["gh", "greenhouse"]:
                sim.set_scenario(Scenario.GREENHOUSE_MODE)
            
            # Test
            elif cmd in ["ft", "full_test"]:
                threading.Thread(target=sim.run_full_test_suite, daemon=True).start()
                print("🧪 Test suite avviata in background...")
            
            elif cmd == "stress":
                duration = int(args[0]) if args else 60
                threading.Thread(target=sim.run_stress_test, args=(duration,), daemon=True).start()
                print(f"⚡ Stress test avviato ({duration}s)...")
            
            # Azioni
            elif cmd in ["!", "alarm", "trigger"]:
                sim.trigger_alarm()
            
            elif cmd == "arm":
                sim.arm_all()
            
            elif cmd == "disarm":
                sim.disarm_all()
            
            # Help
            elif cmd in ["h", "help", "?"]:
                print_menu()
            
            else:
                print(f"❌ Comando sconosciuto: {cmd}")
                print("   Digita 'help' per vedere i comandi disponibili")
        
        except (KeyboardInterrupt, EOFError):
            print("\n⚠️ Interruzione...")
            break
        
        except Exception as e:
            logger.error(f"Errore comando: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description="AgriSecure IoT Simulator v4 - Enhanced Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi d'uso:
  
  # Modalità interattiva (default)
  python simulator_enhanced.py
  
  # Auto mode con scenario specifico
  python simulator_enhanced.py --auto --scenario person --duration 60
  
  # Full test suite
  python simulator_enhanced.py --auto --scenario full_test
  
  # Stress test
  python simulator_enhanced.py --auto --scenario stress_test --duration 120
  
  # MQTT custom
  python simulator_enhanced.py --broker mqtt.example.com --port 8883 --username user --password pass
        """
    )
    
    # MQTT options
    parser.add_argument("--broker", default="localhost", help="MQTT broker hostname")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", default="agrisecure", help="MQTT username")
    parser.add_argument("--password", default="mqtt_secure_password", help="MQTT password")
    
    # Simulation options
    parser.add_argument("--auto", action="store_true", help="Auto mode (non-interactive)")
    parser.add_argument("--scenario", default="normal", help="Initial scenario")
    parser.add_argument("--duration", type=int, default=0, help="Duration in seconds (0=infinite)")
    
    # Intervals
    parser.add_argument("--heartbeat-interval", type=int, default=30, help="Heartbeat interval (sec)")
    parser.add_argument("--sensor-interval", type=int, default=60, help="Sensor reading interval (sec)")
    
    # Output
    parser.add_argument("--export-stats", action="store_true", help="Export statistics at end")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Setup logging
    logging.getLogger('AgriSecure-Sim').setLevel(getattr(logging, args.log_level))
    
    # Banner
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║       🌿 AgriSecure IoT Simulator v4 - Enhanced 🌿           ║
    ║                                                               ║
    ║  Test completo MQTT e Dashboard                               ║
    ║  20+ scenari | Test automatici | Stress test                  ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Configurazione
    mqtt_cfg = MQTTConfig(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
    )
    
    sim_cfg = SimConfig(
        heartbeat_interval=args.heartbeat_interval,
        sensor_interval=args.sensor_interval,
    )
    
    # Crea simulatore
    sim = Simulator(mqtt_cfg=mqtt_cfg, sim_cfg=sim_cfg)
    
    # Imposta scenario iniziale
    try:
        initial_scenario = Scenario(args.scenario)
        sim.set_scenario(initial_scenario)
    except ValueError:
        logger.warning(f"Scenario sconosciuto: {args.scenario}, uso 'normal'")
        sim.set_scenario(Scenario.NORMAL)
    
    # Signal handler
    signal.signal(signal.SIGINT, lambda s, f: sim.stop() or sys.exit(0))
    
    # Avvia simulatore
    if not sim.start():
        logger.error("❌ Impossibile avviare simulatore")
        sys.exit(1)
    
    try:
        if args.auto:
            # Modalità automatica
            logger.info(f"🤖 Modalità automatica" + 
                       (f" ({args.duration}s)" if args.duration else ""))
            
            # Test speciali
            if args.scenario == "full_test":
                sim.run_full_test_suite()
            elif args.scenario == "stress_test":
                sim.run_stress_test(args.duration or 60)
            else:
                # Run normale con durata
                if args.duration:
                    time.sleep(args.duration)
                else:
                    while sim.running:
                        time.sleep(1)
        else:
            # Modalità interattiva
            interactive_mode(sim)
    
    finally:
        sim.stop()
        
        # Export statistics
        if args.export_stats:
            sim.export_statistics()
        
        # Stampa statistiche finali
        print("\n" + "="*70)
        print("📊 STATISTICHE FINALI")
        print("="*70)
        stats = sim.stats.to_dict()
        print(json.dumps(stats, indent=2))
        print("="*70)
        
        logger.info("👋 Simulatore terminato")


if __name__ == "__main__":
    main()
