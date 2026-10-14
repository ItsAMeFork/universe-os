"""Yes/no dialogs for actions Claude must not finish alone.

The default dialog is zenity, already part of Universe OS, so the question appears on the user's
screen (recipients, subject, body, or the key about to be pressed). There is no "yes" without a
dialog: if zenity is missing the answer is no.
"""
import shutil
import subprocess


def ask(title, text, runner=None):
    """Returns True only when the user presses Toestaan. runner(title, text) replaces zenity in tests."""
    title = str(title or 'Bevestigen')[:200]
    text = str(text or '')[:8000]
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
