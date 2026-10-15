#!/usr/bin/python3
"""Start the assistant the user picked on the AI page. universe-ai and universe-claude both end here."""
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_provider  # noqa: E402
import sandbox  # noqa: E402


def prepare(fresh=False, env=None):
    plan = ai_provider.launch_plan(fresh=fresh, env=env)
    if not plan['ok']:
        return plan
    for item in plan['writes']:
        folder = os.path.dirname(item['path'])
        os.makedirs(folder, mode=0o700, exist_ok=True)
        tmp = item['path'] + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            handle.write(item['text'])
        os.chmod(tmp, 0o600)
        os.replace(tmp, item['path'])
    inner = list(plan['argv'])
    child = sandbox.child_env(plan['env'], plan.get('key_env'), plan.get('key'))
    used = False
    if sandbox.wanted(plan['env']):
        home = child.get('HOME') or os.path.expanduser('~')
        runtime = os.path.join(home, '.local', 'share', 'universe-os', 'ai-runtime')
        os.makedirs(runtime, mode=0o700, exist_ok=True)
        socket_path = os.path.join(plan['env'].get('XDG_RUNTIME_DIR') or '/tmp', 'universe-shell.sock')
        binds = sandbox.visible_binds(plan.get('binary'), sandbox.roots(), home)
        socket = socket_path if os.path.exists(socket_path) else ''
        inner = sandbox.command(inner, plan['cwd'], home, binds, socket, runtime, share_host=bool(plan.get('chrome')))
        used = True
    plan['exec_argv'] = inner
    plan['exec_env'] = child
    plan['sandboxed'] = used
    return plan


def run_child(plan, popen=None):
    """Wait for the CLI. Codex and Gemini have no Stop hook, so their new session files become a lesson here.

    Claude already writes that lesson from its own hook. Ollama writes it per turn. Doing it again would double the row.
    """
    popen = popen or subprocess.Popen
    started = time.time()
    proc = popen(plan['exec_argv'], env=plan.get('exec_env'), cwd=plan.get('cwd') or None)
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        code = proc.wait()
    provider = plan.get('provider') or ''
    if provider not in ('claude', 'ollama') and plan.get('cwd'):
        previous = os.environ.get('UNIVERSE_AI_REFLECT')
        try:
            if (plan.get('env') or {}).get('UNIVERSE_AI_REFLECT') == '1':
                os.environ['UNIVERSE_AI_REFLECT'] = '1'
            else:
                os.environ.pop('UNIVERSE_AI_REFLECT', None)
            import efficientie
            model = plan.get('model') or ''
            efficientie.capture_folder(provider, model, plan['cwd'], started)
            # Gemini CLI writes chats under the home directory, not in the Universe work folder.
            if provider == 'gemini':
                home = (plan.get('exec_env') or {}).get('HOME') or os.path.expanduser('~')
                extra = os.path.join(home, '.gemini')
                if os.path.isdir(extra):
                    efficientie.capture_folder(provider, model, extra, started)
        except Exception:
            pass
        finally:
            if previous is None:
                os.environ.pop('UNIVERSE_AI_REFLECT', None)
            else:
                os.environ['UNIVERSE_AI_REFLECT'] = previous
    return 0 if code is None else int(code)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        import plugins
        outcome = plugins.ensure()
        if outcome.get('later'):
            print(outcome.get('tekst') or 'Plugins later opnieuw.')
    except Exception:
        pass
    plan = prepare(fresh='--nieuw' in argv)
    if not plan['ok']:
        print(plan['fout'])
        print('Druk op Enter om te sluiten.')
        try:
            input()
        except EOFError:
            pass
        return 1
    if plan['sandboxed']:
        print('Afscherming aan: geen sleutelbos en geen directe muis of toetsen vanuit het programma.')
    else:
        print('Afscherming uit. Zonder bubblewrap kan een terminalopdracht de bevestiging omzeilen.')
    sys.stdout.flush()
    os.chdir(plan['cwd'])
    return run_child(plan)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except OSError as error:
        print('Starten mislukt: %s' % error)
        raise SystemExit(1)
