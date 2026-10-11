"""Larp Studio desktop window. --preview serves a map-only browser preview."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def device_cli(output, arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    code = 1
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            sys.argv = ["pymobiledevice3", *arguments]
            from pymobiledevice3.__main__ import main
            code = int(main())
        except SystemExit as exc:
            code = int(exc.code or 0)
        except BaseException as exc:
            stderr.write(type(exc).__name__ + ": " + str(exc))
    Path(output).write_text(json.dumps({"code": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}), encoding="utf-8")
    return code


def reply(call):
    try:
        return {"ok": True, "data": call()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class Bridge:
    def __init__(self, controller, maps):
        self._controller, self._maps = controller, maps
        self._window = None
        from route_library import RouteLibrary
        self._routes = RouteLibrary(controller.root) if controller is not None else None

    def get_routes(self):
        return reply(self._routes.load)

    def save_routes(self, routes):
        return reply(lambda: self._routes.save(routes))

    def save_artwork(self, data_url):
        def save():
            from artwork import decode_artwork
            import webview
            image = decode_artwork(data_url)
            if self._window is None:
                raise RuntimeError("Das Programmfenster ist noch nicht bereit.")
            paths = self._window.create_file_dialog(webview.FileDialog.SAVE,
                save_filename="Larp-Studio-Kartenbild.png", file_types=("PNG-Bild (*.png)",))
            if not paths:
                return {"saved": False}
            path = Path(paths[0] if not isinstance(paths, str) else paths)
            path.write_bytes(image)
            return {"saved": True}
        return reply(save)

    def get_state(self):
        return reply(self._controller.snapshot)

    def get_settings(self):
        return {"ok": True, "data": {"tiles": self._maps.settings["tiles"]}}

    def connect_device(self):
        return reply(self._controller.connect)

    def set_connection(self, value):
        return reply(lambda: self._controller.connection(value))

    def prepare_wifi(self):
        return reply(self._controller.prepare_wifi)

    def start_session(self, plan):
        return reply(lambda: self._controller.start(plan))

    def pause_session(self):
        return reply(self._controller.pause)

    def stop_session(self):
        return reply(self._controller.stop)

    def recover_device(self):
        return reply(self._controller.recover)

    def set_speed(self, value):
        return reply(lambda: self._controller.speed(value))

    def search_places(self, query):
        return reply(lambda: self._maps.search(query))

    def plan_route(self, points, mode):
        return reply(lambda: self._maps.route(points, mode))

    def save_favorite(self, name, point, detail=""):
        return reply(lambda: self._controller.favorite(name, point, detail))


def browser_preview(port=8765):
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from engine import Maps
    maps = Maps(ROOT)
    class Handler(SimpleHTTPRequestHandler):
        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1024 * 1024:
                    raise ValueError("Ungültige Anfrage.")
                data = json.loads(self.rfile.read(size))
                if self.path == "/api/search_places":
                    result = reply(lambda: maps.search(data[0]))
                elif self.path == "/api/plan_route":
                    result = reply(lambda: maps.route(*data))
                elif self.path == "/api/get_settings":
                    result = {"ok": True, "data": {"tiles": maps.settings["tiles"]}}
                else:
                    result = {"ok": False, "error": "Diese Vorschau verändert keinen iPhone-Standort."}
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(ROOT / "ui")))
    print(f"Larp Studio · Karten-Vorschau: http://127.0.0.1:{port} · kein iPhone verbunden", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--device-cli":
        return device_cli(sys.argv[2], sys.argv[3:])
    if "--preview" in sys.argv:
        browser_preview(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 8765)
        return 0
    if sys.platform != "win32":
        print("Der Desktop-Starter ist für Windows. Karten-Vorschau: python app.py --preview")
        return 1
    smoke_output = Path(sys.argv[sys.argv.index("--smoke-ui") + 1]) if "--smoke-ui" in sys.argv else None
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import webview
    from engine import Controller, Maps
    data_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
    # Config lives beside the app, assets may be in a PyInstaller bundle.
    controller = Controller(data_root)
    maps = Maps(ROOT)
    bridge = Bridge(controller, maps)
    window = webview.create_window("Larp Studio", str(ROOT / "ui" / "index.html"),
                                   js_api=bridge, width=1400, height=920, min_size=(1024, 700),
                                   background_color="#141414", text_select=True, hidden=bool(smoke_output))
    bridge._window = window
    def closing():
        if controller.shutdown(timeout=15):
            return True
        return window.create_confirmation_dialog("Standort noch prüfen", "Das Zurücksetzen ist noch nicht bestätigt. Prüfe Apple Karten und starte das iPhone bei Bedarf neu. App trotzdem schließen?")
    window.events.closing += closing
    smoke_result = {"ok": False, "error": "Window did not start"}
    def check_ui():
        try:
            if not window.events.loaded.wait(45):
                raise RuntimeError("Timed out loading the Windows interface")
            result = window.evaluate_js("""(() => ({
                title: document.title,
                canvas: [document.getElementById('artworkCanvas').width, document.getElementById('artworkCanvas').height],
                native: document.getElementById('previewBadge').hidden,
                api: Object.keys(window.pywebview.api),
                functions: ['get_state','save_artwork','get_routes','save_routes','start_session'].every(k => typeof window.pywebview.api[k] === 'function')
            }))()""")
            if result["title"] != "Larp Studio" or result["canvas"] != [1536, 969] or not result["functions"]:
                raise RuntimeError("Windows interface or API failed to load: " + json.dumps(result))
            if any(k == "window" or k.startswith("window.") for k in result["api"]):
                raise RuntimeError("Internal window object was exposed in the JS API")
            smoke_result.update(ok=True, error=None, details=result)
        except Exception as exc:
            smoke_result.update(ok=False, error=str(exc))
        finally:
            smoke_output.write_text(json.dumps(smoke_result), encoding="utf-8")
            window.destroy()
    webview.start(check_ui if smoke_output else None, gui="edgechromium", http_server=True, user_agent="LarpStudio/1.3 (Windows desktop map)", private_mode=False,
                  icon=str(ROOT / "ui" / "assets" / "larp-studio.ico"))
    return (0 if smoke_result["ok"] else 1) if smoke_output else 0


if __name__ == "__main__":
    raise SystemExit(main())
