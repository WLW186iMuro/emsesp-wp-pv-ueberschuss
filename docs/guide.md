# Guide – EMS-ESP WP PV Überschuss

🇩🇪 [Deutsche Anleitung](anleitung.md) · [Back to overview](../README.md#english)

This guide explains step by step how the integration works, how to set it up and what the card shows.

**Contents**

1. [The idea](#1-the-idea)
2. [Before you start](#2-before-you-start)
3. [Setup step by step](#3-setup-step-by-step)
4. [The first days: observe mode](#4-the-first-days-observe-mode)
5. [How the integration decides](#5-how-the-integration-decides)
6. [Compressor power control (pvmaxcomp)](#6-compressor-power-control-pvmaxcomp)
7. [Price control (optional)](#7-price-control-optional)
8. [The dashboard card explained](#8-the-dashboard-card-explained)
9. [Modes](#9-modes)
10. [Tuning the settings](#10-tuning-the-settings)
11. [Example: a sunny day](#11-example-a-sunny-day)
12. [Entities for your own automations](#12-entities-for-your-own-automations)
13. [FAQ and troubleshooting](#13-faq-and-troubleshooting)

---

## 1. The idea

Buderus, Bosch and Junkers heat pumps have an input for PV / SG Ready. When it is active, the heat pump uses the solar power, for example with a higher hot-water temperature or a heating boost (depending on the controller settings). EMS-ESP exposes this input as text with a bit pattern, e.g. `text.boiler_hpin4opt`:

| State | Bit pattern |
|---|---|
| Normal operation | `000000100000` |
| PV mode | `100000100000` |

The integration sets the first character (bit 0) to `1` when there is enough solar surplus and back to `0` when there isn't. It takes care of three things:

- **The battery comes first.** Solar power only goes to the heat pump once the home battery is charged enough, or when the forecast says it will still be full today.
- **The compressor is protected.** Hysteresis, a minimum runtime, a lock time and a daily limit prevent short cycling.
- **No grid power for PV mode.** Optionally it limits the compressor power (`pvmaxcomp`) to the surplus.

## 2. Before you start

You need:

- **EMS-ESP** connected to Home Assistant (MQTT discovery or the EMS-ESP integration). Check under *Settings → Devices & services → Entities* that `text.boiler_hpin1opt` … `hpin4opt` exist.
- **On the heat pump**, one input (usually input 4) must be set to *PV / SG Ready* in the installer menu. Without that, the heat pump ignores the bit.
- **Inverter sensors:** grid power, battery power and battery state of charge. Check the signs: what is positive when importing, what when charging?
- **Optional:** Solcast (or another PV forecast), plus `number.boiler_pvmaxcomp` and `sensor.boiler_hpcurrpower` for compressor power control.

> ⚠️ **Important:** Turn off other controllers on the same input (evcc SG Ready, your own automations, Node-RED). In *Automatic* mode the integration keeps the bit at the value it wants and overwrites other changes within a minute.

## 3. Setup step by step

1. **Install** via HACS (*Custom repositories* → `https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss`, category *Integration*) or manually to `config/custom_components/emsesp_pv_surplus/`. Restart Home Assistant.
2. **Add it:** *Settings → Devices & services → Add integration → "EMS-ESP WP PV Überschuss"*.
3. **Pick the entities:**

   | Field | Example | Notes |
   |---|---|---|
   | Name | Heat pump PV surplus | device name, defines the entity IDs |
   | EMS-ESP input option | `text.boiler_hpin4opt` | the input set up for PV |
   | Bit position | `0` | first character |
   | Grid power | e.g. smart meter in W | choose the sign |
   | Battery power | e.g. GoodWe battery power | choose the sign |
   | Battery state of charge | SoC in % | |
   | PV max. compressor power | `number.boiler_pvmaxcomp` | optional |
   | Current compressor power | `sensor.boiler_hpcurrpower` | required if pvmaxcomp is set |
   | Forecast remaining today | Solcast "forecast remaining today" (kWh) | optional |
   | Forecast in 30 min | Solcast "power in 30 minutes" (W) | optional |

   ![Setup: source entities](screenshots/einrichtung-1.png) ![Setup: optional entities](screenshots/einrichtung-2.png)

4. **Add the card:** *Edit dashboard → Add card →* search for "EMS-ESP WP PV Überschuss". The card finds the integration by itself.
5. **Check the signs:** on a sunny day, look at the *Grid* tile. If you are exporting it must say "export". If it says "import", the sign is wrong. Change it via *Integration → Configure*.

## 4. The first days: observe mode

New installations start in **observe mode**. The integration does all the calculations but writes nothing to the heat pump. Instead you get logbook entries such as:

```
[Observe] would start PV mode (PV surplus)
[Observe] would set PV max. compressor power 1.0 → 2.2 kW (budget avg 2312 W)
[Observe] would end PV mode (surplus gone)
```

![Logbook in observe mode (German UI)](screenshots/logbuch-start.png)

This way you can check over a few sunny days whether starts and stops fit your house. When everything looks right, turn off the **Observe mode** switch on the card. From then on it really switches.

## 5. How the integration decides

Every 15 seconds the integration reads the sensors and decides again.

### 5.1 Available power

```
available = export − battery discharge − (battery charge, if the battery is released)
```

- Export to the grid always counts as surplus.
- Battery discharge is subtracted. The heat pump should not run from the battery.
- Battery **charging** power only counts as surplus once the battery is **released**. Until then the battery has priority.

**Battery release**, when one of the two conditions holds:

- state of charge ≥ *Battery release from* (default 80 %), **or**
- state of charge ≥ *Battery release with forecast from* (default 60 %) **and** the forecast for the rest of the day minus the *forecast reserve* (4 kWh) is enough to fill the battery.

*Example:* 10 kWh battery at 65 % → 3.5 kWh missing. Solcast still expects 9 kWh today. 9 − 4 = 5 kWh ≥ 3.5 kWh → **released**.

### 5.2 Switching on

PV mode starts when **all** start conditions are met. The card shows them as a checklist:

| Condition | Default |
|---|---|
| Readings available | grid, battery, SoC readable |
| Sun above horizon | `sun.sun` |
| Inside start window | 10:00–16:00 |
| Battery above stop level | > 50 % |
| No lock time | 120 min after the last stop |
| Daily limit not reached | max. 2 starts per day |
| Surplus ≥ switch-on threshold | ≥ 1500 W |
| Forecast in 30 min ≥ threshold | Solcast ≥ 1500 W (if enabled) |
| Surplus stable long enough | 5 min in a row |

If the surplus drops below the threshold during the switch-on delay, the delay starts over. A passing cloud does not start the heat pump.

### 5.3 Switching off

| Reason | When |
|---|---|
| No surplus | after the **minimum runtime** (30 min), when the available power is ≤ **−800 W** (i.e. 800 W drawn from grid/battery) for **10 min** in a row |
| Battery too low | immediately, when the SoC is below the stop level (50 %) for 2 min |
| Sunset | immediately |
| Readings missing | after 10 min without grid, battery or SoC value |

Between −800 W and +1500 W the heat pump simply keeps running. That's the **hysteresis**. It keeps a passing cloud from turning the compressor off.

After each stop the **lock time** (120 min) starts. A new start is only possible after that, at most 2 per day.

## 6. Compressor power control (pvmaxcomp)

In PV mode the heat pump would otherwise run at full power, even with only 1.5 kW of surplus. `number.boiler_pvmaxcomp` (*PV max. compressor power*) limits the compressor in PV mode. The integration adjusts this value:

1. It continuously calculates the **budget** = current compressor power + available power. That's the power the heat pump may use without drawing from the grid.
2. The budget is averaged over the **adjustment interval** (5 min).
3. Every 5 minutes it calculates the target: `budget avg − reserve (0.1 kW)`, limited to **min. 1.0 kW** and **max. 2.5 kW**.
4. It only writes when the target differs from the current value by at least **0.2 kW**.
5. Without battery release the limit stays at the minimum.

*Example:* the compressor draws 1.9 kW and 0.4 kW is still exported → budget 2.3 kW → target 2.2 kW.

> Note: after starting, the heat pump often ramps up first and only switches to PV mode after a while. The limit takes effect from then on. After a stop, `pvmaxcomp` keeps its last value. It only applies in PV mode.

Turn it off with the **Compressor power control** switch on the card.

## 7. Price control (optional)

For anyone with a **dynamic tariff** (e.g. Tibber, aWATTar, Octopus) or a **time-of-use heat pump tariff** (low/standard/high). Without such a tariff just leave it out – there are no price settings then and nothing changes.

### Switching it on – two steps

1. **Add a price sensor:** *Integration → Configure →* **Electricity price sensor**. Only then are the price entities created.
2. Turn on the **Price control** switch on the card. While it is off, all price settings are locked (*unavailable*) and hidden on the card.

### Unit of the price sensor

Internally everything is in **ct/kWh**, and the unit is detected automatically:

| Sensor unit | Examples |
|---|---|
| `EUR/kWh`, `€/kWh` | Tibber, Nord Pool, EPEX Spot, Octopus Germany |
| `c/kWh`, `ct/kWh`, `Cent/kWh` | Nord Pool (HACS) with the cents option |
| `EUR/MWh` | wholesale price sensors |

If the sensor has **no unit** (e.g. your own template sensor), pick it under *Configure → Unit of the price sensor*. An unrecognised unit is reported during setup already; at runtime the price control pauses ("unit unknown") – it never guesses.

### What the price does

| Price | Behaviour |
|---|---|
| **≤ cheap threshold** (default 15 ct/kWh) | PV mode **even without surplus**. Also at night, outside the start window and with an empty battery. Does **not** count towards the daily limit. Minimum runtime and lock time still apply. `pvmaxcomp` is set to *Compressor power on cheap electricity*. |
| in between | normal PV surplus logic |
| **≥ expensive threshold** (default 35 ct/kWh) | no PV start (new start condition "Electricity price not too high"). Optional *Stop when expensive*: a running PV mode ends after the minimum runtime. |

**Hand-overs without a stop:** if PV mode is running and electricity becomes cheap (e.g. at sunset), it carries on as cheap mode. If the cheap period ends and there is PV surplus, it carries on as PV mode. Otherwise cheap mode ends after the minimum runtime.

**Dropouts:** if the price sensor is briefly unavailable (typical at the hour or quarter change), the last price is used for up to 15 minutes. After that the price control pauses – no cheap starts and no blocking. After a Home Assistant restart, a running cheap-power run also continues for up to 15 minutes until the price sensor reports a value again.

> 💡 **Fixed peak/off-peak times without a price sensor?** Create a template sensor that returns the price by time of day, e.g. *Settings → Devices & services → Helpers → Template → Sensor* with `{{ 22.5 if now().hour < 6 or now().hour >= 22 else 31.8 }}` and the unit `ct/kWh`.

> ℹ️ The integration does not control the inverter. Whether the home battery discharges into the heat pump during cheap mode is up to your inverter or its integration.

### 7.1 Peak mode: EVU block on high price and empty battery

When electricity is expensive and the home battery is empty, the heat pump would run on expensive grid power. Peak mode then blocks it for a while through the **EVU block**, the same function a grid operator may use to switch the heat pump off.

**Setup:** *Integration → Configure*. All four entities are needed:

| Field | Example |
|---|---|
| EMS-ESP input option for the EVU block | `text.boiler_hpin1opt` |
| EVU block bit position | `0` (first character, default) |
| Battery backup reserve in % | reserve entity of your inverter |
| Current hourly price | Tibber “Hourly price current” (€/kWh or ct/kWh) |
| Average price today | Tibber “Average price today” (€/kWh or ct/kWh) |

You don't need a price sensor (section 7) for this, but the **Price control** switch must be on. Units are detected as for the price sensor; the *Unit of the price sensor* setting applies to all price sensors.

**Setting the block:** the character at the **bit position** (default: first character, `1xxxxxxxxxxxxxx`) is set to `1`; all other characters stay as they are. This happens when all of these are true at the same time:

| Condition | Default |
|---|---|
| **Readings available:** grid, battery and SoC plus a valid EVU input value (only `0`/`1`, bit position inside the pattern) | |
| Price control on, mode *Automatic*, no PV mode | |
| Hourly price ≥ **expensive threshold** | 35 ct/kWh |
| Hourly price > **daily average × 108 %** | 108 % |
| SoC ≤ **backup reserve + 2 %** | 2 % |
| **Lock time:** 60 min since the last EVU block was lifted | 60 min |
| at most **2 activations per day** | 2 |
| available power **≤ 0 W for 10 min without a break** (grid import) | 10 min |

**Lifting the block** (character back to `0`):

- as soon as the hourly price is **below daily average × 108 %** (or no price is available),
- at the latest after the **maximum block duration of 120 min**, whatever the price is then. The lock time follows; if the conditions are still met afterwards, a second block can follow (daily limit),
- at once if grid, battery or SoC readings are **missing for 10 min**,
- at once when price control is switched off or the mode is changed.

During the block the status shows **Peak mode – EVU block active**, and PV mode does not start. All values in the table can be changed in the settings group *Peak mode (EVU block)* (only while price control is on). In **observe mode** nothing is set; instead the logbook shows “[Observe] would set EVU block (…)” or “… lift …”. A block the integration set itself is always lifted again, also in observe mode and when the integration is removed.

> ⚠️ Check in EMS-ESP first which character of `hpin1opt` is the EVU block on your heat pump (usually the first on Buderus/Bosch/Junkers). An EVU contact wired by the grid operator is not affected.

## 8. The dashboard card explained

![Dashboard card (German UI; shown in English when Home Assistant is set to English)](screenshots/karte.png)

**Header**

- **Status chip:** e.g. *PV mode*, *Waiting for surplus*, *Lock time*, *Battery below stop level*, *Sun has set*.
- **HP signal: on/off:** the actual state of the bit in EMS-ESP.
- **Blue banner:** shown while observe mode is on.
- **Last …:** the latest message (start, stop, power change).

**Tiles**

| Tile | Meaning |
|---|---|
| Available | available power after battery priority, threshold below |
| Budget avg | averaged budget for power control, target below |
| Battery | SoC, release on/off or how many kWh are missing |
| Compressor | current compressor power, limit (pvmaxcomp) below |
| Forecast | Solcast remaining today, power in 30 min below |
| Grid | power at the grid connection: import or export |
| PV surplus today | starts today / daily limit, PV runtime today below |
| EVU locks today | only with peak mode and price control on: blocks today / daily limit, below it the runtime of the current block and until when it lasts at the latest, or until when the lock time applies |
| Electricity price | only with price control: current price in ct/kWh, cheap / normal / expensive below |

**Start conditions / PV mode running**

- While PV mode is off you see the checklist from section 5.2. Green means met, grey means not met, with the current values on the right.
- While PV mode runs you see *since when*, *minimum runtime until* and, if relevant, *surplus missing since*.

**Control**

- **Automatic / Off / Manual on:** see section 9.
- **Observe mode:** calculate only, write nothing.
- **Compressor power control:** adjust pvmaxcomp yes/no.
- **Use PV forecast:** use Solcast for battery release and switch-on.
- **Price control:** only with a price sensor, see section 7.

![Settings 1](screenshots/einstellungen-1.png)
![Settings 2](screenshots/einstellungen-2.png)

**Settings** (collapsible), in the groups *Solar mode (PV surplus)*, *Battery & forecast*, *Compressor protection & times*, *Power control* and – with price control on – *Electricity price* and *Peak mode (EVU block)*. Changes take effect immediately. Below are the **Lift lock time** and **Reset daily counter** buttons. With peak mode they also reset the EVU lock time and the EVU daily counter; a running EVU block stays. The checklists are called **Start conditions solar mode (PV surplus)** and **Start conditions peak mode (EVU block)**; the second one only appears with peak mode and price control on.

Card options (card editor or YAML):

```yaml
type: custom:emsesp-pv-surplus-card
device_id: …            # only with more than one instance
title: Heat pump PV     # optional
show_settings: true     # show the settings
```

## 9. Modes

| Mode | Behaviour |
|---|---|
| **Automatic** | normal control as described above |
| **Off** | hands the heat pump back to normal operation (bit = 0) and writes nothing afterwards. You can then operate the input yourself. |
| **Manual on** | PV mode on immediately, with no conditions and no daily counter. Useful to test whether the heat pump reacts to the signal. Switch back to Automatic afterwards. |

## 10. Tuning the settings

| Situation | Suggestion |
|---|---|
| Small battery (≤ 5 kWh) | set *Battery capacity*, *Battery release from* around 90 % |
| No battery | create template sensors for battery power (always 0 W) and SoC (100 %) |
| Bigger heat pump (9–12 kW) | raise *Compressor power max.*, e.g. 3.5–4 kW |
| Heat pump still cycles | raise *Minimum runtime* and *Lock time*, set *Max. activations* to 1 |
| Starts too rarely | lower the *Switch-on threshold* (e.g. 1200 W), widen the *start window* |
| Often grid import in PV mode | move the *Switch-off threshold* closer to 0 (e.g. −400 W), raise the *Power reserve* |

All settings are entities too (number / switch / select / time). You can change them in automations, e.g. a different start window in winter.

## 11. Example: a sunny day

| Time | What happens | Status |
|---|---|---|
| 08:30 | Sun, but battery at 35 % | Battery below stop level |
| 10:15 | Battery 62 %, Solcast covers the rest → battery released | Waiting for surplus |
| 11:47 | 1,900 W available | Surplus detected – switch-on delay |
| 11:52 | stable for 5 min → bit = 1 | PV mode |
| 11:57 | budget avg 2,312 W → pvmaxcomp 1.0 → 2.2 kW | PV mode |
| 14:30 | Clouds, −900 W | PV mode – surplus missing |
| 14:40 | 10 min deficit → bit = 0 | Lock time until 16:40 |
| 16:40 | Lock time over, but outside start window | Outside start window |
| 18:20 | Sunset | Sun has set |

## 12. Entities for your own automations

| Entity | Content |
|---|---|
| `sensor.<name>_status` | status with many attributes (checks, values, times) |
| `sensor.<name>_available_power` | available power in W |
| `sensor.<name>_power_budget_avg` | budget avg in W |
| `sensor.<name>_compressor_target` | target for pvmaxcomp in kW |
| `sensor.<name>_activations_today` | starts today |
| `sensor.<name>_pv_runtime_today` | PV runtime today |
| `sensor.<name>_locked_until` | end of lock time |
| `binary_sensor.<name>_pv_mode_requested` | the integration wants PV mode |
| `binary_sensor.<name>_pv_signal_at_heat_pump` | bit actually set |
| `binary_sensor.<name>_battery_release` | battery released |
| `select.<name>_mode` | automatic / off / manual |
| `switch.<name>_price_control` | price control on/off (only with a price sensor) |

![Device page](screenshots/geraet.png)

The exact IDs depend on the device name and the Home Assistant language. You find them under *Settings → Devices & services → EMS-ESP WP PV Überschuss → device*.

## 13. FAQ and troubleshooting

**The heat pump doesn't react although "HP signal: on".**
Check in the heat pump controller that the input is set to PV / SG Ready. Test with *Manual on*.

**Status "Readings missing".**
A source sensor has been `unavailable` for more than 2 minutes. Short dropouts (e.g. an MQTT reconnect) are ignored. After 10 minutes a running PV mode is stopped to be safe.

**Card shows "Custom element doesn't exist".**
Reload the page once with Ctrl+F5. With dashboards in YAML mode, add the resource `/emsesp_pv_surplus/emsesp-pv-surplus-card.js` (type *module*) yourself.

**I use evcc / my own automation on the same input.**
Turn one of them off, or they will keep switching each other.

**What happens when I remove the integration?**
If it had set the bit, it resets it to normal operation.

**Report a bug:** [open an issue](https://github.com/WLW186iMuro/emsesp-wp-pv-ueberschuss/issues) and attach the diagnostics (*Integration → ⋮ → Download diagnostics*).
