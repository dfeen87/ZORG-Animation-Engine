"""Explicit, bounded creator settings; normalized motion remains numeric."""
from .morph_commands import parse_command as parse_morph

MOTION_PRESETS = {'gentle': .1, 'normal': .2, 'bold': .3}
SPEED_PRESETS = {'slow': 240, 'normal': 120, 'fast': 60}
HELP = ('motion gentle/normal/bold | motion auto on/off\n'
        'speed slow/normal/fast | morph NAME [seconds]\n'
        'color on/off | palette auto/neutral/circle/oval/cloud/hill\n'
        'left/right/up/down [strength] [seconds] (absolute deformation targets)\n'
        'squash/stretch | wander on/off | reset | capture LABEL | save | quit')


def parse_command(text, motion_preset='bold', speed_preset='normal'):
    if type(text) is not str:
        raise ValueError('command must be text')
    words = text.split()
    if words and words[0] == 'color':
        if words not in (['color', 'on'], ['color', 'off']):
            raise ValueError('usage: color on/off')
        return {'action': 'color', 'enabled': words[1] == 'on'}
    if words and words[0] == 'palette':
        if len(words) != 2 or words[1] not in ('auto', 'neutral', 'circle', 'oval', 'cloud', 'hill'):
            raise ValueError('usage: palette auto/neutral/circle/oval/cloud/hill')
        return {'action': 'palette', 'name': words[1], 'duration_ticks': SPEED_PRESETS[speed_preset]}
    if len(words) == 2 and words[0] in ('motion', 'speed'):
        values = MOTION_PRESETS if words[0] == 'motion' else SPEED_PRESETS
        if words[1] not in values:
            raise ValueError('unknown creator preset; type help')
        return {'action': words[0]+'_preset', 'name': words[1],
                'strength' if words[0] == 'motion' else 'duration_ticks': values[words[1]]}
    command = parse_morph(text)
    if command['action'] == 'morph' and len(words) == 2:
        command['duration_ticks'] = SPEED_PRESETS[speed_preset]
    if command['action'] == 'motion':
        motion = command['motion']
        if motion['action'] in ('left', 'right', 'up', 'down') and len(words) == 1:
            motion['strength'] = MOTION_PRESETS[motion_preset]
        if motion['action'] in ('left', 'right', 'up', 'down', 'squash', 'stretch') and len(words) < 3:
            motion['duration_ticks'] = SPEED_PRESETS[speed_preset]
    return command
