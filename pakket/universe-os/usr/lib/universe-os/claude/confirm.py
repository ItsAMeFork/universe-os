"""Yes/no dialogs for actions Claude must not finish alone.

The default dialog is zenity, already part of Universe OS, so the question appears on the user's
screen (recipients, subject, body, or the key about to be pressed). There is no "yes" without a
dialog: if zenity is missing the answer is no. Auto-accept can say yes for ordinary questions
only; payments, deletion, sending, passwords and system changes stay unanswered until the user
is back.
"""
import shutil
import subprocess
import threading

# While a dialog is open the shell refuses further screen actions, so the assistant cannot
# click Toestaan itself through the screen tools. ydotool outside those tools is a separate hole;
# the launcher closes that with bubblewrap.
_depth = 0
_last = threading.local()


def busy():
    return _depth > 0


def deferred():
    return getattr(_last, 'kind', '') == 'wacht'


def refused_message(normal):
    if deferred():
        return 'Uitgesteld tot je terug bent. De actie staat in het brein onder Acties.'
    return normal


def ask(title, text, runner=None, force=False):
    """Returns True only when the user presses Toestaan. runner(title, text) replaces zenity in tests.

    force=True always shows the dialog. Installing Chrome is a system change, so away-mode
    must not answer it. Mail, payment, deletion and passwords already stay a question.
    """
    global _depth
    title = str(title or 'Bevestigen')[:200]
    text = str(text or '')[:8000]
    if not force:
        import auto_accept
        kind = auto_accept.decide(title, text)
        _last.kind = kind
        if kind == 'automatisch':
            auto_accept.record(title, text, 'automatisch')
            return True
        if kind == 'wacht':
            auto_accept.record(title, text, 'wacht')
            return False
    else:
        _last.kind = 'vraag'
    _depth += 1
    try:
        if runner is not None:
            return bool(runner(title, text))
        if not shutil.which('zenity'):
            return False
        try:
            result = subprocess.run(
                ['zenity', '--question', '--title', title, '--text', text, '--ok-label', 'Toestaan',
                 '--cancel-label', 'Weigeren', '--width', '520'],
                timeout=180, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0
    finally:
        _depth -= 1
