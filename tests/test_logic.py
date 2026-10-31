"""Unit tests for the decision logic (run: python -m unittest discover tests)."""

from __future__ import annotations

import importlib.util
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import sys
import unittest

_LOGIC = Path(__file__).resolve().parents[1] / "custom_components" / "emsesp_pv_surplus" / "logic.py"
_spec = importlib.util.spec_from_file_location("logic", _LOGIC)
logic = importlib.util.module_from_spec(_spec)
sys.modules["logic"] = logic
_spec.loader.exec_module(logic)

TZ = timezone(timedelta(hours=2))
BITS_OFF = "000000100000"
BITS_ON = "100000100000"


def at(h: int, m: int = 0, s: int = 0, day: int = 18) -> datetime:
    return datetime(2026, 10, day, h, m, s, tzinfo=TZ)


class Sim:
    """Steps the controller in 15 s ticks with a scripted environment."""

    def __init__(self, **settings):
        self.settings = logic.Settings(**settings)
        self.state = logic.State()
        self.now = at(11)
        self.grid_w = 0.0
        self.battery_w = 0.0
        self.soc = 100.0
        self.sun_up = True
        self.remaining = 10.0
        self.f30 = 3000.0
        self.hp_w = 25.0
        self.bits = BITS_OFF
        self.pvmax = 1.0
        self.price_configured = False
        self.price = None
        self.last: logic.Result | None = None
        self.events: list[str] = []

    def step(self, seconds: int = 15) -> logic.Result:
        self.now += timedelta(seconds=seconds)
        res = logic.evaluate(
            self.settings,
            self.state,
            logic.Inputs(
                now=self.now,
                grid_w=self.grid_w,
                battery_w=self.battery_w,
                soc=self.soc,
                sun_up=self.sun_up,
                forecast_remaining_kwh=self.remaining,
                forecast_30min_w=self.f30,
                hp_power_w=self.hp_w,
                signal_bits=self.bits,
                pvmaxcomp_kw=self.pvmax,
                price_configured=self.price_configured,
                price_ct=self.price,
            ),
        )
        # emulate the heat pump following the signal and the limit
        if res.enforce_signal and res.signal_bits_target and res.signal_bits_target != self.bits:
            self.bits = res.signal_bits_target
        if res.write_comp and res.comp_target_kw is not None:
            self.pvmax = res.comp_target_kw
            self.events.append(f"comp:{res.comp_target_kw}")
        if res.started:
            self.events.append(f"start:{res.reason}")
        if res.stopped:
            self.events.append(f"stop:{res.reason}")
        self.last = res
        return res

    def run(self, minutes: float) -> logic.Result:
        res = self.last
        for _ in range(int(minutes * 4)):
            res = self.step()
        return res


class TestHelpers(unittest.TestCase):
    def test_battery_release(self):
        s = logic.Settings(soc_release=80, soc_forecast=60, battery_capacity_kwh=10, forecast_reserve_kwh=4)
        self.assertTrue(logic.battery_release(s, 80, 0))
        self.assertFalse(logic.battery_release(s, 79, 0))
        # 65 % -> 3.5 kWh missing; 8 - 4 = 4 >= 3.5
        self.assertTrue(logic.battery_release(s, 65, 8))
        self.assertFalse(logic.battery_release(s, 65, 7))
        # below forecast threshold never released by forecast
        self.assertFalse(logic.battery_release(s, 55, 30))
        s.use_forecast = False
        self.assertFalse(logic.battery_release(s, 65, 30))
        self.assertFalse(logic.battery_release(s, None, 30))

    def test_available_power(self):
        # exporting 500 W, battery charging 2000 W
        self.assertEqual(logic.available_power(-500, -2000, True), 2500)
        self.assertEqual(logic.available_power(-500, -2000, False), 500)
        # battery discharging 800 W always subtracted
        self.assertEqual(logic.available_power(0, 800, True), -800)
        self.assertEqual(logic.available_power(0, 800, False), -800)

    def test_compressor_target(self):
        s = logic.Settings(comp_min_kw=1.0, comp_max_kw=2.5, comp_reserve_kw=0.1)
        self.assertEqual(logic.compressor_target(s, 2300, True), 2.2)
        self.assertEqual(logic.compressor_target(s, 4600, True), 2.5)
        self.assertEqual(logic.compressor_target(s, 800, True), 1.0)
        self.assertEqual(logic.compressor_target(s, 4600, False), 1.0)
        self.assertEqual(logic.compressor_target(s, None, True), 1.0)

    def test_bits(self):
        self.assertEqual(logic.set_bit(BITS_OFF, 0, True), BITS_ON)
        self.assertEqual(logic.set_bit(BITS_ON, 0, False), BITS_OFF)
        self.assertTrue(logic.valid_bits(BITS_OFF, 0))
        self.assertFalse(logic.valid_bits("unavailable", 0))
        self.assertFalse(logic.valid_bits("0101", 4))
        self.assertFalse(logic.valid_bits(None, 0))

    def test_window(self):
        self.assertTrue(logic.in_window(time(10), time(10), time(16)))
        self.assertFalse(logic.in_window(time(16), time(10), time(16)))
        self.assertTrue(logic.in_window(time(23), time(22), time(6)))
        self.assertTrue(logic.in_window(time(3), time(3), time(3)))

    def test_persistence_roundtrip(self):
        st = logic.State(requested=True, requested_since=at(12), last_off=at(9), activations=1, runtime_s=600)
        st.day = at(12).date()
        back = logic.State.from_dict(st.to_dict())
        self.assertTrue(back.requested)
        self.assertEqual(back.requested_since, at(12))
        self.assertEqual(back.last_off, at(9))
        self.assertEqual(back.activations, 1)
        self.assertEqual(back.day, at(12).date())
        s = logic.Settings(on_threshold_w=1700, window_start=time(9, 30), mode="manual")
        s2 = logic.Settings.from_dict(s.to_dict())
        self.assertEqual(s2.on_threshold_w, 1700)
        self.assertEqual(s2.window_start, time(9, 30))
        self.assertEqual(s2.mode, "manual")
        self.assertEqual(logic.Settings.from_dict({"mode": "nonsense"}).mode, "auto")


class TestControl(unittest.TestCase):
    def test_start_needs_stable_surplus(self):
        sim = Sim()
        sim.grid_w = -2000  # exporting 2 kW
        res = sim.run(4.5)
        self.assertEqual(res.status, logic.ST_PENDING)
        self.assertFalse(sim.state.requested)
        res = sim.run(1)
        self.assertTrue(sim.state.requested)
        self.assertEqual(res.status, logic.ST_PV)
        self.assertEqual(sim.bits, BITS_ON)
        self.assertEqual(sim.state.activations, 1)
        self.assertIn("start:surplus", sim.events)

    def test_short_dip_resets_on_delay(self):
        sim = Sim()
        sim.grid_w = -2000
        sim.run(4)
        sim.grid_w = 0
        sim.step()
        sim.grid_w = -2000
        sim.run(4)
        self.assertFalse(sim.state.requested)

    def test_forecast_blocks_start(self):
        sim = Sim()
        sim.grid_w = -2000
        sim.f30 = 500
        res = sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertFalse(res.checks["forecast"])
        self.assertEqual(res.status, logic.ST_WAIT)
        sim.settings.use_forecast = False
        sim.run(6)
        self.assertTrue(sim.state.requested)

    def test_min_runtime_then_stop_and_lock(self):
        sim = Sim()
        sim.grid_w = -2000
        sim.run(6)
        self.assertTrue(sim.state.requested)
        # heat pump now draws more than the surplus
        sim.grid_w = 1500
        res = sim.run(20)
        self.assertTrue(sim.state.requested, "must keep running during min runtime")
        self.assertEqual(res.status, logic.ST_DEFICIT)
        sim.run(11)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:no_surplus", sim.events)
        self.assertEqual(sim.bits, BITS_OFF)
        # surplus again -> locked for 2 h
        sim.grid_w = -2500
        res = sim.run(60)
        self.assertFalse(sim.state.requested)
        self.assertEqual(res.status, logic.ST_LOCKED)
        self.assertIsNotNone(res.lock_until)
        sim.run(65)
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.activations, 2)

    def test_deficit_between_thresholds_keeps_running(self):
        sim = Sim()
        sim.grid_w = -2000
        sim.run(6)
        sim.grid_w = 300  # small import, above off threshold of -800 W available
        sim.run(60)
        self.assertTrue(sim.state.requested)

    def test_daily_limit(self):
        sim = Sim(lock_min=1, min_runtime_min=1, off_delay_min=1, on_delay_min=1)
        for _ in range(2):
            sim.grid_w = -2000
            sim.run(3)
            self.assertTrue(sim.state.requested)
            sim.grid_w = 2000
            sim.run(3)
            self.assertFalse(sim.state.requested)
        sim.grid_w = -2000
        res = sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertEqual(res.status, logic.ST_LIMIT)
        # next day resets the counter
        sim.now = at(10, 30, day=19)
        res = sim.run(3)
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.activations, 1)

    def test_battery_low_stops(self):
        sim = Sim()
        sim.grid_w = -2000
        sim.run(6)
        sim.soc = 49
        sim.run(1.5)
        self.assertTrue(sim.state.requested)
        sim.run(1)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:battery_low", sim.events)

    def test_battery_below_stop_blocks_start(self):
        sim = Sim()
        sim.soc = 45
        sim.grid_w = -2500
        res = sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertEqual(res.status, logic.ST_BATTERY)

    def test_night_and_window(self):
        sim = Sim()
        sim.now = at(16, 0)
        sim.grid_w = -2500
        res = sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertEqual(res.status, logic.ST_WINDOW)
        sim2 = Sim()
        sim2.grid_w = -2500
        sim2.run(6)
        sim2.sun_up = False
        res = sim2.step()
        self.assertFalse(sim2.state.requested)
        self.assertEqual(res.status, logic.ST_NIGHT)

    def test_sensor_failure_stops_after_10_min(self):
        sim = Sim()
        sim.grid_w = -2500
        sim.run(6)
        sim.grid_w = None
        res = sim.run(9)
        self.assertTrue(sim.state.requested)
        sim.run(1.5)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:sensor_error", sim.events)

    def test_short_sensor_dropout_keeps_status(self):
        sim = Sim()
        sim.soc = 40
        res = sim.run(2)
        self.assertEqual(res.status, logic.ST_BATTERY)
        sim.soc = None
        res = sim.step()
        self.assertEqual(res.status, logic.ST_BATTERY)
        self.assertFalse(res.checks["sensors"])
        sim.soc = 40
        self.assertEqual(sim.step().status, logic.ST_BATTERY)
        sim.soc = None
        res = sim.run(2.5)
        self.assertEqual(res.status, logic.ST_SENSOR)

    def test_battery_priority_without_release(self):
        sim = Sim()
        sim.soc = 60
        sim.remaining = 3  # forecast won't fill the battery
        sim.grid_w = 0
        sim.battery_w = -3000  # all surplus goes into the battery
        res = sim.run(10)
        self.assertFalse(res.battery_release)
        self.assertFalse(sim.state.requested)
        sim.soc = 85
        res = sim.run(6)
        self.assertTrue(res.battery_release)
        self.assertTrue(sim.state.requested)

    def test_modes(self):
        sim = Sim()
        sim.settings.mode = logic.MODE_MANUAL
        res = sim.step()
        self.assertTrue(sim.state.requested)
        self.assertEqual(res.status, logic.ST_MANUAL)
        self.assertEqual(sim.state.activations, 0)
        self.assertEqual(sim.bits, BITS_ON)
        sim.settings.mode = logic.MODE_OFF
        res = sim.step()
        self.assertFalse(sim.state.requested)
        self.assertEqual(res.status, logic.ST_OFF)
        self.assertFalse(res.enforce_signal)

    def test_compressor_follows_budget_every_5_min(self):
        sim = Sim()
        sim.grid_w = -2400
        sim.run(6)
        self.assertTrue(sim.state.requested)
        # immediate start value from pre-start average (2400 + 25 W)
        self.assertEqual(sim.events.count("comp:2.3"), 1)
        # heat pump ramps to 2.3 kW, grid goes to 0 -> budget stays ~2.3 kW
        sim.hp_w = 2300
        sim.grid_w = -100
        sim.run(10)
        self.assertEqual(sim.pvmax, 2.3)
        # sun increases, 4.6 kW budget -> capped at 2.5
        sim.grid_w = -2300
        sim.run(10)
        self.assertEqual(sim.pvmax, 2.5)
        # cloud, budget 1.2 kW -> 1.1
        sim.hp_w = 1000
        sim.grid_w = -200
        sim.run(10)
        self.assertEqual(sim.pvmax, 1.1)

    def test_compressor_min_without_release(self):
        sim = Sim()
        sim.settings.mode = logic.MODE_MANUAL
        sim.soc = 60
        sim.remaining = 0
        sim.pvmax = 2.0
        sim.battery_w = -3000
        sim.step()
        self.assertEqual(sim.pvmax, 1.0)

    def test_compressor_only_writes_on_big_change(self):
        sim = Sim()
        sim.grid_w = -2400
        sim.run(6)
        writes = len([e for e in sim.events if e.startswith("comp:")])
        sim.grid_w = -2450  # +50 W
        sim.run(15)
        self.assertEqual(len([e for e in sim.events if e.startswith("comp:")]), writes)

    def test_runtime_counts(self):
        sim = Sim()
        sim.grid_w = -2400
        sim.run(6)
        sim.run(30)
        self.assertAlmostEqual(sim.state.runtime_s / 60, 30.75, delta=1)


if __name__ == "__main__":
    unittest.main()


class TestPriceUnits(unittest.TestCase):
    def test_known_units(self):
        f = logic.price_unit_factor
        self.assertEqual(f("EUR/kWh"), 100.0)  # Tibber, Nord Pool
        self.assertEqual(f("€/kWh"), 100.0)  # Octopus Germany, EPEX Spot
        self.assertEqual(f("c/kWh"), 1.0)  # Nord Pool (HACS) in cents
        self.assertEqual(f("ct/kWh"), 1.0)
        self.assertEqual(f("Cent/kWh"), 1.0)
        self.assertEqual(f("Öre/kWh"), 1.0)
        self.assertEqual(f("Øre/kWh"), 1.0)
        self.assertAlmostEqual(f("EUR/MWh"), 0.1)
        self.assertEqual(f("EUR/Wh"), 100000.0)
        self.assertEqual(f("NOK/kWh"), 100.0)
        self.assertEqual(f(" eur / kwh "), 100.0)
        self.assertEqual(f("ct./kWh"), 1.0)

    def test_unknown_units(self):
        f = logic.price_unit_factor
        for unit in (None, "", "EUR", "kWh", "W", "EUR/kW", "%", "XYZ/kWh", "EUR/kWh/h"):
            self.assertIsNone(f(unit), unit)

    def test_normalize(self):
        n = logic.normalize_price
        self.assertAlmostEqual(n(0.2873, "EUR/kWh"), 28.73)
        self.assertAlmostEqual(n(28.73, "c/kWh"), 28.73)
        self.assertAlmostEqual(n(95.4, "EUR/MWh"), 9.54)
        self.assertAlmostEqual(n(-0.012, "€/kWh"), -1.2)
        self.assertIsNone(n(0.3, None))
        self.assertIsNone(n(None, "EUR/kWh"))
        # manual unit for sensors without unit
        self.assertAlmostEqual(n(0.3, None, logic.PRICE_UNIT_MAJOR_KWH), 30.0)
        self.assertAlmostEqual(n(30, "", logic.PRICE_UNIT_MINOR_KWH), 30.0)
        self.assertAlmostEqual(n(300, None, logic.PRICE_UNIT_MAJOR_MWH), 30.0)
        # manual unit wins over the sensor unit
        self.assertAlmostEqual(n(30, "EUR/kWh", logic.PRICE_UNIT_MINOR_KWH), 30.0)


def price_sim(**kw):
    sim = Sim(price_control=True, **kw)
    sim.price_configured = True
    return sim


class TestPrice(unittest.TestCase):
    def test_no_price_sensor_unchanged(self):
        sim = Sim(price_control=True)  # switch on, but no sensor configured
        sim.price = 1.0
        res = sim.run(2)
        self.assertNotIn("price", res.checks)
        self.assertFalse(sim.state.requested)
        self.assertFalse(res.price_active)

    def test_switch_off_ignores_price(self):
        sim = Sim()
        sim.price_configured = True
        sim.price = 1.0
        res = sim.run(2)
        self.assertNotIn("price", res.checks)
        self.assertFalse(sim.state.requested)

    def test_cheap_starts_at_night_with_empty_battery(self):
        sim = price_sim()
        sim.now = at(2)
        sim.sun_up = False
        sim.soc = 10
        sim.grid_w = 1500
        sim.price = 12.0
        res = sim.step()
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        self.assertEqual(res.status, logic.ST_CHEAP)
        self.assertIn("start:price_cheap", sim.events)
        self.assertEqual(sim.state.activations, 0)  # not counted
        self.assertEqual(sim.bits, BITS_ON)

    def test_cheap_respects_lock(self):
        sim = price_sim()
        sim.state.last_off = sim.now
        sim.price = 5.0
        sim.run(5)
        self.assertFalse(sim.state.requested)
        sim.run(120)
        self.assertTrue(sim.state.requested)

    def test_cheap_end_waits_for_min_runtime_then_stops(self):
        sim = price_sim()
        sim.now = at(3)
        sim.sun_up = False
        sim.price = 10.0
        sim.step()
        sim.price = 25.0
        sim.run(20)
        self.assertTrue(sim.state.requested)  # min runtime 30 min
        sim.run(11)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:price_end", sim.events)
        self.assertEqual(sim.bits, BITS_OFF)

    def test_cheap_end_hands_over_to_pv(self):
        sim = price_sim()
        sim.price = 10.0
        sim.step()
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        sim.price = 25.0
        sim.grid_w = -2500
        res = sim.step()
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.run_kind, logic.RUN_PV)
        self.assertEqual(res.status, logic.ST_PV)
        self.assertFalse(any(e.startswith("stop:") for e in sim.events))

    def test_pv_turns_into_cheap_at_sunset(self):
        sim = price_sim()
        sim.price = 25.0
        sim.grid_w = -2500
        sim.run(6)
        self.assertEqual(sim.state.run_kind, logic.RUN_PV)
        sim.sun_up = False
        sim.price = 10.0
        sim.step()
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        self.assertNotIn("stop:night", sim.events)

    def test_pv_battery_low_still_stops_when_not_cheap(self):
        sim = price_sim()
        sim.price = 25.0
        sim.grid_w = -2500
        sim.run(6)
        sim.soc = 40
        sim.run(3)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:battery_low", sim.events)

    def test_expensive_blocks_start(self):
        sim = price_sim()
        sim.grid_w = -2500
        sim.price = 45.0
        res = sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertFalse(res.checks["price"])
        self.assertEqual(res.status, logic.ST_EXPENSIVE)
        sim.price = 30.0
        sim.run(6)
        self.assertTrue(sim.state.requested)

    def test_expensive_stop_option(self):
        for stop_flag, expected in ((False, True), (True, False)):
            sim = price_sim(price_stop_expensive=stop_flag)
            sim.grid_w = -2500
            sim.price = 30.0
            sim.run(6)
            self.assertTrue(sim.state.requested)
            sim.price = 50.0
            sim.run(10)
            self.assertTrue(sim.state.requested)  # min runtime not over
            sim.run(25)
            self.assertEqual(sim.state.requested, expected)

    def test_price_dropout_grace(self):
        sim = price_sim()
        sim.now = at(3)
        sim.sun_up = False
        sim.price = 10.0
        sim.step()
        sim.price = None
        sim.run(14)
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        self.assertTrue(sim.last.price_cheap)
        sim.run(60)
        self.assertFalse(sim.state.requested)  # price unknown -> no longer cheap
        self.assertIsNone(sim.last.price_ct)

    def test_restart_during_cheap_run_waits_for_price(self):
        # Issue #1: after a restart the first steps run before the price sensor is loaded
        sim = price_sim(price_cheap_ct=23.0, price_expensive_ct=34.0)
        sim.now = at(13)
        sim.price = 22.59
        sim.step()
        sim.run(90)  # well past the minimum runtime
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        restored = logic.State.from_dict(sim.state.to_dict())  # restart: volatile state lost
        sim.state = restored
        sim.price = None
        sim.run(2)  # price sensor still loading
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.last.status, logic.ST_CHEAP)
        self.assertNotIn("stop:price_end", sim.events)
        sim.price = 22.59  # sensor back, still cheap
        sim.run(5)
        self.assertTrue(sim.state.requested)
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)

    def test_restart_cheap_run_ends_if_price_is_no_longer_cheap(self):
        sim = price_sim()
        sim.now = at(3)
        sim.sun_up = False
        sim.price = 10.0
        sim.step()
        sim.run(60)
        sim.state = logic.State.from_dict(sim.state.to_dict())
        sim.price = None
        sim.run(1)
        self.assertTrue(sim.state.requested)
        sim.price = 30.0  # cheap phase ended during the restart
        sim.step()
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:price_end", sim.events)

    def test_restart_price_never_arrives(self):
        sim = price_sim()
        sim.now = at(3)
        sim.sun_up = False
        sim.price = 10.0
        sim.step()
        sim.run(60)
        sim.state = logic.State.from_dict(sim.state.to_dict())
        sim.price = None
        sim.run(14)
        self.assertTrue(sim.state.requested)
        sim.run(2)
        self.assertFalse(sim.state.requested)  # held at most 15 minutes
        self.assertIn("stop:price_end", sim.events)

    def test_no_cheap_start_without_price_after_restart(self):
        sim = price_sim()
        sim.now = at(3)
        sim.sun_up = False
        sim.price = None
        sim.run(5)
        self.assertFalse(sim.state.requested)

    def test_unknown_price_does_not_block(self):
        sim = price_sim()
        sim.grid_w = -2500
        sim.price = None
        res = sim.run(6)
        self.assertTrue(res.checks["price"])
        self.assertTrue(sim.state.requested)

    def test_cheap_compressor_limit(self):
        sim = price_sim(price_comp_kw=3.0)
        sim.now = at(3)
        sim.sun_up = False
        sim.grid_w = None  # grid sensor not needed for cheap mode
        sim.price = 10.0
        res = sim.step()
        self.assertTrue(res.write_comp)
        self.assertEqual(sim.pvmax, 3.0)
        writes = sum(1 for e in sim.events if e.startswith("comp:"))
        sim.run(30)
        self.assertEqual(sum(1 for e in sim.events if e.startswith("comp:")), writes)

    def test_cheap_threshold_wins_if_overlapping(self):
        sim = price_sim(price_cheap_ct=40.0, price_expensive_ct=30.0)
        sim.price = 35.0
        res = sim.step()
        self.assertTrue(res.price_cheap)
        self.assertFalse(res.price_expensive)

    def test_negative_price(self):
        sim = price_sim(price_cheap_ct=0.0)
        sim.price = -2.5
        sim.step()
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)

    def test_run_kind_persisted(self):
        sim = price_sim()
        sim.price = 10.0
        sim.step()
        data = sim.state.to_dict()
        restored = logic.State.from_dict(data)
        self.assertEqual(restored.run_kind, logic.RUN_CHEAP)
        self.assertTrue(restored.requested)
        old = logic.State.from_dict({k: v for k, v in data.items() if k != "run_kind"})
        self.assertEqual(old.run_kind, logic.RUN_PV)

    def test_manual_mode_unaffected(self):
        sim = price_sim(mode=logic.MODE_MANUAL)
        sim.price = 50.0
        res = sim.step()
        self.assertTrue(sim.state.requested)
        self.assertEqual(res.status, logic.ST_MANUAL)

    def test_settings_roundtrip_with_price(self):
        s1 = logic.Settings(price_control=True, price_cheap_ct=12.5, price_expensive_ct=38.0, price_stop_expensive=True, price_comp_kw=3.2)
        s2 = logic.Settings.from_dict(s1.to_dict())
        self.assertEqual(s1, s2)
        self.assertFalse(logic.Settings.from_dict({"mode": "auto"}).price_control)


def idle_sim(**kw):
    """Running PV mode with plenty of surplus; the heat pump starts right away."""
    kw.setdefault("min_runtime_min", 60)
    sim = Sim(observe=False, **kw)
    sim.grid_w = -2500
    sim.run(6)
    assert sim.state.requested
    sim.hp_w = 1100  # compressor running (DHW)
    sim.run(30)
    return sim


class TestIdleStop(unittest.TestCase):
    def test_off_by_default(self):
        sim = idle_sim()
        sim.hp_w = 40
        sim.run(120)
        self.assertTrue(sim.state.requested)
        self.assertNotIn("stop:hp_idle", sim.events)

    def test_ends_when_heat_pump_is_done(self):
        # 31.10.: DHW done, compressor stands still, the heat pump would start again after ~31 min
        sim = idle_sim(idle_stop_min=20)
        sim.hp_w = 40
        res = sim.run(19)
        self.assertTrue(sim.state.requested)
        self.assertIsNotNone(res.hp_idle_since)
        sim.run(1.25)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:hp_idle", sim.events)
        self.assertEqual(sim.bits, BITS_OFF)
        sim.run(60)  # surplus still there, but the lock time keeps it off
        self.assertFalse(sim.state.requested)
        self.assertEqual(sim.last.status, logic.ST_LOCKED)

    def test_short_pause_keeps_running(self):
        # 22.10.: 15 min compressor pause between DHW and heating, then heating with PV raise
        sim = idle_sim(idle_stop_min=20)
        sim.hp_w = 40
        sim.run(15)
        sim.hp_w = 900
        sim.step()
        self.assertIsNone(sim.last.hp_idle_since)
        sim.hp_w = 40
        sim.run(19)
        self.assertTrue(sim.state.requested)  # idle timer started over
        self.assertNotIn("stop:hp_idle", sim.events)

    def test_standby_spikes_do_not_count_as_running(self):
        sim = idle_sim(idle_stop_min=20)
        sim.hp_w = 40
        sim.run(10)
        sim.hp_w = 115  # standby spike seen on the WLW186i
        sim.step()
        sim.hp_w = 40
        sim.run(10)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:hp_idle", sim.events)

    def test_waits_until_the_compressor_has_run(self):
        sim = Sim(observe=False, idle_stop_min=10, min_runtime_min=60)
        sim.grid_w = -2500
        sim.hp_w = 40  # heat pump slow to react to the signal
        sim.run(40)
        self.assertTrue(sim.state.requested)
        self.assertNotIn("stop:hp_idle", sim.events)

    def test_missing_power_reading_does_not_stop(self):
        sim = idle_sim(idle_stop_min=20)
        sim.hp_w = None
        sim.run(60)
        self.assertTrue(sim.state.requested)

    def test_cheap_run_also_ends(self):
        sim = Sim(observe=False, price_control=True, idle_stop_min=20, min_runtime_min=30)
        sim.price_configured = True
        sim.now = at(3)
        sim.sun_up = False
        sim.price = 10.0
        sim.hp_w = 1500
        sim.step()
        self.assertEqual(sim.state.run_kind, logic.RUN_CHEAP)
        sim.run(40)
        sim.hp_w = 40
        sim.run(21)
        self.assertFalse(sim.state.requested)
        self.assertIn("stop:hp_idle", sim.events)

    def test_manual_mode_unaffected(self):
        sim = Sim(observe=False, mode=logic.MODE_MANUAL, idle_stop_min=5)
        sim.hp_w = 1000
        sim.run(5)
        sim.hp_w = 40
        sim.run(30)
        self.assertTrue(sim.state.requested)

    def test_setting_persisted(self):
        s = logic.Settings(idle_stop_min=20)
        self.assertEqual(logic.Settings.from_dict(s.to_dict()).idle_stop_min, 20.0)
        self.assertEqual(logic.Settings.from_dict({}).idle_stop_min, 0.0)
