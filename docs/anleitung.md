# Anleitung – EMS-ESP WP PV Überschuss

🇬🇧 [English guide](guide.md) · [Zurück zur Übersicht](../README.md)

Diese Anleitung erklärt Schritt für Schritt, wie die Integration arbeitet, wie du sie einrichtest und was du auf der Karte siehst.

**Inhalt**

1. [Grundidee](#1-grundidee)
2. [Bevor du anfängst](#2-bevor-du-anfängst)
3. [Einrichtung Schritt für Schritt](#3-einrichtung-schritt-für-schritt)
4. [Die ersten Tage: Beobachtungsmodus](#4-die-ersten-tage-beobachtungsmodus)
5. [So entscheidet die Integration](#5-so-entscheidet-die-integration)
6. [Leistungsnachführung (pvmaxcomp)](#6-leistungsnachführung-pvmaxcomp)
7. [Strompreis-Steuerung (optional)](#7-strompreis-steuerung-optional)
8. [Die Dashboard-Karte erklärt](#8-die-dashboard-karte-erklärt)
9. [Betriebsarten](#9-betriebsarten)
10. [Einstellungen anpassen – Empfehlungen](#10-einstellungen-anpassen--empfehlungen)
11. [Beispiel: ein sonniger Tag](#11-beispiel-ein-sonniger-tag)
12. [Entitäten für eigene Automationen](#12-entitäten-für-eigene-automationen)
13. [Häufige Fragen und Fehlersuche](#13-häufige-fragen-und-fehlersuche)

---

## 1. Grundidee

Buderus-, Bosch- und Junkers-Wärmepumpen haben einen Eingang für PV / SG Ready. Ist er aktiv, nutzt die Wärmepumpe den Solarstrom, z. B. mit höherer Warmwasser-Temperatur oder einer Anhebung der Heizung (je nach Einstellung im Regler). EMS-ESP stellt diesen Eingang als Text mit einem Bitmuster bereit, z. B. `text.boiler_hpin4opt`:

| Zustand | Bitmuster |
|---|---|
| Normalbetrieb | `000000100000` |
| PV-Betrieb | `100000100000` |

Die Integration setzt das erste Zeichen (Bit 0) auf `1`, wenn genug Solarstrom übrig ist, und wieder auf `0`, wenn nicht. Dabei achtet sie auf drei Dinge:

- **Der Akku geht vor.** Erst wenn der Hausakku ausreichend geladen ist (oder laut Prognose heute noch voll wird), darf der Solarstrom in die Wärmepumpe.
- **Der Kompressor wird geschont.** Hysterese, Mindestlaufzeit, Sperrzeit und ein Tageslimit verhindern häufiges Takten.
- **Kein Netzstrom für den PV-Betrieb.** Optional begrenzt sie die Kompressorleistung (`pvmaxcomp`) auf den Überschuss.

## 2. Bevor du anfängst

Du brauchst:

- **EMS-ESP** mit Anbindung an Home Assistant (MQTT-Discovery oder EMS-ESP-Integration). Prüfe unter *Einstellungen → Geräte & Dienste → Entitäten*, ob es `text.boiler_hpin1opt` … `hpin4opt` gibt.
- **An der Wärmepumpe** muss ein Eingang (meist Eingang 4) im Fachmann-Menü für *PV / SG Ready* eingestellt sein. Ohne diese Einstellung reagiert die Wärmepumpe nicht auf das Bit.
- **Wechselrichter-Sensoren:** Netzleistung, Akku-Leistung und Akku-Ladestand. Prüfe die Vorzeichen: Was ist positiv bei Bezug, was beim Laden?
- **Optional:** Solcast (oder eine andere PV-Prognose) sowie `number.boiler_pvmaxcomp` und `sensor.boiler_hpcurrpower` für die Leistungsnachführung.

> ⚠️ **Wichtig:** Schalte andere Steuerungen auf denselben Eingang ab (evcc SG Ready, eigene Automationen, Node-RED). Im Modus *Automatik* hält die Integration das Bit aktiv auf dem gewünschten Wert und überschreibt fremde Änderungen innerhalb einer Minute.

## 3. Einrichtung Schritt für Schritt

1. **Installieren:** über HACS (*Benutzerdefinierte Repositories* → `https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss`, Kategorie *Integration*) oder manuell nach `config/custom_components/emsesp_pv_surplus/`. Danach Home Assistant neu starten.
2. **Hinzufügen:** *Einstellungen → Geräte & Dienste → Integration hinzufügen → „EMS-ESP WP PV Überschuss“*.
3. **Entitäten auswählen:**

   | Feld | Beispiel | Hinweis |
   |---|---|---|
   | Name | PV-Überschuss Wärmepumpe | Gerätename, bestimmt die Entitäts-IDs |
   | EMS-ESP Eingangs-Option | `text.boiler_hpin4opt` | der für PV eingestellte Eingang |
   | Bit-Position | `0` | erstes Zeichen |
   | Netzleistung | z. B. Smart-Meter in W | Vorzeichen wählen |
   | Akku-Leistung | z. B. GoodWe Battery Power | Vorzeichen wählen |
   | Akku-Ladestand | SoC in % | |
   | PV max. Kompressorleistung | `number.boiler_pvmaxcomp` | optional |
   | Aktuelle Kompressorleistung | `sensor.boiler_hpcurrpower` | Pflicht, wenn pvmaxcomp gewählt |
   | Prognose verbleibend heute | Solcast „Prognose verbleibende Leistung heute“ (kWh) | optional |
   | Prognose in 30 min | Solcast „Leistung in 30 Minuten“ (W) | optional |

   ![Einrichtung: Quell-Entitäten](screenshots/einrichtung-1.png) ![Einrichtung: optionale Entitäten](screenshots/einrichtung-2.png)

4. **Karte aufs Dashboard:** *Dashboard bearbeiten → Karte hinzufügen →* nach „EMS-ESP WP PV Überschuss“ suchen. Die Karte findet die Integration selbst.
5. **Vorzeichen prüfen:** Schau auf der Karte bei Sonnenschein auf die Kachel *Netz*. Speist du ein, muss dort „Einspeisung“ stehen. Steht „Bezug“, ist das Vorzeichen falsch. Ändern kannst du es unter *Integration → Konfigurieren*.

## 4. Die ersten Tage: Beobachtungsmodus

Neue Einrichtungen starten im **Beobachtungsmodus**. Die Integration rechnet alles durch, schreibt aber nichts an die Wärmepumpe. Stattdessen erscheinen Einträge im Logbuch, z. B.:

```
[Beobachtung] würde PV-Betrieb starten (PV-Überschuss)
[Beobachtung] würde PV max. Kompressorleistung 1.0 → 2.2 kW setzen (Budget Ø 2312 W)
[Beobachtung] würde PV-Betrieb beenden (kein Überschuss mehr)
```

![Logbuch im Beobachtungsmodus](screenshots/logbuch-start.png)

So kannst du ein paar sonnige Tage lang prüfen, ob die Starts und Stopps zu deinem Haus passen. Wenn alles stimmt, schaltest du auf der Karte den Schalter **Beobachtungsmodus** aus. Ab dann wird wirklich geschaltet.

## 5. So entscheidet die Integration

Alle 15 Sekunden liest die Integration die Sensoren und entscheidet neu.

### 5.1 Verfügbare Leistung

```
verfügbar = Einspeisung − Akku-Entladung − (Akku-Ladung, wenn der Akku freigegeben ist)
```

- Einspeisung ins Netz zählt immer als Überschuss.
- Entlädt der Akku, wird das abgezogen. Die Wärmepumpe soll nicht aus dem Akku laufen.
- **Lädt** der Akku, zählt diese Ladeleistung nur als Überschuss, wenn der Akku **freigegeben** ist. Vorher hat der Akku Vorrang.

**Akku-Freigabe**, wenn eine der beiden Bedingungen erfüllt ist:

- Ladestand ≥ *Akku-Freigabe ab* (Standard 80 %), **oder**
- Ladestand ≥ *Freigabe mit Prognose ab* (Standard 60 %) **und** die Prognose für den Rest des Tages abzüglich *Prognose-Reserve* (4 kWh) reicht, um den Akku voll zu bekommen.

*Beispiel:* Akku 10 kWh, Ladestand 65 % → es fehlen 3,5 kWh. Solcast meldet noch 9 kWh für heute. 9 − 4 = 5 kWh ≥ 3,5 kWh → **freigegeben**.

### 5.2 Einschalten

PV-Betrieb startet, wenn **alle** Startbedingungen erfüllt sind. Die Karte zeigt sie als Checkliste:

| Bedingung | Standard |
|---|---|
| Messwerte vorhanden | Netz, Akku, SoC lesbar |
| Sonne über dem Horizont | `sun.sun` |
| Im Startfenster | 10:00–16:00 |
| Akku über Abschaltgrenze | > 50 % |
| Keine Sperrzeit | 120 min nach dem letzten Stopp |
| Tageslimit nicht erreicht | max. 2 Starts pro Tag |
| Überschuss ≥ Einschaltschwelle | ≥ 1500 W |
| Prognose in 30 min ≥ Schwelle | Solcast ≥ 1500 W (falls aktiviert) |
| Überschuss lange genug stabil | 5 min am Stück |

Fällt der Überschuss während der Einschaltverzögerung kurz unter die Schwelle, beginnt die Verzögerung von vorn. Eine kurze Wolke startet die Wärmepumpe also nicht.

### 5.3 Ausschalten

| Grund | Wann |
|---|---|
| Kein Überschuss mehr | nach der **Mindestlaufzeit** (30 min), wenn die verfügbare Leistung **10 min** am Stück ≤ **−800 W** ist (also 800 W Bezug aus Netz/Akku) |
| Akku zu leer | sofort, wenn der Ladestand 2 min unter der Abschaltgrenze (50 %) liegt |
| Sonnenuntergang | sofort |
| Messwerte fehlen | nach 10 min ohne Netz-, Akku- oder SoC-Wert |
| Wärmepumpe fertig (optional) | wenn der Kompressor im PV-Betrieb gelaufen ist und danach so lange still steht wie unter *Beenden nach Kompressor-Stillstand* eingestellt (Standard 0 = aus) |

Zwischen −800 W und +1500 W läuft die Wärmepumpe einfach weiter. Das ist die **Hysterese**. Sie verhindert, dass eine vorbeiziehende Wolke den Kompressor ausschaltet.

Nach jedem Stopp beginnt die **Sperrzeit** (120 min). Erst danach ist ein neuer Start möglich, maximal 2 pro Tag.

**Beenden nach Kompressor-Stillstand (optional, nur mit Leistungsnachführung):** Solange das PV-Signal anliegt, gilt an der Wärmepumpe meist ein höheres Warmwasser-Soll. Schafft sie es mit wenig Kompressorleistung nicht ganz, bricht sie ab und startet nach ihrer eigenen Pause einen weiteren, oft nutzlosen Versuch. Mit dieser Einstellung beendet die Integration den PV-Betrieb, sobald der Kompressor gelaufen ist und danach die eingestellte Zeit still steht (unter 200 W). Danach gilt die Sperrzeit. Wähle die Zeit länger als die normale Pause deiner Wärmepumpe zwischen Warmwasser und Heizen (bei der WLW186i rund 15 min), z. B. **20 min**. Sonst endet der PV-Betrieb, bevor die Wärmepumpe mit PV-Anhebung weiterheizt.

## 6. Leistungsnachführung (pvmaxcomp)

Im PV-Betrieb würde die Wärmepumpe sonst mit voller Leistung laufen, auch wenn nur 1,5 kW Überschuss da sind. Mit `number.boiler_pvmaxcomp` (*PV max. Kompressorleistung*) lässt sich der Kompressor im PV-Modus begrenzen. Die Integration passt diesen Wert an:

1. Sie bildet laufend das **Budget** = aktuelle Kompressorleistung + verfügbare Leistung. Das ist die Leistung, die die Wärmepumpe haben dürfte, ohne Strom zu beziehen.
2. Das Budget wird über das **Anpassungsintervall** (5 min) gemittelt.
3. Alle 5 Minuten wird das Ziel berechnet: `Budget Ø − Reserve (0,1 kW)`, begrenzt auf **min. 1,0 kW** und **max. 2,5 kW**.
4. Geschrieben wird nur, wenn sich das Ziel um mindestens **0,2 kW** vom aktuellen Wert unterscheidet.
5. Ohne Akku-Freigabe bleibt die Grenze auf dem Minimum.

*Beispiel:* Kompressor zieht 1,9 kW, es werden zusätzlich 0,4 kW eingespeist → Budget 2,3 kW → Ziel 2,2 kW.

> Hinweis: Die Wärmepumpe fährt nach dem Start oft erst einmal hoch und wechselt erst nach einiger Zeit in den PV-Modus. Die Grenze wirkt erst dann. Nach einem Stopp bleibt `pvmaxcomp` auf dem letzten Wert. Er gilt nur im PV-Modus.

Ausschalten lässt sich die Nachführung auf der Karte über den Schalter **Leistungsnachführung**.

## 7. Strompreis-Steuerung (optional)

Für alle mit **dynamischem Tarif** (z. B. Tibber, aWATTar, Octopus) oder **zeitvariablem Wärmepumpen-Tarif** (Niedrig-/Normal-/Hochtarif). Ohne solchen Tarif einfach weglassen – dann gibt es keine Preis-Einstellungen und nichts ändert sich.

### Einschalten – in zwei Stufen

1. **Preis-Sensor eintragen:** *Integration → Konfigurieren →* **Strompreis-Sensor**. Erst dann legt die Integration die Preis-Entitäten an.
2. **Schalter „Preissteuerung“** auf der Karte einschalten. Solange er aus ist, sind alle Preis-Einstellungen gesperrt (*nicht verfügbar*) und auf der Karte ausgeblendet.

### Einheit des Preis-Sensors

Die Integration rechnet intern in **ct/kWh** und erkennt die Einheit selbst:

| Sensor-Einheit | Beispiele |
|---|---|
| `EUR/kWh`, `€/kWh` | Tibber, Nord Pool, EPEX Spot, Octopus Germany |
| `c/kWh`, `ct/kWh`, `Cent/kWh` | Nord Pool (HACS) mit Cent-Option |
| `EUR/MWh` | Börsenpreis-Sensoren |

Hat der Sensor **keine Einheit** (z. B. ein eigener Template-Sensor), wählst du sie unter *Konfigurieren → Einheit des Strompreis-Sensors* von Hand. Wird eine Einheit nicht erkannt, meldet das schon die Einrichtung; im Betrieb pausiert die Preissteuerung dann („Einheit unbekannt“) – sie rät nie.

### So wirkt der Preis

| Preis | Verhalten |
|---|---|
| **≤ Günstig-Schwelle** (Standard 15 ct/kWh) | PV-Betrieb **auch ohne Überschuss**. Gilt auch nachts, außerhalb des Startfensters und bei leerem Akku. Zählt **nicht** ins Tageslimit. Mindestlaufzeit und Sperrzeit gelten weiter. `pvmaxcomp` steht auf *Kompressorleistung bei günstigem Strom*. |
| dazwischen | normale PV-Überschuss-Logik |
| **≥ Teuer-Schwelle** (Standard 35 ct/kWh) | kein PV-Start (neue Startbedingung „Strompreis nicht zu hoch“). Optional *Bei teurem Strom beenden*: ein laufender PV-Betrieb endet nach der Mindestlaufzeit. |

**Übergänge ohne Stopp:** Läuft PV-Betrieb und der Strom wird günstig (z. B. bei Sonnenuntergang), geht es als Günstig-Betrieb weiter. Endet die Günstig-Phase und ist PV-Überschuss da, geht es als PV-Betrieb weiter. Sonst endet der Günstig-Betrieb nach der Mindestlaufzeit.

**Ausfälle:** Ist der Preis-Sensor kurz nicht verfügbar (typisch zum Stunden- oder Viertelstundenwechsel), gilt der letzte Preis bis zu 15 Minuten weiter. Danach pausiert die Preissteuerung – es gibt dann keine Günstig-Starts und keine Sperre. Nach einem Neustart von Home Assistant läuft ein Günstig-Betrieb ebenfalls bis zu 15 Minuten weiter, bis der Preis-Sensor wieder einen Wert liefert.

> 💡 **Feste Hoch-/Niedertarif-Zeiten ohne Preis-Sensor?** Lege einen Template-Sensor an, der je nach Uhrzeit den Preis liefert, z. B. *Einstellungen → Geräte & Dienste → Helfer → Template → Sensor* mit `{{ 22.5 if now().hour < 6 or now().hour >= 22 else 31.8 }}` und der Einheit `ct/kWh`.

> ℹ️ Die Integration steuert nicht den Wechselrichter. Ob der Hausakku während des Günstig-Betriebs in die Wärmepumpe entlädt, regelt dein Wechselrichter bzw. dessen Integration.

## 8. Die Dashboard-Karte erklärt

![Dashboard-Karte](screenshots/karte.png)

**Kopfzeile**

- **Status-Chip:** z. B. *PV-Betrieb*, *Wartet auf Überschuss*, *Sperrzeit*, *Akku unter Abschaltgrenze*, *Sonne untergegangen*.
- **Signal WP: an/aus:** der tatsächliche Zustand des Bits in EMS-ESP.
- **Blauer Hinweis:** erscheint, solange der Beobachtungsmodus aktiv ist.
- **Zuletzt …:** die letzte Meldung (Start, Stopp, Leistungsänderung).

**Kacheln**

| Kachel | Bedeutung |
|---|---|
| Verfügbar | verfügbare Leistung nach Akku-Vorrang, darunter die Einschaltschwelle |
| Budget Ø | gemitteltes Budget für die Leistungsnachführung, darunter das Ziel |
| Akku | Ladestand, Freigabe an/aus oder wie viel kWh noch fehlen |
| Kompressor | aktuelle Kompressorleistung, darunter die gesetzte Grenze (pvmaxcomp) |
| Prognose | Solcast-Rest heute, darunter die Leistung in 30 min |
| Netz | Leistung am Netzanschluss: Bezug oder Einspeisung |
| Heute | Starts heute / Tageslimit, darunter die PV-Laufzeit heute |
| Strompreis | nur mit Preissteuerung: aktueller Preis in ct/kWh, darunter günstig / normal / teuer |

**Startbedingungen / Laufender PV-Betrieb**

- Ist der PV-Betrieb aus, siehst du die Checkliste aus Abschnitt 5.2. Grün heißt erfüllt, grau heißt nicht erfüllt. Rechts stehen die aktuellen Werte.
- Läuft der PV-Betrieb, siehst du stattdessen *seit wann*, *Mindestlaufzeit bis* und ggf. *Überschuss fehlt seit*.

**Steuerung**

- **Automatik / Aus / Manuell an:** siehe Abschnitt 9.
- **Beobachtungsmodus:** nur rechnen, nichts schreiben.
- **Leistungsnachführung:** pvmaxcomp anpassen ja/nein.
- **PV-Prognose verwenden:** Solcast für Akku-Freigabe und Einschalten nutzen.
- **Preissteuerung:** nur mit Strompreis-Sensor, siehe Abschnitt 7.

![Einstellungen 1](screenshots/einstellungen-1.png)
![Einstellungen 2](screenshots/einstellungen-2.png)

**Einstellungen** (aufklappbar) mit den Gruppen *Überschuss*, *Akku & Prognose*, *Kompressorschutz & Zeiten*, *Leistungsnachführung* und – bei eingeschalteter Preissteuerung – *Strompreis*. Änderungen gelten sofort. Darunter liegen die Tasten **Sperrzeit aufheben** und **Tageszähler zurücksetzen**.

Karten-Optionen (im Karten-Editor oder YAML):

```yaml
type: custom:emsesp-pv-surplus-card
device_id: …          # nur bei mehreren Einrichtungen
title: Wärmepumpe PV  # optional
show_settings: true   # Einstellungen anzeigen
```

## 9. Betriebsarten

| Betriebsart | Verhalten |
|---|---|
| **Automatik** | normale Regelung wie oben beschrieben |
| **Aus** | gibt die Wärmepumpe in den Normalbetrieb zurück (Bit = 0) und schreibt danach nichts mehr. Du kannst den Eingang dann selbst bedienen. |
| **Manuell an** | PV-Betrieb sofort an, ohne Bedingungen und ohne Tageszähler. Gut zum Testen, ob die Wärmepumpe auf das Signal reagiert. Danach wieder auf Automatik stellen. |

## 10. Einstellungen anpassen – Empfehlungen

| Situation | Empfehlung |
|---|---|
| Kleiner Akku (≤ 5 kWh) | *Akku-Kapazität* anpassen, *Akku-Freigabe ab* eher 90 % |
| Kein Akku | Akku-Leistung als Sensor mit dauerhaft 0 W anlegen, SoC 100 % (z. B. Template-Sensoren) |
| Größere Wärmepumpe (9–12 kW) | *Kompressorleistung max.* erhöhen, z. B. 3,5–4 kW |
| Wärmepumpe taktet trotzdem | *Mindestlaufzeit* und *Sperrzeit* erhöhen, *Max. Aktivierungen* auf 1 |
| Zweiter Warmwasser-Start im PV-Betrieb | *Beenden nach Kompressor-Stillstand* auf 20 min |
| Startet zu selten | *Einschaltschwelle* senken (z. B. 1200 W), *Startfenster* erweitern |
| Häufig Netzbezug im PV-Betrieb | *Ausschaltschwelle* näher an 0 (z. B. −400 W), *Leistungsreserve* erhöhen |

Alle Einstellungen sind auch Entitäten (number / switch / select / time). Du kannst sie in Automationen ändern, z. B. im Winter ein anderes Startfenster.

## 11. Beispiel: ein sonniger Tag

| Uhrzeit | Was passiert | Status |
|---|---|---|
| 08:30 | Sonne, aber Akku 35 % | Akku unter Abschaltgrenze |
| 10:15 | Akku 62 %, Solcast reicht → Akku-Freigabe | Wartet auf Überschuss |
| 11:47 | 1.900 W verfügbar | Überschuss erkannt – Einschaltverzögerung |
| 11:52 | 5 min stabil → Bit = 1 | PV-Betrieb |
| 11:57 | Budget Ø 2.312 W → pvmaxcomp 1,0 → 2,2 kW | PV-Betrieb |
| 14:30 | Wolken, −900 W | PV-Betrieb – Überschuss fehlt |
| 14:40 | 10 min Defizit → Bit = 0 | Sperrzeit bis 16:40 |
| 16:40 | Sperrzeit vorbei, aber außerhalb Startfenster | Außerhalb Startfenster |
| 18:20 | Sonnenuntergang | Sonne untergegangen |

## 12. Entitäten für eigene Automationen

| Entität | Inhalt |
|---|---|
| `sensor.<name>_status` | Status mit vielen Attributen (Checks, Werte, Zeiten) |
| `sensor.<name>_verfugbare_leistung` | verfügbare Leistung in W |
| `sensor.<name>_leistungsbudget_o` | Budget Ø in W |
| `sensor.<name>_kompressor_zielleistung` | Ziel für pvmaxcomp in kW |
| `sensor.<name>_aktivierungen_heute` | Starts heute |
| `sensor.<name>_pv_laufzeit_heute` | PV-Laufzeit heute |
| `sensor.<name>_sperrzeit_bis` | Ende der Sperrzeit |
| `binary_sensor.<name>_pv_betrieb_angefordert` | Integration will PV-Betrieb |
| `binary_sensor.<name>_pv_signal_an_warmepumpe` | Bit tatsächlich gesetzt |
| `binary_sensor.<name>_akku_freigabe` | Akku freigegeben |
| `select.<name>_betriebsart` | Automatik / Aus / Manuell |
| `switch.<name>_preissteuerung` | Preissteuerung an/aus (nur mit Preis-Sensor) |

![Geräteseite](screenshots/geraet.png)

Die genauen IDs hängen vom Gerätenamen ab. Du findest sie unter *Einstellungen → Geräte & Dienste → EMS-ESP WP PV Überschuss → Gerät*.

## 13. Häufige Fragen und Fehlersuche

**Die Wärmepumpe reagiert nicht, obwohl „Signal WP: an“.**
Prüfe im Regler der Wärmepumpe, ob der Eingang für PV / SG Ready eingestellt ist. Teste mit *Manuell an*.

**Status „Messwerte fehlen“.**
Ein Quell-Sensor ist länger als 2 Minuten `unavailable`. Kurze Aussetzer (z. B. MQTT-Reconnect) werden ignoriert. Nach 10 Minuten wird ein laufender PV-Betrieb sicherheitshalber beendet.

**Karte zeigt „Custom element doesn't exist“.**
Seite einmal mit Strg+F5 neu laden. Bei Dashboards im YAML-Modus die Ressource `/emsesp_pv_surplus/emsesp-pv-surplus-card.js` (Typ *module*) selbst eintragen.

**Ich habe evcc / eine eigene Automation auf demselben Eingang.**
Eine davon abschalten. Sonst schalten sich beide gegenseitig um.

**Was passiert beim Entfernen der Integration?**
Hatte sie das Bit gesetzt, setzt sie es auf Normalbetrieb zurück.

**Fehler melden:** [Issue anlegen](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/issues) und die Diagnosedaten anhängen (*Integration → ⋮ → Diagnosedaten herunterladen*).
