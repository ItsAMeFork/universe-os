"""Taskbar buttons are readable and usable with the keyboard (dock.js): tooltip, aria-label, active state, popup menu."""
import os, re
root = os.path.join(os.path.dirname(__file__), '..', '..', 'pakket', 'universe-os', 'usr', 'share', 'universe-os', 'ui')
js = open(os.path.join(root, 'dock.js')).read()
# Every taskbar button goes through button(): it needs a tooltip (title) and a name for screen readers (aria-label).
assert re.search(r"h\('button',\{class:`item[^`]*`,type:'button',title:name,\s*'aria-label':name", js)
# Active programs say so to screen readers, not only with the dot.
assert "'aria-current':active?'true':null" in js and "(actief)" in js
# The start button is named and reports whether the start menu is open.
assert re.search(r"h\('button',\{class:'item start-button'[^}]*title:'Start','aria-label':'Start','aria-expanded'", js)
# The right-click menu has a name and can be walked with the arrow keys.
assert "role:'menu','aria-label':'Acties'" in js
assert "e.key==='ArrowDown'||e.key==='ArrowUp'" in js
# Buttons stay native buttons (focusable with Tab, activated with Enter/Space).
assert js.count("type:'button'") >= 3
print('ok')
