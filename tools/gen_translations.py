"""Generate translations/{de,en}.json and strings.json from one table."""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "emsesp_pv_surplus"

FIELDS = {
    "name": ("Name", "Name", "Anzeigename des Geräts.", "Display name of the device."),
    "signal_entity": (
        "EMS-ESP Eingangs-Option (z. B. hpin4opt)",
        "EMS-ESP input option (e.g. hpin4opt)",
        "Text-Entität mit dem Bitmuster des SG-/PV-Eingangs. Das gewählte Bit wird für den PV-Betrieb auf 1 gesetzt (wie im evcc-Template: 1xxxxxxxxxxx = Boost).",
        "Text entity holding the bit pattern of the SG/PV input. The selected bit is set to 1 for PV mode (as in the evcc template: 1xxxxxxxxxxx = boost).",
    ),
    "signal_bit": (
        "Bit-Position",
        "Bit position",
        "0 = erstes Zeichen. Bei Buderus/Bosch/Junkers für PV/SG4 meist 0.",
        "0 = first character. Usually 0 for PV/SG4 on Buderus/Bosch/Junkers.",
    ),
    "grid_entity": ("Netzleistung", "Grid power", "Leistung am Netzanschlusspunkt.", "Power at the grid connection point."),
    "grid_sign": ("Vorzeichen Netzleistung", "Grid power sign", None, None),
    "battery_power_entity": ("Akku-Leistung", "Battery power", None, None),
    "battery_sign": ("Vorzeichen Akku-Leistung", "Battery power sign", None, None),
    "soc_entity": ("Akku-Ladestand (SoC)", "Battery state of charge", None, None),
    "pvmaxcomp_entity": (
        "PV max. Kompressorleistung (optional)",
        "PV max. compressor power (optional)",
        "EMS-ESP-Entität pvmaxcomp. Wird im PV-Betrieb an den Überschuss angepasst.",
        "EMS-ESP entity pvmaxcomp. Adjusted to the surplus during PV mode.",
    ),
    "hp_power_entity": (
        "Aktuelle Kompressorleistung (optional)",
        "Current compressor power (optional)",
        "EMS-ESP-Entität hpcurrpower (elektrische Leistung). Nötig für die Leistungsnachführung.",
        "EMS-ESP entity hpcurrpower (electrical power). Needed for compressor power control.",
    ),
    "forecast_remaining_entity": (
        "PV-Prognose verbleibend heute (optional)",
        "PV forecast remaining today (optional)",
        "z. B. Solcast „Prognose verbleibende Leistung heute“ (kWh).",
        "e.g. Solcast “Forecast remaining today” (kWh).",
    ),
    "forecast_30min_entity": (
        "PV-Prognose Leistung in 30 Minuten (optional)",
        "PV forecast power in 30 minutes (optional)",
        "z. B. Solcast „Leistung in 30 Minuten“ (W).",
        "e.g. Solcast “Power in 30 minutes” (W).",
    ),
    "price_entity": (
        "Strompreis-Sensor (optional, für dynamische / zeitvariable Tarife)",
        "Electricity price sensor (optional, for dynamic / time-of-use tariffs)",
        "Aktueller Strompreis, z. B. von Tibber, Nord Pool, EPEX Spot oder Octopus. Leer lassen, wenn du keinen dynamischen Tarif hast – dann gibt es keine Preis-Einstellungen.",
        "Current electricity price, e.g. from Tibber, Nord Pool, EPEX Spot or Octopus. Leave empty without a dynamic tariff – then there are no price settings.",
    ),
    "price_unit": (
        "Einheit des Strompreis-Sensors",
        "Unit of the price sensor",
        "„Automatisch“ erkennt €/kWh, ct/kWh und €/MWh aus dem Sensor. Nur ändern, wenn der Sensor keine Einheit hat.",
        "“Automatic” detects €/kWh, ct/kWh and €/MWh from the sensor. Only change it if the sensor has no unit.",
    ),
}

SELECTORS = {
    "grid_sign": {
        "import_positive": ("Positiv = Bezug, negativ = Einspeisung", "Positive = import, negative = export"),
        "export_positive": ("Positiv = Einspeisung, negativ = Bezug", "Positive = export, negative = import"),
    },
    "battery_sign": {
        "discharge_positive": ("Positiv = Entladen, negativ = Laden", "Positive = discharging, negative = charging"),
        "charge_positive": ("Positiv = Laden, negativ = Entladen", "Positive = charging, negative = discharging"),
    },
    "price_unit": {
        "auto": ("Automatisch (aus dem Sensor)", "Automatic (from the sensor)"),
        "major_kwh": ("€/kWh (Hauptwährung pro kWh)", "€/kWh (main currency per kWh)"),
        "minor_kwh": ("ct/kWh (Cent pro kWh)", "ct/kWh (cent per kWh)"),
        "major_mwh": ("€/MWh (Hauptwährung pro MWh)", "€/MWh (main currency per MWh)"),
    },
}

STATUS = {
    "off": ("Aus", "Off"),
    "manual": ("Manuell: PV-Betrieb", "Manual: PV mode"),
    "pv_active": ("PV-Betrieb", "PV mode"),
    "deficit_pending": ("PV-Betrieb – Überschuss fehlt", "PV mode – surplus missing"),
    "waiting": ("Wartet auf Überschuss", "Waiting for surplus"),
    "surplus_pending": ("Überschuss erkannt – Einschaltverzögerung", "Surplus detected – switch-on delay"),
    "locked": ("Sperrzeit", "Lock time"),
    "daily_limit": ("Tageslimit erreicht", "Daily limit reached"),
    "outside_window": ("Außerhalb Startfenster", "Outside start window"),
    "night": ("Sonne untergegangen", "Sun has set"),
    "battery_low": ("Akku unter Abschaltgrenze", "Battery below stop level"),
    "sensor_error": ("Messwerte fehlen", "Readings missing"),
    "price_cheap": ("Günstiger Strom – PV-Betrieb", "Cheap electricity – PV mode"),
    "price_high": ("Strompreis zu hoch", "Electricity price too high"),
}

ENTITIES = {
    "sensor": {
        "status": ("Status", "Status"),
        "available_power": ("Verfügbare Leistung", "Available power"),
        "power_budget": ("Leistungsbudget Ø", "Power budget avg"),
        "compressor_target": ("Kompressor-Zielleistung", "Compressor target"),
        "activations_today": ("Aktivierungen heute", "Activations today"),
        "runtime_today": ("PV-Laufzeit heute", "PV runtime today"),
        "lock_until": ("Sperrzeit bis", "Locked until"),
    },
    "binary_sensor": {
        "requested": ("PV-Betrieb angefordert", "PV mode requested"),
        "signal_active": ("PV-Signal an Wärmepumpe", "PV signal at heat pump"),
        "battery_release": ("Akku-Freigabe", "Battery release"),
        "surplus": ("Überschuss über Einschaltschwelle", "Surplus above threshold"),
    },
    "number": {
        "on_threshold_w": ("Einschaltschwelle", "Switch-on threshold"),
        "off_threshold_w": ("Ausschaltschwelle", "Switch-off threshold"),
        "on_delay_min": ("Einschaltverzögerung", "Switch-on delay"),
        "off_delay_min": ("Ausschaltverzögerung", "Switch-off delay"),
        "soc_release": ("Akku-Freigabe ab", "Battery release from"),
        "soc_stop": ("Akku-Abschaltgrenze", "Battery stop level"),
        "min_runtime_min": ("Mindestlaufzeit", "Minimum runtime"),
        "lock_min": ("Sperrzeit", "Lock time"),
        "max_activations": ("Max. Aktivierungen pro Tag", "Max. activations per day"),
        "soc_forecast": ("Akku-Freigabe mit Prognose ab", "Battery release with forecast from"),
        "battery_capacity_kwh": ("Akku-Kapazität", "Battery capacity"),
        "forecast_reserve_kwh": ("Prognose-Reserve", "Forecast reserve"),
        "comp_min_kw": ("Kompressorleistung min.", "Compressor power min."),
        "comp_max_kw": ("Kompressorleistung max.", "Compressor power max."),
        "comp_reserve_kw": ("Leistungsreserve", "Power reserve"),
        "comp_step_kw": ("Mindeständerung", "Minimum change"),
        "comp_interval_min": ("Anpassungsintervall", "Adjustment interval"),
        "idle_stop_min": ("Beenden nach Kompressor-Stillstand", "End after compressor idle"),
        "price_cheap_ct": ("Günstig-Schwelle", "Cheap threshold"),
        "price_expensive_ct": ("Teuer-Schwelle", "Expensive threshold"),
        "price_comp_kw": ("Kompressorleistung bei günstigem Strom", "Compressor power on cheap electricity"),
    },
    "switch": {
        "observe": ("Beobachtungsmodus", "Observe mode"),
        "dynamic_power": ("Leistungsnachführung", "Compressor power control"),
        "use_forecast": ("PV-Prognose verwenden", "Use PV forecast"),
        "price_control": ("Preissteuerung", "Price control"),
        "price_stop_expensive": ("Bei teurem Strom PV-Betrieb beenden", "Stop PV mode on expensive electricity"),
    },
    "select": {"mode": ("Betriebsart", "Mode")},
    "time": {
        "window_start": ("Startfenster von", "Start window from"),
        "window_end": ("Startfenster bis", "Start window until"),
    },
    "button": {
        "reset_lock": ("Sperrzeit aufheben", "Lift lock time"),
        "reset_counter": ("Tageszähler zurücksetzen", "Reset daily counter"),
    },
}

MODES = {
    "auto": ("Automatik", "Automatic"),
    "off": ("Aus", "Off"),
    "manual": ("Manuell: PV-Betrieb an", "Manual: PV mode on"),
}

TEXT = {
    "user_title": ("PV-Überschuss für die Wärmepumpe", "PV surplus for the heat pump"),
    "user_desc": (
        "Wählt die Entitäten von EMS-ESP, Netzzähler, Akku und optional der PV-Prognose. Nach der Einrichtung startet die Integration im Beobachtungsmodus: Sie rechnet und protokolliert, schreibt aber nichts an die Wärmepumpe.",
        "Pick the entities from EMS-ESP, grid meter, battery and optionally the PV forecast. After setup the integration starts in observe mode: it calculates and logs, but writes nothing to the heat pump.",
    ),
    "options_title": ("Quell-Entitäten ändern", "Change source entities"),
    "hp_power_required": (
        "Für die Leistungsnachführung wird auch die aktuelle Kompressorleistung benötigt.",
        "Compressor power control also needs the current compressor power.",
    ),
    "already": ("Für diese Eingangs-Entität gibt es schon eine Einrichtung.", "This input entity is already set up."),
    "price_unit_unknown": (
        "Die Einheit des Strompreis-Sensors wurde nicht erkannt. Bitte die Einheit unten von Hand auswählen.",
        "The unit of the price sensor was not recognised. Please choose the unit below manually.",
    ),
}


def build(lang: int) -> dict:
    data = {k: v[lang] for k, v in FIELDS.items()}
    desc = {k: v[2 + lang] for k, v in FIELDS.items() if v[2 + lang]}
    opt_data = {k: v for k, v in data.items() if k != "name"}
    opt_desc = {k: v for k, v in desc.items() if k != "name"}
    entity: dict = {}
    for platform, items in ENTITIES.items():
        entity[platform] = {}
        for key, names in items.items():
            entity[platform][key] = {"name": names[lang]}
    entity["sensor"]["status"]["state"] = {k: v[lang] for k, v in STATUS.items()}
    entity["select"]["mode"]["state"] = {k: v[lang] for k, v in MODES.items()}
    return {
        "config": {
            "step": {
                "user": {
                    "title": TEXT["user_title"][lang],
                    "description": TEXT["user_desc"][lang],
                    "data": data,
                    "data_description": desc,
                }
            },
            "error": {
                "hp_power_required": TEXT["hp_power_required"][lang],
                "price_unit_unknown": TEXT["price_unit_unknown"][lang],
            },
            "abort": {"already_configured": TEXT["already"][lang]},
        },
        "options": {
            "step": {
                "init": {
                    "title": TEXT["options_title"][lang],
                    "data": opt_data,
                    "data_description": opt_desc,
                }
            },
            "error": {
                "hp_power_required": TEXT["hp_power_required"][lang],
                "price_unit_unknown": TEXT["price_unit_unknown"][lang],
            },
        },
        "selector": {
            name: {"options": {k: v[lang] for k, v in opts.items()}}
            for name, opts in SELECTORS.items()
        },
        "entity": entity,
    }


def main() -> None:
    (BASE / "translations").mkdir(exist_ok=True)
    de, en = build(0), build(1)
    for path, content in (
        (BASE / "translations" / "de.json", de),
        (BASE / "translations" / "en.json", en),
        (BASE / "strings.json", en),
    ):
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
