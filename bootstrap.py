"""Friendly first-run installation window for the Windows desktop app."""
import importlib.util
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def main():
    if sys.platform != "win32":
        print("Dieser Starter ist für Windows.")
        return 1
    window = tk.Tk()
    window.title("Larp Studio")
    try:
        window.iconbitmap(str(ROOT / "ui" / "assets" / "larp-studio.ico"))
    except tk.TclError:
        pass
    window.geometry("480x310")
    window.resizable(False, False)
    window.configure(bg="#141414")
    tk.Label(window, text="larp studio", font=("Segoe UI", 30, "bold"), fg="#f5f5f5", bg="#141414").pack(anchor="w", padx=30, pady=(24, 4))
    tk.Label(window, text="Larp Studio wird vorbereitet.", font=("Segoe UI", 12), fg="#f5f5f5", bg="#141414").pack(anchor="w", padx=30)
    message = tk.StringVar(value="Beim ersten Start werden die benötigten Dateien geladen.")
    label = tk.Label(window, textvariable=message, wraplength=418, justify="left", font=("Segoe UI", 10), fg="#b0b0b0", bg="#141414")
    label.pack(anchor="w", padx=30, pady=(16, 12))
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("Larp Studio.Horizontal.TProgressbar", troughcolor="#353535", background="#f5f5f5", borderwidth=0, lightcolor="#f5f5f5", darkcolor="#f5f5f5")
    progress = ttk.Progressbar(window, mode="indeterminate", length=418, style="Larp Studio.Horizontal.TProgressbar")
    progress.pack(padx=30, pady=(0, 12))
    progress.start(12)
    actions = tk.Frame(window, bg="#141414")
    actions.pack(anchor="w", padx=30)
    events = queue.Queue()
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYMOBILEDEVICE3_")}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    log = ROOT / "Larp Studio-Start.log"

    def prepare():
        try:
            with log.open("w", encoding="utf-8") as output:
                if not PYTHON.is_file():
                    events.put(("message", "Eine eigene Umgebung wird eingerichtet …"))
                    subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], stdout=output, stderr=output, check=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                stamp = ROOT / ".venv" / ".atlas-version"
                expected = (ROOT / "requirements.txt").read_text(encoding="utf-8")
                if not stamp.is_file() or stamp.read_text(encoding="utf-8") != expected:
                    events.put(("message", "Die App-Dateien werden geladen. Das kann einige Minuten dauern."))
                    subprocess.run([str(PYTHON), "-m", "pip", "--isolated", "--disable-pip-version-check", "install", "--index-url", "https://pypi.org/simple", "-r", str(ROOT / "requirements.txt")], stdout=output, stderr=output, check=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                    stamp.write_text(expected, encoding="utf-8")
                events.put(("message", "Larp Studio öffnet sich …"))
                process = subprocess.Popen([str(PYTHON), str(ROOT / "app.py")], stdout=output, stderr=output, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    code = process.wait(timeout=5)
                    if code:
                        raise RuntimeError("Larp Studio konnte nicht geöffnet werden.")
                except subprocess.TimeoutExpired:
                    pass
            events.put(("done", ""))
        except Exception as exc:
            events.put(("error", str(exc)))

    def poll():
        try:
            while True:
                kind, text = events.get_nowait()
                if kind == "message":
                    message.set(text)
                elif kind == "done":
                    window.destroy()
                    return
                elif kind == "error":
                    progress.stop()
                    progress.pack_forget()
                    message.set("Larp Studio konnte nicht starten. Details stehen in Larp Studio-Start.log. Falls WebView2 fehlt, installiere die Microsoft-Komponente über den Button unten und starte Larp Studio erneut.")
                    tk.Button(actions, text="Startprotokoll öffnen", command=lambda: os.startfile(log), bg="#f5f5f5", fg="#141414", relief="flat", padx=10, pady=7).pack(side="left", padx=(0, 8))
                    tk.Button(actions, text="WebView2", command=lambda: webbrowser.open("https://developer.microsoft.com/microsoft-edge/webview2/"), bg="#353535", fg="#e8edef", relief="flat", padx=10, pady=7).pack(side="left")
        except queue.Empty:
            pass
        window.after(150, poll)
    threading.Thread(target=prepare, name="atlas-setup", daemon=True).start()
    window.after(150, poll)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
