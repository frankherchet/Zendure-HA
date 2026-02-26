# Datenstrukturen Zendure-HA

## 1. Konfigurationsdaten

### 1.1 ConfigEntry-Datenfelder
Wesentliche Keys aus `const.py` und `config_flow.py`:
- `token` (`CONF_APPTOKEN`): base64-encodierter Zendure App Token.
- `p1meter` (`CONF_P1METER`): Entity-ID des Netzleistungssensors.
- `mqttlog` (`CONF_MQTTLOG`): MQTT-Logging aktiv/inaktiv.
- `mqttlocal` (`CONF_MQTTLOCAL`): lokale MQTT-Nutzung aktiviert.
- Lokale MQTT-Daten: `mqttserver`, `mqttport`, `mqttuser`, `mqttpsw`.
- BLE/WLAN-Provisionierung: `wifissid`, `wifipsw`.
- Optionale Simulation: `simulation`.

### 1.2 Persistenter Speicher
- Store-Datei ueber HA `Store` (`{DOMAIN}.storage`) fuer zwischengespeicherte Device-Daten.
- RestoreEntity fuer Number/Sensor/Select-Werte (zustandsbehaftete Entities).

## 2. Kernklassen und Objektgraph

### 2.1 `Api` (Transport- und Registry-Container)
- Enthaltene Daten:
  - `createdevice: dict[str, Callable]` (Produktmodell -> Device-Klasse)
  - `devices: dict[str, ZendureDevice]` (Device-ID -> Instanz)
  - MQTT-Clients: `mqttCloud`, `mqttLocal`
  - MQTT/WLAN-Konfigurationswerte (Server, Port, Credentials)
- Charakteristik: weitgehend **globaler Klassenzustand**.

### 2.2 `ZendureManager` (Orchestrator)
- Enthaltene Daten:
  - `devices: list[ZendureDevice]`
  - `fuseGroups: list[FuseGroup]`
  - Betriebszustand (`operation`, `operationstate`, Timer, History)
  - Verteiler-Container fuer `charge`, `discharge`, `idle`
- Zustaendig fuer Lastverteilung, Event-Verarbeitung und periodischen Refresh.

### 2.3 `EntityDevice` / `EntityZendure`
- `EntityDevice` haelt:
  - Device-Metadaten (`attr_device_info`, Name, IDs)
  - `entities: dict[str, EntityZendure]`
  - `createEntity`-Schema zur dynamischen Erzeugung.
- `EntityZendure` haelt:
  - `unique_id`, `translation_key`, Device-Verknuepfung.

### 2.4 `ZendureDevice`-Hierarchie
- Basisklasse `ZendureDevice`:
  - Transportfelder: `mqtt`, `zendure`, Topics.
  - Betriebsgrenzen: `charge_limit`, `discharge_limit`, `pwr_max`, etc.
  - Status: `state`, `lastseen`, `connectionStatus`, SOC/Power-Sensoren.
- Spezialisierungen:
  - `ZendureLegacy`: Cloud/lokales MQTT + BLE-Provisionierung.
  - `ZendureZenSdk`: MQTT + lokales HTTP (`httpGet/httpPost`).

### 2.5 `ZendureBattery`
- Sub-Device je Batterie-SN aus `packData`.
- Leitet Modell und Kapazitaet aus Seriennummern-Pruefzeichen ab.
- Ist via `via_device` dem Hauptgeraet zugeordnet.

### 2.6 `FuseGroup`
- Struktur:
  - `name`, `maxpower`, `minpower`, `devices`, `initPower`.
- Methoden:
  - `charge_limit(device)`
  - `discharge_limit(device)`
- Zweck: Leistungslimits bei gemeinsam abgesicherter Leitung.

## 3. Enums und Konstanten

### 3.1 Betriebsbezogene Enums
- `DeviceState`: `OFFLINE`, `SOCEMPTY`, `INACTIVE`, `SOCFULL`, `ACTIVE`.
- `ManagerMode`: `OFF`, `MANUAL`, `MATCHING`, `MATCHING_DISCHARGE`, `MATCHING_CHARGE`, `STORE_SOLAR`.
- `ManagerState`: `IDLE`, `CHARGE`, `DISCHARGE`, `OFF`.

### 3.2 Regelungsparameter (`SmartMode`)
- Timing: `TIMEFAST`, `TIMEZERO`, `P1_MIN_UPDATE`.
- Rauschfilter: `P1_STDDEV_FACTOR`, `P1_STDDEV_MIN`, `SETPOINT_STDDEV_*`.
- Leistungsgrenzen: `POWER_START`, `POWER_TOLERANCE`.
- HEMS-Timeout: `HEMSOFF_TIMEOUT`.

## 4. Payload- und Nachrichtenstrukturen

### 4.1 Cloud API Antwort (vereinfacht)
```json
{
  "code": 200,
  "success": true,
  "data": {
    "deviceList": [
      {
        "deviceKey": "...",
        "productModel": "Hyper 2000",
        "productKey": "...",
        "snNumber": "..."
      }
    ],
    "mqtt": {
      "url": "host:port",
      "clientId": "...",
      "username": "...",
      "password": "..."
    }
  }
}
```

### 4.2 MQTT Report Payload (vereinfacht)
```json
{
  "deviceId": "...",
  "properties": {
    "electricLevel": 74,
    "outputHomePower": 450
  },
  "packData": [
    {
      "sn": "A....",
      "electricLevel": 80
    }
  ]
}
```

### 4.3 Write-Payload fuer `properties/write`
```json
{
  "deviceId": "...",
  "messageId": 42,
  "timestamp": 1730000000,
  "properties": {
    "outputLimit": 600
  }
}
```

### 4.4 Function Invoke fuer Legacy Commands
```json
{
  "function": "deviceAutomation",
  "arguments": [
    {
      "autoModelProgram": 2,
      "autoModelValue": 500,
      "msgType": 1,
      "autoModel": 8
    }
  ],
  "deviceKey": "...",
  "messageId": 43,
  "timestamp": 1730000001
}
```

## 5. Entity-Mapping-Struktur
- `EntityDevice.createEntity` mappt Property-Keys auf Typ/Template/Einheit.
- Dynamische Erzeugung je Key in `entityUpdate`:
  - Sensor (`W`, `V`, `%`, `A`, `h`, `dBm`, `template`)
  - Binary Sensor (`binary`)
  - Switch (`switch`)
  - Select (`select`)
  - Ignoriert (`none`)
- Folge: hohe Flexibilitaet, aber zentraler Hotspot fuer Mapping-Korrektheit.
