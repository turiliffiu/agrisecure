#!/usr/bin/env python3
"""
AgriSecure IoT Simulator v2
===========================
Simula nodi IoT per testare backend e frontend senza hardware reale.
Formato dati compatibile con mqtt_subscriber.

Uso:
    python simulator.py                    # Avvia simulazione interattiva
    python simulator.py --auto             # Avvia simulazione automatica
    python simulator.py --scenario alarm   # Avvia scenario specifico

Scenari:
    - normal: Funzionamento normale
    - alarm: Simula intrusione
    - sensor_alert: Alert sensori
    - node_failure: Guasto nodo
    - battery_low: Batterie scariche
    - full_test: Ciclo completo

Autore: AgriSecure Team
Versione: 2.0
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
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ Errore: paho-mqtt non installato")
    print("   Installa con: pip install paho-mqtt")
    sys.exit(1)


# ============================================================================
# Configurazione
# ============================================================================

@dataclass
class MQTTConfig:
    broker: str = "localhost"
    port: int = 1883
    username: str = "agrisecure"
    password: str = "mqtt_secure_password"
    base_topic: str = "agrisecure"


@dataclass
class SimConfig:
    heartbeat_interval: int = 30
    sensor_interval: int = 60
    security_check_interval: int = 5
    motion_probability: float = 0.02
    alarm_probability: float = 0.3


# ============================================================================
# Enums
# ============================================================================

class NodeType(Enum):
    GATEWAY = "GW"
    AMBIENT = "AMB"
    SECURITY = "SEC"


class Classification(Enum):
    NONE = "none"
    PERSON = "person"
    ANIMAL_LARGE = "animal_lg"
    ANIMAL_SMALL = "animal_sm"
    UNKNOWN = "unknown"
    TAMPER = "tamper"


# ============================================================================
# Nodo Simulato
# ============================================================================

@dataclass
class SimNode:
    node_id: str
    node_type: NodeType
    name: str
    lat: float = 37.5
    lon: float = 14.0
    
    # Runtime
    status: str = "online"
    battery: int = 100
    rssi: int = -45
    uptime: int = 0
    mesh_peers: int = 2
    is_armed: bool = True
    
    # Sensori AMB
    temperature: float = 22.0
    humidity: float = 65.0
    pressure: float = 1013.0
    light: int = 5000
    soil_moisture: int = 45
    soil_raw: int = 1800
    
    # Security SEC
    last_motion: Optional[datetime] = None


# ============================================================================
# Simulatore
# ============================================================================

class Simulator:
    def __init__(self, mqtt_cfg: MQTTConfig = None, sim_cfg: SimConfig = None):
        self.mqtt_cfg = mqtt_cfg or MQTTConfig()
        self.sim_cfg = sim_cfg or SimConfig()
        
        self.client = mqtt.Client(client_id=f"simulator-{random.randint(1000,9999)}")
        self.client.username_pw_set(self.mqtt_cfg.username, self.mqtt_cfg.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        self.connected = False
        self.running = False
        self.scenario = "normal"
        self.lock = threading.Lock()
        
        self.nodes: Dict[str, SimNode] = {}
        self._init_nodes()
        
        self.stats = {
            "heartbeats": 0,
            "sensor_readings": 0,
            "security_events": 0,
            "alarms": 0,
        }
    
    def _init_nodes(self):
        """Crea nodi di default"""
        # Gateway
        self.nodes["GW-001"] = SimNode("GW-001", NodeType.GATEWAY, "Gateway Principale", battery=100)
        
        # Ambientali
        self.nodes["AMB-001"] = SimNode("AMB-001", NodeType.AMBIENT, "Sensore Campo Nord", battery=85)
        self.nodes["AMB-002"] = SimNode("AMB-002", NodeType.AMBIENT, "Sensore Campo Sud", battery=72)
        self.nodes["AMB-003"] = SimNode("AMB-003", NodeType.AMBIENT, "Sensore Serra", battery=90, temperature=28.0, humidity=80.0)
        
        # Sicurezza
        self.nodes["SEC-001"] = SimNode("SEC-001", NodeType.SECURITY, "Sicurezza Ingresso", battery=95)
        self.nodes["SEC-002"] = SimNode("SEC-002", NodeType.SECURITY, "Sicurezza Est", battery=88)
        self.nodes["SEC-003"] = SimNode("SEC-003", NodeType.SECURITY, "Sicurezza Ovest", battery=78)
    
    # ========================================================================
    # MQTT
    # ========================================================================
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print(f"✅ Connesso a MQTT {self.mqtt_cfg.broker}:{self.mqtt_cfg.port}")
            client.subscribe(f"{self.mqtt_cfg.base_topic}/+/command")
        else:
            print(f"❌ Connessione fallita: {rc}")
    
    def _on_message(self, client, userdata, msg):
        try:
            parts = msg.topic.split("/")
            if len(parts) >= 3 and parts[2] == "command":
                node_id = parts[1]
                cmd = json.loads(msg.payload.decode())
                self._handle_cmd(node_id, cmd)
        except Exception as e:
            print(f"Errore comando: {e}")
    
    def _handle_cmd(self, node_id: str, cmd: dict):
        action = cmd.get("command", "")
        print(f"📥 Comando {node_id}: {action}")
        
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if action == "reboot":
                node.uptime = 0
            elif action == "arm":
                node.is_armed = True
            elif action == "disarm":
                node.is_armed = False
    
    def _publish(self, topic: str, data: dict) -> bool:
        if not self.connected:
            return False
        try:
            full_topic = f"{self.mqtt_cfg.base_topic}/{topic}"
            self.client.publish(full_topic, json.dumps(data), qos=1)
            return True
        except:
            return False
    
    # ========================================================================
    # Invio Dati (formato compatibile con mqtt_subscriber)
    # ========================================================================
    
    def _send_heartbeat(self, node: SimNode):
        """Heartbeat - formato atteso da _process_status()"""
        data = {
            "node_id": node.node_id,
            "type": node.node_type.value,  # GW, AMB, SEC
            "timestamp": int(time.time()),
            "uptime": node.uptime,
            "battery": node.battery,
            "rssi": node.rssi,
            "signal": node.rssi,
            "mesh_peers": node.mesh_peers,
            "firmware": "1.0.0",
            "heap_free": random.randint(100000, 200000),
        }
        
        if self._publish(f"{node.node_id}/status", data):
            self.stats["heartbeats"] += 1
    
    def _send_sensors(self, node: SimNode):
        """Dati sensori - formato atteso da _process_sensor_data()"""
        if node.node_type != NodeType.AMBIENT:
            return
        
        # Formato piatto come atteso dal subscriber
        data = {
            "node_id": node.node_id,
            "timestamp": int(time.time()),
            "temperature": round(node.temperature, 2),
            "humidity": round(node.humidity, 2),
            "pressure": round(node.pressure, 2),
            "light": node.light,
            "soil_moisture": node.soil_moisture,
            "soil_raw": node.soil_raw,
        }
        
        if self._publish(f"{node.node_id}/sensors/ambient", data):
            self.stats["sensor_readings"] += 1
    
    def _send_security_event(self, node: SimNode, classification: Classification, trigger_alarm: bool = False):
        """Evento sicurezza - formato atteso da _process_security_event()"""
        if node.node_type != NodeType.SECURITY:
            return
        
        priority = "CRITICAL" if classification == Classification.PERSON else "MEDIUM"
        
        # Formato piatto come atteso dal subscriber
        data = {
            "node_id": node.node_id,
            "timestamp": int(time.time()),
            "classification": classification.value,
            "priority": priority,
            "pir_main": True,
            "pir_backup": random.random() > 0.3,
            "tamper": classification == Classification.TAMPER,
            "accel_x": round(random.uniform(-0.1, 0.1), 3),
            "accel_y": round(random.uniform(-0.1, 0.1), 3),
            "accel_z": round(random.uniform(0.95, 1.05), 3),
        }
        
        if self._publish(f"{node.node_id}/security/event", data):
            self.stats["security_events"] += 1
            if trigger_alarm and node.is_armed:
                self.stats["alarms"] += 1
                print(f"🚨 ALLARME: {node.node_id} - {classification.value}")
    
    # ========================================================================
    # Simulazione
    # ========================================================================
    
    def _simulate_sensors(self, node: SimNode):
        """Simula variazioni realistiche"""
        hour = datetime.now().hour
        is_day = 6 <= hour <= 20
        
        # Temperatura
        temp_mod = 3.0 if 12 <= hour <= 16 else -2.0 if 0 <= hour <= 6 else 0
        node.temperature = 22.0 + temp_mod + random.uniform(-2, 2)
        
        # Umidità
        node.humidity = max(20, min(95, 65 + random.uniform(-8, 8)))
        
        # Pressione
        node.pressure = 1013 + random.uniform(-5, 5)
        
        # Luce
        if is_day:
            progress = (hour - 6) / 14
            factor = 1 - abs(progress - 0.5) * 2
            node.light = int(80000 * factor * random.uniform(0.7, 1.0))
        else:
            node.light = random.randint(0, 10)
        
        # Suolo
        node.soil_moisture = max(5, min(95, node.soil_moisture + random.uniform(-1, 1)))
        node.soil_raw = int(node.soil_moisture * 40.95)
    
    def _simulate_battery(self, node: SimNode):
        """Simula scarica/ricarica"""
        hour = datetime.now().hour
        is_day = 6 <= hour <= 18
        
        if is_day and node.battery < 100:
            node.battery = min(100, node.battery + random.uniform(0.1, 0.3))
        elif not is_day:
            node.battery = max(0, node.battery - random.uniform(0.01, 0.05))
        
        node.battery = int(node.battery)
    
    def _apply_scenario(self):
        """Applica scenario attivo"""
        if self.scenario == "alarm":
            # Alta probabilità allarmi
            for node in self.nodes.values():
                if node.node_type == NodeType.SECURITY and node.is_armed:
                    if random.random() < 0.3:
                        cls = random.choice([Classification.PERSON, Classification.ANIMAL_LARGE])
                        self._send_security_event(node, cls, trigger_alarm=cls == Classification.PERSON)
        
        elif self.scenario == "sensor_alert":
            # Valori fuori range
            for node in self.nodes.values():
                if node.node_type == NodeType.AMBIENT:
                    if random.random() < 0.5:
                        node.temperature = random.uniform(40, 48)
                    else:
                        node.soil_moisture = random.randint(3, 10)
        
        elif self.scenario == "node_failure":
            # Un nodo offline
            node = random.choice([n for n in self.nodes.values() if n.node_type != NodeType.GATEWAY])
            node.status = "offline"
            print(f"⚠️  {node.node_id} OFFLINE")
        
        elif self.scenario == "battery_low":
            # Batterie basse
            for node in self.nodes.values():
                if node.node_type != NodeType.GATEWAY:
                    node.battery = random.randint(5, 18)
    
    # ========================================================================
    # Thread Loops
    # ========================================================================
    
    def _heartbeat_loop(self):
        while self.running:
            with self.lock:
                for node in self.nodes.values():
                    if node.status == "online":
                        node.uptime += self.sim_cfg.heartbeat_interval
                        self._send_heartbeat(node)
            time.sleep(self.sim_cfg.heartbeat_interval)
    
    def _sensor_loop(self):
        while self.running:
            with self.lock:
                for node in self.nodes.values():
                    if node.status == "online":
                        self._simulate_sensors(node)
                        self._simulate_battery(node)
                        if node.node_type == NodeType.AMBIENT:
                            self._send_sensors(node)
            time.sleep(self.sim_cfg.sensor_interval)
    
    def _security_loop(self):
        while self.running:
            with self.lock:
                self._apply_scenario()
                
                # Eventi casuali in scenario normal
                if self.scenario == "normal":
                    for node in self.nodes.values():
                        if node.node_type == NodeType.SECURITY and node.status == "online":
                            if random.random() < self.sim_cfg.motion_probability:
                                cls = random.choices(
                                    [Classification.ANIMAL_SMALL, Classification.ANIMAL_LARGE, 
                                     Classification.PERSON, Classification.UNKNOWN],
                                    weights=[0.5, 0.3, 0.1, 0.1]
                                )[0]
                                trigger = cls == Classification.PERSON and random.random() < 0.3
                                self._send_security_event(node, cls, trigger_alarm=trigger)
            
            time.sleep(self.sim_cfg.security_check_interval)
    
    def _full_test_loop(self):
        scenarios = ["normal", "sensor_alert", "battery_low", "alarm", "normal"]
        for s in scenarios:
            if not self.running:
                break
            print(f"\n🔄 Test: {s}")
            self.scenario = s
            time.sleep(60)
        self.scenario = "normal"
        print("✅ Full test completato")
    
    # ========================================================================
    # Controllo
    # ========================================================================
    
    def connect(self) -> bool:
        try:
            print(f"🔌 Connessione a {self.mqtt_cfg.broker}:{self.mqtt_cfg.port}...")
            self.client.connect(self.mqtt_cfg.broker, self.mqtt_cfg.port, 60)
            self.client.loop_start()
            
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            return self.connected
        except Exception as e:
            print(f"❌ Errore: {e}")
            return False
    
    def start(self):
        if not self.connected and not self.connect():
            return False
        
        self.running = True
        
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._sensor_loop, daemon=True).start()
        threading.Thread(target=self._security_loop, daemon=True).start()
        
        print(f"▶️  Simulazione avviata - {len(self.nodes)} nodi")
        return True
    
    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("⏹️  Fermato")
    
    def set_scenario(self, s: str):
        valid = ["normal", "alarm", "sensor_alert", "node_failure", "battery_low", "full_test"]
        if s not in valid:
            print(f"❌ Scenario invalido. Validi: {', '.join(valid)}")
            return
        
        # Reset nodi
        for node in self.nodes.values():
            node.status = "online"
        
        self.scenario = s
        print(f"🎬 Scenario: {s}")
        
        if s == "full_test":
            threading.Thread(target=self._full_test_loop, daemon=True).start()
    
    def trigger_alarm(self, node_id: str = None):
        with self.lock:
            targets = [self.nodes.get(node_id)] if node_id else [
                n for n in self.nodes.values() if n.node_type == NodeType.SECURITY
            ]
            for node in targets:
                if node and node.node_type == NodeType.SECURITY:
                    self._send_security_event(node, Classification.PERSON, trigger_alarm=True)
    
    def print_status(self):
        print("\n" + "="*60)
        print(f"📊 STATO - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        print(f"Scenario: {self.scenario} | MQTT: {'✅' if self.connected else '❌'}")
        print(f"\nStats: HB={self.stats['heartbeats']} | Sens={self.stats['sensor_readings']} | Sec={self.stats['security_events']} | Allarmi={self.stats['alarms']}")
        print(f"\n📡 Nodi:")
        for n in self.nodes.values():
            icon = "🟢" if n.status == "online" else "🔴"
            t = "🌐" if n.node_type == NodeType.GATEWAY else "🌡️" if n.node_type == NodeType.AMBIENT else "🛡️"
            info = f"{icon} {t} {n.node_id}: {n.name} | 🔋{n.battery}%"
            if n.node_type == NodeType.AMBIENT:
                info += f" | {n.temperature:.1f}°C {n.humidity:.0f}%"
            elif n.node_type == NodeType.SECURITY:
                info += f" | {'🔒' if n.is_armed else '🔓'}"
            print(f"  {info}")
        print("="*60)


# ============================================================================
# Menu Interattivo
# ============================================================================

def menu():
    print("\n" + "-"*40)
    print("🎮 COMANDI:")
    print("-"*40)
    print("  s = stato     n = normal    a = alarm")
    print("  e = sensor    f = failure   b = battery")
    print("  t = full_test ! = trigger   q = quit")
    print("-"*40)


def interactive(sim: Simulator):
    menu()
    while sim.running:
        try:
            cmd = input("\n> ").strip().lower()
            if cmd in ["q", "quit"]:
                break
            elif cmd in ["s", "status"]:
                sim.print_status()
            elif cmd in ["n", "normal"]:
                sim.set_scenario("normal")
            elif cmd in ["a", "alarm"]:
                sim.set_scenario("alarm")
            elif cmd in ["e", "sensor"]:
                sim.set_scenario("sensor_alert")
            elif cmd in ["f", "failure"]:
                sim.set_scenario("node_failure")
            elif cmd in ["b", "battery"]:
                sim.set_scenario("battery_low")
            elif cmd in ["t", "test"]:
                sim.set_scenario("full_test")
            elif cmd in ["!", "trigger"]:
                sim.trigger_alarm()
            elif cmd in ["h", "help"]:
                menu()
            elif cmd:
                print("❌ Comando sconosciuto. 'h' per aiuto")
        except (KeyboardInterrupt, EOFError):
            break


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="AgriSecure Simulator v2")
    parser.add_argument("--auto", action="store_true", help="Modalità automatica")
    parser.add_argument("--duration", type=int, default=0, help="Durata (0=infinito)")
    parser.add_argument("--scenario", default="normal", help="Scenario iniziale")
    parser.add_argument("--broker", default="localhost", help="MQTT broker")
    parser.add_argument("--port", type=int, default=1883, help="MQTT port")
    parser.add_argument("--username", default="agrisecure", help="MQTT user")
    parser.add_argument("--password", default="mqtt_secure_password", help="MQTT pass")
    
    args = parser.parse_args()
    
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║         🌿 AgriSecure Simulator v2 🌿                 ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    mqtt_cfg = MQTTConfig(
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
    )
    
    sim = Simulator(mqtt_cfg=mqtt_cfg)
    sim.set_scenario(args.scenario)
    
    signal.signal(signal.SIGINT, lambda s, f: sim.stop() or sys.exit(0))
    
    if not sim.start():
        sys.exit(1)
    
    try:
        if args.auto:
            print(f"🤖 Auto mode" + (f" ({args.duration}s)" if args.duration else ""))
            if args.duration:
                time.sleep(args.duration)
            else:
                while sim.running:
                    time.sleep(1)
        else:
            interactive(sim)
    finally:
        sim.stop()
    
    print(f"\n📊 Finale: {sim.stats}")


if __name__ == "__main__":
    main()
