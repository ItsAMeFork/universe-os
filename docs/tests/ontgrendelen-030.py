#!/usr/bin/env python3
"""0.3.0: veilig ontgrendelen bij terugwisselen, gtklock-herstart, live greeter-lijst."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parents[2] / "pakket/universe-os"
fout = []
def eis(c, m):
    if not c: fout.append(m)
w = (R / "usr/lib/universe-os/universe-ontgrendel-wacht").read_text()
eis("Unlock" in w and "GetSession" in w, "wachter luistert niet op eigen logind Unlock")
eis("universe-ontgrendeld" in w, "wachter zet geen marker")
r = (R / "usr/share/polkit-1/rules.d/50-universe-ontgrendelen.rules").read_text()
eis("org.freedesktop.login1.lock-sessions" in r and "AUTH_ADMIN" in r, "polkit-regel ontbreekt")
l = (R / "usr/bin/universe-lock").read_text()
eis("universe-ontgrendeld" in l and "while" in l, "universe-lock herstart gtklock niet")
eis("universe-ontgrendel-wacht" in (R / "usr/lib/universe-os/shell/session.py").read_text(), "wachter niet in autostart")
g = (R / "usr/lib/universe-os/shell/greeter.py").read_text()
eis("user-added" in g and "user-removed" in g, "greeter niet live")
eis("login-users" in (R / "usr/share/universe-os/ui/login.js").read_text(), "login.js luistert niet")
print("\n".join(fout) or "OK ontgrendelen-030"); sys.exit(bool(fout))
