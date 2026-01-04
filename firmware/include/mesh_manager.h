/**
 * AgriSecure IoT System - Modulo Mesh ESP-NOW
 * 
 * Gestisce la comunicazione mesh tra i nodi usando ESP-NOW
 * - Peer discovery automatico
 * - Routing multi-hop
 * - Gestione priorità messaggi
 * - Encryption AES-128
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#ifndef MESH_MANAGER_H
#define MESH_MANAGER_H

#include "agrisecure_config.h"
#include <vector>
#include <map>

// ============================================================
// Configurazione Mesh
// ============================================================
#define MESH_MAX_PEERS 20
#define MESH_MSG_QUEUE_SIZE 10
#define MESH_RETRY_COUNT 3
#define MESH_RETRY_DELAY_MS 100
#define MESH_ACK_TIMEOUT_MS 1000

// ============================================================
// Struttura Peer (nodo vicino)
// ============================================================
typedef struct {
    uint8_t mac[6];              // MAC address
    char node_id[NODE_ID_SIZE];  // ID logico
    uint8_t node_type;           // Tipo nodo
    int8_t rssi;                 // Segnale
    uint32_t last_seen;          // Ultimo heartbeat
    bool is_gateway;             // È un gateway?
    uint8_t hop_to_gateway;      // Hop per raggiungere GW
} MeshPeer;

// ============================================================
// Callback per ricezione messaggi
// ============================================================
typedef void (*MeshMessageCallback)(const MeshMessage* msg, const uint8_t* sender_mac);

// ============================================================
// Classe MeshManager
// ============================================================
class MeshManager {
public:
    /**
     * Inizializza il modulo mesh
     * @param node_id ID univoco del nodo
     * @param node_type Tipo di nodo (GATEWAY, AMBIENT, SECURITY)
     * @param channel Canale WiFi (1-13)
     * @return true se inizializzazione OK
     */
    bool begin(const char* node_id, NodeType node_type, uint8_t channel = MESH_CHANNEL);
    
    /**
     * Loop principale - chiamare nel loop() principale
     */
    void update();
    
    /**
     * Invia messaggio a un nodo specifico
     * @param target_id ID nodo destinatario ("*" per broadcast)
     * @param msg_type Tipo messaggio
     * @param payload Dati da inviare
     * @param payload_len Lunghezza dati
     * @param priority Priorità messaggio
     * @return true se invio riuscito
     */
    bool sendMessage(const char* target_id, MessageType msg_type, 
                     const uint8_t* payload, uint8_t payload_len,
                     MessagePriority priority = PRIORITY_MEDIUM);
    
    /**
     * Invia messaggio broadcast a tutti i nodi
     */
    bool broadcast(MessageType msg_type, const uint8_t* payload, 
                   uint8_t payload_len, MessagePriority priority = PRIORITY_MEDIUM);
    
    /**
     * Invia dati sensori ambientali
     */
    bool sendSensorData(const SensorDataAmbient* data);
    
    /**
     * Invia allarme sicurezza
     */
    bool sendSecurityAlarm(IntrusionClass classification, const SensorDataSecurity* data);
    
    /**
     * Invia heartbeat
     */
    bool sendHeartbeat();
    
    /**
     * Invia status batteria
     */
    bool sendBatteryStatus(const BatteryStatus* status);
    
    /**
     * Registra callback per ricezione messaggi
     */
    void onMessage(MeshMessageCallback callback);
    
    /**
     * Ottiene lista peer connessi
     */
    std::vector<MeshPeer>& getPeers();
    
    /**
     * Trova il gateway più vicino
     */
    MeshPeer* findNearestGateway();
    
    /**
     * Ottiene il proprio MAC address
     */
    void getOwnMac(uint8_t* mac);
    
    /**
     * Ottiene il proprio Node ID
     */
    const char* getNodeId();
    
    /**
     * Verifica se connesso a un gateway
     */
    bool isConnectedToGateway();
    
    /**
     * Ottiene RSSI del peer specificato
     */
    int8_t getPeerRSSI(const char* node_id);
    
    /**
     * Numero di peer attivi
     */
    uint8_t getActivePeerCount();

private:
    char _node_id[NODE_ID_SIZE];
    NodeType _node_type;
    uint8_t _channel;
    uint8_t _own_mac[6];
    uint16_t _sequence;
    
    std::vector<MeshPeer> _peers;
    MeshMessageCallback _message_callback;
    
    // Coda messaggi in uscita
    struct QueuedMessage {
        MeshMessage msg;
        uint8_t retry_count;
        uint32_t next_retry;
    };
    std::vector<QueuedMessage> _tx_queue;
    
    // Messaggi in attesa di ACK
    std::map<uint16_t, QueuedMessage> _pending_ack;
    
    // Metodi interni
    bool _initESPNow();
    bool _addPeer(const uint8_t* mac);
    bool _removePeer(const uint8_t* mac);
    MeshPeer* _findPeerByMac(const uint8_t* mac);
    MeshPeer* _findPeerById(const char* node_id);
    bool _routeMessage(MeshMessage* msg);
    void _processQueue();
    void _cleanupPeers();
    
    // Callback statiche per ESP-NOW
    static void _onDataSent(const uint8_t* mac, esp_now_send_status_t status);
    static void _onDataRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len);
    
    // Istanza singleton per callback
    static MeshManager* _instance;
};

// Istanza globale
extern MeshManager Mesh;

#endif // MESH_MANAGER_H
