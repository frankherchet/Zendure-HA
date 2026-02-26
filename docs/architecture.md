# Architekturuebersicht Zendure-HA

## 1. Ziel und Scope
Dieses Dokument beschreibt die technische Architektur des Repositories mit Fokus auf die Home-Assistant-Integration in `custom_components/zendure_ha`. Ziel ist eine belastbare Gesamtuebersicht als Grundlage fuer ein spaeteres Refactoring.

## 2. Systemkontext
- Das Projekt ist eine **Custom Integration fuer Home Assistant** (`manifest.json`, Domain `zendure_ha`).
- Es verbindet Zendure-Geraete ueber:
  - Zendure Cloud API (`/api/ha/deviceList`),
  - MQTT (Cloud + optional lokal),
  - optional lokale HTTP-Endpunkte bei ZenSDK-Geraeten,
  - optional BLE fuer MQTT-Provisionierung.
- Zentrale Aufgabe: Geraetedaten als HA-Entities bereitstellen und optional Lastmanagement (P1-Meter-basiert) ueber mehrere Geraete steuern.

## 3. Schichtenmodell

### 3.1 Integrations- und Lifecycle-Schicht
- `custom_components/zendure_ha/__init__.py`
  - `async_setup_entry`: Plattformen laden, `ZendureManager` erzeugen, Devices laden, ersten Refresh starten.
  - `async_unload_entry`: MQTT/BLE-Verbindungen abbauen, Runtime-Strukturen leeren.
  - `async_migrate_entry`: Migration von Unique IDs / Device-Namen.

### 3.2 Konfiguration und Validierung
- `custom_components/zendure_ha/config_flow.py`
  - `ZendureConfigFlow`: Token-Validierung und optional lokale MQTT-Daten.
  - `ZendureOptionsFlowHandler`: Update von Optionen (P1-Meter, MQTT-Logging, Simulation).

### 3.3 Kommunikations- und Transport-Schicht
- `custom_components/zendure_ha/api.py` (`Api`)
  - Cloud-Handshake (`ApiHA`), Signaturbildung, Device-Liste/MQTT-Credentials.
  - MQTT-Client-Initialisierung (Cloud/lokal).
  - MQTT-Routing auf Device-Instanzen (`mqttMsgCloud`, `mqttMsgLocal`, `mqttMsgDevice`).

### 3.4 Orchestrierung / Domainenlogik
- `custom_components/zendure_ha/manager.py` (`ZendureManager`)
  - Discovery/Instanzierung von Devices.
  - Periodisches Refreshing (`DataUpdateCoordinator`).
  - P1-Ereignisverarbeitung, Lastverteilung, Betriebsmodi.
  - FuseGroup-Bildung und Leistungsbegrenzungen ueber mehrere Devices.

### 3.5 Device-Domaenenmodell
- `custom_components/zendure_ha/device.py`
  - `ZendureDevice` Basisklasse (Entity-Layer + MQTT-Commands + Zustandsableitung).
  - `ZendureLegacy` fuer klassische MQTT/BLE-Geraete.
  - `ZendureZenSdk` fuer MQTT/HTTP-Hybridgeraete.
  - `ZendureBattery` Sub-Device-Modell.

### 3.6 HA-Entity-Layer
- Basisklassen: `custom_components/zendure_ha/entity.py`.
- Plattformen:
  - `sensor.py`, `binary_sensor.py`, `number.py`, `select.py`, `switch.py`, `button.py`.
- Entities werden teils statisch, teils dynamisch aus Payload-Keys erzeugt (`EntityDevice.createEntity`).

### 3.7 Device-spezifische Implementierungen
- `custom_components/zendure_ha/devices/*.py`
- Modelliert Geraetegrenzen (`setLimits`), Offgrid-Verhalten und konkrete Command-Payloads pro Produktfamilie.

## 4. Laufzeitarchitektur

### 4.1 Startup-Sequenz (vereinfachte Sicht)
1. Config Entry startet (`async_setup_entry`).
2. Plattformen registrieren Add-Callbacks fuer Entities.
3. `ZendureManager.loadDevices()`:
   - Cloud-API holen,
   - Device-Typen mappen (`Api.createdevice`),
   - Device-Objekte erzeugen,
   - MQTT initialisieren,
   - P1-Event abonnieren,
   - FuseGroups berechnen.
4. Erster Coordinator-Refresh (`async_config_entry_first_refresh`).

### 4.2 Datenaktualisierung
- Pull-Pfad: `DataUpdateCoordinator` (Intervall 60s) ruft `device.dataRefresh()`.
- Push-Pfad: MQTT-Reports -> `device.mqttMessage()` -> `device.mqttProperties()` -> `entityUpdate()`.
- ZenSDK-HTTP wird zusaetzlich fuer lokale Abfragen/Commands genutzt.

### 4.3 Steuerungslogik
- Bei P1-State-Aenderungen (`_p1_changed`) berechnet der Manager Setpoints.
- Devices werden in `charge`, `discharge`, `idle` gruppiert.
- Verteilung nach SOC, Limits, FuseGroup und Hysterese-Parametern (`SmartMode`).

## 5. Abhaengigkeiten und Kopplung
- Externe Libraries: `paho-mqtt`, `aiohttp`, `bleak`, `stringcase`, Home Assistant APIs.
- Hohe Kopplungspunkte:
  - `Api` als globaler statischer Zustand.
  - `ZendureDevice` vereint Domain + Transport + Entity-Update.
  - `EntityDevice.createEntity` als zentrale Mapping-Matrix.

## 6. Staerken und Risiken

### Staerken
- Klare Trennung nach Device-Familien (`devices/`).
- Leistungsmanagement bereits zentralisiert in `ZendureManager`.
- Gute Integration in HA-Lifecycle (ConfigEntry, Coordinator, RestoreEntity).

### Risiken / technische Schulden
- Globaler Singleton-Charakter in `Api` erschwert Tests und Multi-Entry-Szenarien.
- Grosse Verantwortung in `manager.py` (Algorithmus + Scheduling + Orchestrierung).
- Dynamische Entity-Erstellung ist flexibel, aber schwer testbar und schwer typisierbar.
- Teilweise inkonsistente Feldnamen (`hemsStateUpdate` vs. `hemsStateUpdated`) mit Bug-Potenzial.

## 7. Refactoring-Seams (priorisiert)
1. **Runtime-Context kapseln**: `Api`-Klassenvariablen in entry-spezifischen Context ueberfuehren.
2. **Power-Algorithmus extrahieren**: reine Berechnungslogik aus `ZendureManager` in testbare Engine.
3. **Transportadapter trennen**: MQTT/BLE/HTTP aus `ZendureDevice` in dedizierte Adapter.
4. **Entity-Schema modularisieren**: `createEntity` in deklarative Teilmodule je Domane.
5. **Command-Builders vereinheitlichen**: wiederholte `deviceAutomation`-Payloads zentral bauen.
