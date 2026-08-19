/**
 * AgriSecure IoT System - Main Entry Point
 * 
 * Questo file seleziona automaticamente il firmware corretto
 * in base alla configurazione NODE_TYPE in platformio.ini
 * 
 * Compilare con:
 *   pio run -e node_gateway    # Per gateway 4G
 *   pio run -e node_ambient    # Per nodo ambientale
 *   pio run -e node_security   # Per nodo sicurezza
 * 
 * @author Turiliffiu
 * @version 1.0.0
 */

// Selezione automatica del firmware basata su NODE_TYPE
// definito in platformio.ini build_flags

// NOTA (fix agosto 2026): il preprocessore C non conosce gli enum C++ (NodeType
// in agrisecure_config.h). In un #if, un identificatore non definito come macro
// vale sempre 0 - quindi confrontare NODE_TYPE == NODE_GATEWAY qui valutava
// sempre "0 == 0" (vero), indipendentemente dal nodo compilato: il branch
// GATEWAY vinceva sempre. Fix: confronto sui valori numerici dell'enum,
// passati come macro da platformio.ini (NODE_TYPE=0/1/2/99).
// Mappatura: 0=NODE_GATEWAY, 1=NODE_AMBIENT, 2=NODE_SECURITY, 99=NODE_TEST
#if defined(NODE_TYPE) && NODE_TYPE == 0
    // Gateway 4G/LTE
    #include "main_gateway.cpp"
    
#elif defined(NODE_TYPE) && NODE_TYPE == 1
    // Nodo ambientale
    #include "main_ambient.cpp"
    
#elif defined(NODE_TYPE) && NODE_TYPE == 2
    // Nodo sicurezza
    #include "main_security.cpp"
    
#else
    // Default: nodo di test
    #warning "NODE_TYPE non definito, compilazione firmware di test"
    
    #include <Arduino.h>
    #include "agrisecure_config.h"
    
    void setup() {
        Serial.begin(115200);
        delay(1000);
        
        Serial.println(F("\n"));
        Serial.println(F("╔═══════════════════════════════════════════╗"));
        Serial.println(F("║   AgriSecure IoT - TEST MODE              ║"));
        Serial.println(F("╚═══════════════════════════════════════════╝"));
        Serial.println(F(""));
        Serial.println(F("Questo è un firmware di test."));
        Serial.println(F("Per compilare un nodo specifico usa:"));
        Serial.println(F(""));
        Serial.println(F("  pio run -e node_gateway"));
        Serial.println(F("  pio run -e node_ambient"));
        Serial.println(F("  pio run -e node_security"));
        Serial.println(F(""));
        Serial.printf("Firmware version: %s\n", FIRMWARE_VERSION);
        Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
    }
    
    void loop() {
        static uint32_t last_print = 0;
        if (millis() - last_print > 5000) {
            Serial.println(F("Test mode running..."));
            last_print = millis();
        }
        delay(100);
    }
    
#endif
