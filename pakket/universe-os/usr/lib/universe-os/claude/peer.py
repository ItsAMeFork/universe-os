"""Who may send `call` on the shell socket.

The socket is mode 0600, but that only keeps other users out. The assistant runs as the
same user, so a terminal command can open the socket too. `call` is therefore limited to
the real universe_mcp.py. Shortcuts (`scherm-stop`, `claude-event`, …) stay open: they do
not perform mail, calendar or screen actions. A faked argv that merely mentions the file
name does not pass; the path has to be this file.
"""
import os


def script_path():
    return os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'universe_mcp.py'))


def read_cmdline(pid):
    try:
        raw = open('/proc/%s/cmdline' % int(pid), 'rb').read()
    except (OSError, ValueError):
        return []
    return [part.decode('utf-8', 'replace') for part in raw.split(b'\0') if part]


def cmdline_is_mcp(argv, mcp_path=None):
    """True when this process is Python executing the installed universe_mcp.py."""
    argv = list(argv or [])
    if len(argv) < 2:
        return False
    exe = os.path.basename(argv[0])
    if exe not in ('python', 'python3', 'python3.11', 'python3.12', 'python3.13'):
        return False
    real = os.path.realpath(mcp_path or script_path())
    for arg in argv[1:]:
        if not arg or arg.startswith('-'):
            continue
        try:
            if os.path.realpath(arg) == real:
                return True
        except OSError:
            continue
    return False


def allow_call(line, argv, mcp_path=None):
    """Socket lines that are not `call` stay allowed. `call` only from the MCP server."""
    if not str(line or '').startswith('call '):
        return True
    return cmdline_is_mcp(argv, mcp_path)


def cmdline_of_connection(connection):
    """Peer command line, or [] when the credentials cannot be read (then `call` is refused)."""
    try:
        pid = connection.get_socket().get_credentials().get_unix_pid()
    except Exception:
        return []
    return read_cmdline(pid)
