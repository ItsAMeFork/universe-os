"""Optional local voice: openWakeWord, whisper.cpp and Piper. Off by default.

Nothing is downloaded until the user starts the install in a terminal. Speech
stays on this computer. The microphone stays closed until the switch is on and
the programs are installed. Without a private wake-word file, whisper.cpp checks
short clips for the words Hé Buddy.
"""
import os
import shutil
import subprocess
import tempfile

import kast

OWW = '0.6.0'
WHISPER_TAG = 'v1.9.5'
WHISPER_COMMIT = 'd1be6fde11ac6e0407606b4e42fe72d34add8037'
WHISPER_MODEL = 'ggml-base.bin'
WHISPER_MODEL_REV = '5359861c739e955e79d9a303bcbc70fb988958b1'
PIPER_TAG = '2023.11.14-2'
WHY = ('Hé Buddy staat uit. openWakeWord, whisper.cpp en Piper draaien alleen hier, '
       'zonder account en zonder wolk. Zet het aan als de programma\'s geïnstalleerd zijn.')


def enabled():
    return bool(kast.load()['stem'].get('aan'))


def profile():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return os.path.join(base, 'universe-os', 'stem')


def piper_bin():
    path = os.path.join(profile(), 'piper', 'piper')
    if os.access(path, os.X_OK):
        return path
    return shutil.which('piper') or ''


def whisper_bin():
    for name in ('whisper-cli', 'main'):
        path = os.path.join(profile(), 'whisper.cpp', 'build', 'bin', name)
        if os.access(path, os.X_OK):
            return path
    return shutil.which('whisper-cli') or ''


def wake_model():
    path = os.path.join(profile(), 'hey_buddy.onnx')
    return path if os.path.isfile(path) else ''


def model_path():
    return os.path.join(profile(), WHISPER_MODEL)


def ready():
    return bool(piper_bin() and whisper_bin() and os.path.isfile(model_path()))


def configure(args):
    args = args if isinstance(args, dict) else {}
    if 'aan' in args:
        kast.update('stem', aan=bool(args.get('aan')))
    return public()


def heard(transcript):
    """True when the local transcript is the wake phrase."""
    words = ' '.join(str(transcript or '').lower().split())
    for phrase in ('hé buddy', 'hee buddy', 'hey buddy'):
        if phrase in words:
            return True
    return False


def _record(seconds=3):
    """One short clip. Empty when arecord is missing. Never called while the switch is off."""
    binary = shutil.which('arecord')
    if not binary:
        return ''
    handle, path = tempfile.mkstemp(prefix='buddy-', suffix='.wav')
    os.close(handle)
    try:
        done = subprocess.run(
            [binary, '-q', '-d', str(int(seconds)), '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', path],
            capture_output=True, timeout=seconds + 8, check=False)
    except (OSError, subprocess.SubprocessError):
        done = None
    if done is None or done.returncode != 0 or not os.path.isfile(path) or os.path.getsize(path) < 1000:
        try:
            os.remove(path)
        except OSError:
            pass
        return ''
    return path


def _whisper(path):
    binary = whisper_bin()
    model = model_path()
    if not binary or not os.path.isfile(model) or not path:
        return ''
    try:
        done = subprocess.run(
            [binary, '-m', model, '-f', path, '-l', 'nl', '-nt'],
            capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return ''
    if done.returncode != 0:
        return ''
    return done.stdout.decode('utf-8', 'replace')


def _oww_score(path):
    """Score one clip with the venv. None when openWakeWord or the model file is absent."""
    model = wake_model()
    py = os.path.join(profile(), 'venv', 'bin', 'python')
    if not model or not os.access(py, os.X_OK) or not path:
        return None
    script = (
        'import sys,wave\n'
        'from openwakeword.model import Model\n'
        'import numpy as np\n'
        'path,model=sys.argv[1],sys.argv[2]\n'
        'with wave.open(path,"rb") as handle:\n'
        '    raw=handle.readframes(handle.getnframes())\n'
        'audio=np.frombuffer(raw,dtype=np.int16)\n'
        'scorer=Model(wakeword_models=[model],inference_framework="onnx")\n'
        'best=0.0\n'
        'for i in range(0,max(0,len(audio)-1280)+1,1280):\n'
        '    scores=scorer.predict(audio[i:i+1280])\n'
        '    for value in scores.values():\n'
        '        best=max(best,float(value))\n'
        'print("%.4f"%best)\n'
    )
    try:
        done = subprocess.run(
            [py, '-c', script, path, model],
            capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    try:
        return float(done.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def listen_once(capture=None, transcribe=None):
    """One local pass. The microphone is not opened when the switch is off.

    capture and transcribe replace arecord and whisper.cpp in tests.
    """
    if not enabled():
        return {'gehoord': False, 'reden': 'uit', 'pad': 'dicht'}
    own = capture is None and transcribe is None
    if own and not ready() and not wake_model():
        return {'gehoord': False, 'reden': 'stil', 'pad': 'dicht'}
    wav = ''
    try:
        blob = _record() if capture is None else capture()
        if not blob:
            return {'gehoord': False, 'reden': 'stil', 'pad': 'dicht'}
        if isinstance(blob, str):
            wav = blob
        if transcribe is not None:
            text = transcribe(blob)
            pad = 'test'
        elif wake_model():
            score = _oww_score(wav)
            if score is not None:
                hit = score >= 0.5
                return {'gehoord': hit, 'tekst': '', 'reden': 'wekwoord' if hit else 'nee', 'pad': 'wekwoord'}
            text = _whisper(wav)
            pad = 'whisper'
        else:
            text = _whisper(wav)
            pad = 'whisper'
    except Exception:  # noqa: BLE001 - a missing mic stays quiet
        return {'gehoord': False, 'reden': 'stil', 'pad': 'dicht'}
    finally:
        if wav and capture is None:
            try:
                os.remove(wav)
            except OSError:
                pass
    text = ' '.join(str(text or '').split())[:400]
    hit = heard(text)
    return {'gehoord': hit, 'tekst': text, 'reden': 'gehoord' if hit else 'nee', 'pad': pad}


def speak(text, runner=None):
    """Say one line with Piper. runner(text) replaces the process in tests."""
    if not enabled():
        return {'ok': False, 'reden': 'uit'}
    line = ' '.join(str(text or '').split())[:400]
    if not line:
        return {'ok': False, 'reden': 'leeg'}
    if runner is not None:
        runner(line)
        return {'ok': True, 'tekst': line}
    binary = piper_bin()
    voice = os.path.join(profile(), 'nl_NL-mls-medium.onnx')
    if not binary or not os.path.isfile(voice):
        return {'ok': False, 'reden': 'piper ontbreekt'}
    try:
        done = subprocess.run(
            [binary, '--model', voice, '--output_raw'],
            input=line.encode(), capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return {'ok': False, 'reden': 'piper mislukt'}
    if done.returncode != 0:
        return {'ok': False, 'reden': 'piper mislukt'}
    return {'ok': True, 'tekst': line}


def install_script():
    """Terminal script. Pinned versions, local profile, nothing from a third-party recorder."""
    return '''set -eu
OWW=%s
WHISPER_TAG=%s
WHISPER_COMMIT=%s
PIPER_TAG=%s
WHISPER_MODEL=%s
WHISPER_MODEL_REV=%s
BASE="${XDG_DATA_HOME:-$HOME/.local/share}/universe-os/stem"
mkdir -p "$BASE"
python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install --disable-pip-version-check "openwakeword==$OWW"
if [ ! -d "$BASE/whisper.cpp/.git" ]; then
  git clone --depth 1 --branch "$WHISPER_TAG" https://github.com/ggml-org/whisper.cpp.git "$BASE/whisper.cpp"
fi
git -C "$BASE/whisper.cpp" fetch --depth 1 origin "$WHISPER_COMMIT"
git -C "$BASE/whisper.cpp" checkout "$WHISPER_COMMIT"
cmake -S "$BASE/whisper.cpp" -B "$BASE/whisper.cpp/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BASE/whisper.cpp/build" --target whisper-cli -j"$(nproc)"
curl -fsSL -o "$BASE/$WHISPER_MODEL" "https://huggingface.co/ggerganov/whisper.cpp/resolve/$WHISPER_MODEL_REV/$WHISPER_MODEL"
case "$(uname -m)" in
  x86_64) PIPER_ASSET=piper_linux_x86_64.tar.gz ;;
  aarch64|arm64) PIPER_ASSET=piper_linux_aarch64.tar.gz ;;
  *) echo "Geen Piper-build voor deze processor."; exit 1 ;;
esac
curl -fsSL -o "$BASE/piper.tar.gz" "https://github.com/rhasspy/piper/releases/download/$PIPER_TAG/$PIPER_ASSET"
rm -rf "$BASE/piper"
mkdir -p "$BASE/piper"
tar -xzf "$BASE/piper.tar.gz" -C "$BASE/piper" --strip-components=1
curl -fsSL -o "$BASE/nl_NL-mls-medium.onnx" "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx"
curl -fsSL -o "$BASE/nl_NL-mls-medium.onnx.json" "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx.json"
echo "Klaar in $BASE."
echo "openWakeWord $OWW, whisper.cpp $WHISPER_TAG ($WHISPER_COMMIT), Piper $PIPER_TAG."
echo "Alles blijft op deze computer. Geen wekwoord-wolk."
echo "Druk op Enter."; read -r _
''' % (OWW, WHISPER_TAG, WHISPER_COMMIT, PIPER_TAG, WHISPER_MODEL, WHISPER_MODEL_REV)


def public():
    on = enabled()
    installed = ready()
    if on and installed:
        tekst = 'Aan. Alleen op deze computer.'
    elif on:
        tekst = 'Aan, programma\'s nog niet geïnstalleerd. Tot die tijd blijft het stil.'
    else:
        tekst = 'Uit'
    return {
        'aan': on,
        'geinstalleerd': installed,
        'wekwoord': bool(wake_model()),
        'tekst': tekst,
        'waarom': WHY,
        'openwakeword': OWW,
        'whisper': WHISPER_TAG,
        'piper': PIPER_TAG,
        'uitleg': ('Installeert openWakeWord %s, whisper.cpp %s en Piper %s in een eigen map. '
                   'Zonder hey_buddy.onnx luistert whisper.cpp naar de woorden Hé Buddy.') % (
                       OWW, WHISPER_TAG, PIPER_TAG),
    }
