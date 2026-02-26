# API-Dokumentation Zendure-HA

## 1. Externe APIs

### 1.1 Zendure Cloud HTTP API

#### Endpoint
- `POST {api_url}/api/ha/deviceList`

#### Quelle im Code
- `custom_components/zendure_ha/api.py` (`Api.ApiHA`)

#### Auth/Signatur
- Token wird aus Config gelesen und base64-decodiert zu `{api_url}.{appKey}`.
- Request-Body enthaelt `appKey`.
- Signaturheader (`timestamp`, `nonce`, `clientid`, `sign`) wird per SHA1 ueber sortierte Parameter erstellt.
- `CONF_HAKEY` dient als Signatur-Secret-Salt.

#### Antwortnutzung
- `data.deviceList`: Liste erkannter Zendure-Geraete.
- `data.mqtt`: Cloud-MQTT-Credentials (`url`, `clientId`, `username`, `password`).

### 1.2 MQTT Broker (Cloud + optional lokal)

#### Verbindungen
- Cloud-MQTT aus Cloud-API-Antwort.
- Lokaler MQTT optional aus Config (`mqttserver`, `mqttport`, `mqttuser`, `mqttpsw`).

#### Relevante Topics
- Device-Read: `iot/{productKey}/{deviceId}/properties/read`
- Device-Write: `iot/{productKey}/{deviceId}/properties/write`
- Function Invoke: `iot/{productKey}/{deviceId}/function/invoke`
- Subscriptions erfolgen auf `/{productKey}/{deviceId}/#` und `iot/{productKey}/{deviceId}/#`.

#### Wichtige Subtopics (Ingress)
- `properties/report`: Haupttelemetrie.
- `properties/energy`: HEMS/Liveness-Indikator.
- `register/replay`: Re-Registration / Retain-Handling.
- `function/invoke/reply`, `properties/read/reply`: rueckseitige Bestaetigungen.

### 1.3 Lokale HTTP API (ZenSDK)

#### Endpunkte
- `GET http://{ipAddress}/properties/report`
- `POST http://{ipAddress}/properties/write`

#### Quelle im Code
- `custom_components/zendure_ha/device.py` (`ZendureZenSdk.httpGet/httpPost`)

#### Einsatzfall
- Lokaler Betriebsmodus bei ZenSDK-Geraeten (`connection` = `zenSDK`).
- Fallback/Ergaenzung fuer Status und Commands ohne Cloud-MQTT.

### 1.4 BLE Provisioning API

#### Transport
- BLE GATT Characteristic: `0000c304-0000-1000-8000-00805f9b34fb`

#### Befehle
- `token` (setzt WLAN/MQTT Daten)
- `station` (staedt Stationsinfo)

#### Einsatzfall
- Umstellung Legacy-Device auf Cloud- oder lokalen MQTT-Broker.

## 2. Interne Home Assistant APIs

### 2.1 ConfigEntry + Plattform-Lifecycle
- `async_setup_entry`, `async_unload_entry`, `async_migrate_entry` in `__init__.py`.
- Plattformen: Binary Sensor, Button, Number, Select, Sensor, Switch.

### 2.2 Coordinator API
- `ZendureManager` erweitert `DataUpdateCoordinator`.
- Regelmaessiger Poll ueber `_async_update_data()` (60 Sekunden).

### 2.3 Event API
- `async_track_state_change_event` fuer P1-Meter in `manager.py`.
- Handler `_p1_changed` triggert Lastverteilungslogik.

### 2.4 Device/Entity Registry APIs
- `device_registry` und `entity_registry` fuer Migrationen, Renames, Device-Infos.
- `RestoreEntity` fuer persistente Zustandswiederherstellung.

### 2.5 Auth API (lokaler MQTT-Fall)
- Nutzung von `homeassistant.auth` um pro Device lokale MQTT-Credentials bereitzustellen.

## 3. Interne Modul-Interfaces (Code-intern)

### 3.1 `Api` -> `ZendureDevice`
- `Api.devices` mappt Device-ID auf Instanz.
- MQTT-Handler rufen `device.mqttMessage(topic, payload)`.

### 3.2 `ZendureManager` -> `ZendureDevice`
- Polling: `await device.dataRefresh(update_count)`.
- Leistungssteuerung: `await device.power_charge(power)` / `await device.power_discharge(power)` / `await device.power_off()`.
- Statusabfrage: `await device.power_get()`.

### 3.3 `ZendureDevice` -> Entity-Layer
- `entityUpdate(key, value)` aktualisiert oder erstellt passende Entity.
- `entityWrite(entity, value)` schreibt Befehle via MQTT/HTTP.

## 4. Command-API nach Device-Typ

### 4.1 Legacy-Modelle
- Verwenden vor allem `function/invoke` mit `function = "deviceAutomation"`.
- Payload-Struktur pro Device leicht unterschiedlich, aber semantisch identisch (Charge/Discharge/Off).

### 4.2 ZenSDK-Modelle
- Bevorzugen `properties/write` (MQTT oder lokal HTTP je `connection`).
- Typischer Command setzt `smartMode`, `acMode`, `outputLimit`, `inputLimit`.

## 5. API-Grenzen fuer Refactoring
- `Api` sollte von globalem Zustand auf entry-lokalen Runtime-Context umgebaut werden.
- Transportprotokolle (MQTT/BLE/HTTP) sollten als Adapter hinter stabilen Device-Interfaces liegen.
- Einheitliches Command-Schema fuer Legacy-DeviceAutomation reduziert Duplikate und Fehlerflaeche.
