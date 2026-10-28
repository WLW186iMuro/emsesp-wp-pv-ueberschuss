/*
 * EMS-ESP WP PV Überschuss – Dashboard-Karte
 * Wird von der Integration automatisch geladen (kein Ressourcen-Eintrag nötig).
 * Karten-Typ: custom:emsesp-pv-surplus-card
 */
(() => {
  const DOMAIN = "emsesp_pv_surplus";
  const CARD = "emsesp-pv-surplus-card";
  const EDITOR = "emsesp-pv-surplus-card-editor";
  const VERSION = "0.3.0";

  const T = {
    de: {
      title: "PV-Überschuss Wärmepumpe",
      notFound: "Keine Einrichtung der Integration „EMS-ESP WP PV Überschuss“ gefunden.",
      observe: "Beobachtungsmodus: Die Integration rechnet und protokolliert, schreibt aber nichts an die Wärmepumpe.",
      signal: "Signal WP",
      on: "an",
      off: "aus",
      tiles: {
        available: "Verfügbar",
        budget: "Budget Ø",
        battery: "Akku",
        compressor: "Kompressor",
        forecast: "Prognose",
        today: "PV-Überschuss heute",
        grid: "Netz",
        price: "Strompreis",
        evu: "EVU-Sperren heute",
      },
      evuActiveUntil: "bis",
      evuLockUntil: "Sperrzeit bis",
      price: { cheap: "günstig", expensive: "teuer", normal: "normal", unavailable: "nicht verfügbar", unit_unknown: "Einheit unbekannt" },
      runningCheap: "PV-Betrieb mit günstigem Strom",
      threshold: "Schwelle",
      target: "Ziel",
      limit: "Grenze",
      release: "Freigabe",
      missing: "fehlt",
      in30: "in 30 min",
      runtime: "Laufzeit",
      import: "Bezug",
      export: "Einspeisung",
      conditions: "Startbedingungen Solarbetrieb (PV-Überschuss)",
      running: "Laufender PV-Betrieb",
      since: "seit",
      minRuntimeUntil: "Mindestlaufzeit bis",
      deficitSince: "Überschuss fehlt seit",
      minRuntimeDone: "Mindestlaufzeit erfüllt",
      checks: {
        sensors: "Messwerte vorhanden",
        sun: "Sonne über dem Horizont",
        window: "Im Startfenster",
        battery: "Akku über Abschaltgrenze",
        lock: "Keine Sperrzeit",
        limit: "Tageslimit nicht erreicht",
        surplus: "Überschuss ≥ Einschaltschwelle",
        forecast: "Prognose in 30 min ≥ Schwelle",
        price: "Strompreis nicht zu hoch",
        delay: "Überschuss lange genug stabil",
      },
      peak: "Startbedingungen Peak-Modus (EVU-Sperre)",
      peakRunning: "EVU-Sperre aktiv",
      peakUntil: "Spätestens aufgehoben um",
      peakLiftBelow: "Aufhebung, sobald der Stundenpreis unter",
      peakChecks: {
        sensors: "Messwerte vorhanden (inkl. EVU-Eingang)",
        pv_off: "Automatik, kein PV-Betrieb",
        expensive: "Stundenpreis ≥ Teuer-Schwelle",
        above_average: "Stundenpreis > Tagesdurchschnitt",
        battery: "Akku an der Notstromreserve",
        lock: "Keine Sperrzeit",
        limit: "Tageslimit nicht erreicht",
        no_surplus: "Netzbezug lange genug",
      },
      lockUntil: "bis",
      control: "Steuerung",
      modes: { auto: "Automatik", off: "Aus", manual: "Manuell an" },
      toggles: {
        observe: ["Beobachtungsmodus", "Nur rechnen, nichts schreiben"],
        dynamic_power: ["Leistungsnachführung", "PV max. Kompressorleistung an den Überschuss anpassen"],
        use_forecast: ["PV-Prognose verwenden", "Solcast für Akku-Freigabe und Einschalten nutzen"],
        price_control: ["Preissteuerung", "Bei günstigem Strom einschalten, bei teurem nicht starten"],
      },
      settings: "Einstellungen",
      groups: {
        surplus: "Solarbetrieb (PV-Überschuss)",
        battery: "Akku & Prognose",
        protect: "Kompressorschutz & Zeiten",
        compressor: "Leistungsnachführung",
        price: "Strompreis",
        peak: "Peak-Modus (EVU-Sperre)",
      },
      fields: {
        on_threshold_w: ["Einschaltschwelle", "verfügbare Leistung zum Einschalten"],
        off_threshold_w: ["Ausschaltschwelle", "negativ = Bezug aus Akku/Netz"],
        on_delay_min: ["Einschaltverzögerung", "so lange muss der Überschuss anliegen"],
        off_delay_min: ["Ausschaltverzögerung", "so lange muss das Defizit anliegen"],
        soc_release: ["Akku-Freigabe ab", "ab hier zählt Akku-Laden als Überschuss"],
        soc_forecast: ["Freigabe mit Prognose ab", "wenn Solcast den Akku noch voll bekommt"],
        battery_capacity_kwh: ["Akku-Kapazität", ""],
        forecast_reserve_kwh: ["Prognose-Reserve", "Sicherheitsabzug von der Prognose"],
        soc_stop: ["Akku-Abschaltgrenze", "darunter sofort beenden"],
        min_runtime_min: ["Mindestlaufzeit", "pro Start"],
        lock_min: ["Sperrzeit", "Pause nach dem Ausschalten"],
        max_activations: ["Max. Aktivierungen", "pro Tag"],
        window_start: ["Startfenster von", ""],
        window_end: ["Startfenster bis", ""],
        comp_min_kw: ["Kompressorleistung min.", ""],
        comp_max_kw: ["Kompressorleistung max.", ""],
        comp_reserve_kw: ["Leistungsreserve", "wird vom Budget abgezogen"],
        comp_step_kw: ["Mindeständerung", "kleinere Änderungen werden nicht geschrieben"],
        comp_interval_min: ["Anpassungsintervall", "Mittelwert und Takt"],
        price_cheap_ct: ["Günstig-Schwelle", "darunter PV-Betrieb auch ohne Überschuss"],
        price_expensive_ct: ["Teuer-Schwelle", "darüber keine Starts"],
        price_stop_expensive: ["Bei teurem Strom beenden", "laufenden PV-Betrieb nach der Mindestlaufzeit stoppen"],
        price_comp_kw: ["Kompressorleistung bei günstigem Strom", "PV max. Kompressorleistung im Günstig-Betrieb"],
        peak_factor_pct: ["Preis über Tagesdurchschnitt", "Sperre ab Stundenpreis > Ø × Wert, Aufhebung darunter"],
        peak_soc_margin: ["Abstand zur Notstromreserve", "Sperre ab Ladestand ≤ Reserve + Wert"],
        peak_import_min: ["Netzbezug seit mindestens", "verfügbare Leistung ≤ 0 W am Stück"],
        peak_max_duration_min: ["Max. Dauer der Sperre", "danach immer aufheben, egal wie der Preis ist"],
        peak_lock_min: ["Sperrzeit", "Pause nach der letzten EVU-Sperre"],
        peak_max_per_day: ["Max. Aktivierungen pro Tag", ""],
      },
      buttons: { reset_lock: "Sperrzeit aufheben", reset_counter: "Tageszähler zurücksetzen" },
      lastAction: "Zuletzt",
      editor: { device_id: "Gerät (leer = erstes)", title: "Titel (optional)", show_settings: "Einstellungen anzeigen" },
    },
    en: {
      title: "PV surplus heat pump",
      notFound: "No “EMS-ESP WP PV Überschuss” integration entry found.",
      observe: "Observe mode: the integration calculates and logs, but writes nothing to the heat pump.",
      signal: "HP signal",
      on: "on",
      off: "off",
      tiles: {
        available: "Available",
        budget: "Budget avg",
        battery: "Battery",
        compressor: "Compressor",
        forecast: "Forecast",
        today: "PV surplus today",
        grid: "Grid",
        price: "Electricity price",
        evu: "EVU locks today",
      },
      evuActiveUntil: "until",
      evuLockUntil: "lock time until",
      price: { cheap: "cheap", expensive: "expensive", normal: "normal", unavailable: "unavailable", unit_unknown: "unit unknown" },
      runningCheap: "PV mode on cheap electricity",
      threshold: "Threshold",
      target: "Target",
      limit: "Limit",
      release: "Release",
      missing: "missing",
      in30: "in 30 min",
      runtime: "Runtime",
      import: "import",
      export: "export",
      conditions: "Start conditions solar mode (PV surplus)",
      running: "PV mode running",
      since: "since",
      minRuntimeUntil: "Minimum runtime until",
      deficitSince: "Surplus missing since",
      minRuntimeDone: "Minimum runtime done",
      checks: {
        sensors: "Readings available",
        sun: "Sun above horizon",
        window: "Inside start window",
        battery: "Battery above stop level",
        lock: "No lock time",
        limit: "Daily limit not reached",
        surplus: "Surplus ≥ switch-on threshold",
        forecast: "Forecast in 30 min ≥ threshold",
        price: "Electricity price not too high",
        delay: "Surplus stable long enough",
      },
      peak: "Start conditions peak mode (EVU block)",
      peakRunning: "EVU block active",
      peakUntil: "Lifted at the latest at",
      peakLiftBelow: "Lifted once the hourly price is below",
      peakChecks: {
        sensors: "Readings available (incl. EVU input)",
        pv_off: "Automatic, no PV mode",
        expensive: "Hourly price ≥ expensive threshold",
        above_average: "Hourly price > daily average",
        battery: "Battery at backup reserve",
        lock: "No lock time",
        limit: "Daily limit not reached",
        no_surplus: "Grid import long enough",
      },
      lockUntil: "until",
      control: "Control",
      modes: { auto: "Automatic", off: "Off", manual: "Manual on" },
      toggles: {
        observe: ["Observe mode", "Calculate only, write nothing"],
        dynamic_power: ["Compressor power control", "Adapt PV max. compressor power to the surplus"],
        use_forecast: ["Use PV forecast", "Use Solcast for battery release and switch-on"],
        price_control: ["Price control", "Switch on with cheap electricity, do not start when expensive"],
      },
      settings: "Settings",
      groups: {
        surplus: "Solar mode (PV surplus)",
        battery: "Battery & forecast",
        protect: "Compressor protection & times",
        compressor: "Compressor power control",
        price: "Electricity price",
        peak: "Peak mode (EVU block)",
      },
      fields: {
        on_threshold_w: ["Switch-on threshold", "available power needed to start"],
        off_threshold_w: ["Switch-off threshold", "negative = drawing from battery/grid"],
        on_delay_min: ["Switch-on delay", "surplus must last this long"],
        off_delay_min: ["Switch-off delay", "deficit must last this long"],
        soc_release: ["Battery release from", "from here battery charging counts as surplus"],
        soc_forecast: ["Release with forecast from", "if Solcast will still fill the battery"],
        battery_capacity_kwh: ["Battery capacity", ""],
        forecast_reserve_kwh: ["Forecast reserve", "safety margin on the forecast"],
        soc_stop: ["Battery stop level", "below this, stop immediately"],
        min_runtime_min: ["Minimum runtime", "per start"],
        lock_min: ["Lock time", "pause after switching off"],
        max_activations: ["Max. activations", "per day"],
        window_start: ["Start window from", ""],
        window_end: ["Start window until", ""],
        comp_min_kw: ["Compressor power min.", ""],
        comp_max_kw: ["Compressor power max.", ""],
        comp_reserve_kw: ["Power reserve", "subtracted from the budget"],
        comp_step_kw: ["Minimum change", "smaller changes are not written"],
        comp_interval_min: ["Adjustment interval", "averaging window and cadence"],
        price_cheap_ct: ["Cheap threshold", "below this, PV mode even without surplus"],
        price_expensive_ct: ["Expensive threshold", "above this, no starts"],
        price_stop_expensive: ["Stop when expensive", "end running PV mode after the minimum runtime"],
        price_comp_kw: ["Compressor power on cheap electricity", "PV max. compressor power in cheap mode"],
        peak_factor_pct: ["Price above daily average", "block from hourly price > avg × value, lifted below"],
        peak_soc_margin: ["Margin above backup reserve", "block from SoC ≤ reserve + value"],
        peak_import_min: ["Grid import for at least", "available power ≤ 0 W without a break"],
        peak_max_duration_min: ["Max. block duration", "always lifted after this, whatever the price"],
        peak_lock_min: ["Lock time", "pause after the last EVU lock activation"],
        peak_max_per_day: ["Max. activations per day", ""],
      },
      buttons: { reset_lock: "Lift lock time", reset_counter: "Reset daily counter" },
      lastAction: "Last",
      editor: { device_id: "Device (empty = first)", title: "Title (optional)", show_settings: "Show settings" },
    },
  };

  const GROUPS = [
    ["surplus", ["on_threshold_w", "off_threshold_w", "on_delay_min", "off_delay_min"]],
    ["battery", ["soc_release", "soc_stop", "soc_forecast", "battery_capacity_kwh", "forecast_reserve_kwh"]],
    ["protect", ["min_runtime_min", "lock_min", "max_activations", "window_start", "window_end"]],
    ["compressor", ["comp_min_kw", "comp_max_kw", "comp_reserve_kw", "comp_step_kw", "comp_interval_min"]],
    ["price", ["price_cheap_ct", "price_expensive_ct", "price_stop_expensive", "price_comp_kw"]],
    ["peak", ["peak_factor_pct", "peak_soc_margin", "peak_import_min", "peak_max_duration_min", "peak_lock_min", "peak_max_per_day"]],
  ];
  const SWITCH_FIELDS = new Set(["price_stop_expensive"]);
  const CHECKS = ["sensors", "sun", "window", "battery", "lock", "limit", "surplus", "forecast", "price", "delay"];
  const PEAK_CHECKS = ["sensors", "pv_off", "expensive", "above_average", "battery", "lock", "limit", "no_surplus"];

  const STATUS_TONE = {
    pv_active: "sun",
    manual: "sun",
    deficit_pending: "warn",
    surplus_pending: "info",
    waiting: "idle",
    locked: "idle",
    daily_limit: "idle",
    outside_window: "idle",
    night: "idle",
    off: "idle",
    battery_low: "warn",
    sensor_error: "error",
    price_cheap: "sun",
    price_high: "warn",
    peak_block: "error",
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const STYLE = `
    :host { display:block; }
    ha-card { display:block; padding: 16px; overflow: hidden; box-sizing: border-box; }
    .n { font-size:.92rem; color:var(--primary-text-color); hyphens:auto; overflow-wrap:anywhere; }
    .h { font-size:.78rem; color:var(--secondary-text-color); hyphens:auto; }
    .head { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
    .title { display:flex; align-items:center; gap:10px; font-size:1.15rem; font-weight:500; color:var(--primary-text-color); min-width:0; }
    .title ha-icon { --mdc-icon-size:26px; color:var(--state-icon-color, var(--primary-color)); }
    .title span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .chips { display:flex; gap:6px; flex-wrap:wrap; }
    .chip { display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:999px; font-size:.85rem; font-weight:500; cursor:pointer; border:1px solid transparent; background:var(--secondary-background-color); color:var(--primary-text-color); }
    .chip ha-icon, .chip ha-state-icon { --mdc-icon-size:16px; }
    .tone-sun { background: color-mix(in srgb, var(--amber-color, #ffb300) 22%, transparent); color: var(--primary-text-color); border-color: color-mix(in srgb, var(--amber-color, #ffb300) 55%, transparent); }
    .tone-info { background: color-mix(in srgb, var(--info-color, #039be5) 18%, transparent); border-color: color-mix(in srgb, var(--info-color, #039be5) 45%, transparent); }
    .tone-warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent); border-color: color-mix(in srgb, var(--warning-color, #ffa600) 50%, transparent); }
    .tone-error { background: color-mix(in srgb, var(--error-color, #db4437) 18%, transparent); border-color: color-mix(in srgb, var(--error-color, #db4437) 50%, transparent); }
    .chip.small { padding:3px 10px; font-size:.78rem; cursor:default; }
    .dot { width:8px; height:8px; border-radius:50%; background:var(--disabled-text-color, #9e9e9e); }
    .dot.on { background: var(--amber-color, #ffb300); box-shadow: 0 0 0 3px color-mix(in srgb, var(--amber-color, #ffb300) 25%, transparent); }
    .banner { margin-top:12px; padding:8px 12px; border-radius:10px; font-size:.85rem; display:flex; gap:8px; align-items:flex-start;
      background: color-mix(in srgb, var(--info-color, #039be5) 12%, transparent); color: var(--primary-text-color); }
    .banner ha-icon { --mdc-icon-size:18px; color: var(--info-color, #039be5); flex:none; }
    .msg { margin-top:10px; font-size:.82rem; color:var(--secondary-text-color); }
    .tiles { margin-top:14px; display:grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap:8px; }
    .tile { padding:10px 12px; border-radius:12px; background:var(--secondary-background-color); min-width:0; }
    .tile .l { font-size:.75rem; color:var(--secondary-text-color); text-transform:uppercase; letter-spacing:.04em; }
    .tile .v { font-size:1.25rem; font-weight:500; margin-top:2px; color:var(--primary-text-color); white-space:nowrap; font-variant-numeric: tabular-nums; }
    .tile .s { font-size:.78rem; color:var(--secondary-text-color); margin-top:2px; }
    .tile .v.pos { color: var(--success-color, #43a047); }
    .tile .v.neg { color: var(--error-color, #db4437); }
    .sec { margin-top:16px; }
    .sec-t { font-size:.8rem; font-weight:600; color:var(--secondary-text-color); text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px; }
    .checks { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap:4px 16px; }
    .check { display:flex; align-items:center; gap:8px; font-size:.88rem; color:var(--primary-text-color); padding:3px 0; min-width:0; }
    .check ha-icon { --mdc-icon-size:18px; flex:none; }
    .check.ok ha-icon { color: var(--success-color, #43a047); }
    .check.no ha-icon { color: var(--disabled-text-color, #9e9e9e); }
    .check.no { color: var(--secondary-text-color); }
    .check .d { margin-left:auto; color:var(--secondary-text-color); font-size:.8rem; white-space:nowrap; font-variant-numeric: tabular-nums; }
    .run { font-size:.88rem; line-height:1.6; color:var(--primary-text-color); }
    .run b { font-weight:500; }
    .modes { display:flex; border-radius:10px; overflow:hidden; border:1px solid var(--divider-color); }
    .modes button { flex:1; border:0; padding:9px 6px; font:inherit; font-size:.88rem; cursor:pointer; background:transparent; color:var(--primary-text-color); }
    .modes button + button { border-left:1px solid var(--divider-color); }
    .modes button.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .row { display:flex; align-items:center; gap:12px; padding:8px 0; }
    .row + .row { border-top:1px solid var(--divider-color); }
    .row .txt { flex:1; min-width:0; }
    .row .n { font-size:.92rem; color:var(--primary-text-color); }
    .row .h { font-size:.78rem; color:var(--secondary-text-color); }
    details { margin-top:16px; border-top:1px solid var(--divider-color); padding-top:8px; }
    summary { cursor:pointer; font-size:.95rem; font-weight:500; color:var(--primary-text-color); padding:6px 0; list-style:none; display:flex; align-items:center; gap:6px; }
    summary::-webkit-details-marker { display:none; }
    summary ha-icon { --mdc-icon-size:20px; transition: transform .2s; }
    details[open] summary ha-icon { transform: rotate(90deg); }
    .grp { margin-top:10px; }
    .grp-t { font-size:.78rem; font-weight:600; color:var(--secondary-text-color); text-transform:uppercase; letter-spacing:.05em; margin:6px 0 2px; }
    .field { display:flex; align-items:center; gap:10px; padding:6px 0; }
    .field + .field { border-top:1px dashed var(--divider-color); }
    .field .txt { flex:1; min-width:0; }
    .inp { display:flex; align-items:center; gap:6px; flex:none; }
    .inp input { width:104px; box-sizing:border-box; padding:6px 8px; border-radius:8px; border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color); font:inherit; font-size:.92rem; text-align:right; font-variant-numeric: tabular-nums; }
    .inp input[type=time] { text-align:right; }
    .inp input:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
    .inp .u { width:34px; font-size:.8rem; color:var(--secondary-text-color); }
    .inp input.saved { outline:2px solid var(--success-color, #43a047); }
    .foot { margin-top:14px; display:flex; gap:8px; flex-wrap:wrap; }
    .btn { border:1px solid var(--divider-color); background:transparent; color:var(--primary-text-color); border-radius:999px; padding:6px 14px; font:inherit; font-size:.82rem; cursor:pointer; display:inline-flex; align-items:center; gap:6px; }
    .btn ha-icon { --mdc-icon-size:16px; }
    .btn:hover, .modes button:hover:not(.active) { background: var(--secondary-background-color); }
    .empty { padding:8px 0; color:var(--secondary-text-color); }
    [hidden] { display:none !important; }
  `;

  // Safari/WebKit (iPhone/iPad) has no working scroll anchoring: when the card above the
  // viewport changes height, the page jumps. Compensate the scroll position there.
  const UA = navigator.userAgent || "";
  const WEBKIT = /iPhone|iPad|iPod/.test(UA)
    || (/Macintosh/.test(UA) && navigator.maxTouchPoints > 1)
    || (/AppleWebKit/.test(UA) && !/(Chrome|Chromium|Edg|OPR|Android)/.test(UA));
  const NATIVE_ANCHOR = !WEBKIT && typeof CSS !== "undefined" && !!CSS.supports && CSS.supports("overflow-anchor", "auto");
  const raf = (f) => (typeof requestAnimationFrame === "function" ? requestAnimationFrame(f) : setTimeout(f, 16));

  const findScroller = (el) => {
    let n = el;
    for (let i = 0; i < 80 && n; i++) {
      n = n.assignedSlot || n.parentNode || (n instanceof ShadowRoot ? n.host : null);
      if (!n || n === document || n === document.documentElement || n === document.body) break;
      if (n.nodeType === 1) {
        const oy = getComputedStyle(n).overflowY;
        if ((oy === "auto" || oy === "scroll" || oy === "overlay") && n.scrollHeight > n.clientHeight + 1) return n;
      }
    }
    return document.scrollingElement || document.documentElement;
  };

  const sameMap = (a, b) => {
    if (a === b) return true;
    if (!a || !b) return false;
    const ka = Object.keys(a);
    return ka.length === Object.keys(b).length && ka.every((k) => a[k] === b[k]);
  };

  class PvSurplusCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._map = null;
      this._mapSource = null;
      this._built = false;
    }

    static getStubConfig() {
      return {};
    }

    static getConfigElement() {
      return document.createElement(EDITOR);
    }

    setConfig(config) {
      this._config = { show_settings: true, ...(config || {}) };
      this._built = false;
      if (this._hass) this._update();
    }

    set hass(hass) {
      this._hass = hass;
      this._update();
    }

    getCardSize() {
      return 9;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, rows: "auto" };
    }

    get _t() {
      const lang = (this._hass?.locale?.language || this._hass?.language || "en").split("-")[0];
      return T[lang] || T.en;
    }

    _lang() {
      return this._hass?.locale?.language || this._hass?.language || "en";
    }

    _resolve() {
      const entities = this._hass.entities || {};
      if (this._map && this._mapSource === entities) return this._map;
      const wanted = this._config.device_id;
      let device = wanted;
      const map = {};
      for (const [eid, e] of Object.entries(entities)) {
        if (e.platform !== DOMAIN || !e.translation_key) continue;
        if (!device) device = e.device_id;
        if (e.device_id !== device) continue;
        map[e.translation_key] = eid;
      }
      const next = Object.keys(map).length ? map : null;
      // Home Assistant hands out a new entities object now and then with the same content.
      // Keep the old map then, so the card is not rebuilt (a rebuild makes the page jump).
      if (!(this._map && next && this._device === device && sameMap(this._map, next))) this._map = next;
      this._device = device;
      this._mapSource = entities;
      return this._map;
    }

    _st(key) {
      const eid = this._map?.[key];
      return eid ? this._hass.states[eid] : undefined;
    }

    _num(v, digits = 0) {
      if (v === null || v === undefined || Number.isNaN(Number(v))) return "–";
      return new Intl.NumberFormat(this._lang(), { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(v));
    }

    _time(iso) {
      if (!iso) return "–";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "–";
      return d.toLocaleTimeString(this._lang(), { hour: "2-digit", minute: "2-digit" });
    }

    _call(domain, service, data) {
      return this._hass.callService(domain, service, data).catch((err) => {
        // eslint-disable-next-line no-console
        console.error(`[${CARD}]`, err);
      });
    }

    _moreInfo(key) {
      const entityId = this._map?.[key];
      if (!entityId) return;
      this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
    }

    _guardScroll() {
      if (NATIVE_ANCHOR || this.__scrollGuard || typeof ResizeObserver === "undefined") return;
      const g = { h: 0, w: 0, sc: null };
      this.__scrollGuard = new ResizeObserver(() => {
        if (!this.isConnected) { g.h = 0; return; }
        const r = this.getBoundingClientRect();
        const oldH = g.h, oldW = g.w;
        if (r.height <= 0) return;
        g.h = r.height; g.w = r.width;
        if (!oldH || Math.abs(r.width - oldW) > 1) return;
        const d = r.height - oldH;
        if (Math.abs(d) < 1) return;
        if (!g.sc || !g.sc.isConnected) g.sc = findScroller(this);
        const sc = g.sc;
        const isDoc = sc === document.scrollingElement || sc === document.documentElement || sc === document.body;
        const top = isDoc ? 0 : sc.getBoundingClientRect().top;
        const vw = isDoc ? window.innerWidth : sc.clientWidth;
        // only when the card is completely above the visible area and spans the width
        if (r.top + oldH > top + 1 || r.width < vw * 0.8) return;
        if (isDoc) window.scrollBy(0, d); else sc.scrollTop += d;
      });
      this.__scrollGuard.observe(this);
    }

    // ------------------------------------------------------------------ build
    _build() {
      // Keep the current height until the new ha-card shows its content.
      const held = this.isConnected && this.shadowRoot.childElementCount ? this.getBoundingClientRect().height : 0;
      if (held > 0) this.style.minHeight = `${held}px`;
      try {
        this._render();
      } finally {
        this._guardScroll();
        if (held > 0) {
          const tag = (this.__holdTag = (this.__holdTag || 0) + 1);
          raf(() => raf(() => { if (this.__holdTag === tag) this.style.minHeight = ""; }));
        }
      }
    }

    _render() {
      const t = this._t;
      const root = this.shadowRoot;
      if (!this._map) {
        root.innerHTML = `<style>${STYLE}</style><ha-card><div class="empty">${esc(t.notFound)}</div></ha-card>`;
        this._built = false;
        return;
      }
      const has = (k) => !!this._map[k];
      const toggles = ["observe", "dynamic_power", "use_forecast", "price_control"].filter(has);
      const groups = GROUPS.map(([g, keys]) => [g, keys.filter(has)]).filter(([, keys]) => keys.length);

      root.innerHTML = `
        <style>${STYLE}</style>
        <ha-card lang="${esc((this._lang() || "en").split("-")[0])}">
          <div class="head">
            <div class="title"><ha-icon icon="mdi:heat-pump"></ha-icon><span id="name"></span></div>
            <div class="chips">
              <span class="chip" id="status" role="button" tabindex="0"><ha-state-icon id="status-icon"></ha-state-icon><span id="status-text"></span></span>
              <span class="chip small" id="signal"><span class="dot" id="signal-dot"></span><span>${esc(t.signal)}: <span id="signal-text"></span></span></span>
            </div>
          </div>
          <div class="banner" id="banner" hidden><ha-icon icon="mdi:eye-outline"></ha-icon><span>${esc(t.observe)}</span></div>
          <div class="msg" id="msg" hidden></div>
          <div class="tiles" id="tiles"></div>
          <div class="sec" id="cond-sec">
            <div class="sec-t" id="cond-title"></div>
            <div class="checks" id="checks"></div>
            <div class="run" id="run" hidden></div>
          </div>
          <div class="sec" id="peak-sec" hidden>
            <div class="sec-t" id="peak-title"></div>
            <div class="checks" id="peak-checks"></div>
            <div class="run" id="peak-run" hidden></div>
          </div>
          <div class="sec">
            <div class="sec-t">${esc(t.control)}</div>
            <div class="modes" id="modes">
              ${["auto", "off", "manual"].map((m) => `<button data-mode="${m}">${esc(t.modes[m])}</button>`).join("")}
            </div>
            <div id="toggles">
              ${toggles
                .map(
                  (k) => `<div class="row"><div class="txt"><div class="n">${esc(t.toggles[k][0])}</div><div class="h">${esc(t.toggles[k][1])}</div></div><ha-switch data-toggle="${k}"></ha-switch></div>`
                )
                .join("")}
            </div>
          </div>
          <details id="settings" ${this._config.show_settings === false ? "hidden" : ""}>
            <summary><ha-icon icon="mdi:chevron-right"></ha-icon>${esc(t.settings)}</summary>
            ${groups
              .map(
                ([g, keys]) => `<div class="grp" data-grp="${g}"><div class="grp-t">${esc(t.groups[g])}</div>
                  ${keys
                    .map((k) => {
                      const [label, help] = t.fields[k] || [k, ""];
                      if (SWITCH_FIELDS.has(k)) {
                        return `<div class="field"><div class="txt"><div class="n">${esc(label)}</div>${help ? `<div class="h">${esc(help)}</div>` : ""}</div>
                        <ha-switch data-toggle="${k}"></ha-switch></div>`;
                      }
                      const isTime = k.startsWith("window_");
                      return `<div class="field"><div class="txt"><div class="n">${esc(label)}</div>${help ? `<div class="h">${esc(help)}</div>` : ""}</div>
                        <div class="inp"><input data-field="${k}" type="${isTime ? "time" : "number"}" ${isTime ? 'step="60"' : 'inputmode="decimal"'}><span class="u" data-unit="${k}"></span></div></div>`;
                    })
                    .join("")}
                </div>`
              )
              .join("")}
            <div class="foot">
              ${["reset_lock", "reset_counter"]
                .filter(has)
                .map((k) => `<button class="btn" data-press="${k}"><ha-icon icon="${k === "reset_lock" ? "mdi:lock-open-variant-outline" : "mdi:counter"}"></ha-icon>${esc(t.buttons[k])}</button>`)
                .join("")}
            </div>
          </details>
        </ha-card>`;

      root.getElementById("status").addEventListener("click", () => this._moreInfo("status"));
      root.querySelectorAll("[data-mode]").forEach((b) =>
        b.addEventListener("click", () =>
          this._call("select", "select_option", { entity_id: this._map.mode, option: b.dataset.mode })
        )
      );
      root.querySelectorAll("[data-toggle]").forEach((sw) =>
        sw.addEventListener("change", (ev) => {
          const key = sw.dataset.toggle;
          const on = ev.target.checked;
          this._call("switch", on ? "turn_on" : "turn_off", { entity_id: this._map[key] });
        })
      );
      root.querySelectorAll("[data-field]").forEach((inp) =>
        inp.addEventListener("change", () => this._saveField(inp))
      );
      root.querySelectorAll("[data-press]").forEach((b) =>
        b.addEventListener("click", () => this._call("button", "press", { entity_id: this._map[b.dataset.press] }))
      );
      this._built = true;
    }

    _saveField(inp) {
      const key = inp.dataset.field;
      const entity_id = this._map[key];
      const st = this._hass.states[entity_id];
      if (!st) return;
      let promise;
      if (key.startsWith("window_")) {
        if (!inp.value) return;
        const v = inp.value.length === 5 ? `${inp.value}:00` : inp.value;
        promise = this._call("time", "set_value", { entity_id, time: v });
      } else {
        let v = Number(String(inp.value).replace(",", "."));
        if (Number.isNaN(v)) return;
        const { min, max } = st.attributes;
        if (min !== undefined) v = Math.max(min, v);
        if (max !== undefined) v = Math.min(max, v);
        promise = this._call("number", "set_value", { entity_id, value: v });
      }
      promise.then(() => {
        inp.classList.add("saved");
        setTimeout(() => inp.classList.remove("saved"), 900);
      });
    }

    // ----------------------------------------------------------------- update
    _update() {
      if (!this._hass || !this._config) return;
      const before = this._map;
      this._resolve();
      if (!this._built || before !== this._map) this._build();
      if (!this._built) return;
      const t = this._t;
      const root = this.shadowRoot;
      const status = this._st("status");
      const a = status?.attributes || {};

      // Header
      const dev = this._hass.devices?.[this._device];
      root.getElementById("name").textContent = this._config.title || dev?.name_by_user || dev?.name || t.title;
      const statusEl = root.getElementById("status");
      const stateText = status
        ? this._hass.formatEntityState
          ? this._hass.formatEntityState(status)
          : status.state
        : "–";
      root.getElementById("status-text").textContent = stateText;
      const iconEl = root.getElementById("status-icon");
      iconEl.hass = this._hass;
      iconEl.stateObj = status;
      iconEl.hidden = !status;
      statusEl.className = `chip tone-${STATUS_TONE[status?.state] || "idle"}`;
      const sig = a.signal_active;
      root.getElementById("signal-dot").className = `dot${sig ? " on" : ""}`;
      root.getElementById("signal-text").textContent = sig === null || sig === undefined ? "–" : sig ? t.on : t.off;
      root.getElementById("banner").hidden = !a.observe;
      const msg = root.getElementById("msg");
      if (a.last_message) {
        msg.hidden = false;
        msg.textContent = `${t.lastAction} ${this._time(a.last_message_at)}: ${a.last_message}`;
      } else msg.hidden = true;

      // Tiles
      const val = (key) => {
        const s = this._st(key);
        return s ? Number(s.state) : undefined;
      };
      const tiles = [];
      const avail = a.available_w;
      tiles.push({
        l: t.tiles.available,
        v: `${this._num(avail)} W`,
        cls: avail >= (val("on_threshold_w") ?? Infinity) ? "pos" : avail < 0 ? "neg" : "",
        s: `${t.threshold} ${this._num(val("on_threshold_w"))} W`,
      });
      if (a.compressor_control) {
        tiles.push({
          l: t.tiles.budget,
          v: `${this._num(a.budget_avg_w)} W`,
          s: a.comp_target_kw !== null && a.comp_target_kw !== undefined ? `${t.target} ${this._num(a.comp_target_kw, 1)} kW` : "",
        });
      }
      tiles.push({
        l: t.tiles.battery,
        v: `${this._num(a.soc)} %`,
        s: `${t.release} ${a.battery_release ? t.on : t.off}`,
      });
      if (a.compressor_control) {
        tiles.push({
          l: t.tiles.compressor,
          v: `${this._num(a.hp_power_w)} W`,
          s: `${t.limit} ${this._num(a.pvmaxcomp_kw, 1)} kW`,
        });
      }
      if (a.forecast) {
        tiles.push({
          l: t.tiles.forecast,
          v: a.forecast_remaining_kwh !== null && a.forecast_remaining_kwh !== undefined ? `${this._num(a.forecast_remaining_kwh, 1)} kWh` : "–",
          s: a.forecast_30min_w !== null && a.forecast_30min_w !== undefined ? `${t.in30} ${this._num(a.forecast_30min_w)} W` : "",
        });
      }
      const grid = a.grid_w;
      tiles.push({
        l: t.tiles.grid,
        v: `${this._num(grid === undefined || grid === null ? grid : Math.abs(grid))} W`,
        s: grid === undefined || grid === null ? "" : grid > 0 ? t.import : t.export,
      });
      if (a.price && a.price_control) {
        const p = a.price_ct;
        const st = a.price_state;
        tiles.push({
          l: t.tiles.price,
          v: p !== null && p !== undefined ? `${this._num(p, 2)} ct/kWh` : "–",
          cls: a.price_cheap ? "pos" : a.price_expensive ? "neg" : "",
          s: st && st !== "ok" ? t.price[st] || st : a.price_cheap ? t.price.cheap : a.price_expensive ? t.price.expensive : t.price.normal,
        });
      }
      const runtime = val("runtime_today");
      tiles.push({
        l: t.tiles.today,
        v: `${a.activations ?? "–"} / ${a.max_activations ?? "–"}`,
        s: `${t.runtime} ${this._num(runtime)} min`,
      });
      if (a.peak && a.price_control) {
        // Runtime of the running EVU block
        const since = a.peak_active && a.peak_since ? new Date(a.peak_since).getTime() : NaN;
        const evuRuntime = Number.isNaN(since) ? 0 : Math.max(0, (Date.now() - since) / 60000);
        tiles.push({
          l: t.tiles.evu,
          v: `${a.peak_count ?? "–"} / ${a.peak_max_per_day ?? "–"}`,
          cls: a.peak_active ? "neg" : "",
          s: a.peak_active
            ? `${t.runtime} ${this._num(evuRuntime)} min · ${t.evuActiveUntil} ${this._time(a.peak_until)}`
            : a.peak_lock_until
              ? `${t.evuLockUntil} ${this._time(a.peak_lock_until)}`
              : `${t.runtime} 0 min`,
        });
      }
      root.getElementById("tiles").innerHTML = tiles
        .map((x) => `<div class="tile"><div class="l">${esc(x.l)}</div><div class="v ${x.cls || ""}">${esc(x.v)}</div><div class="s">${esc(x.s || "")}</div></div>`)
        .join("");

      // Conditions or running info
      const checks = a.checks || {};
      const run = root.getElementById("run");
      const checksEl = root.getElementById("checks");
      const condTitle = root.getElementById("cond-title");
      if (a.requested) {
        condTitle.textContent = a.run_kind === "cheap" ? t.runningCheap : t.running;
        checksEl.hidden = true;
        run.hidden = false;
        const lines = [`<b>${esc(t.since)}</b> ${esc(this._time(a.requested_since))}`];
        lines.push(
          a.min_runtime_until
            ? `<b>${esc(t.minRuntimeUntil)}</b> ${esc(this._time(a.min_runtime_until))}`
            : esc(t.minRuntimeDone)
        );
        if (a.deficit_since) lines.push(`<b>${esc(t.deficitSince)}</b> ${esc(this._time(a.deficit_since))}`);
        run.innerHTML = lines.join("<br>");
      } else {
        condTitle.textContent = t.conditions;
        checksEl.hidden = false;
        run.hidden = true;
        const ws = this._st("window_start")?.state?.slice(0, 5);
        const we = this._st("window_end")?.state?.slice(0, 5);
        const detail = {
          window: ws && we ? `${ws}–${we}` : "",
          battery: a.soc !== undefined && a.soc !== null ? `${this._num(a.soc)} % / ${this._num(val("soc_stop"))} %` : "",
          lock: a.lock_until ? `${t.lockUntil} ${this._time(a.lock_until)}` : "",
          limit: `${a.activations ?? "–"} / ${a.max_activations ?? "–"}`,
          surplus: `${this._num(a.available_w)} W`,
          forecast: a.forecast_30min_w !== null && a.forecast_30min_w !== undefined ? `${this._num(a.forecast_30min_w)} W` : "",
          delay: a.surplus_since ? `${t.since} ${this._time(a.surplus_since)}` : "",
          price: a.price_ct !== null && a.price_ct !== undefined ? `${this._num(a.price_ct, 1)} / ${this._num(a.price_expensive_ct, 1)} ct` : "",
        };
        const keys = CHECKS.filter((k) => (k !== "forecast" || a.forecast) && (k !== "price" || k in checks));
        checksEl.innerHTML = keys
          .map((k) => {
            const ok = !!checks[k];
            return `<div class="check ${ok ? "ok" : "no"}"><ha-icon icon="${ok ? "mdi:check-circle" : "mdi:circle-outline"}"></ha-icon><span>${esc(t.checks[k])}</span><span class="d">${esc(detail[k] || "")}</span></div>`;
          })
          .join("");
      }

      // EVU block (peak mode)
      const peakSec = root.getElementById("peak-sec");
      peakSec.hidden = !a.peak || a.price_control !== true;
      if (!peakSec.hidden) {
        const peakRun = root.getElementById("peak-run");
        const peakChecksEl = root.getElementById("peak-checks");
        const ct = (v) => (v !== null && v !== undefined ? `${this._num(v, 1)} ct` : "–");
        if (a.peak_active) {
          root.getElementById("peak-title").textContent = t.peakRunning;
          peakChecksEl.hidden = true;
          peakRun.hidden = false;
          const lines = [`<b>${esc(t.since)}</b> ${esc(this._time(a.peak_since))}`];
          lines.push(`<b>${esc(t.peakUntil)}</b> ${esc(this._time(a.peak_until))}`);
          lines.push(`${esc(t.peakLiftBelow)} ${esc(ct(a.peak_limit_ct))}`);
          peakRun.innerHTML = lines.join("<br>");
        } else {
          root.getElementById("peak-title").textContent = t.peak;
          peakChecksEl.hidden = false;
          peakRun.hidden = true;
          const pc = a.peak_checks || {};
          const pd = {
            expensive: `${ct(a.peak_price_ct)} / ${ct(a.price_expensive_ct)}`,
            above_average: `${ct(a.peak_price_ct)} / ${ct(a.peak_limit_ct)}`,
            battery:
              a.soc !== undefined && a.soc !== null
                ? `${this._num(a.soc)} % / ${this._num(a.backup_reserve)} %`
                : "",
            lock: a.peak_lock_until ? `${t.lockUntil} ${this._time(a.peak_lock_until)}` : "",
            limit: `${a.peak_count ?? "–"} / ${a.peak_max_per_day ?? "–"}`,
            no_surplus: a.peak_import_since ? `${t.since} ${this._time(a.peak_import_since)}` : "",
          };
          peakChecksEl.innerHTML = PEAK_CHECKS.filter((k) => k in pc)
            .map((k) => {
              const ok = !!pc[k];
              return `<div class="check ${ok ? "ok" : "no"}"><ha-icon icon="${ok ? "mdi:check-circle" : "mdi:circle-outline"}"></ha-icon><span>${esc(t.peakChecks[k])}</span><span class="d">${esc(pd[k] || "")}</span></div>`;
            })
            .join("");
        }
      }

      // Controls
      const mode = this._st("mode")?.state;
      root.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
      root.querySelectorAll("[data-toggle]").forEach((sw) => {
        const s = this._st(sw.dataset.toggle);
        sw.checked = s?.state === "on";
        sw.disabled = !s || s.state === "unavailable";
      });

      // Price settings only while the price control is switched on
      const priceOn = this._st("price_control")?.state === "on";
      root.querySelectorAll('[data-grp="price"], [data-grp="peak"]').forEach((g) => (g.hidden = !priceOn));

      // Settings (do not overwrite a field the user is editing)
      const active = root.activeElement;
      root.querySelectorAll("[data-field]").forEach((inp) => {
        const key = inp.dataset.field;
        const s = this._st(key);
        const unit = root.querySelector(`[data-unit="${key}"]`);
        if (unit) unit.textContent = s?.attributes?.unit_of_measurement || "";
        if (!s || inp === active) return;
        if (key.startsWith("window_")) {
          inp.value = (s.state || "").slice(0, 5);
        } else {
          inp.min = s.attributes.min;
          inp.max = s.attributes.max;
          inp.step = s.attributes.step;
          const n = Number(s.state);
          inp.value = Number.isNaN(n) ? "" : String(Math.round(n * 100) / 100);
        }
      });
    }
  }

  class PvSurplusCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    _render() {
      if (!this._hass) return;
      const lang = (this._hass.locale?.language || this._hass.language || "en").split("-")[0];
      const t = (T[lang] || T.en).editor;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = (s) => t[s.name] || s.name;
        this._form.addEventListener("value-changed", (ev) => {
          this._config = ev.detail.value;
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.data = { show_settings: true, ...this._config };
      this._form.schema = [
        { name: "device_id", selector: { device: { integration: DOMAIN } } },
        { name: "title", selector: { text: {} } },
        { name: "show_settings", selector: { boolean: {} } },
      ];
    }
  }

  // Some HACS cards install a scoped custom element registry polyfill that
  // replaces window.customElements. Elements defined before that swap are
  // no longer found ("Custom element doesn't exist"), so check again for a
  // while and register with the current registry if needed.
  const ensureDefined = () => {
    try {
      if (!customElements.get(CARD)) customElements.define(CARD, PvSurplusCard);
      if (!customElements.get(EDITOR)) customElements.define(EDITOR, PvSurplusCardEditor);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn(`[${CARD}] define failed`, err);
    }
  };
  ensureDefined();
  [250, 1000, 3000, 8000, 20000].forEach((ms) => setTimeout(ensureDefined, ms));
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === CARD)) {
    const de = String(document.documentElement.lang || navigator.language || "").toLowerCase().startsWith("de");
    window.customCards.push({
      type: CARD,
      name: "EMS-ESP WP PV Überschuss",
      description: de
        ? "Status, Live-Werte und Einstellungen der PV-Überschuss-Steuerung für die Wärmepumpe."
        : "Status, live values and settings of the heat pump PV surplus control.",
      preview: true,
      documentationURL: "https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss",
    });
  }
  // eslint-disable-next-line no-console
  console.info(`%c ${CARD} %c v${VERSION} `, "background:#ffb300;color:#000;border-radius:3px 0 0 3px", "background:#333;color:#fff;border-radius:0 3px 3px 0");
})();
