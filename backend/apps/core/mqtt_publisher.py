"""
AgriSecure IoT System - MQTT Publisher

Modulo per pubblicare comandi ai gateway IoT via MQTT
"""

import json
import logging
from django.conf import settings
import paho.mqtt.client as mqtt

logger = logging.getLogger('mqtt')

# Client singleton
_mqtt_client = None


def get_mqtt_client():
    """Ottiene o crea client MQTT singleton"""
    global _mqtt_client
    
    if _mqtt_client is None or not _mqtt_client.is_connected():
        config = settings.MQTT_CONFIG
        
        _mqtt_client = mqtt.Client(
            client_id=f"agrisecure-publisher-{id(_mqtt_client)}",
            protocol=mqtt.MQTTv5
        )
        
        if config.get('USER'):
            _mqtt_client.username_pw_set(
                config['USER'],
                config['PASSWORD']
            )
        
        try:
            _mqtt_client.connect(
                config['BROKER'],
                config['PORT'],
                config['KEEPALIVE']
            )
            _mqtt_client.loop_start()
            logger.info("MQTT Publisher connesso")
        except Exception as e:
            logger.error(f"Errore connessione MQTT Publisher: {e}")
            return None
    
    return _mqtt_client


def publish_command(node_id, command, params=None):
    """
    Pubblica un comando a un nodo specifico
    
    Args:
        node_id: ID del nodo destinatario o gateway
        command: Comando da eseguire (es. 'arm', 'test_siren')
        params: Parametri aggiuntivi (dict)
    
    Returns:
        bool: True se pubblicazione riuscita
    """
    client = get_mqtt_client()
    if not client:
        return False
    
    # Costruisci topic
    # Format: agrisecure/{gateway_id}/command
    topic = f"agrisecure/{node_id}/command"
    
    # Payload
    payload = {
        'command': command,
        'target': node_id,
        'params': params or {},
        'timestamp': int(__import__('time').time())
    }
    
    try:
        result = client.publish(
            topic,
            json.dumps(payload),
            qos=settings.MQTT_CONFIG['QOS']
        )
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Comando pubblicato: {command} -> {node_id}")
            return True
        else:
            logger.error(f"Errore pubblicazione: {result.rc}")
            return False
            
    except Exception as e:
        logger.error(f"Errore pubblicazione comando: {e}")
        return False


def publish_arm_command(mode, node_ids):
    """
    Pubblica comando di arma/disarma a più nodi
    
    Args:
        mode: Modalità armamento ('armed', 'disarmed', etc.)
        node_ids: Lista di node_id da comandare
    """
    client = get_mqtt_client()
    if not client:
        return False
    
    command = 'arm' if mode != 'disarmed' else 'disarm'
    
    payload = {
        'command': command,
        'mode': mode,
        'targets': node_ids,
        'timestamp': int(__import__('time').time())
    }
    
    # Pubblica su topic broadcast per tutti i gateway
    topic = "agrisecure/+/command"
    
    # Per ogni gateway, pubblica il comando
    from apps.nodes.models import Node, NodeType
    
    gateways = Node.objects.filter(
        node_type=NodeType.GATEWAY,
        is_active=True
    ).values_list('node_id', flat=True)
    
    success = True
    for gw_id in gateways:
        topic = f"agrisecure/{gw_id}/command"
        try:
            result = client.publish(
                topic,
                json.dumps(payload),
                qos=1
            )
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                success = False
                logger.error(f"Errore invio a {gw_id}")
        except Exception as e:
            logger.error(f"Errore invio comando arm a {gw_id}: {e}")
            success = False
    
    return success


def publish_config(node_id, config):
    """
    Pubblica nuova configurazione a un nodo
    
    Args:
        node_id: ID del nodo
        config: Dict con la configurazione
    """
    client = get_mqtt_client()
    if not client:
        return False
    
    topic = f"agrisecure/{node_id}/config"
    
    payload = {
        'command': 'config_update',
        'config': config,
        'timestamp': int(__import__('time').time())
    }
    
    try:
        result = client.publish(
            topic,
            json.dumps(payload),
            qos=1,
            retain=True  # Retained per quando il nodo si riconnette
        )
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    except Exception as e:
        logger.error(f"Errore pubblicazione config: {e}")
        return False


def disconnect():
    """Disconnette il client MQTT"""
    global _mqtt_client
    
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        _mqtt_client = None
        logger.info("MQTT Publisher disconnesso")
