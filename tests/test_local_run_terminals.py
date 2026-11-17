"""Adapter argv, desktop selection and failures; Linux desktop calls are mocked."""
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest
from core import local_run as local


@pytest.mark.parametrize('desktop,expected', [
    ('GNOME','gnome-terminal'), ('KDE:Plasma','konsole'), ('XFCE','xfce4-terminal'), ('','gnome-terminal')])
def test_linux_desktop_priority(monkeypatch, desktop, expected):
    monkeypatch.setattr(local.shutil, 'which', lambda name, **kw: '/usr/bin/' + name)
    env = {'PATH':'/usr/bin', 'DISPLAY':':1', 'XDG_CURRENT_DESKTOP':desktop}
    before = dict(env)
    assert local.detect_terminal('Linux', env).kind == expected
    assert env == before


def test_linux_fallback_wayland_and_headless(monkeypatch):
    monkeypatch.setattr(local.shutil, 'which', lambda name, **kw: '/usr/bin/xterm' if name == 'xterm' else None)
    assert local.detect_terminal('Linux', {'DISPLAY':':0'}).kind == 'xterm'
    for env in [{}, {'WAYLAND_DISPLAY':'wayland-0'}]:
        with pytest.raises(local.LocalRunError):
            local.detect_terminal('Linux', env)


def test_windows_never_uses_cmd_and_missing_bash_fails(monkeypatch):
    with pytest.raises(local.LocalRunError):
        local.detect_terminal('Windows', {'PATH':'anything'})
    monkeypatch.setattr(local.shutil, 'which', lambda *a, **kw: None)
    monkeypatch.setattr(local.os, 'access', lambda *a: False)
    with pytest.raises(local.LocalRunError):
        local.detect_bash({})
    with pytest.raises(local.LocalRunError):
        local.detect_terminal('Darwin', {})


@pytest.mark.parametrize('kind,separator', [('gnome-terminal','--'),('konsole','-e'),
                                         ('xfce4-terminal','--execute'),('xterm','-e')])
def test_linux_adapter_literal_argv_and_new_window(kind, separator, tmp_path):
    path = tmp_path / "中 文 ' ; $(touch injected) `touch injected`"
    command = ['/bin/bash', '/helper with spaces', str(path)]
    argv = local.terminal_argv(local.Terminal(kind,'/usr/bin/'+kind), 'title',path,command)
    assert argv[argv.index(separator)+1:] == command
    assert not (tmp_path/'injected').exists()
    if kind == 'gnome-terminal':
        assert '--window' in argv and '--working-directory='+str(path) in argv
    elif kind == 'konsole':
        assert '--separate' in argv and argv[argv.index('--workdir')+1] == str(path)
    elif kind == 'xfce4-terminal':
        assert '--window' in argv and '--disable-server' in argv


def test_macos_fixed_applescript_and_shell_escaping(tmp_path):
    path = tmp_path / "中文 ' ; $(touch injected) `touch injected`\n(test)"
    path.mkdir()
    target = tmp_path / 'cwd'
    command = ['/bin/bash','-c','pwd > "$1"','bash',str(target)]
    argv = local.terminal_argv(local.Terminal('macos','/usr/bin/osascript'),'title',path,command)
    assert argv[:3] == ['/usr/bin/osascript','-e',local.APPLESCRIPT]
    assert str(path) not in local.APPLESCRIPT
    subprocess.run(['/bin/bash','-c',argv[3]], check=True, cwd=tmp_path)
    assert target.read_text().rstrip('\n') == str(path)
    assert not list(tmp_path.rglob('injected'))
    assert argv[4] == 'title'


@pytest.mark.parametrize('reason', ['denied','timeout','other'])
def test_macos_automation_errors_do_not_launch_second_terminal(tmp_path, monkeypatch, reason):
    backend = local.LocalRunBackend(cache=tmp_path / 'cache')
    package = local.Package(tmp_path, '/bin/bash',local.Terminal('macos','/usr/bin/osascript'))
    calls=[]
    def run(argv, **kwargs):
        calls.append((argv,kwargs))
        if reason == 'timeout':
            raise subprocess.TimeoutExpired(argv,20)
        return SimpleNamespace(returncode=1,stdout='',stderr='not authorized (-1743)' if reason=='denied' else 'mock failure')
    monkeypatch.setattr(local.subprocess,'run',run)
    with pytest.raises(local.LocalRunError) as error:
        backend._open_terminal(package, tmp_path,'run')
    assert len(calls) == 1 and calls[0][1]['timeout'] == 20
    assert not calls[0][1].get('shell')
    assert error.value.args[0].code == 'local.'+ {'denied':'automation_denied','timeout':'automation_timeout','other':'terminal_failed'}[reason]


def test_linux_starts_detached_with_inherited_environment(tmp_path, monkeypatch):
    backend = local.LocalRunBackend(cache=tmp_path)
    package = local.Package(tmp_path,'/bin/bash',local.Terminal('xterm','/usr/bin/xterm'))
    calls=[]
    def popen(argv, **kw):
        calls.append((argv,kw))
        return SimpleNamespace(pid=123,poll=lambda:None)
    monkeypatch.setattr(local.subprocess,'Popen',popen)
    monkeypatch.setattr(local.time,'sleep',lambda *a: None)
    assert backend._open_terminal(package,tmp_path,'run') == '123'
    argv,kw=calls[0]
    assert kw['start_new_session'] and kw['cwd'] == tmp_path
    assert 'env' not in kw and 'shell' not in kw
    assert argv[argv.index('-e')+1:] == ['/bin/bash',str(tmp_path/'terminal.sh'),
        str(tmp_path),local.sys.executable,str(tmp_path/'runtime.py'),'run',str(tmp_path/'launch.json')]


def test_linux_terminal_failure_keeps_error_log(tmp_path,monkeypatch):
    backend=local.LocalRunBackend(cache=tmp_path)
    package=local.Package(tmp_path,'/bin/bash',local.Terminal('xterm','/bin/false'))
    monkeypatch.setattr(local.time,'sleep',lambda *a:None)
    class Failed:
        pid=1
        def poll(self):return 1
    monkeypatch.setattr(local.subprocess,'Popen',lambda *a,**kw:Failed())
    with pytest.raises(local.LocalRunError):
        backend._open_terminal(package,tmp_path,'run')
    assert (tmp_path/'run-terminal.log').exists()
