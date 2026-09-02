"""Deterministic mission coordinator and line-following decision prototype.

There are deliberately no SSH, HTTP, GPIO, CAN, or arm driver imports here.
Observations and actuator acknowledgements are simulated, not hardware evidence.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Stage(str, Enum):
    NAVIGATE = 'NAVIGATE'
    DOCK = 'DOCK'
    DETECT = 'DETECT'
    PICK = 'PICK'
    PLACE = 'PLACE'
    VERIFY = 'VERIFY'
    DONE = 'DONE'
    FAULT = 'FAULT'
    CANCELLED = 'CANCELLED'


@dataclass(frozen=True)
class Observation:
    timestamp: float
    distance_cm: float
    line: tuple[bool, bool, bool, bool] = (False, True, True, False)
    at_station: bool = False
    dock_confirmed: bool = False
    item_detected: bool = False
    grip_confirmed: bool = False
    place_ack: bool = False
    load_confirmed: bool = False


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


def decide_line(observation: Observation, now: float) -> Decision:
    """Pure bounded decision, not a motor command. Sensor polarity needs calibration."""
    if not all(math.isfinite(v) for v in (now, observation.timestamp, observation.distance_cm)):
        return Decision('stop', 'invalid_sensor')
    if not 0 <= now - observation.timestamp <= .5:
        return Decision('stop', 'stale_sensor')
    if observation.distance_cm <= 20:
        return Decision('stop', 'obstacle')
    if len(observation.line) != 4 or any(type(v) is not bool for v in observation.line):
        return Decision('stop', 'invalid_line')
    active = [weight for weight, detected in zip((-3, -1, 1, 3), observation.line) if detected]
    if not active:
        return Decision('stop', 'line_lost')
    if len(active) == 4:
        return Decision('stop', 'ambiguous_intersection')
    offset = sum(active) / len(active)
    return Decision('turn_left' if offset < -.5 else 'turn_right' if offset > .5 else 'forward', 'tracking')


class SimulatedActuators:
    """Only records commands. Never sends them to a robot."""
    def __init__(self):
        self.commands: list[dict] = []

    def send(self, target: str, action: str):
        self.commands.append({'source': 'SIMULATOR', 'target': target, 'action': action})


class Mission:
    def __init__(self, actuators: SimulatedActuators, *, now: float = 0.0):
        if type(actuators) is not SimulatedActuators:
            raise ValueError('Only SimulatedActuators is supported. Hardware adapter is not implemented.')
        self.actuators = actuators
        self.stage = Stage.NAVIGATE
        self.stage_started = now
        self.last_tick = now
        self.events: list[dict] = []
        self.pick_attempts = 0

    def event(self, message: str):
        self.events.append({'source': 'SIMULATOR', 'stage': self.stage.value, 'message': message})

    def transition(self, stage: Stage, now: float):
        self.stage, self.stage_started = stage, now
        self.event('stage_enter')

    def halt(self, reason: str, *, cancelled: bool = False):
        self.actuators.send('base', 'stop')
        self.actuators.send('arm', 'stop')
        self.stage = Stage.CANCELLED if cancelled else Stage.FAULT
        self.event(reason)

    def tick(self, observation: Observation, now: float, *, cancel: bool = False):
        if self.stage in (Stage.DONE, Stage.FAULT, Stage.CANCELLED):
            return
        if cancel:
            self.halt('operator_stop', cancelled=True)
            return
        if not math.isfinite(now) or now < self.last_tick or now - self.stage_started > 10:
            self.halt('stage_timeout_or_invalid_clock')
            return
        self.last_tick = now
        decision = decide_line(observation, now)
        # Sensor freshness/obstacle checks are required even during arm phases.
        if decision.reason in ('invalid_sensor', 'stale_sensor', 'obstacle', 'invalid_line'):
            self.halt(decision.reason)
            return

        if self.stage == Stage.NAVIGATE:
            if decision.action == 'stop':
                self.halt(decision.reason)
            elif observation.at_station:
                self.actuators.send('base', 'stop')
                self.transition(Stage.DOCK, now)
            else:
                self.actuators.send('base', decision.action + '_pulse')
                self.event(decision.reason)
        elif self.stage == Stage.DOCK:
            self.actuators.send('base', 'stop')
            if observation.dock_confirmed:
                self.transition(Stage.DETECT, now)
        elif self.stage == Stage.DETECT:
            if observation.item_detected:
                self.actuators.send('arm', 'pick')
                self.pick_attempts += 1
                self.transition(Stage.PICK, now)
        elif self.stage == Stage.PICK:
            if observation.grip_confirmed:
                self.actuators.send('arm', 'place')
                self.transition(Stage.PLACE, now)
            elif self.pick_attempts < 2:
                self.actuators.send('arm', 'stop')
                self.transition(Stage.DETECT, now)  # Re-detect before one retry.
                self.event('retry_pick')
            else:
                self.halt('grip_verification_failed')
        elif self.stage == Stage.PLACE:
            if observation.place_ack:
                self.actuators.send('arm', 'stop')
                self.transition(Stage.VERIFY, now)
        elif self.stage == Stage.VERIFY:
            if observation.load_confirmed:
                self.actuators.send('base', 'stop')
                self.actuators.send('arm', 'stop')
                self.transition(Stage.DONE, now)
            else:
                self.halt('load_verification_failed')


SCENARIOS = ('success', 'obstacle', 'line-lost', 'pick-failure', 'verify-failure', 'timeout', 'cancel')


def simulate(scenario: str = 'success') -> dict:
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    actuators = SimulatedActuators()
    mission = Mission(actuators)
    for index in range(30):
        now = index * .1
        observation = Observation(
            timestamp=now, distance_cm=10 if scenario == 'obstacle' else 60,
            line=(False, False, False, False) if scenario == 'line-lost' else (False, True, True, False),
            at_station=index >= 3, dock_confirmed=True, item_detected=True,
            grip_confirmed=scenario != 'pick-failure', place_ack=True,
            load_confirmed=scenario != 'verify-failure',
        )
        mission.tick(observation, 11 if scenario == 'timeout' else now, cancel=scenario == 'cancel')
        if mission.stage in (Stage.DONE, Stage.FAULT, Stage.CANCELLED):
            break
    else:
        mission.halt('simulation_step_limit')
    return {'mode': 'SIMULATION_ONLY', 'hardware_executed': False,
            'scenario': scenario, 'final_state': mission.stage.value,
            'commands': actuators.commands, 'events': mission.events}
