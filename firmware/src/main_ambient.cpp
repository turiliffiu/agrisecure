/**
 * AgriSecure IoT System - Firmware Nodo Ambientale
 * 
 * Nodo per monitoraggio parametri climatici e suolo:
 * - Temperatura, Umidità, Pressione (BME280)
 * - Luminosità (BH1750)
 * - Umidità suolo (sensore capacitivo)
 * 
 * Funzionamento:
 * 1. Wake up da deep sleep
 * 2. Leggi sensori
 * 3. Invia dati via mesh al gateway
 * 4. Torna in deep sleep
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <WebServer.h>
#include <Preferences.h>
#include <driver/rtc_io.h>
#include "agrisecure_config.h"
#include "mesh_manager.h"
#include "sensors_ambient.h"

// LED RGB WS2812 (settembre 2026: stesso pattern del gateway, GPIO48 su
// hardware S3-N16R8 - sostituisce il vecchio LED singolo-colore GPIO2 del
// precedente hardware ESP32-WROOM-32D)
Adafruit_NeoPixel statusRGB(1, LED_RGB_PIN, NEO_GRB + NEO_KHZ800);

// ============================================================
// Configurazione NVS + AP on-demand (settembre 2026, pattern gateway)
// ============================================================
Preferences prefs;
String cfgNodeId;
String cfgAPSSID;
String cfgAPPassword;
WebServer configServer(80);
bool apModeActive = false;

// ============================================================
// Configurazione
// ============================================================
#ifndef NODE_ID
#define NODE_ID "AMB-001"
#endif

#ifndef SENSOR_READ_INTERVAL
#define SENSOR_READ_INTERVAL 600000  // 10 minuti in ms
#endif

#ifndef DEEP_SLEEP_DURATION
#define DEEP_SLEEP_DURATION 600  // 10 minuti in secondi
#endif

// ============================================================
// Variabili Globali
// ============================================================
RTC_DATA_ATTR uint32_t boot_count = 0;  // Persistente durante deep sleep
RTC_DATA_ATTR uint32_t total_readings = 0;

uint32_t last_sensor_read = 0;
uint32_t last_heartbeat = 0;
bool mesh_connected = false;

// ============================================================
// Prototipi
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac);
void readAndSendSensors();
void enterDeepSleep();
void printWakeupReason();
void loadConfig();
void handleConfigRoot();
void handleConfigGet();
void handleConfigPost();
void handleConfigExit();
void runAPConfigMode();
void exitAPConfigMode();

// Uscita robusta da AP-config (settembre 2026): ESP.restart() e' un
// soft-reset, la cui interazione col registro hardware della causa di
// risveglio si e' rivelata inaffidabile in test (il nodo rientrava subito
// in AP-config dopo l'uscita, sia da pulsante che da timeout). Un vero
// mini deep-sleep con wakeup a timer garantisce che il prossimo boot
// legga ESP_SLEEP_WAKEUP_TIMER, non piu' EXT0 - comportamento hardware
// documentato e affidabile, a differenza del soft-reset.
void exitAPConfigMode() {
    configServer.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_OFF);
    statusRGB.setPixelColor(0, 0);
    statusRGB.show();
    // NB (fix post-test): non serve disabilitare esplicitamente EXT0 qui -
    // a questo punto il pulsante e' gia' rilasciato (altrimenti non saremmo
    // usciti dal ciclo di attesa), quindi il pin resta HIGH durante il mini
    // sleep e non puo' scattare per errore. esp_sleep_disable_wakeup_source()
    // su EXT0 dava "Incorrect wakeup source (2) to disable" - disabilitare
    // singolarmente questa sorgente non e' supportato in modo pulito su
    // questo chip/IDF, ma non serve: enterDeepSleep() la riarma comunque
    // (idempotente) al prossimo vero ciclo.
    esp_sleep_enable_timer_wakeup(1000000ULL);  // 1 secondo
    esp_deep_sleep_start();
}

// ============================================================
// Configurazione NVS (settembre 2026, pattern gateway)
// ============================================================
void loadConfig() {
    prefs.begin("agrisecure", false);  // read-write: crea il namespace al primo avvio
    cfgNodeId = prefs.getString("node_id", NODE_ID);
    cfgAPSSID = prefs.getString("ap_ssid", AP_SSID);
    cfgAPPassword = prefs.getString("ap_pass", AP_PASSWORD);
    prefs.end();
    Serial.println(F("[CONFIG] Parametri caricati da NVS (o default se prima esecuzione)"));
}

void handleConfigRoot() {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>AgriSecure " + cfgNodeId + "</title>";
    html += "<style>body{font-family:sans-serif;max-width:480px;margin:20px auto;padding:0 15px;}";
    html += "h1{color:#2c5f2d;} .row{padding:8px 0;border-bottom:1px solid #eee;}</style></head><body>";
    html += "<h1>AgriSecure - " + cfgNodeId + "</h1>";
    html += "<div class='row'>Firmware: " + String(FIRMWARE_VERSION) + "</div>";
    html += "<div class='row'>Tipo nodo: Ambientale</div>";
    html += "<div class='row'>IP AP: " + WiFi.softAPIP().toString() + "</div>";
    html += "<div class='row'>Uptime: " + String(millis() / 1000) + " s</div>";
    html += "<p><a href='/config'>Modifica configurazione</a></p>";
    html += "<p><a href='/exit' style='color:#c0392b;'>Esci senza salvare</a></p>";
    html += "</body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigExit() {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'></head><body>";
    html += "<h1>Uscita in corso</h1><p>Il nodo torna al normale ciclo di funzionamento...</p></body></html>";
    configServer.send(200, "text/html", html);

    Serial.println(F("[AP] Uscita richiesta dal web, riavvio..."));
    delay(500);
    exitAPConfigMode();
}

void handleConfigGet() {
    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>Configurazione " + cfgNodeId + "</title>";
    html += "<style>body{font-family:sans-serif;max-width:480px;margin:20px auto;padding:0 15px;}";
    html += "h1{color:#2c5f2d;} label{display:block;margin-top:12px;font-weight:bold;}";
    html += "input{width:100%;padding:8px;box-sizing:border-box;margin-top:4px;}";
    html += "button{margin-top:20px;padding:10px 20px;background:#2c5f2d;color:#fff;border:none;border-radius:4px;}";
    html += "small{color:#888;}</style></head><body>";
    html += "<h1>Configurazione</h1>";
    html += "<form method='POST' action='/config'>";
    html += "<label>Node ID</label><input name='node_id' value='" + cfgNodeId + "'>";
    html += "<small>Es. AMB-001, AMB-002... determina anche i topic mesh</small>";
    html += "<label>AP SSID</label><input name='ap_ssid' value='" + cfgAPSSID + "'>";
    html += "<label>AP Password</label><input name='ap_pass' type='password' value=''>";
    html += "<small>Lascia vuoto per non modificare</small>";
    html += "<br><button type='submit'>Salva e riavvia</button>";
    html += "</form><p><a href='/'>Torna allo stato</a></p></body></html>";
    configServer.send(200, "text/html", html);
}

void handleConfigPost() {
    prefs.begin("agrisecure", false);
    if (configServer.hasArg("node_id")) prefs.putString("node_id", configServer.arg("node_id"));
    if (configServer.hasArg("ap_ssid")) prefs.putString("ap_ssid", configServer.arg("ap_ssid"));
    if (configServer.hasArg("ap_pass") && configServer.arg("ap_pass").length() > 0) {
        prefs.putString("ap_pass", configServer.arg("ap_pass"));
    }
    prefs.end();

    String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1'></head><body>";
    html += "<h1>Configurazione salvata</h1><p>Il nodo si sta riavviando...</p></body></html>";
    configServer.send(200, "text/html", html);

    Serial.println(F("[CONFIG] Nuovi parametri salvati su NVS, riavvio..."));
    delay(1000);
    exitAPConfigMode();
}

// ============================================================
// Modalita' AP-config (settembre 2026, pattern gateway adattato)
// A differenza del gateway (sempre acceso, loop() persistente), qui non
// c'e' un loop operativo a cui tornare: il nodo entra in questa modalita'
// SOLO se svegliato dal pulsante (EXT0), resta bloccato qui finche' non
// si salva o si preme di nuovo il pulsante per uscire senza salvare -
// entrambe le uscite chiamano exitAPConfigMode() (mini deep-sleep con
// wakeup a timer, non un soft-reset - vedi nota li' sopra sul perche').
// ============================================================
void runAPConfigMode() {
    statusRGB.setPixelColor(0, statusRGB.Color(0, 0, 255));  // blu fisso: AP attivo
    statusRGB.show();

    WiFi.mode(WIFI_MODE_APSTA);
    WiFi.softAP(cfgAPSSID.c_str(), cfgAPPassword.c_str(), MESH_CHANNEL);
    Serial.print(F("[AP] Attivo - SSID: "));
    Serial.print(cfgAPSSID);
    Serial.print(F(" - IP: "));
    Serial.println(WiFi.softAPIP());

    configServer.on("/", handleConfigRoot);
    configServer.on("/config", HTTP_GET, handleConfigGet);
    configServer.on("/config", HTTP_POST, handleConfigPost);
    configServer.on("/exit", handleConfigExit);
    configServer.begin();
    Serial.println(F("[AP] Web server avviato su porta 80"));
    Serial.println(F("[AP] Premi di nuovo il pulsante per uscire senza salvare"));

    // Timeout di inattivita' (settembre 2026): su un nodo a batteria, restare
    // svegli indefinitamente con AP+web server attivi scarica la batteria
    // inutilmente se nessuno configura davvero (es. pulsante premuto per
    // errore). Dopo AP_CONFIG_TIMEOUT_MS senza richieste HTTP, esce da solo.
    #ifndef AP_CONFIG_TIMEOUT_MS
    #define AP_CONFIG_TIMEOUT_MS 300000  // 5 minuti
    #endif
    uint32_t apStartTime = millis();
    Serial.printf("[AP] Timeout automatico: %d secondi senza richieste\n", AP_CONFIG_TIMEOUT_MS / 1000);

    while (true) {
        configServer.handleClient();

        // Pulsante collegato a GND: pressione = LOW -> esci senza salvare
        if (digitalRead(BUTTON_AP) == LOW) {
            delay(50);  // debounce minimo
            if (digitalRead(BUTTON_AP) == LOW) {
                Serial.println(F("[AP] Uscita richiesta dal pulsante, riavvio..."));
                delay(300);
                exitAPConfigMode();
            }
        }

        // Timeout raggiunto senza nessuna interazione -> esci automaticamente
        if (millis() - apStartTime > AP_CONFIG_TIMEOUT_MS) {
            Serial.println(F("[AP] Timeout inattivita' raggiunto, riavvio..."));
            delay(300);
            exitAPConfigMode();
        }

        delay(10);
    }
}

// ============================================================
// Setup
// ============================================================
void setup() {
    // Inizializza Serial
    Serial.begin(115200);
    delay(100);
    
    boot_count++;
    
    Serial.println(F("\n"));
    Serial.println(F("╔═══════════════════════════════════════════╗"));
    Serial.println(F("║   AgriSecure IoT - Nodo Ambientale        ║"));
    Serial.println(F("╚═══════════════════════════════════════════╝"));
    Serial.printf("Versione: %s\n", FIRMWARE_VERSION);
    Serial.printf("Node ID: %s\n", NODE_ID);
    Serial.printf("Boot count: %d\n", boot_count);
    Serial.printf("Letture totali: %d\n", total_readings);
    
    // Motivo wakeup
    esp_sleep_wakeup_cause_t wakeup_cause = esp_sleep_get_wakeup_cause();
    printWakeupReason();
    
    // Carica configurazione da NVS (settembre 2026, pattern gateway)
    pinMode(BUTTON_AP, INPUT_PULLUP);
    loadConfig();
    
    // LED RGB di stato (settembre 2026: NeoPixel, non piu' digitalWrite)
    statusRGB.begin();
    statusRGB.setBrightness(50);
    
    // Se il risveglio e' dovuto al pulsante (non al timer), verifica che
    // resti premuto per BUTTON_HOLD_MS (settembre 2026: evita ingressi
    // accidentali in AP-config per un tocco/vibrazione casuale - un tocco
    // breve viene ignorato, si torna a dormire subito senza consumare
    // batteria in modalita' config).
    #ifndef BUTTON_HOLD_MS
    #define BUTTON_HOLD_MS 5000  // 5 secondi
    #endif
    if (wakeup_cause == ESP_SLEEP_WAKEUP_EXT0) {
        Serial.printf("[BUTTON] Risveglio da pulsante, verifica pressione (%d ms)...\n", BUTTON_HOLD_MS);
        uint32_t pressStart = millis();
        bool heldLongEnough = true;
        while (millis() - pressStart < BUTTON_HOLD_MS) {
            if (digitalRead(BUTTON_AP) == HIGH) {
                // Rilasciato troppo presto: tocco accidentale, ignora
                heldLongEnough = false;
                break;
            }
            delay(20);
        }

        if (heldLongEnough) {
            Serial.println(F("[BUTTON] Pressione confermata -> modalita' AP-config"));
            runAPConfigMode();  // bloccante, non ritorna mai
        } else {
            Serial.println(F("[BUTTON] Pressione troppo breve, ignorato - torno a dormire"));
            exitAPConfigMode();  // mini deep-sleep, non ritorna mai
        }
    }
    
    statusRGB.setPixelColor(0, statusRGB.Color(0, 0, 255));  // blu: setup in corso
    statusRGB.show();
    
    // Inizializza sensori ambientali
    Serial.println(F("\nInizializzazione sensori..."));
    bool sensors_ok = AmbientSensors.begin();
    if (!sensors_ok) {
        Serial.println(F("ATTENZIONE: Alcuni sensori non disponibili!"));
        statusRGB.setPixelColor(0, statusRGB.Color(255, 0, 0));  // rosso: problema sensori
        statusRGB.show();
    }
    
    // Inizializza mesh
    Serial.println(F("\nInizializzazione mesh..."));
    if (!Mesh.begin(cfgNodeId.c_str(), NODE_AMBIENT)) {
        Serial.println(F("ERRORE: Mesh non inizializzato!"));
        // Continua comunque, prova a riconnettersi
    }
    
    // Registra callback messaggi
    Mesh.onMessage(onMeshMessage);
    
    // Prima lettura sensori
    readAndSendSensors();
    
    // LED verde: invio completato, poi spegne prima del deep sleep
    statusRGB.setPixelColor(0, statusRGB.Color(0, 255, 0));
    statusRGB.show();
    delay(300);
    statusRGB.setPixelColor(0, 0);
    statusRGB.show();
    
    Serial.println(F("\nSetup completato!"));
    Serial.println(F("───────────────────────────────────────────"));
    
    #ifdef DEEP_SLEEP_ENABLED
    // Se deep sleep abilitato, dormi subito dopo invio
    Serial.println(F("Deep sleep abilitato, entro in sleep..."));
    delay(1000);  // Attendi invio mesh
    enterDeepSleep();
    #endif
}

// ============================================================
// Loop Principale
// ============================================================
void loop() {
    // Aggiorna mesh
    Mesh.update();
    
    uint32_t now = millis();
    
    // Lettura sensori periodica
    if (now - last_sensor_read >= SENSOR_READ_INTERVAL) {
        readAndSendSensors();
        last_sensor_read = now;
    }
    
    // Heartbeat periodico
    if (now - last_heartbeat >= MESH_HEARTBEAT_INTERVAL) {
        Serial.println(F("Invio heartbeat..."));
        Mesh.sendHeartbeat();
        last_heartbeat = now;
    }
    
    // Verifica connessione gateway
    bool connected = Mesh.isConnectedToGateway();
    if (connected != mesh_connected) {
        mesh_connected = connected;
        if (connected) {
            Serial.println(F("✓ Connesso al gateway"));
        } else {
            Serial.println(F("✗ Disconnesso dal gateway"));
        }
    }
    
    // LED lampeggia giallo se non connesso (settembre 2026: NeoPixel non
    // supporta digitalRead - stato di toggle tenuto in una variabile)
    static uint32_t last_blink = 0;
    static bool blink_state = false;
    if (!mesh_connected && now - last_blink > 1000) {
        blink_state = !blink_state;
        if (blink_state) {
            statusRGB.setPixelColor(0, statusRGB.Color(255, 255, 0));
        } else {
            statusRGB.setPixelColor(0, 0);
        }
        statusRGB.show();
        last_blink = now;
    }
    
    // Piccola pausa per risparmiare energia
    delay(100);
}

// ============================================================
// Lettura e Invio Sensori
// ============================================================
void readAndSendSensors() {
    Serial.println(F("\n>>> Lettura sensori <<<"));
    
    statusRGB.setPixelColor(0, statusRGB.Color(0, 100, 255));  // ciano: lettura in corso
    statusRGB.show();
    
    SensorDataAmbient data;
    if (AmbientSensors.read(&data)) {
        Serial.println(F("Dati sensori:"));
        Serial.printf("  Temperatura: %.1f °C\n", data.temperature);
        Serial.printf("  Umidità aria: %.1f %%\n", data.humidity);
        Serial.printf("  Pressione: %.1f hPa\n", data.pressure);
        Serial.printf("  Luce: %d lux\n", data.light_lux);
        Serial.printf("  Umidità suolo: %d%% (raw: %d)\n", 
                      data.soil_percent, data.soil_moisture);
        
        // Invia via mesh
        if (Mesh.sendSensorData(&data)) {
            Serial.println(F("✓ Dati inviati al gateway"));
            total_readings++;
        } else {
            Serial.println(F("✗ Errore invio dati"));
        }
    } else {
        Serial.println(F("Errore lettura sensori!"));
    }
    
    statusRGB.setPixelColor(0, 0);
    statusRGB.show();
}

// ============================================================
// Callback Messaggi Mesh
// ============================================================
void onMeshMessage(const MeshMessage* msg, const uint8_t* sender_mac) {
    Serial.printf("\nMessaggio ricevuto da %s, tipo: %d\n", 
                  msg->sender_id, msg->msg_type);
    
    switch (msg->msg_type) {
        case MSG_COMMAND:
            Serial.println(F("Comando ricevuto"));
            // TODO: gestire comandi (es. calibrazione, config)
            break;
            
        case MSG_CONFIG:
            Serial.println(F("Configurazione ricevuta"));
            // TODO: applicare nuova configurazione
            break;
            
        case MSG_OTA:
            Serial.println(F("Richiesta OTA ricevuta"));
            // TODO: avviare OTA update
            break;
            
        default:
            // Altri messaggi ignorati
            break;
    }
}

// ============================================================
// Deep Sleep
// ============================================================
void enterDeepSleep() {
    Serial.printf("Entro in deep sleep per %d secondi...\n", DEEP_SLEEP_DURATION);
    Serial.flush();
    
    // Configura wakeup timer
    esp_sleep_enable_timer_wakeup(DEEP_SLEEP_DURATION * 1000000ULL);
    
    // Configura wakeup su pulsante (settembre 2026, pattern gateway):
    // pressione durante il deep sleep sveglia il nodo in modalita'
    // AP-config invece del normale ciclo sensori. Livello 0 = wake su LOW
    // (pulsante collegato a GND).
    esp_sleep_enable_ext0_wakeup((gpio_num_t)BUTTON_AP, 0);
    
    // Fix (settembre 2026): pinMode(INPUT_PULLUP) usa il pull-up digitale
    // standard, che si spegne durante il deep sleep insieme al resto della
    // logica digitale - solo il dominio RTC_PERIPH resta acceso. Senza un
    // pull-up RTC esplicito il pin resta flottante durante il sonno,
    // captando rumore che l'EXT0 interpreta come pressioni spurie (risvegli
    // continui senza che il pulsante venga davvero premuto, osservato in
    // test). Documentazione ufficiale ESP-IDF: va configurato con
    // rtc_gpio_pullup_en()/rtc_gpio_pulldown_en() prima di
    // esp_deep_sleep_start().
    rtc_gpio_pullup_en((gpio_num_t)BUTTON_AP);
    rtc_gpio_pulldown_dis((gpio_num_t)BUTTON_AP);
    
    // Entra in deep sleep
    esp_deep_sleep_start();
}

void printWakeupReason() {
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
    
    switch (wakeup_reason) {
        case ESP_SLEEP_WAKEUP_TIMER:
            Serial.println(F("Wakeup: Timer"));
            break;
        case ESP_SLEEP_WAKEUP_EXT0:
            Serial.println(F("Wakeup: External signal (RTC_IO)"));
            break;
        case ESP_SLEEP_WAKEUP_EXT1:
            Serial.println(F("Wakeup: External signal (RTC_CNTL)"));
            break;
        case ESP_SLEEP_WAKEUP_GPIO:
            Serial.println(F("Wakeup: GPIO"));
            break;
        default:
            Serial.println(F("Wakeup: Power on / Reset"));
            break;
    }
}
