"""Fifteen-second automated take using exactly the interactive runtime."""
from pathlib import Path

from .canonical import atomic_json
from .live_motion import LiveRuntime
from .session import Recorder

DEMO_COMMANDS = {120:'right 0.3 1.2', 240:'stretch 0.55 1.2',
                 360:'left 0.3 1.2', 480:'squash 0.55 1.2', 600:'reset'}


def run_demo(config, out, *, mp4=True):
    from .live_export import render_session
    runtime = LiveRuntime(config)
    if runtime.scene.terminal_tick < 900:
        raise ValueError('demo requires a live horizon of at least 900 ticks')
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    recorder = Recorder(out/'record',runtime.config)
    atomic_json(out/'demo_status.json',{'state':'running'})
    finished = False
    try:
        for tick in range(900):
            if tick in DEMO_COMMANDS:
                recorder.record_event(runtime.accept(DEMO_COMMANDS[tick]))
            runtime.step()
        session = recorder.finish(runtime,reason='automated_demo')
        finished = True
        report = render_session(session,out/'video',mp4=mp4)
        atomic_json(out/'demo_status.json',{'state':'complete','final_tick':900,
                                          'session':'record/session.json','manifest':'video/manifest.json'})
        return {'completed':True,'session':str(session),'manifest':str(out/'video/manifest.json'),
                'video':report.get('media'),'frames':report['frames'],'duration_seconds':15.0}
    except BaseException as exc:
        if not finished:
            recorder.finish(runtime,status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',reason=str(exc))
        atomic_json(out/'demo_status.json',{'state':'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                                          'last_committed_tick':runtime.state.tick,'error':f'{type(exc).__name__}: {exc}'})
        raise
