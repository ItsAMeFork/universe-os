"""Hé Buddy: the buddy may speak a prompt out loud. Off until the user turns it on in the Brein.

Speech stays on this computer (espeak-ng, espeak or speech-dispatcher). Nothing is said
while the switch is off, and the switch is off until the user sets it.
"""
import shutil
import subprocess

WHY = 'Aan: de buddy spreekt meldingen uit. Uit: stil.'


def enabled(settings=None):
    if settings is None:
        import config
        settings = config.settings()
    return bool(settings.get('heBuddy'))


def line_of(text):
    raw = ''.join(ch if ch == '\n' or ord(ch) >= 32 else ' ' for ch in str(text or ''))
    return ' '.join(raw.split())[:400]


def public(settings=None):
    on = enabled(settings)
    return {'aan': on, 'tekst': 'Aan' if on else 'Uit', 'uitleg': WHY}


def configure(aan):
    import config
    config.set_setting('heBuddy', True if aan else False)
    return public()


def _engines(line):
    return (
        ['espeak-ng', '-v', 'nl', '-s', '148', line],
        ['espeak', '-v', 'nl', '-s', '148', line],
        ['spd-say', '-l', 'nl', line],
    )


def speak(text, runner=None, settings=None):
    """Say one buddy prompt. runner(text) replaces the speech program in tests.

    When Hé Buddy is off this returns immediately and does not look for a speech program.
    """
    if not enabled(settings):
        return {'ok': False, 'reden': 'uit'}
    line = line_of(text)
    if not line:
        return {'ok': False, 'reden': 'leeg'}
    if runner is not None:
        runner(line)
        return {'ok': True, 'tekst': line}
    for argv in _engines(line):
        binary = shutil.which(argv[0])
        if not binary:
            continue
        try:
            subprocess.run([binary, *argv[1:]], timeout=25, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            continue
        return {'ok': True, 'tekst': line}
    return {'ok': False, 'reden': 'geen stem', 'tekst': line}
