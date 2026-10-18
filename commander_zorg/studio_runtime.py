"""Creator contract 0.3, isolated from historical morph event semantics."""
from copy import deepcopy
from itertools import product

import numpy as np

from .canonical import canonical_bytes, strict_json
from .morph_commands import parse_command
from .morph_runtime import MorphRuntime


ADMISSION = 'future-corners-v1'
DIRECTIONS = ('left', 'right', 'up', 'down')


class StudioRuntime(MorphRuntime):
    session_version = 'cz-morph-session-0.3'

    def __init__(self, config, targets):
        super().__init__(config, targets)
        self._future_admission = False

    def _admit(self, translation=None):
        if not self._future_admission:
            return super()._admit(translation)
        # Only the interval from NOW to each endpoint is reachable in future.
        # At any future tick the quintic blend stays in this convex segment.
        tick = self.state.tick
        translation = self.translation if translation is None else translation
        relative = self.scene.home_xy-self.scene.home_xy.mean(axis=0)
        wander = .08*max(float(self.wander_mix.at(tick)), float(self.wander_mix.end))
        for shape, offset, morph, sx, sy in product(
                (self.shape.at(tick), self.shape.end),
                (translation.at(tick), translation.end),
                (self.morph.at(tick), self.morph.end), (-1, 1), (-1, 1)):
            norms = np.linalg.norm(shape+offset+morph*relative*[-.5, 1.]
                                   +wander*np.array([sx, sy]), axis=1)
            if (np.any(norms*self.scene.spring_k > self.scene.max_total_force)
                    or np.any(norms > self.scene.max_displacement)):
                raise ValueError('combined motion exceeds conservative force/displacement admission budget; reduce motion or turn wander off')

    def accept(self, text):
        operation = parse_command(text)
        self._future_admission = True
        try:
            if (operation['action'] == 'motion' and self.motion_auto
                    and operation['motion']['action'] in DIRECTIONS):
                operation = self._adaptive_command(operation['motion'])
            event = {'schema_version': 'cz-morph-event-0.3', 'sequence': len(self.events),
                     'effective_tick': self.state.tick,
                     'command': {'action': 'creator', 'operation': operation,
                                 'admission': ADMISSION}}
            self.apply_event(event)
            return deepcopy(event)
        except ValueError as error:
            message = str(error)
            if 'no meaningful safe movement' in message:
                raise ValueError('MOTION: LIMIT REACHED; this absolute direction target cannot increase safely. Try another direction or reduce deformation/wander.') from error
            if 'admission budget' in message:
                raise ValueError('SHAPE / MOTION LIMIT: this combination cannot be admitted safely. Directional auto adapts movement only; reduce the direction target, reset, or let wander off settle before morphing.') from error
            raise
        finally:
            self._future_admission = False

    def apply_event(self, event):
        event = strict_json(canonical_bytes(event))
        if type(event) is not dict:
            raise ValueError('invalid creator event')
        if event.get('schema_version') != 'cz-morph-event-0.3':
            # Original events always use the original conservative calculation.
            previous = self._future_admission
            self._future_admission = False
            try:
                return super().apply_event(event)
            finally:
                self._future_admission = previous
        command = event.get('command')
        if (type(command) is not dict or set(command) != {'action', 'operation', 'admission'}
                or command['action'] != 'creator' or command['admission'] != ADMISSION
                or type(command['operation']) is not dict):
            raise ValueError('invalid creator operation/admission version')
        operation = command['operation']
        extended = operation.get('action') in ('motion_auto', 'adaptive_motion')
        inner = {**event, 'schema_version': 'cz-morph-event-0.2' if extended else 'cz-morph-event-0.1',
                 'command': operation}
        directional = (operation.get('action') == 'adaptive_motion'
                       or (operation.get('action') == 'motion'
                           and operation.get('motion', {}).get('action') in DIRECTIONS))
        origin = deepcopy(self.translation)
        count = len(self.events)
        previous = self._future_admission
        self._future_admission = True
        try:
            super().apply_event(inner)
            if directional and np.linalg.norm(self.translation.end-origin.end) < 1e-6:
                self.translation = origin
                del self.events[count:]
                raise ValueError('MOTION: TARGET ALREADY SET; no additional movement applied. Directions set absolute targets; the current transition may still be running.')
            self.events[-1] = event
        finally:
            self._future_admission = previous

    def command_feedback(self, event):
        if event['schema_version'] != 'cz-morph-event-0.3':
            return super().command_feedback(event)
        return super().command_feedback({'command': event['command']['operation']})
