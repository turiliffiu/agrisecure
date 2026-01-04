/**
 * AgriSecure IoT System - Implementazione Mesh ESP-NOW
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include "mesh_manager.h"
#include <esp_wifi.h>
#include <string.h>

// Istanza singleton
MeshManager* MeshManager::_instance = nullptr;
MeshManager Mesh;

// ============================================================
// Funzioni Utility (da agrisecure_config.h)
// ============================================================
uint16_t calculateCRC16(const uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

String macToString(const uint8_t* mac) {
    char str[18];
    snprintf(str, sizeof(str), "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    return String(str);
}

uint32_t getCurrentTimestamp() {
    // Per ora ritorna millis/1000, in futuro sincronizzare con NTP/GPS
    return millis() / 1000;
}

// ============================================================
// Inizializzazione
// ============================================================
bool MeshManager::begin(const char* node_id, NodeType node_type, uint8_t channel) {
    _instance = this;
    _node_type = node_type;
    _channel = channel;
    _sequence = 0;
    _message_callback = nullptr;
    
    // Copia node_id
    strncpy(_node_id, node_id, NODE_ID_SIZE - 1);
    _node_id[NODE_ID_SIZE - 1] = '\0';
    
    DEBUG_PRINTLN(F(""));
    DEBUG_PRINTLN(F("==========================================="));
    DEBUG_PRINTLN(F(" AgriSecure Mesh - Inizializzazione"));
    DEBUG_PRINTLN(F("==========================================="));
    DEBUG_PRINTF("Node ID: %s\n", _node_id);
    DEBUG_PRINTF("Node Type: %d\n", _node_type);
    DEBUG_PRINTF("Channel: %d\n", _channel);
    
    // Inizializza WiFi in modalità STA
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    
    // Ottieni MAC address
    esp_read_mac(_own_mac, ESP_MAC_WIFI_STA);
    DEBUG_PRINTF("MAC Address: %s\n", macToString(_own_mac).c_str());
    
    // Imposta canale
    esp_wifi_set_channel(_channel, WIFI_SECOND_CHAN_NONE);
    
    // Inizializza ESP-NOW
    if (!_initESPNow()) {
        DEBUG_PRINTLN(F("ERRORE: Inizializzazione ESP-NOW fallita!"));
        return false;
    }
    
    // Aggiungi peer broadcast
    uint8_t broadcast_mac[] = MESH_BROADCAST_ADDR;
    _addPeer(broadcast_mac);
    
    DEBUG_PRINTLN(F("Mesh inizializzato con successo!"));
    DEBUG_PRINTLN(F("==========================================="));
    
    return true;
}

bool MeshManager::_initESPNow() {
    if (esp_now_init() != ESP_OK) {
        return false;
    }
    
    // Registra callback
    esp_now_register_send_cb(_onDataSent);
    esp_now_register_recv_cb(_onDataRecv);
    
    return true;
}

// ============================================================
// Loop Update
// ============================================================
void MeshManager::update() {
    // Processa coda messaggi
    _processQueue();
    
    // Cleanup peer inattivi (ogni 5 minuti)
    static uint32_t last_cleanup = 0;
    if (millis() - last_cleanup > 300000) {
        _cleanupPeers();
        last_cleanup = millis();
    }
}

// ============================================================
// Invio Messaggi
// ============================================================
bool MeshManager::sendMessage(const char* target_id, MessageType msg_type,
                               const uint8_t* payload, uint8_t payload_len,
                               MessagePriority priority) {
    if (payload_len > MESH_MSG_MAX_SIZE) {
        DEBUG_PRINTLN(F("ERRORE: Payload troppo grande!"));
        return false;
    }
    
    // Costruisci messaggio
    MeshMessage msg;
    memset(&msg, 0, sizeof(msg));
    
    strncpy(msg.sender_id, _node_id, NODE_ID_SIZE - 1);
    strncpy(msg.target_id, target_id, NODE_ID_SIZE - 1);
    msg.msg_type = msg_type;
    msg.priority = priority;
    msg.timestamp = getCurrentTimestamp();
    msg.sequence = _sequence++;
    msg.hop_count = 0;
    msg.payload_len = payload_len;
    
    if (payload && payload_len > 0) {
        memcpy(msg.payload, payload, payload_len);
    }
    
    // Calcola CRC (escluso il campo CRC stesso)
    msg.crc = calculateCRC16((uint8_t*)&msg, sizeof(msg) - sizeof(msg.crc));
    
    // Routing
    return _routeMessage(&msg);
}

bool MeshManager::broadcast(MessageType msg_type, const uint8_t* payload,
                            uint8_t payload_len, MessagePriority priority) {
    return sendMessage("*", msg_type, payload, payload_len, priority);
}

bool MeshManager::_routeMessage(MeshMessage* msg) {
    uint8_t* target_mac = nullptr;
    
    // Se broadcast, usa indirizzo broadcast
    if (strcmp(msg->target_id, "*") == 0) {
        static uint8_t broadcast_mac[] = MESH_BROADCAST_ADDR;
        target_mac = broadcast_mac;
    } else {
        // Cerca peer diretto
        MeshPeer* peer = _findPeerById(msg->target_id);
        if (peer) {
            target_mac = peer->mac;
        } else {
            // Cerca gateway per routing
            MeshPeer* gw = findNearestGateway();
            if (gw) {
                target_mac = gw->mac;
                msg->hop_count++;
            } else {
                DEBUG_PRINTLN(F("ERRORE: Nessun percorso verso destinazione!"));
                return false;
            }
        }
    }
    
    // Invia via ESP-NOW
    esp_err_t result = esp_now_send(target_mac, (uint8_t*)msg, sizeof(MeshMessage));
    
    if (result == ESP_OK) {
        DEBUG_PRINTF("MSG INVIATO: tipo=%d, seq=%d, target=%s\n", 
                     msg->msg_type, msg->sequence, msg->target_id);
        return true;
    } else {
        DEBUG_PRINTF("ERRORE INVIO: %d\n", result);
        return false;
    }
}

// ============================================================
// Invio Dati Specifici
// ============================================================
bool MeshManager::sendSensorData(const SensorDataAmbient* data) {
    // Trova gateway più vicino
    MeshPeer* gw = findNearestGateway();
    const char* target = gw ? gw->node_id : "*";
    
    return sendMessage(target, MSG_SENSOR_DATA, 
                       (uint8_t*)data, sizeof(SensorDataAmbient),
                       PRIORITY_LOW);
}

bool MeshManager::sendSecurityAlarm(IntrusionClass classification, 
                                     const SensorDataSecurity* data) {
    MessageType msg_type;
    MessagePriority priority;
    
    switch (classification) {
        case CLASS_PERSON:
            msg_type = MSG_ALARM_PERSON;
            priority = PRIORITY_CRITICAL;
            break;
        case CLASS_ANIMAL_LARGE:
            msg_type = MSG_ALARM_ANIMAL;
            priority = PRIORITY_HIGH;
            break;
        default:
            msg_type = MSG_SENSOR_DATA;
            priority = PRIORITY_LOW;
    }
    
    // Broadcast allarmi critici a tutti i gateway
    if (priority == PRIORITY_CRITICAL) {
        return broadcast(msg_type, (uint8_t*)data, sizeof(SensorDataSecurity), priority);
    } else {
        MeshPeer* gw = findNearestGateway();
        const char* target = gw ? gw->node_id : "*";
        return sendMessage(target, msg_type, (uint8_t*)data, sizeof(SensorDataSecurity), priority);
    }
}

bool MeshManager::sendHeartbeat() {
    HeartbeatData hb;
    hb.node_type = _node_type;
    hb.status = 0; // OK
    hb.uptime_sec = millis() / 1000;
    hb.free_heap = ESP.getFreeHeap() / 1024;
    hb.rssi = WiFi.RSSI();
    hb.battery_pct = 100; // TODO: leggere da sensore
    hb.mesh_neighbors = _peers.size();
    
    return broadcast(MSG_HEARTBEAT, (uint8_t*)&hb, sizeof(HeartbeatData), PRIORITY_MEDIUM);
}

bool MeshManager::sendBatteryStatus(const BatteryStatus* status) {
    MeshPeer* gw = findNearestGateway();
    const char* target = gw ? gw->node_id : "*";
    
    return sendMessage(target, MSG_BATTERY, 
                       (uint8_t*)status, sizeof(BatteryStatus),
                       PRIORITY_MEDIUM);
}

// ============================================================
// Gestione Peer
// ============================================================
bool MeshManager::_addPeer(const uint8_t* mac) {
    // Verifica se già presente
    if (_findPeerByMac(mac)) {
        return true;
    }
    
    esp_now_peer_info_t peer_info;
    memset(&peer_info, 0, sizeof(peer_info));
    memcpy(peer_info.peer_addr, mac, 6);
    peer_info.channel = _channel;
    peer_info.encrypt = false; // TODO: abilitare encryption
    
    if (esp_now_add_peer(&peer_info) == ESP_OK) {
        DEBUG_PRINTF("Peer aggiunto: %s\n", macToString(mac).c_str());
        return true;
    }
    return false;
}

bool MeshManager::_removePeer(const uint8_t* mac) {
    if (esp_now_del_peer(mac) == ESP_OK) {
        // Rimuovi dalla lista
        for (auto it = _peers.begin(); it != _peers.end(); ++it) {
            if (memcmp(it->mac, mac, 6) == 0) {
                _peers.erase(it);
                break;
            }
        }
        return true;
    }
    return false;
}

MeshPeer* MeshManager::_findPeerByMac(const uint8_t* mac) {
    for (auto& peer : _peers) {
        if (memcmp(peer.mac, mac, 6) == 0) {
            return &peer;
        }
    }
    return nullptr;
}

MeshPeer* MeshManager::_findPeerById(const char* node_id) {
    for (auto& peer : _peers) {
        if (strcmp(peer.node_id, node_id) == 0) {
            return &peer;
        }
    }
    return nullptr;
}

MeshPeer* MeshManager::findNearestGateway() {
    MeshPeer* nearest = nullptr;
    int8_t best_rssi = -127;
    
    for (auto& peer : _peers) {
        if (peer.is_gateway && peer.rssi > best_rssi) {
            best_rssi = peer.rssi;
            nearest = &peer;
        }
    }
    return nearest;
}

void MeshManager::_cleanupPeers() {
    uint32_t now = millis();
    uint32_t timeout = MESH_HEARTBEAT_INTERVAL * 2; // 2x heartbeat interval
    
    for (auto it = _peers.begin(); it != _peers.end(); ) {
        if (now - it->last_seen > timeout) {
            DEBUG_PRINTF("Peer timeout: %s\n", it->node_id);
            _removePeer(it->mac);
            it = _peers.erase(it);
        } else {
            ++it;
        }
    }
}

// ============================================================
// Callback ESP-NOW
// ============================================================
void MeshManager::_onDataSent(const uint8_t* mac, esp_now_send_status_t status) {
    if (_instance) {
        if (status != ESP_NOW_SEND_SUCCESS) {
            DEBUG_PRINTF("Invio fallito a: %s\n", macToString(mac).c_str());
        }
    }
}

void MeshManager::_onDataRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
    if (!_instance || len != sizeof(MeshMessage)) {
        return;
    }
    
    MeshMessage* msg = (MeshMessage*)data;
    
    // Verifica CRC
    uint16_t received_crc = msg->crc;
    msg->crc = 0;
    uint16_t calc_crc = calculateCRC16(data, sizeof(MeshMessage) - sizeof(msg->crc));
    msg->crc = received_crc;
    
    if (calc_crc != received_crc) {
        DEBUG_PRINTLN(F("ERRORE: CRC non valido!"));
        return;
    }
    
    DEBUG_PRINTF("MSG RICEVUTO: tipo=%d, da=%s, seq=%d\n", 
                 msg->msg_type, msg->sender_id, msg->sequence);
    
    // Aggiorna/aggiungi peer
    MeshPeer* peer = _instance->_findPeerByMac(info->src_addr);
    if (!peer) {
        // Nuovo peer
        MeshPeer new_peer;
        memcpy(new_peer.mac, info->src_addr, 6);
        strncpy(new_peer.node_id, msg->sender_id, NODE_ID_SIZE - 1);
        new_peer.rssi = info->rx_ctrl->rssi;
        new_peer.last_seen = millis();
        new_peer.is_gateway = (msg->msg_type == MSG_HEARTBEAT && 
                               ((HeartbeatData*)msg->payload)->node_type == NODE_GATEWAY);
        new_peer.hop_to_gateway = 1;
        
        _instance->_addPeer(info->src_addr);
        _instance->_peers.push_back(new_peer);
        
        DEBUG_PRINTF("Nuovo peer: %s (%s)\n", new_peer.node_id, 
                     macToString(new_peer.mac).c_str());
    } else {
        // Aggiorna peer esistente
        peer->rssi = info->rx_ctrl->rssi;
        peer->last_seen = millis();
    }
    
    // Se messaggio per questo nodo o broadcast, processa
    if (strcmp(msg->target_id, _instance->_node_id) == 0 || 
        strcmp(msg->target_id, "*") == 0) {
        
        // Chiama callback utente
        if (_instance->_message_callback) {
            _instance->_message_callback(msg, info->src_addr);
        }
    } else if (_instance->_node_type == NODE_GATEWAY) {
        // Gateway: routing verso destinazione
        msg->hop_count++;
        if (msg->hop_count < 5) { // Max 5 hop
            _instance->_routeMessage(msg);
        }
    }
}

// ============================================================
// Getter
// ============================================================
void MeshManager::onMessage(MeshMessageCallback callback) {
    _message_callback = callback;
}

std::vector<MeshPeer>& MeshManager::getPeers() {
    return _peers;
}

void MeshManager::getOwnMac(uint8_t* mac) {
    memcpy(mac, _own_mac, 6);
}

const char* MeshManager::getNodeId() {
    return _node_id;
}

bool MeshManager::isConnectedToGateway() {
    return findNearestGateway() != nullptr;
}

int8_t MeshManager::getPeerRSSI(const char* node_id) {
    MeshPeer* peer = _findPeerById(node_id);
    return peer ? peer->rssi : -127;
}

uint8_t MeshManager::getActivePeerCount() {
    return _peers.size();
}

void MeshManager::_processQueue() {
    // TODO: implementare coda con retry
}
