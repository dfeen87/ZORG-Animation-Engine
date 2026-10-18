"""Explicit creator commands; original live grammar is delegated unchanged."""
import math
from .live_commands import parse_command as parse_live
from .morph_targets import label

HELP = 'morph NAME [0.5–10 seconds] | capture LABEL | motion auto on/off | left/right/up/down | squash/stretch | wander on/off | reset | save | quit'


def parse_command(text):
    if type(text) is not str:
        raise ValueError('command must be text')
    words = text.split()
    if words and words[0] == 'motion':
        if words not in (['motion','auto','on'], ['motion','auto','off']):
            raise ValueError('usage: motion auto on/off')
        return {'action':'motion_auto','enabled':words[2]=='on'}
    if words and words[0] == 'morph':
        if len(words) not in (2,3):
            raise ValueError('usage: morph NAME [seconds]')
        target = label(words[1])
        seconds = float(words[2]) if len(words)==3 else 2.0
        if not math.isfinite(seconds) or not .5 <= seconds <= 10:
            raise ValueError('morph duration must be 0.5–10 seconds')
        return {'action':'morph','target':target,'duration_ticks':math.floor(seconds*60+.5)}
    if words and words[0] == 'capture':
        if len(words)!=2:
            raise ValueError('usage: capture LABEL')
        return {'action':'capture','label':label(words[1])}
    return {'action':'motion','motion':parse_live(text)}
