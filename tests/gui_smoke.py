"""v0.8.2 GUI construction smoke test (run with an X display)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gui
app=gui.App(auto_setup=False)
app.update_idletasks()
assert tuple(app.tree['columns'])==('check','system','name','status')
assert app.cget('background')==gui.BG
assert app.detail_canvas.winfo_exists()
assert app.name_entry.winfo_exists()
assert app.description.winfo_exists()
print('v0.8.2 neutral dark GUI smoke: OK')
app.destroy()
