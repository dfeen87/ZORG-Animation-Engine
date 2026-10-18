"""Strict inventory, failure propagation and diagnostics before cancellation."""
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from scripts import ci

ROOT = Path(__file__).resolve().parents[1]


def _inventory(directory, *, skipped=False, forged_junit=False):
    count = ci.BASELINE_TESTS
    report = {'collected': count, 'selected': count, 'deselected': [],
              'collection_problems': [], 'pytest_exit_status': 0,
              'call_executed': count - int(skipped),
              'counts': {'passed': count - int(skipped)}}
    if skipped:
        report['counts']['skipped'] = 1
    (directory / 'pytest-outcomes.json').write_text(json.dumps(report))
    suite = ET.Element('testsuite')
    for index in range(count):
        case = ET.SubElement(suite, 'testcase', classname='fixture', name=str(index))
        if index == 0 and skipped:
            ET.SubElement(case, 'skipped')
        elif index == 0 and forged_junit:
            ET.SubElement(case, 'failure')
    path = directory / 'junit.xml'
    ET.ElementTree(suite).write(path)
    return path


def test_ci_audit_accepts_complete_independent_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, 'RESULTS', tmp_path)
    assert ci.audit_tests(_inventory(tmp_path)) == 0
    assert json.loads((tmp_path / 'test-audit-report.json').read_text())['passed']


def test_ci_audit_keeps_zero_skip_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, 'RESULTS', tmp_path)
    assert ci.audit_tests(_inventory(tmp_path, skipped=True)) == 1
    result = json.loads((tmp_path / 'test-audit-report.json').read_text())
    assert not result['passed'] and result['outcomes']['skipped'] == 1
    assert result['call_executed'] < result['selected']


def test_ci_audit_rejects_independent_junit_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, 'RESULTS', tmp_path)
    assert ci.audit_tests(_inventory(tmp_path, forged_junit=True)) == 1
    result = json.loads((tmp_path / 'test-audit-report.json').read_text())
    assert result['outcomes'] == {'passed': ci.BASELINE_TESTS}
    assert result['junit_outcomes']['failed'] == 1
    assert not result['passed']


def test_ci_child_failure_keeps_exact_exit_and_full_log(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, 'RESULTS', tmp_path)
    command = [sys.executable, '-c',
               "import sys; print('stdout evidence'); print('stderr evidence',file=sys.stderr); sys.exit(7)"]
    assert ci.run_stage('failure-fixture', command) == 7
    status = json.loads((tmp_path / 'failure-fixture.json').read_text())
    assert status['status'] == 'failed' and status['exit_code'] == 7
    log = (tmp_path / 'failure-fixture.log').read_text()
    assert 'stdout evidence' in log and 'stderr evidence' in log


def test_ci_phase_traceback_survives_later_hung_test(tmp_path):
    fixture = tmp_path / 'test_fixture.py'
    fixture.write_text("def test_first_failure():\n assert False, 'immediate traceback evidence'\n\n"
                       "def test_later_hang():\n import time\n time.sleep(30)\n")
    environment = os.environ.copy()
    environment.update(PYTEST_PLUGINS='scripts.ci', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                       ZORG_CI_PYTEST_REPORT=str(tmp_path / 'outcomes.json'), PYTHONUNBUFFERED='1')
    child = subprocess.Popen([sys.executable, '-m', 'pytest', '-q', str(fixture)],
                             cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, start_new_session=True)
    output = b''
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            if select.select([child.stdout], [], [], .05)[0]:
                block = os.read(child.stdout.fileno(), 65536)
                if not block:
                    break
                output += block
            if b'CI phase failed:' in output and b'immediate traceback evidence' in output:
                break
        assert b'CI phase failed:' in output and b'immediate traceback evidence' in output, output
        assert child.poll() is None
        rows = [json.loads(line) for line in (tmp_path / 'pytest-progress.jsonl').read_text().splitlines()]
        assert any(row.get('outcome') == 'failed' and
                   'immediate traceback evidence' in row['detail'] for row in rows)
        assert not (tmp_path / 'outcomes.json').exists()
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.communicate(timeout=3)


def test_ci_compact_keeps_chromatic_report_without_frames(tmp_path, monkeypatch):
    take = tmp_path / 'take'
    for relative in ('chromatic/report.json', 'unrelated/report.json',
                     'chromatic/video/frames/manifest.json'):
        path = take / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}')
    results = tmp_path / 'results'
    monkeypatch.setattr(ci, 'RESULTS', results)
    ci.compact_evidence(take)
    index = json.loads((results / 'deep-index.json').read_text())
    assert index['files'] == ['chromatic/report.json']
    assert (results / 'deep/chromatic/report.json').read_text() == '{}'
    assert index['bytes'] == 2
