"""Bubblewrap around the assistant CLI.

The CLI runs as the user, so its own permission list cannot be the lock. This sandbox
hides the session bus (keyring), the Wayland socket (wtype) and /dev/uinput. The shell
socket is the one door that stays open, and the shell still asks before sending mail,
creating events or driving the screen. Home stays writable: the assistant is supposed to
edit the user's files. That residual is documented in docs/REVIEW-AI-STACK.md.
"""
import os
import shutil


def available(which=None):
    which = which or shutil.which
    return bool(which('bwrap'))


def wanted(env=None, which=None):
    env = os.environ if env is None else env
    if str(env.get('UNIVERSE_AI_SANDBOX', '1')) == '0':
        return False
    return available(which)


def roots(existing=None):
    """Directories that exist on this machine and should be readable inside the sandbox."""
    if existing is None:
        existing = os.path.isdir
    found = []
    for path in ('/usr', '/usr/local', '/lib', '/lib64', '/bin', '/sbin', '/etc'):
        if existing(path):
            found.append(path)
    return found


def visible_binds(binary, binds, home):
    """Keep a CLI that lives outside /usr (for example /opt) visible."""
    if not binary:
        return list(binds)
    path = os.path.realpath(binary)
    home = os.path.realpath(home)
    if path == home or path.startswith(home + os.sep):
        return list(binds)
    for root in binds:
        root = os.path.realpath(root)
        if path == root or path.startswith(root + os.sep):
            return list(binds)
    parent = os.path.dirname(path)
    return list(binds) + [parent]


def command(inner, cwd, home, binds, socket_path, runtime, bwrap='bwrap', share_host=False):
    """argv for bwrap. Secrets stay in the environment, never in this list.

    share_host keeps /tmp and the real runtime directory, so Claude in Chrome's
    native host (started by Chrome, outside this sandbox) can reach the session.
    The session bus, Wayland and /dev/uinput stay hidden.
    """
    argv = [bwrap, '--die-with-parent']
    for path in binds:
        argv += ['--ro-bind', path, path]
    argv += ['--bind', home, home, '--dev', '/dev', '--ro-bind', '/dev/null', '/dev/uinput',
             '--proc', '/proc']
    if share_host:
        argv += ['--bind', '/tmp', '/tmp']
    else:
        argv += ['--tmpfs', '/tmp']
    argv += ['--unsetenv', 'DBUS_SESSION_BUS_ADDRESS', '--unsetenv', 'WAYLAND_DISPLAY', '--unsetenv', 'DISPLAY']
    if share_host and socket_path:
        host_runtime = os.path.dirname(socket_path) or '/tmp'
        argv += ['--bind', host_runtime, host_runtime]
    elif socket_path:
        argv += ['--bind', runtime, runtime,
                 '--ro-bind', socket_path, os.path.join(runtime, 'universe-shell.sock'),
                 '--setenv', 'XDG_RUNTIME_DIR', runtime]
    argv += ['--chdir', cwd, '--']
    argv += list(inner)
    return argv


def child_env(env, key_env=None, key=None):
    """Environment for the sandboxed CLI: no session bus, optional API key."""
    cleaned = dict(env)
    for name in ('DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY', 'DISPLAY'):
        cleaned.pop(name, None)
    cleaned['UNIVERSE_AI_SANDBOX'] = '1'
    if key_env and key:
        cleaned[key_env] = key
    elif key_env:
        cleaned.pop(key_env, None)
    return cleaned
