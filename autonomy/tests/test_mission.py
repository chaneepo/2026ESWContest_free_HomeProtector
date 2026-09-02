import unittest
from dataclasses import replace

from autonomy.mission import Mission, Observation, SimulatedActuators, Stage, decide_line, simulate


class MissionTests(unittest.TestCase):
    def test_success_has_simulation_provenance(self):
        result = simulate()
        self.assertEqual(result['final_state'], 'DONE')
        self.assertFalse(result['hardware_executed'])
        self.assertTrue(all(event['source'] == 'SIMULATOR' for event in result['events']))
        stages = [e['stage'] for e in result['events'] if e['message'] == 'stage_enter']
        self.assertEqual(stages, ['DOCK', 'DETECT', 'PICK', 'PLACE', 'VERIFY', 'DONE'])

    def test_failures_never_report_success(self):
        for scenario in ('obstacle', 'line-lost', 'pick-failure', 'verify-failure', 'timeout'):
            with self.subTest(scenario=scenario):
                result = simulate(scenario)
                self.assertEqual(result['final_state'], 'FAULT')
                self.assertEqual(result['commands'][-2:], [
                    {'source': 'SIMULATOR', 'target': 'base', 'action': 'stop'},
                    {'source': 'SIMULATOR', 'target': 'arm', 'action': 'stop'},
                ])

    def test_pick_retry_bounded(self):
        commands = simulate('pick-failure')['commands']
        self.assertEqual(sum(c['action'] == 'pick' for c in commands), 2)
        self.assertFalse(any(c['action'] == 'place' for c in commands))

    def test_cancel_is_terminal(self):
        actuators = SimulatedActuators()
        mission = Mission(actuators)
        mission.tick(Observation(0, 60), 0, cancel=True)
        count = len(actuators.commands)
        mission.tick(Observation(.1, 60), .1)
        self.assertEqual(mission.stage, Stage.CANCELLED)
        self.assertEqual(len(actuators.commands), count)

    def test_stale_sensor_and_invalid_distance_stop(self):
        self.assertEqual(decide_line(Observation(0, 60), 1).reason, 'stale_sensor')
        for value in (float('nan'), float('inf'), -1):
            self.assertEqual(decide_line(Observation(0, value), 0).action, 'stop')

    def test_line_following_decisions(self):
        observation = Observation(0, 60)
        self.assertEqual(decide_line(observation, 0).action, 'forward')
        self.assertEqual(decide_line(replace(observation, line=(True, False, False, False)), 0).action, 'turn_left')
        self.assertEqual(decide_line(replace(observation, line=(False, False, False, True)), 0).action, 'turn_right')
        self.assertEqual(decide_line(replace(observation, line=(True, True, True, True)), 0).action, 'stop')

    def test_arm_waits_for_dock_and_detection(self):
        actuators = SimulatedActuators()
        mission = Mission(actuators)
        mission.tick(Observation(0, 60, at_station=True), 0)
        for i in range(1, 5):
            mission.tick(Observation(i * .1, 60), i * .1)
        self.assertEqual(mission.stage, Stage.DOCK)
        self.assertFalse(any(c['target'] == 'arm' for c in actuators.commands))

    def test_place_ack_is_not_load_success(self):
        self.assertEqual(simulate('verify-failure')['final_state'], 'FAULT')

    def test_non_simulator_adapter_rejected(self):
        with self.assertRaises(ValueError):
            Mission(object())
