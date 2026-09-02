"""Regression tests use fake motors only. Never connect physical hardware."""
import json
import threading
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

from server import ControllerRuntime, build_handler


class FakeController:
    def __init__(self):
        self.started = threading.Event()
        self.stop_calls = 0
        self.connect_error = self.probe_error = self.stop_error = False
        self.moves = []

    def connect(self):
        if self.connect_error:
            raise OSError('connect failed')

    def read_line(self):
        if self.probe_error:
            raise OSError('probe failed')
        return SimpleNamespace(x1=False, x2=True, x3=True, x4=False, raw=6)

    def read_distance_cm(self):
        return 30.0

    def start_motion(self, motion, *, speed):
        self.moves.append((motion, speed))
        self.started.set()

    def stop(self):
        self.stop_calls += 1
        if self.stop_error:
            raise OSError('STOP failed')

    def close(self):
        pass


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeController()
        self.now = 0.0
        self.runtime = ControllerRuntime(controller_factory=lambda: self.fake, clock=lambda: self.now)

    def arm(self):
        return self.runtime.set_mode('hardware', confirm_safe=True)['control_token']

    def test_failed_connection_never_publishes_controller_on_retry(self):
        self.fake.connect_error = True
        for _ in range(2):
            with self.assertRaises(OSError):
                self.arm()
            self.assertIsNone(self.runtime._controller)
            self.assertFalse(self.runtime.snapshot()['movement_enabled'])

    def test_probe_failure_does_not_arm(self):
        self.fake.probe_error = True
        with self.assertRaises(OSError):
            self.arm()
        self.assertFalse(self.runtime.snapshot()['hardware_enabled'])

    def test_legacy_hardware_flag_starts_locked(self):
        self.assertFalse(ControllerRuntime(hardware=True).snapshot()['movement_enabled'])

    def test_token_required_and_not_exposed_to_pollers(self):
        token = self.arm()
        self.assertNotIn('control_token', self.runtime.snapshot())
        for bad in (None, '', 'wrong'):
            with self.assertRaises(PermissionError):
                self.runtime.move('forward', 40, .01, control_token=bad)
        self.runtime.move('forward', 40, .001, control_token=token)
        self.assertEqual(len(self.fake.moves), 1)

    def test_stop_revokes_old_token(self):
        token = self.arm()
        self.runtime.stop()
        self.assertNotEqual(token, self.arm())
        with self.assertRaises(PermissionError):
            self.runtime.move('forward', 40, .01, control_token=token)

    def test_stop_failure_latches_safe(self):
        self.arm()
        self.fake.stop_error = True
        with self.assertRaises(OSError):
            self.runtime.stop()
        status = self.runtime.snapshot()
        self.assertFalse(status['hardware_enabled'])
        self.assertFalse(status['connected'])
        self.assertIn('STOP failed', status['last_error'])

    def test_stop_interrupts_four_second_turn_and_rejects_queued_motion(self):
        token = self.arm()
        errors = []
        def turn():
            try:
                self.runtime.turn('left', 180, 20, control_token=token)
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=turn)
        thread.start()
        self.assertTrue(self.fake.started.wait(1))
        with self.assertRaises(RuntimeError):
            self.runtime.move('forward', 40, .1, control_token=token)
        start = time.monotonic()
        self.runtime.stop()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(errors, [])
        self.assertFalse(self.runtime.snapshot()['movement_enabled'])
        self.assertEqual(self.runtime.snapshot()['last_action'], 'stop')
        self.assertEqual(len(self.fake.moves), 1)

    def test_stop_cancels_inflight_arming(self):
        entered, release = threading.Event(), threading.Event()
        def connect():
            entered.set()
            release.wait(2)
        self.fake.connect = connect
        errors = []
        def arm():
            try:
                self.arm()
            except Exception as exc:
                errors.append(exc)
        armer = threading.Thread(target=arm)
        armer.start()
        self.assertTrue(entered.wait(1))
        stopper = threading.Thread(target=self.runtime.stop)
        stopper.start()
        deadline = time.monotonic() + 1
        while not self.runtime._halt.is_set() and time.monotonic() < deadline:
            time.sleep(.001)
        release.set()
        armer.join(1)
        stopper.join(1)
        self.assertFalse(armer.is_alive() or stopper.is_alive())
        self.assertTrue(errors)
        self.assertFalse(self.runtime.snapshot()['hardware_enabled'])

    def test_watchdog_status_polls_do_not_renew_lease(self):
        self.arm()
        self.now = 6
        self.runtime.snapshot()
        self.runtime.check_watchdog()
        self.assertFalse(self.runtime.snapshot()['hardware_enabled'])
        self.assertGreaterEqual(self.fake.stop_calls, 2)

    def test_only_valid_heartbeat_renews_lease(self):
        token = self.arm()
        self.now = 4
        with self.assertRaises(PermissionError):
            self.runtime.heartbeat('wrong')
        self.runtime.heartbeat(token)
        self.now = 6
        self.runtime.check_watchdog()
        self.assertTrue(self.runtime.snapshot()['movement_enabled'])
        self.now = 10
        with self.assertRaises(PermissionError):
            self.runtime.heartbeat(token)

    def test_sensor_failure_disarms(self):
        self.arm()
        self.fake.probe_error = True
        with self.assertRaises(OSError):
            self.runtime.sensors()
        self.assertFalse(self.runtime.snapshot()['movement_enabled'])

    def test_numeric_input_validation(self):
        for value in (float('nan'), float('inf'), -1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.runtime.move('forward', value, .1)
                with self.assertRaises(ValueError):
                    self.runtime.turn('left', value, 40)
                with self.assertRaises(ValueError):
                    self.runtime.move('forward', 40, value)

    def test_close_forbids_new_arming(self):
        self.arm()
        self.runtime.close()
        with self.assertRaises(PermissionError):
            self.arm()

    def test_no_controller_does_not_claim_stop_confirmed(self):
        self.assertFalse(self.runtime.stop()['stop_confirmed'])


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = FakeController()
        cls.runtime = ControllerRuntime(controller_factory=lambda: cls.fake)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), build_handler(cls.runtime))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(1)
        cls.runtime.close()

    def call(self, path, payload='{}', headers=None, method='POST'):
        connection = HTTPConnection(*self.server.server_address, timeout=2)
        connection.request(method, path, payload, headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        data = json.loads(response.read())
        connection.close()
        return response.status, data

    def test_cross_origin_arm_rejected(self):
        status, _ = self.call('/api/raspbot/mode', '{"mode":"hardware","confirm_safe":true}',
                              {'Content-Type':'application/json', 'Origin':'https://untrusted.example'})
        self.assertEqual(status, 403)

    def test_non_json_stop_rejected(self):
        status, _ = self.call('/api/stop', headers={'Content-Type':'text/plain'})
        self.assertEqual(status, 400)

    def test_malformed_json_rejected(self):
        status, _ = self.call('/api/raspbot/mode', '{')
        self.assertEqual(status, 400)

    def test_boolean_angle_rejected(self):
        status, _ = self.call('/api/raspbot/turn', '{"direction":"left","angle":true}')
        self.assertEqual(status, 400)

    def test_status_protocol(self):
        status, data = self.call('/api/status', method='GET')
        self.assertEqual(status, 200)
        self.assertEqual(data['safety_protocol'], 2)
        self.assertNotIn('control_token', data)
