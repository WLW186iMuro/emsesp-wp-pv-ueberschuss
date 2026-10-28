# Änderungsprotokoll

## Unveröffentlicht

- **Neu: Peak-Modus (optional)** – EVU-Sperre der Wärmepumpe bei hohem Strompreis und leerem Akku.
  - Neue Quell-Entitäten unter *Konfigurieren*: EMS-ESP Eingangs-Option für die EVU-Sperre (z. B. `text.boiler_hpin1opt`) mit Bit-Position (Standard 0), Akku-Notstromreserve, aktueller Stundenpreis, Durchschnittspreis heute. Nur alle vier zusammen.
  - Sperre (gewähltes Bit → `1`, die übrigen bleiben) bei: Preissteuerung an, Automatik ohne PV-Betrieb, Stundenpreis ≥ Teuer-Schwelle und > 108 % des Tagesdurchschnitts, Ladestand ≤ Reserve + 2 %, 10 min Netzbezug am Stück, 60 min Pause, max. 2 pro Tag.
  - Aufhebung, sobald der Preis unter 108 % des Durchschnitts fällt, spätestens nach der maximalen Sperrdauer (120 min) unabhängig vom Preis; sofort bei 10 min fehlenden Messwerten, ausgeschalteter Preissteuerung oder geänderter Betriebsart.
  - Beobachtungsmodus: keine Sperre, aber Logbuch-Eintrag „[Beobachtung] würde EVU-Sperre setzen / aufheben“.
  - Neuer Status „Peak-Modus – EVU-Sperre aktiv“, eigener Abschnitt und Kachel „EVU-Sperren heute“ auf der Karte, alle Werte als Einstellungen.
  - *Sperrzeit aufheben* und *Tageszähler zurücksetzen* gelten auch für die EVU-Sperre.
  - Schalter *Preissteuerung* und *Teuer-Schwelle* gibt es auch ohne Strompreis-Sensor, wenn der Peak-Modus eingerichtet ist.

## 0.3.0 – 2026-10-22

- **Neu: Strompreis-Steuerung (optional)** für dynamische und zeitvariable Tarife (Issue #1).
  - Strompreis-Sensor unter *Konfigurieren* auswählbar; die Einheit (€/kWh, ct/kWh, €/MWh …) wird erkannt oder kann von Hand gewählt werden.
  - Ohne Preis-Sensor gibt es keine Preis-Entitäten – für alle ohne dynamischen Tarif ändert sich nichts.
  - Schalter *Preissteuerung*: solange aus, sind alle Preis-Einstellungen gesperrt und auf der Karte ausgeblendet.
  - Günstiger Strom (≤ Schwelle): PV-Betrieb auch ohne Überschuss, auch nachts; zählt nicht ins Tageslimit; Mindestlaufzeit und Sperrzeit gelten weiter; eigene Kompressorleistung.
  - Teurer Strom (≥ Schwelle): kein Start; optional laufenden PV-Betrieb nach der Mindestlaufzeit beenden.
  - Nahtlose Übergänge zwischen PV- und Günstig-Betrieb, 15 Minuten Kulanz bei Aussetzern des Preis-Sensors.
- Entitäten nicht mehr konfigurierter Zusatzfunktionen (Prognose, Leistungsnachführung, Strompreis) werden automatisch entfernt.
- Automatische Tests gegen eine echte Home-Assistant-Instanz in der GitHub-Prüfung.

## 0.2.2 – 2026-10-21

- Karte: Kein Springen der Seite mehr auf iPhone/iPad, wenn sich die Kartenhöhe ändert (Safari hat kein Scroll-Anchoring).
- Karte: Kein kompletter Neuaufbau mehr, wenn Home Assistant die Entitätenliste mit gleichem Inhalt neu verteilt; bei einem nötigen Neuaufbau hält die Karte ihre Höhe.
- Karte: Zeitfelder (Startfenster) bündig mit den Zahlenfeldern.

Dokumentation und Repository:

- Repository komplett auf Deutsch, englische Dokumentation am Ende der README deutlich markiert.
- Ausführliche Anleitung auf Deutsch (`docs/anleitung.md`) und Englisch (`docs/guide.md`).
- Echte Screenshots aus einer laufenden Installation (Buderus WLW186i).
- Repo umbenannt in `emsesp-wp-pv-ueberschuss`, Links in Manifest und Karte angepasst.
- PayPal-Button (PayPal.me) zum Unterstützen des Projekts.
- Raumnamen aus den Screenshots entfernt.

## 0.2.1 – 2026-10-21

- Neuer Anzeigename: **EMS-ESP WP PV Überschuss** (Integrationsliste, HACS, Kartenauswahl, Gerätehersteller). Die Domain `emsesp_pv_surplus` und der Kartentyp `custom:emsesp-pv-surplus-card` bleiben gleich, bestehende Einrichtungen und Dashboards laufen ohne Änderung weiter.

## 0.2.0 – 2026-10-21

Erste öffentliche Version.

- Kurze Aussetzer von Messwerten (EMS-ESP-/MQTT-Reconnect, Abfragelücken des Wechselrichters) setzen den Status nicht mehr auf „Messwerte fehlen“. Der Status wechselt erst nach 2 Minuten; der Sicherheits-Stopp nach 10 Minuten bleibt.
- Diagnose-Download für Fehlerberichte.
- Der vorgeschlagene Gerätename folgt der Home-Assistant-Sprache (DE/EN).
- Name und Beschreibung in der Kartenauswahl auf Deutsch oder Englisch.
- Manifest: Links zu Dokumentation und Issue-Tracker.
- Repository für HACS eingerichtet (benutzerdefiniertes Repository), mit hassfest-/HACS-Prüfung, Tests und automatisch gebautem Release-ZIP.

## 0.1.1

- Die Karte wird nur noch als Lovelace-Ressource geladen, registriert nach dem Start von Home Assistant. Das behebt „Custom element doesn't exist“ zusammen mit HACS-Karten, die eine eigene Custom-Element-Registry installieren.
- Die Karte registriert sich erneut, falls ein anderes Skript `window.customElements` ersetzt.

## 0.1.0

- Erste Version: PV-/SG-Ready-Signal über eine EMS-ESP-Eingangsoption, Akku-Vorrang, Solcast-Prognose, Leistungsnachführung, Beobachtungsmodus, Dashboard-Karte.
