# EMS-ESP WP PV Überschuss

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/actions/workflows/validate.yml/badge.svg)](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/WLW186iMuro/emsesp-wp-pv-ueberschuss)](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/releases/latest)
[![PayPal](https://img.shields.io/badge/PayPal-Projekt%20unterst%C3%BCtzen-00457C?logo=paypal&logoColor=white)](https://paypal.me/MDogan90)

> [!IMPORTANT]
> 🇬🇧 **English speakers:** the complete English documentation is at the end of this page → **[English version](#english)** · **[Full English guide](docs/guide.md)**

Home-Assistant-Integration, die eine Buderus-, Bosch- oder Junkers-Wärmepumpe über **[EMS-ESP](https://emsesp.org)** bei PV-Überschuss in den PV-/SG-Ready-Betrieb schaltet. Der Batteriespeicher hat Vorrang. Eine PV-Prognose (z. B. Solcast) kann berücksichtigt werden. Optional wird auch die Kompressorleistung an den Überschuss angepasst. Mit dabei ist eine Dashboard-Karte für Status und Einstellungen.

Du brauchst kein YAML, keine Helfer und keine Automationen: installieren, Entitäten auswählen, Karte aufs Dashboard.

> ✅ **Erfolgreich getestet mit einer Buderus WLW186i** (7 kW) im Alltagsbetrieb, zusammen mit EMS-ESP, einem GoodWe-Hybridwechselrichter (GW10K-ET) mit 10-kWh-Akku und Solcast unter Home Assistant 2026.10.
> EMS-ESP führt die WLW186i in derselben Gerätegruppe wie die Buderus WLW176i und die Bosch Compress CS5800i / CS6800i AW. Diese Modelle sollten daher genauso funktionieren. Rückmeldungen zu weiteren Modellen sind willkommen.

📖 **[Ausführliche Anleitung: wie alles funktioniert](docs/anleitung.md)**

![Dashboard-Karte](docs/screenshots/karte.png)

*Die Dashboard-Karte im echten Betrieb an einer Buderus WLW186i (abends: Sonne untergegangen, Akku fast leer – alle Startbedingungen auf einen Blick).*

## Funktionen

- **PV-Signal über EMS-ESP:** setzt ein Bit in der EMS-ESP-Eingangsoption, z. B. `text.boiler_hpin4opt`: `000000100000` ↔ `100000100000`. Das ist dasselbe Muster wie im evcc-Template für Buderus SG Ready. Nach Neustarts von EMS-ESP oder HA wird der Wert wieder gesetzt.
- **Akku zuerst:** Die Ladeleistung des Akkus zählt erst als Überschuss, wenn der Freigabe-Ladestand erreicht ist oder der Akku laut Prognose heute noch voll wird.
- **Schaltlogik:**
  - Hysterese mit Ein-/Ausschaltschwelle und Verzögerungen
  - Mindestlaufzeit, danach Sperrzeit nach jedem Stopp
  - maximale Aktivierungen pro Tag
  - Startfenster
- **Sofort-Stopp:** bei Akku unter der Abschaltgrenze (2 min), bei Sonnenuntergang oder wenn Messwerte 10 min fehlen.
- **Leistungsnachführung (optional):** passt im PV-Betrieb `PV max. Kompressorleistung` (`pvmaxcomp`) an das gemittelte Budget an (aktuelle Kompressorleistung + verbleibender Überschuss). Die Grenze bleibt in einem Min/Max-Bereich und ändert sich nur alle *n* Minuten, nicht im Sekundentakt.
- **Strompreis-Steuerung (optional):** für dynamische oder zeitvariable Tarife (Tibber, aWATTar, Octopus …). Bei günstigem Strom PV-Betrieb auch ohne Überschuss, bei teurem Strom kein Start. Ohne Preis-Sensor unsichtbar; mit Preis-Sensor erst nach Einschalten der *Preissteuerung* einstellbar. [Details](docs/anleitung.md#7-strompreis-steuerung-optional)
- **Peak-Modus (optional):** setzt bei hohem Stundenpreis und leerem Akku die EVU-Sperre der Wärmepumpe (ein wählbares Bit von z. B. `text.boiler_hpin1opt`, Standard: erstes Zeichen) und hebt sie wieder auf, sobald der Preis sinkt – spätestens nach der maximalen Sperrdauer. [Details](docs/anleitung.md#71-peak-modus-evu-sperre-bei-hohem-preis-und-leerem-akku)
- **Beobachtungsmodus:** rechnet und schreibt Logbuch-Einträge („würde starten …“), schreibt aber nichts an die Wärmepumpe. **Neue Einrichtungen starten in diesem Modus.**
- **Betriebsarten:** Automatik, Aus (gibt die Wärmepumpe in den Normalbetrieb zurück), Manuell (PV-Betrieb an).
- **Dashboard-Karte:** Status, Live-Werte, Checkliste der Startbedingungen, Betriebsart und alle Einstellungen. Die Integration lädt die Karte selbst, ein Ressourcen-Eintrag ist nicht nötig.
- Deutsch und Englisch. Diagnose-Download für Fehlerberichte.

## Screenshots

Alle Bilder stammen aus einer laufenden Installation (Buderus WLW186i, GoodWe GW10K-ET, Solcast).

| Einrichtung: Quell-Entitäten (1/2) | Einrichtung: Quell-Entitäten (2/2) |
|---|---|
| ![Einrichtung 1](docs/screenshots/einrichtung-1.png) | ![Einrichtung 2](docs/screenshots/einrichtung-2.png) |

| Einstellungen in der Karte (1/2) | Einstellungen in der Karte (2/2) |
|---|---|
| ![Einstellungen 1](docs/screenshots/einstellungen-1.png) | ![Einstellungen 2](docs/screenshots/einstellungen-2.png) |

**Logbuch eines echten Tages im Beobachtungsmodus** – Start nach 5 Minuten stabilem Überschuss, danach Anpassung der Kompressorleistung alle 5 Minuten, am Ende Stopp mangels Überschuss und Sperrzeit:

| Vormittag: Start und Leistungsanpassung | Nachmittag: Defizit, Stopp, Sperrzeit |
|---|---|
| ![Logbuch Start](docs/screenshots/logbuch-start.png) | ![Logbuch Ende](docs/screenshots/logbuch-ende.png) |

**Geräteseite** mit Betriebsart, Sensoren und Verlauf:

![Geräteseite](docs/screenshots/geraet.png)

## Voraussetzungen

- Home Assistant **2025.3** oder neuer
- EMS-ESP, bei dem die Eingangsoptionen der Wärmepumpe als `text`-Entitäten vorhanden sind (z. B. `hpin4opt`). Optional zusätzlich `number.boiler_pvmaxcomp` und `sensor.boiler_hpcurrpower`.
- Sensoren für Netzleistung, Akku-Leistung und Akku-Ladestand (beliebige Wechselrichter-Integration, z. B. GoodWe, Fronius, SMA, Huawei, Victron …)
- Optional: PV-Prognose (z. B. [Solcast](https://github.com/BJReplay/ha-solcast-solar) „verbleibende Prognose heute“ in kWh und „Leistung in 30 Minuten“ in W)
- Optional: ein Strompreis-Sensor für dynamische / zeitvariable Tarife (z. B. Tibber, Nord Pool, EPEX Spot, Octopus Germany)
- An der Wärmepumpe muss der Eingang (z. B. Eingang 4) im Regler (HMC300 / HPC410 / Fachmann-Menü) für PV / SG Ready eingestellt sein.

> ⚠️ Lass nicht mehrere Steuerungen gleichzeitig auf dieselbe Eingangs-Entität schreiben (evcc SG Ready, eigene Automationen, Node-RED …), sonst überschreiben sie sich gegenseitig. Zum Vergleich zuerst den Beobachtungsmodus nutzen.

## Installation

### HACS (empfohlen)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss` mit der Kategorie **Integration** hinzufügen.
2. Nach **EMS-ESP WP PV Überschuss** suchen und installieren.
3. Home Assistant neu starten.

### Manuell

1. `emsesp_pv_surplus.zip` aus dem [neuesten Release](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/releases/latest) herunterladen.
2. Nach `config/custom_components/emsesp_pv_surplus/` entpacken, z. B. über die Samba-Freigabe oder Studio Code Server.
3. Home Assistant neu starten.

## Einrichtung

**Einstellungen → Geräte & Dienste → Integration hinzufügen → „EMS-ESP WP PV Überschuss“**

| Feld | Beispiel | Hinweis |
|---|---|---|
| EMS-ESP Eingangs-Option | `text.boiler_hpin4opt` | Pflicht |
| Bit-Position | `0` | 0 = erstes Zeichen; bei Buderus/Bosch/Junkers für PV/SG meist 0 |
| Netzleistung | Zähler in W/kW | Vorzeichen wählbar (Bezug positiv / Einspeisung positiv) |
| Akku-Leistung | Akku in W/kW | Vorzeichen wählbar (Entladen positiv / Laden positiv) |
| Akku-Ladestand | SoC in % | Pflicht |
| PV max. Kompressorleistung | `number.boiler_pvmaxcomp` | optional, aktiviert die Nachführung |
| Aktuelle Kompressorleistung | `sensor.boiler_hpcurrpower` | Pflicht bei Nachführung |
| PV-Prognose verbleibend heute | Solcast, kWh | optional |
| PV-Prognose in 30 min | Solcast, W | optional |
| Strompreis-Sensor | z. B. Tibber `EUR/kWh` | optional, nur bei dynamischem / zeitvariablem Tarif |
| Einheit des Strompreis-Sensors | Automatisch | nur ändern, wenn der Sensor keine Einheit hat; gilt für alle Preis-Sensoren |
| Eingangs-Option für die EVU-Sperre | `text.boiler_hpin1opt` | optional, Peak-Modus |
| Bit-Position der EVU-Sperre | `0` | 0 = erstes Zeichen |
| Akku-Notstromreserve | Reserve in % | Pflicht beim Peak-Modus |
| Aktueller Stundenpreis | Tibber „Hourly price current“ | Pflicht beim Peak-Modus |
| Durchschnittspreis heute | Tibber „Average price today“ | Pflicht beim Peak-Modus |

Später änderbar über **Integration → Konfigurieren**. Wenn das Verhalten im Beobachtungsmodus passt, schalte auf der Karte den **Beobachtungsmodus** aus.

## Dashboard-Karte

Dashboard bearbeiten → **Karte hinzufügen** → „EMS-ESP WP PV Überschuss“, oder in YAML:

```yaml
type: custom:emsesp-pv-surplus-card
# device_id: …          # nur bei mehreren Einrichtungen
# title: Wärmepumpe PV
# show_settings: true
```

## Einstellungen und Standardwerte

Alle Einstellungen sind Entitäten (number / switch / select / time). Du kannst sie also auch in Automationen oder Skripten verwenden.

| Einstellung | Standard | Bedeutung |
|---|---|---|
| Einschaltschwelle | 1500 W | nötige verfügbare Leistung zum Start |
| Ausschaltschwelle | −800 W | darunter (also 800 W Bezug) läuft die Ausschaltverzögerung |
| Ein-/Ausschaltverzögerung | 5 / 10 min | wie lange die Bedingung anliegen muss |
| Akku-Freigabe ab | 80 % | ab diesem SoC zählt die Ladeleistung als Überschuss |
| Akku-Freigabe mit Prognose ab | 60 % | frühere Freigabe, wenn die Prognose die fehlende Energie + Reserve deckt |
| Akku-Kapazität / Prognose-Reserve | 10 kWh / 4 kWh | für die Prognoseprüfung |
| Akku-Abschaltgrenze | 50 % | darunter Stopp und keine Starts |
| Mindestlaufzeit | 30 min | vorher kein Stopp wegen fehlenden Überschusses |
| Sperrzeit | 120 min | nach jedem Stopp |
| Max. Aktivierungen pro Tag | 2 | |
| Startfenster | 10:00–16:00 | Starts nur in diesem Fenster, Stopps jederzeit |
| Kompressorleistung min./max. | 1,0 / 2,5 kW | Bereich für `pvmaxcomp` |
| Leistungsreserve / Mindeständerung / Intervall | 0,1 kW / 0,2 kW / 5 min | |
| Günstig-Schwelle / Teuer-Schwelle | 15 / 35 ct/kWh | nur mit Preissteuerung |
| Bei teurem Strom beenden | aus | nur mit Preissteuerung |
| Kompressorleistung bei günstigem Strom | 2,5 kW | nur mit Preissteuerung und Leistungsnachführung |
| Peak: Preis über Tagesdurchschnitt | 108 % | EVU-Sperre ab Stundenpreis > Ø × Wert, Aufhebung darunter |
| Peak: Abstand zur Notstromreserve | 2 % | EVU-Sperre ab Ladestand ≤ Reserve + Wert |
| Peak: Netzbezug seit mindestens | 10 min | verfügbare Leistung ≤ 0 W am Stück |
| Peak: Max. Dauer der EVU-Sperre | 120 min | danach immer aufheben, egal wie der Preis ist |
| Peak: Sperrzeit / Max. Aktivierungen pro Tag | 60 min / 2 | Pause nach der letzten EVU-Sperre |

Passe die Standardwerte an deine Anlage an: die Akku-Kapazität und den Kompressorbereich für deine Wärmepumpe (die Standardwerte passen zu einem 7-kW-Gerät wie der WLW186i-7).

### Berechnung des Überschusses

```
verfügbar = −Netz − (Akku            wenn Akku freigegeben
                     max(Akku, 0)    sonst)
            (Netz + = Bezug, Akku + = Entladen)

Budget    = Kompressorleistung + verfügbar   (gemittelt über das Intervall)
Ziel      = begrenzt(Budget − Reserve, min, max) bei Akku-Freigabe, sonst min
```

## Entitäten

- **Sensoren:** Status (mit vielen Attributen), verfügbare Leistung, Leistungsbudget, Kompressor-Zielleistung, Aktivierungen heute, PV-Laufzeit heute, Sperrzeit bis
- **Binärsensoren:** PV-Betrieb angefordert, PV-Signal an Wärmepumpe, Akku-Freigabe, Überschuss über Einschaltschwelle; mit Peak-Modus: EVU-Sperre angefordert, EVU-Signal an Wärmepumpe
- **Tasten:** Sperrzeit aufheben, Tageszähler zurücksetzen (mit Peak-Modus auch für die EVU-Sperre)

## Entfernen

Wenn du die Integration löschst, setzt sie das PV-Bit auf Normalbetrieb zurück, falls sie es gesetzt hatte.

## Fehlersuche

- **Karte zeigt „Custom element doesn't exist“:** Seite einmal mit Strg+F5 neu laden. Die Karte ist als Dashboard-Ressource registriert (`/emsesp_pv_surplus/emsesp-pv-surplus-card.js`). Wenn deine Dashboards im YAML-Modus laufen, trage sie selbst als Ressource vom Typ `module` ein.
- **Status „Messwerte fehlen“:** Eine Quell-Entität ist länger als 2 Minuten `unavailable`. Kürzere Aussetzer werden ignoriert.
- **Fehlerberichte:** bitte den Diagnose-Download anhängen (Integration → ⋮ → Diagnosedaten herunterladen).

## Haftungsausschluss

Das ist kein offizielles Projekt von EMS-ESP, Bosch, Buderus oder Junkers. Nutzung auf eigene Gefahr. Prüfe die Eingangskonfiguration deiner Wärmepumpe und die Vorgaben des Herstellers.

## Getestet mit

| Komponente | Version / Modell |
|---|---|
| Wärmepumpe | Buderus WLW186i, 7 kW |
| Anbindung | EMS-ESP (MQTT-Discovery), Eingang 4 (`hpin4opt`), `pvmaxcomp`, `hpcurrpower` |
| Wechselrichter / Akku | GoodWe GW10K-ET, 10 kWh |
| Prognose | Solcast PV Forecast |
| Home Assistant | 2026.10 (Home Assistant OS) |

Du nutzt ein anderes Modell? Schreib gern in einem [Issue](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/issues), ob es funktioniert.

## Projekt unterstützen

Dir gefällt die Integration und sie spart dir Strom? Über eine kleine Unterstützung freue ich mich sehr – sie hilft, das Projekt weiterzuentwickeln. ☕

[![Mit PayPal unterstützen](https://www.paypalobjects.com/de_DE/DE/i/btn/btn_donateCC_LG.gif)](https://paypal.me/MDogan90)

Auch ein ⭐ auf GitHub und Rückmeldungen zu weiteren Wärmepumpen-Modellen helfen sehr.

## Lizenz

[MIT](LICENSE)

---

<a id="english"></a>

## 🇬🇧 English version

> [!NOTE]
> **This is the English part of the documentation.** The German version is above. For step-by-step details, see the **[full English guide](docs/guide.md)**. The screenshots show the German interface; with Home Assistant set to English, the integration and the card are shown in English automatically.

A Home Assistant integration that switches a Buderus, Bosch or Junkers heat pump into its PV / SG Ready mode through **[EMS-ESP](https://emsesp.org)** when there is solar surplus. The home battery gets priority, and a PV forecast (for example Solcast) can be taken into account. It can also adjust the compressor power limit to match the surplus. It comes with a dashboard card for status and settings.

No YAML, no helpers, no automations: you install it, pick your entities, and put the card on a dashboard.

> ✅ **Successfully tested with a Buderus WLW186i** (7 kW) in everyday use, together with EMS-ESP, a GoodWe hybrid inverter (GW10K-ET) with a 10 kWh battery and Solcast on Home Assistant 2026.10.
> EMS-ESP puts the WLW186i in the same device group as the Buderus WLW176i and the Bosch Compress CS5800i / CS6800i AW, so these models should work the same way. Feedback on other models is welcome.

📖 **[Full English guide: how everything works](docs/guide.md)**

![Dashboard card](docs/screenshots/karte.png)

### Features

- **PV signal via EMS-ESP:** sets one bit of an EMS-ESP input option, e.g. `text.boiler_hpin4opt`: `000000100000` ↔ `100000100000`. This is the same pattern the evcc template for Buderus SG Ready uses. The value is written again after EMS-ESP or Home Assistant restarts.
- **Battery first:** the battery's charging power only counts as surplus once the battery has reached the release level, or when the forecast says it will still be full today.
- **Switching rules:**
  - hysteresis with on/off thresholds and delays
  - a minimum runtime, then a lock time after each stop
  - a maximum number of activations per day
  - a daily start window
- **Immediate stop:** when the battery falls below the stop level (for 2 min), at sunset, or when readings are missing for 10 min.
- **Compressor power control (optional):** in PV mode it adjusts `PV max. compressor power` (`pvmaxcomp`) to the averaged budget (current compressor power + remaining surplus). The limit stays inside a min/max range and changes only every *n* minutes, never second by second.
- **Price control (optional):** for dynamic or time-of-use tariffs (Tibber, aWATTar, Octopus …). PV mode even without surplus when electricity is cheap, no start when it is expensive. Invisible without a price sensor; with one, adjustable only after turning on *Price control*. [Details](docs/guide.md#7-price-control-optional)
- **Peak mode (optional):** sets the heat pump's EVU block (a selectable bit of e.g. `text.boiler_hpin1opt`, default: first character) when the hourly price is high and the battery is empty, and lifts it as soon as the price drops, at the latest after the maximum block duration. [Details](docs/guide.md#71-peak-mode-evu-block-on-high-price-and-empty-battery)
- **Observe mode:** it calculates and writes logbook entries ("would start …") but does not write anything to the heat pump. **New installations start in observe mode**, so you can compare it with your current setup first.
- **Modes:** automatic, off (hands the heat pump back to normal operation), manual (PV mode on).
- **Dashboard card:** status, live values, a start-condition checklist, the mode buttons and all settings in one card. The integration loads it automatically, so no resource entry is needed.
- German and English. Diagnostics download for bug reports.

### Requirements

- Home Assistant **2025.3** or newer
- EMS-ESP with the heat pump's input options exposed as `text` entities (e.g. `hpin4opt`). Optionally also `number.boiler_pvmaxcomp` and `sensor.boiler_hpcurrpower`.
- Sensors for grid power, battery power and battery state of charge (any inverter integration, e.g. GoodWe, Fronius, SMA, Huawei, Victron …)
- Optional: a PV forecast (e.g. [Solcast](https://github.com/BJReplay/ha-solcast-solar) "forecast remaining today" in kWh and "power in 30 minutes" in W)
- Optional: an electricity price sensor for dynamic / time-of-use tariffs (e.g. Tibber, Nord Pool, EPEX Spot, Octopus Germany)
- On the heat pump, the input (e.g. input 4) must be configured for PV / SG Ready on the controller (HMC300 / HPC410 / installer menu).

> ⚠️ Don't run several controllers on the same input entity at the same time (evcc SG Ready, your own automations, Node-RED …), or they will overwrite each other. Use observe mode to compare them first.

### Installation

#### HACS (recommended)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss` with the category **Integration**.
2. Search for **EMS-ESP WP PV Überschuss** and install it.
3. Restart Home Assistant.

#### Manual

1. Download `emsesp_pv_surplus.zip` from the [latest release](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/releases/latest).
2. Extract it to `config/custom_components/emsesp_pv_surplus/`, for example through the Samba share or Studio Code Server.
3. Restart Home Assistant.

### Setup

**Settings → Devices & services → Add integration → "EMS-ESP WP PV Überschuss"**

| Field | Example | Notes |
|---|---|---|
| EMS-ESP input option | `text.boiler_hpin4opt` | required |
| Bit position | `0` | 0 = first character; usually 0 for PV/SG on Buderus/Bosch/Junkers |
| Grid power | grid meter in W/kW | sign selectable (import positive / export positive) |
| Battery power | battery power in W/kW | sign selectable (discharge positive / charge positive) |
| Battery state of charge | SoC in % | required |
| PV max. compressor power | `number.boiler_pvmaxcomp` | optional, enables power control |
| Current compressor power | `sensor.boiler_hpcurrpower` | required if power control is used |
| PV forecast remaining today | Solcast, kWh | optional |
| PV forecast power in 30 min | Solcast, W | optional |
| Electricity price sensor | e.g. Tibber `EUR/kWh` | optional, only with a dynamic / time-of-use tariff |
| Unit of the price sensor | Automatic | only change it if the sensor has no unit |

Change these later via **Integration → Configure**. When you're happy with the behaviour in observe mode, turn **Observe mode** off on the card.

### Dashboard card

Edit dashboard → **Add card** → "EMS-ESP WP PV Überschuss", or in YAML:

```yaml
type: custom:emsesp-pv-surplus-card
# device_id: …          # only needed with more than one instance
# title: Heat pump PV
# show_settings: true
```

### Settings and defaults

All settings are entities (number / switch / select / time), so you can also use them in automations or scripts.

| Setting | Default | Meaning |
|---|---|---|
| Switch-on threshold | 1500 W | available power needed to start |
| Switch-off threshold | −800 W | below this (i.e. 800 W import) the off delay starts |
| Switch-on / switch-off delay | 5 / 10 min | how long the condition must hold |
| Battery release from | 80 % | from this SoC the charging power counts as surplus |
| Battery release with forecast from | 60 % | earlier release if the forecast covers the missing energy + reserve |
| Battery capacity / forecast reserve | 10 kWh / 4 kWh | for the forecast check |
| Battery stop level | 50 % | stops PV mode and blocks starts below this SoC |
| Minimum runtime | 30 min | no deficit stop before this |
| Lock time | 120 min | after each stop |
| Max. activations per day | 2 | |
| Start window | 10:00–16:00 | starts only in this window; stops are always possible |
| Compressor power min. / max. | 1.0 / 2.5 kW | range for `pvmaxcomp` |
| Power reserve / minimum change / interval | 0.1 kW / 0.2 kW / 5 min | |
| Cheap / expensive threshold | 15 / 35 ct/kWh | only with price control |
| Stop when expensive | off | only with price control |
| Compressor power on cheap electricity | 2.5 kW | only with price control and power control |
| Peak: price above daily average | 108 % | EVU block from hourly price > avg × value, lifted below |
| Peak: margin above backup reserve | 2 % | EVU block from SoC ≤ reserve + value |
| Peak: grid import for at least | 10 min | available power ≤ 0 W without a break |
| Peak: max. EVU block duration | 120 min | always lifted after this, whatever the price |
| Peak: lock time / max. activations per day | 60 min / 2 | pause after the last EVU lock activation |

Match the defaults to your system: the battery capacity, and the compressor range for your heat pump (the defaults suit a 7 kW unit such as the WLW186i-7).

#### How the surplus is calculated

```
available = −grid − (battery            if battery released
                     max(battery, 0)    otherwise)
            (grid + = import, battery + = discharge)

budget    = compressor power + available   (averaged over the interval)
target    = clamp(budget − reserve, min, max) if battery released, otherwise min
```

### Entities

- **Sensors:** status (with lots of attributes), available power, power budget, compressor target, activations today, PV runtime today, locked until
- **Binary sensors:** PV mode requested, PV signal at heat pump, battery release, surplus above threshold; with peak mode: EVU block requested, EVU signal at heat pump
- **Buttons:** lift lock time, reset daily counter (with peak mode also for the EVU block)

### Removing it

When you delete the integration, it resets the PV bit to normal if it had set it.

### Troubleshooting

- **Card shows "Custom element doesn't exist":** reload the page once with Ctrl+F5. The card is registered as a dashboard resource (`/emsesp_pv_surplus/emsesp-pv-surplus-card.js`). If your dashboards are in YAML mode, add it yourself as a resource of type `module`.
- **Status "Readings missing":** one of the source entities is `unavailable` for more than 2 minutes. Shorter dropouts are ignored.
- **Bug reports:** please attach the diagnostics download (Integration → ⋮ → Download diagnostics).

### Development

```bash
python -m unittest discover -s tests      # logic tests (no HA install needed)
node tests/card_check.mjs <out-dir>       # render the card with Playwright
python tools/gen_translations.py          # regenerate translations
```

### Disclaimer

This is not an official project of EMS-ESP, Bosch, Buderus or Junkers. You use it at your own risk. Check the input configuration of your heat pump and what your manufacturer specifies.

### Tested with

| Component | Version / model |
|---|---|
| Heat pump | Buderus WLW186i, 7 kW |
| Connection | EMS-ESP (MQTT discovery), input 4 (`hpin4opt`), `pvmaxcomp`, `hpcurrpower` |
| Inverter / battery | GoodWe GW10K-ET, 10 kWh |
| Forecast | Solcast PV Forecast |
| Home Assistant | 2026.10 (Home Assistant OS) |

Using a different model? Please let us know in an [issue](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/issues) whether it works.

### Support the project

If you like the integration and it saves you energy, a small donation is very welcome and helps keep the project going. ☕

[![Donate with PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://paypal.me/MDogan90)

A ⭐ on GitHub and feedback about other heat pump models help a lot, too.

### License

[MIT](LICENSE)
