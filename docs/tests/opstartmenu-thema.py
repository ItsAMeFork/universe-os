#!/usr/bin/env python3
"""0.2.33: live-opstartmenu (BIOS/syslinux en UEFI/GRUB) in de 'home'-wereld-stijl, één optie, 3 s."""
import os, re, struct, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'live', 'config', 'bootloaders')
fout = []
def lees(p): return open(os.path.join(R, p), encoding='utf-8').read()
def png_maat(p):
    b = open(os.path.join(R, p), 'rb').read(32); assert b[:8] == b'\x89PNG\r\n\x1a\n', p
    return struct.unpack('>II', b[16:24]), b[24], b[25]
def eis(c, m):
    if not c: fout.append(m)
menu, std, iso, live = lees('syslinux_common/menu.cfg'), lees('syslinux_common/stdmenu.cfg'), lees('isolinux/isolinux.cfg'), lees('syslinux_common/live.cfg.in')
eis(not re.search(r'^\s*menu title', menu + std, re.M), 'syslinux: menu title moet weg (viel over het logo)')
eis(len(re.findall(r'^label ', live, re.M)) == 1, 'syslinux: precies één optie')
eis(re.search(r'^timeout 30$', iso, re.M), 'syslinux: 3 s autostart')
eis('menu background splash.png' in std, 'syslinux: achtergrond')
(w, h), diepte, kleur = png_maat('isolinux/splash.png')
eis((w, h) == (640, 480) and diepte == 8 and kleur in (2, 3), 'syslinux splash: 640x480, 8 bit')
grub, thema, tcfg = lees('grub-pc/grub.cfg'), lees('grub-pc/live-theme/theme.txt'), lees('grub-pc/theme.cfg')
eis(grub.count('menuentry ') == 1 and 'set timeout=3' in grub, 'grub: één optie, 3 s')
eis('title-text: ""' in thema, 'grub: geen titel')
eis(png_maat('grub-pc/live-theme/achtergrond.png')[0] == (1920, 1080), 'grub: achtergrond 1920x1080')
for f in re.findall(r'"(Universe Noto [A-Za-z]+ \d+)"', thema):
    naam, stijl, maat = f.rsplit(' ', 2)[0], f.split()[-2], f.split()[-1]
    pf = 'grub-pc/live-theme/universe-noto-%s%s.pf2' % ('bold-' if stijl == 'Bold' else '', maat)
    eis(os.path.exists(os.path.join(R, pf)) and pf.split('/')[-1] in tcfg, 'grub: font %s ontbreekt of wordt niet geladen' % f)
for d in ('nw', 'n', 'ne', 'w', 'c', 'e', 'sw', 's', 'se'):
    eis(os.path.exists(os.path.join(R, 'grub-pc/live-theme/sel_%s.png' % d)), 'grub: sel_%s.png' % d)
eis('__timeout__' in thema, 'grub: aftelling')
eis('play ' not in lees('grub-pc/config.cfg'), 'grub: geen piep')
print('\n'.join(fout) or 'OK opstartmenu-thema'); sys.exit(1 if fout else 0)
