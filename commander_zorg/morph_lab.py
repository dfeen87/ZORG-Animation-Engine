"""Terminal adapter and deterministic demo using the same morph runtime."""
from pathlib import Path
import time
from .live import run_live
from .terminal_view import frame_lines
from .studio_commands import HELP,parse_command
from .morph_runtime import MorphRuntime
from .studio_runtime import StudioRuntime
from .morph_session import MorphRecorder,verify_session
from .morph_export import render_session
from .morph_targets import load_targets
from .live_motion import LiveRuntime


def _ui_command(text):
    command=parse_command(text)
    return command['motion'] if command['action']=='motion' else command


def _studio_header(runtime, columns):
    """Prioritize visible shape/color state at ordinary and narrow widths."""
    target = runtime.active_target.upper()
    if not hasattr(runtime, 'chromatic'):
        return f'ZORG MORPH LAB — TARGET: {target}'[:max(1, columns)]
    color = f"COLOR {'ON' if runtime.chromatic.enabled else 'OFF'} {runtime.chromatic.palette_name.upper()}"
    auto = f"AUTO {'ON' if runtime.motion_auto else 'OFF'}"
    full = ' | '.join((f'ZORG {target}', color, auto,
                     f'MOTION {runtime.motion_preset.upper()}', f'SPEED {runtime.speed_preset.upper()}'))
    if len(full) <= columns:
        return full
    compact = ' | '.join((f'Z {target}', color, auto,
                        f'M {runtime.motion_preset.upper()}', f'S {runtime.speed_preset.upper()}'))
    if len(compact) <= columns:
        return compact
    return (color + ' | ' + target)[:max(1, columns)]


def _viewport(runtime,size,**kwargs):
    if hasattr(runtime, 'terminal_color_mode'):
        kwargs['mono'] = runtime.terminal_color_mode == 'mono'
    lines=frame_lines(runtime,size,**kwargs)
    lines[0] = _studio_header(runtime, max(1, size.columns))
    return lines


def run_lab(config,targets,record,**kwargs):
    def factory(config):
        from .terminal_view import detect_color_mode
        runtime = StudioRuntime(config, targets)
        runtime.terminal_color_mode = detect_color_mode(kwargs.get('mono', False))
        return runtime
    return run_live(config,record,runtime_factory=factory,
        recorder_factory=MorphRecorder,command_parser=_ui_command,help_text=HELP,viewport=_viewport,**kwargs)


def run_demo(config,targets,out,mp4=True):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    runtime=MorphRuntime(config,targets)
    if runtime.scene.terminal_tick<1200:
        raise ValueError('demo requires max_ticks >=1200')
    recorder=MorphRecorder(out/'record',runtime)
    # Endpoint captures are commands too, making their tick/state reconstructable.
    schedule={178:['capture original'],180:['wander off','morph circle 0.5'],
        358:['capture circle'],360:['morph oval 0.5'],538:['capture oval'],
        540:['morph cloud 0.5'],778:['capture cloud'],780:['morph hill 0.5'],
        958:['capture hill'],960:['morph home 0.5'],1198:['capture returned_home']}
    started=time.perf_counter()
    try:
        for tick in range(1200):
            for text in schedule.get(tick,[]): recorder.record_event(runtime.accept(text))
            runtime.step()
        session=recorder.finish(runtime,metrics={'simulation_seconds':time.perf_counter()-started,'ticks':1200})
    except BaseException as error:
        recorder.finish(runtime,status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',reason=str(error))
        raise
    replay=verify_session(session)
    exported=render_session(session,out/'video',mp4=mp4)
    return {'completed':True,'session':str(session),'replay':replay,**exported}
