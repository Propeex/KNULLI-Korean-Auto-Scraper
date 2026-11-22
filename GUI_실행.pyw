"""No-console Windows GUI launcher. Double-click this .pyw file."""
import traceback
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
try:
    # Before importing the GUI, quietly check GitHub for newer beta releases.
    # If installed update helper is launched, close this process so the helper
    # can replace application files and automatically restart the updated GUI.
    from auto_update import try_launch_update
    if not try_launch_update(Path(__file__).resolve().parent):
        from gui import App
        App().mainloop()
except Exception:
    log=Path(__file__).resolve().parent/'work'/'startup_error.txt'
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(traceback.format_exc(),encoding='utf-8')
    try:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        messagebox.showerror('KNULLI 시작 오류','프로그램 시작 중 문제가 발생했습니다.\n'+str(log))
        root.destroy()
    except Exception:pass
