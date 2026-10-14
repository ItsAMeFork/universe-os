"""Screen control for the assistant, on the labwc (wlroots) session.

labwc does not have its own remote-control protocol. What it does accept:
  * a real keyboard and mouse via the kernel (uinput) — ydotool, dotool, or python3-evdev
  * a virtual keyboard (zwp_virtual_keyboard_v1) — wtype, which is in Debian 13

ydotool is preferred when ydotoold is running. It is not in Debian 13 itself (only backports), so the
fallback that is packaged is python3-evdev for the pointer and wtype for keys. xdotool is not used.

The user must turn on "AI mag scherm bedienen" for this login. Super+Escape clears that flag.
Sending, paying, deleting and password fields ask for a zenity confirmation first. The audit line
never contains a password.
"""
import os
import shutil
import subprocess

import brein
import confirm

PANIC = 'Super+Escape'
SENSITIVE_KEYS = frozenset({
    'delete', 'shift+delete', 'ctrl+delete', 'ctrl+shift+delete',
    'alt+f4', 'ctrl+w', 'ctrl+q', 'ctrl+enter', 'ctrl+shift+enter', 'alt+enter',
})
# Opening a terminal from here would let the next typed line run outside the confirmation gate.
BLOCKED_KEYS = frozenset({'ctrl+alt+t', 'super+t', 'super+return'})
TERMINALS = frozenset({
    'xfce4-terminal', 'gnome-terminal', 'org.gnome.terminal', 'org.gnome.console', 'kgx',
    'kitty', 'foot', 'alacritty', 'xterm', 'wezterm', 'tilix', 'com.mitchellh.ghostty',
    'io.elementary.terminal', 'universe-claude', 'universe-ai',
})
_MODS = ('ctrl', 'alt', 'shift', 'super')
_ALIAS = {'control': 'ctrl', 'win': 'super', 'meta': 'super', 'return': 'enter', 'del': 'delete', 'esc': 'escape'}
# evdev keycodes (linux/input-event-codes.h), the values ydotool's `key` command expects.
_CODE = {
    'esc': 1, 'escape': 1, '1': 2, '2': 3, '3': 4, '4': 5, '5': 6, '6': 7, '7': 8, '8': 9, '9': 10, '0': 11,
    'backspace': 14, 'tab': 15, 'q': 16, 'w': 17, 'e': 18, 'r': 19, 't': 20, 'y': 21, 'u': 22, 'i': 23, 'o': 24,
    'p': 25, 'enter': 28, 'return': 28, 'ctrl': 29, 'a': 30, 's': 31, 'd': 32, 'f': 33, 'g': 34, 'h': 35, 'j': 36,
    'k': 37, 'l': 38, 'shift': 42, 'z': 44, 'x': 45, 'c': 46, 'v': 47, 'b': 48, 'n': 49, 'm': 50, 'space': 57,
    'f4': 62, 'alt': 56, 'up': 103, 'left': 105, 'right': 106, 'down': 108, 'delete': 111, 'super': 125,
}
_CLICK = {'left': '0xC0', 'right': '0xC1', 'middle': '0xC2'}
_DOEL = ('verwijder', 'delete', 'betalen', 'betaal', 'payment', 'pay', 'verzend', 'verzenden', 'send',
         'wachtwoord', 'password', 'overschrijf')
_PASSWORD_FIELDS = frozenset({'wachtwoord', 'password', 'pin', 'betaling', 'payment'})


# The grant lives in this process (the shell). A file in the runtime dir was writable by the
# assistant itself, so `touch` turned screen control on without the user. Do not read one.
_granted = False
_working = False


def _discard_flag_file():
    """Remove a leftover flag from older versions. It is never consulted."""
    path = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/tmp', 'universe-os', 'ai-scherm')
    try:
        os.remove(path)
    except OSError:
        return


def enabled():
    _discard_flag_file()
    return _granted


def allow():
    """Session grant. The shell calls this only after the user pressed Toestaan."""
    global _granted
    _discard_flag_file()
    _granted = True
    return status()


def request_grant(confirmer):
    """Turns screen control on only when confirmer returns True. No confirmer means no."""
    if enabled():
        return status()
    if confirmer is None or not confirmer(
            'AI mag het scherm bedienen',
            'Dit geldt tot je afmeldt. De assistent kan dan de muis en toetsen sturen.\n'
            'Super+Escape stopt het meteen.\n'
            'Een terminal kan de assistent niet bedienen.'):
        return status()
    return allow()


def revoke():
    """Panic stop (Super+Escape) and the off switch. Drops the session grant immediately."""
    global _granted, _working
    _granted = False
    _working = False
    _discard_flag_file()
    return status()


def terminal_app(app_id):
    """True for a terminal window. The assistant must not type into one: that is a shell."""
    text = str(app_id or '').strip().lower()
    if text.endswith('.desktop'):
        text = text[:-len('.desktop')]
    base = text.split('.')[-1]
    if text in TERMINALS or base in TERMINALS:
        return True
    return 'terminal' in base or base in ('xterm', 'kitty', 'foot', 'alacritty', 'wezterm', 'tilix')


def available():
    """Which input tools this session can actually use. A missing daemon counts as absent."""
    socket = os.environ.get('YDOTOOL_SOCKET') or os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/tmp', '.ydotool_socket')
    evdev = False
    if os.path.exists('/dev/uinput'):
        try:
            import evdev as _evdev  # noqa: F401
            evdev = True
        except ImportError:
            evdev = False
    return {
        'ydotool': bool(shutil.which('ydotool') and os.path.exists(socket)),
        'dotool': bool(shutil.which('dotool')),
        'evdev': evdev,
        'wtype': bool(shutil.which('wtype') and os.environ.get('WAYLAND_DISPLAY')),
    }


_ORDER = {
    'muis': ('ydotool', 'dotool', 'evdev'),
    'klik': ('ydotool', 'dotool', 'evdev'),
    'scroll': ('dotool', 'evdev'),
    'typ': ('ydotool', 'dotool', 'wtype'),
    'toets': ('ydotool', 'dotool', 'wtype', 'evdev'),
}


def backend_for(kind, have=None):
    """have is a backend name (tests) or None (pick the first installed tool that can do this)."""
    if have:
        return have
    present = available()
    for name in _ORDER.get(kind, ()):
        if present.get(name):
            return name
    return 'geen'


def compositor():
    if shutil.which('labwc'):
        return 'labwc'
    if os.environ.get('WAYLAND_DISPLAY'):
        return 'wayland'
    return 'geen'


def status():
    present = available()
    backend = backend_for('muis')
    if backend == 'geen':
        backend = backend_for('typ')
    return {'toegestaan': _granted, 'bezig': _working, 'backend': backend,
            'beschikbaar': [name for name, ok in present.items() if ok],
            'muis': backend_for('muis') != 'geen', 'compositor': compositor(), 'paniek': PANIC}


def _mark(busy):
    global _working
    _working = bool(busy)


def looks_like_secret(text):
    """A single token with a digit or a symbol. The tool cannot see the real widget type."""
    text = str(text or '')
    if not text or any(ch.isspace() for ch in text) or len(text) < 8:
        return False
    return any(ch.isdigit() for ch in text) or any(ch in text for ch in '!@#$%^&*')


def norm_combo(combo):
    parts = [p.strip().lower() for p in str(combo or '').replace('-', '+').split('+')]
    parts = [_ALIAS.get(p, p) for p in parts if p]
    mods = [name for name in _MODS if name in parts]
    keys = [p for p in parts if p not in _MODS]
    return '+'.join(mods + keys)


def _sensitive(kind, args):
    """Returns (needs confirmation, dialog text, audit summary). The summary never includes a password."""
    if kind == 'typ':
        text = str(args.get('tekst') or '')
        field = str(args.get('veld') or '').strip().lower()
        # The model can omit veld. A token that looks like a secret is still confirmed, and the text stays out of the log.
        if field in _PASSWORD_FIELDS or args.get('verzenden') or looks_like_secret(text):
            summary = 'Tekst in een gevoelig veld (%d tekens, niet gelogd)' % len(text)
            preview = summary + '.\n\nDe tekst komt niet in het logboek.'
            if args.get('verzenden'):
                preview = 'De assistent wil tekst typen en die daarna versturen of bevestigen.\n' + preview
            return True, preview, summary
        return False, '', 'Typ %d tekens' % len(text)
    if kind == 'toets':
        combo = norm_combo(args.get('toets') or args.get('combo') or '')
        if combo in SENSITIVE_KEYS or combo.endswith('+delete'):
            summary = 'Toets %s' % combo
            return True, 'Toetsencombinatie: %s.\nDit kan sluiten, verwijderen of versturen.' % combo, summary
        return False, '', 'Toets %s' % combo
    if kind == 'klik':
        doel = str(args.get('doel') or '')
        low = doel.lower()
        if any(word in low for word in _DOEL):
            return True, 'Klik op: %s' % doel[:300], 'Klik: %s' % doel[:180]
        return False, '', 'Klik %s' % (doel[:180] or args.get('knop') or 'links')
    if kind == 'muis':
        return False, '', 'Muis naar %s, %s' % (args.get('x'), args.get('y'))
    if kind == 'scroll':
        return False, '', 'Scroll %s' % args.get('dy')
    return False, '', kind


def plan(backend, kind, args):
    """The exact command the backend will run. Tests check this list; nothing is executed here."""
    if backend == 'geen':
        raise RuntimeError('Geen schermbediening beschikbaar. Installeer wtype (toetsen) en python3-evdev, of ydotool uit backports.')
    if kind == 'muis':
        x, y = int(args.get('x')), int(args.get('y'))
        if not (0 <= x <= 10000 and 0 <= y <= 10000):
            raise ValueError('Coördinaat buiten beeld')
        if backend == 'ydotool':
            return [{'argv': ['ydotool', 'mousemove', '--absolute', '-x', str(x), '-y', str(y)]}]
        if backend == 'dotool':
            return [{'argv': ['dotool'], 'stdin': 'mouseto %d %d\n' % (x, y)}]
        if backend == 'evdev':
            return [{'evdev': 'move', 'x': x, 'y': y}]
        raise RuntimeError('wtype kan de muis niet verplaatsen. ydotool of python3-evdev (uinput) is nodig.')
    if kind == 'klik':
        button = str(args.get('knop') or 'left').lower()
        if button not in _CLICK:
            raise ValueError('Knoop moet left, right of middle zijn')
        if backend == 'ydotool':
            return [{'argv': ['ydotool', 'click', _CLICK[button]]}]
        if backend == 'dotool':
            return [{'argv': ['dotool'], 'stdin': 'click %s\n' % button}]
        if backend == 'evdev':
            return [{'evdev': 'click', 'button': button}]
        raise RuntimeError('wtype kan niet klikken.')
    if kind == 'typ':
        text = str(args.get('tekst') or '')
        if not text:
            raise ValueError('Geen tekst')
        if len(text) > 2000:
            raise ValueError('Te lange tekst')
        if backend == 'ydotool':
            return [{'argv': ['ydotool', 'type', '--', text]}]
        if backend == 'dotool':
            return [{'argv': ['dotool'], 'stdin': 'type %s\n' % text.replace('\n', ' ')}]
        if backend == 'wtype':
            return [{'argv': ['wtype', '--', text]}]
        raise RuntimeError('Typen gaat via ydotool, dotool of wtype. python3-evdev stuurt hier alleen muis, klik, scroll en toetsen.')
    if kind == 'toets':
        combo = norm_combo(args.get('toets') or args.get('combo') or '')
        if not combo:
            raise ValueError('Geen toets')
        names = combo.split('+')
        if any(name not in _CODE for name in names):
            raise ValueError('Onbekende toets in %s' % combo)
        if backend == 'ydotool':
            down = ['%d:1' % _CODE[name] for name in names]
            up = ['%d:0' % _CODE[name] for name in reversed(names)]
            return [{'argv': ['ydotool', 'key', '--'] + down + up}]
        if backend == 'dotool':
            return [{'argv': ['dotool'], 'stdin': 'key %s\n' % combo}]
        if backend == 'wtype':
            argv = ['wtype']
            keys = []
            for name in names:
                if name in _MODS:
                    argv += ['-M', 'logo' if name == 'super' else name]
                else:
                    keys.append(name)
            argv += ['-k', _wtype_key(keys[0] if keys else 'enter')]
            for name in names:
                if name in _MODS:
                    argv += ['-m', 'logo' if name == 'super' else name]
            return [{'argv': argv}]
        return [{'evdev': 'key', 'combo': combo}]
    if kind == 'scroll':
        dy = int(args.get('dy') or 0)
        dy = max(-20, min(20, dy))
        if dy == 0:
            raise ValueError('Scroll 0')
        if backend == 'dotool':
            return [{'argv': ['dotool'], 'stdin': 'wheel %d\n' % dy}]
        if backend == 'evdev':
            return [{'evdev': 'scroll', 'dy': dy}]
        raise RuntimeError('Scrollen gaat via python3-evdev of dotool. wtype en ydotool 1.0 doen dit niet.')
    raise ValueError('Onbekende schermactie')


def _wtype_key(name):
    return {'enter': 'Return', 'return': 'Return', 'escape': 'Escape', 'esc': 'Escape', 'tab': 'Tab',
            'backspace': 'BackSpace', 'delete': 'Delete', 'space': 'space', 'up': 'Up', 'down': 'Down',
            'left': 'Left', 'right': 'Right', 'f4': 'F4'}.get(name, name)


def _run_subprocess(op):
    subprocess.run(op['argv'], input=op.get('stdin'), text=True, timeout=15, check=True)


def _run_evdev(op):
    from evdev import AbsInfo, UInput, ecodes
    kind = op['evdev']
    if kind == 'move':
        width, height = _screen_size()
        cap = {ecodes.EV_ABS: [ecodes.ABS_X, ecodes.ABS_Y], ecodes.EV_KEY: [ecodes.BTN_LEFT]}
        info = {ecodes.ABS_X: AbsInfo(0, 0, width, 0, 0, 0), ecodes.ABS_Y: AbsInfo(0, 0, height, 0, 0, 0)}
        with UInput(cap, name='universe-assistent', absinfo=info) as device:
            device.write(ecodes.EV_ABS, ecodes.ABS_X, int(op['x']))
            device.write(ecodes.EV_ABS, ecodes.ABS_Y, int(op['y']))
            device.syn()
        return
    if kind == 'click':
        code = {'left': ecodes.BTN_LEFT, 'right': ecodes.BTN_RIGHT, 'middle': ecodes.BTN_MIDDLE}[op['button']]
        with UInput({ecodes.EV_KEY: [code]}, name='universe-assistent') as device:
            device.write(ecodes.EV_KEY, code, 1)
            device.syn()
            device.write(ecodes.EV_KEY, code, 0)
            device.syn()
        return
    if kind == 'scroll':
        with UInput({ecodes.EV_REL: [ecodes.REL_WHEEL]}, name='universe-assistent') as device:
            device.write(ecodes.EV_REL, ecodes.REL_WHEEL, int(op['dy']))
            device.syn()
        return
    if kind == 'key':
        codes = [_CODE[name] for name in op['combo'].split('+')]
        with UInput({ecodes.EV_KEY: codes}, name='universe-assistent') as device:
            for code in codes:
                device.write(ecodes.EV_KEY, code, 1)
            device.syn()
            for code in reversed(codes):
                device.write(ecodes.EV_KEY, code, 0)
            device.syn()
        return
    raise RuntimeError('evdev kan deze tekstactie niet zetten; gebruik wtype of ydotool voor typen')


def _screen_size():
    forced = os.environ.get('UNIVERSE_SCREEN') or ''
    if 'x' in forced:
        width, _, height = forced.partition('x')
        try:
            return max(1, int(width)), max(1, int(height))
        except ValueError:
            pass
    return 1920, 1080


def _execute(op, runner):
    if runner is not None:
        return runner(op)
    if 'evdev' in op:
        return _run_evdev(op)
    return _run_subprocess(op)


def perform(kind, args, confirmer=None, runner=None, have=None):
    """Runs one screen action. Sensitive ones do nothing unless confirmer returns True.

    have replaces backend detection in tests (a backend name). runner replaces the real command.
    """
    args = dict(args or {})
    if confirm.busy():
        brein.log_actie('scherm_' + kind, 'Bevestiging stond open', 'geweigerd')
        raise PermissionError('Er staat een bevestiging open. Die kan de assistent niet zelf aanklikken.')
    if not enabled():
        brein.log_actie('scherm_' + kind, 'Schermbediening stond uit', 'geweigerd')
        raise PermissionError('AI mag het scherm niet bedienen. Zet "AI mag scherm bedienen" aan in '
                              'Controlecentrum → Accounts. Dit geldt tot je afmeldt. Stoppen: %s.' % PANIC)
    if kind in ('typ', 'toets', 'klik') and terminal_app(args.get('venster')):
        brein.log_actie('scherm_' + kind, 'Terminal geweigerd', 'geweigerd')
        raise PermissionError('Een terminal mag de assistent niet bedienen. Dat zou de bevestiging omzeilen.')
    if kind == 'toets' and norm_combo(args.get('toets') or args.get('combo') or '') in BLOCKED_KEYS:
        brein.log_actie('scherm_toets', 'Terminaltoets geweigerd', 'geweigerd')
        raise PermissionError('Die toets opent een terminal. Dat mag de assistent niet.')
    backend = backend_for(kind, have)
    ops = plan(backend, kind, args)
    sensitive, preview, summary = _sensitive(kind, args)
    if sensitive:
        # Fail closed: no dialog function means no.
        allowed = bool(confirmer) and bool(confirmer('Claude wil het scherm bedienen', preview))
        if not allowed:
            if not confirm.deferred():
                brein.log_actie('scherm_' + kind, summary, 'geweigerd')
            raise PermissionError(confirm.refused_message('Geweigerd.'))
        outcome = 'goedgekeurd'
    else:
        outcome = 'uitgevoerd'
    _mark(True)
    try:
        for op in ops:
            _execute(op, runner)
    except Exception:
        brein.log_actie('scherm_' + kind, summary, 'mislukt')
        raise
    finally:
        _mark(False)
    brein.log_actie('scherm_' + kind, summary, outcome)
    return {'gelukt': True, 'backend': backend, 'status': outcome}
