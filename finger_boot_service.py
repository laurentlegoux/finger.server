import logging  
import socket  
import sys  
  
from mpos import (Service, SharedPreferences, TaskManager, Activity, Intent,  
                  SettingsActivity, FileExplorerActivity)  
  
logger = logging.getLogger(__name__)  
  
# App dir by default — finger.py and plan/project/pgpkey/forward ship  
# inside the app. Point the "finger_dir" pref at /data (etc.) to relocate.  
DEFAULT_FINGER_DIR = "/apps/finger.server"  
DEFAULT_FINGER_PORT = 79  
MAX_REPLY_BYTES = 8192  
  
USER_FILES = ("plan", "project", "pgpkey", "forward")  
SCRIPT_NAME = "finger.py"  
  
  
class FingerBootService(Service):  
  
    def __init__(self):  
        super().__init__()  
        self._running = True  
        self._started = False  
        self._online_cb = None  
        self._listen = None  
        self._port = DEFAULT_FINGER_PORT  
        self._dir = DEFAULT_FINGER_DIR  
        self._last_query = ""  
  
    def onStart(self, intent):  
        prefs = SharedPreferences(self.appFullName)  
        if prefs.get_int("finger_enabled", 1) == 0:  
            return  
  
        try:  
            self._port = int(prefs.get_string("finger_port", str(DEFAULT_FINGER_PORT)))  
        except Exception:  
            self._port = DEFAULT_FINGER_PORT  
        self._dir = prefs.get_string("finger_dir", DEFAULT_FINGER_DIR).rstrip("/")  
  
        if TaskManager.disabled:  
            self._start()  
            return  
  
        self._start()  
        logger.info("finger server started")  
  
        try:  
            from mpos.net.connectivity_manager import ConnectivityManager  
            if ConnectivityManager.is_online():  
                self._start()  
            else:  
                self._online_cb = lambda online: self._on_online(online)  
                ConnectivityManager.register_callback(self._online_cb)  
        except Exception as e:  
            logger.warning("ConnectivityManager unavailable (%s), starting anyway", e)  
            self._start()  
  
    def _on_online(self, online):  
        if not online or self._started:  
            return  
        try:  
            from mpos.net.connectivity_manager import ConnectivityManager  
            ConnectivityManager.unregister_callback(self._online_cb)  
        except Exception:  
            pass  
        self._online_cb = None  
        self._start()  
  
    def _start(self):  
        if self._started:  
            return  
        self._started = True  
        TaskManager.create_supervised_task(self._serve, restart_delay_ms=2000)  
  
    async def _serve(self):  
        s = socket.socket()  
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        s.bind(socket.getaddrinfo("0.0.0.0", self._port)[0][4])  
        s.listen(2)  
        s.setblocking(False)  
        self._listen = s  
        logger.info("fingerd listening on port %d, dir %s", self._port, self._dir)  
        while self._running:  
            try:  
                conn, addr = s.accept()  
            except OSError:  
                await TaskManager.sleep_ms(50)  
                continue  
            try:  
                self._handle(conn)  
            except Exception as e:  
                logger.error("fingerd handler error: %s", e)  
                sys.print_exception(e)  
                try:  
                    conn.close()  
                except Exception:  
                    pass  
  
    def _handle(self, conn):  
        try:  
            conn.settimeout(5)  
            req = conn.recv(512)  
            if __debug__:  
                logger.debug("fingerd query: %r", req)  
            self._last_query = req.strip().decode("utf-8", "replace")  
            if self._last_query:  
                conn.send(self._user_reply())      # script + static files  
            else:  
                conn.send(self._script_reply())    # script only  
        finally:  
            conn.close()  
  
    def _script_reply(self):  
        """Run finger.py from the finger dir if present."""  
        script = "%s/%s" % (self._dir, SCRIPT_NAME)  
        try:  
            with open(script, "r") as f:  
                code = f.read()  
        except OSError:  
            return b""  
        return self._run_script(code, script)  
  
    def _user_reply(self):  
        """finger.py output, then static user files appended."""  
        reply = self._script_reply()  
        if len(reply) < MAX_REPLY_BYTES:  
            reply += self._user_files(MAX_REPLY_BYTES - len(reply))  
        return reply or b"no plan\r\n"  
  
    def _run_script(self, code, path):  
        captured = []  
  
        def _print(*args, sep=" ", end="\n"):  
            captured.append(sep.join(str(a) for a in args) + end)  
  
        g = {"__name__": "__finger__", "query": self._last_query, "print": _print}  
        try:  
            exec(code, g)  
        except Exception as e:  
            logger.warning("fingerd script %s failed: %s", path, e)  
            sys.print_exception(e)  
            return b"finger script error\r\n"  
        out = "".join(captured).encode()  
        return out[:MAX_REPLY_BYTES] or b"(no output)\r\n"  
  
    def _user_files(self, budget=MAX_REPLY_BYTES):  
        parts = []  
        total = 0  
        for name in USER_FILES:  
            path = "%s/%s" % (self._dir, name)  
            try:  
                with open(path, "rb") as f:  
                    body = f.read(budget - total)  
            except OSError:  
                continue  
            parts.append(("%s:\r\n" % name).encode() + body + b"\r\n")  
            total += len(body)  
            if total >= budget:  
                break  
        return b"".join(parts)  
  
    def onDestroy(self):  
        self._running = False  
        if self._listen:  
            try:  
                self._listen.close()  
            except Exception:  
                pass  
  
  
class FingerDirBrowser(FileExplorerActivity):  
    """Pick-mode explorer where tapping a dir enters it instead of selecting it."""  
  
    def _on_item_clicked(self, e, path, is_dir):  
        if is_dir:  
            self._populate_dir(path)      # navigate into the folder  
        # files: ignore — we only pick directories  
  
  
class FingerDirPicker(Activity):  
    """Launches FingerDirBrowser; stores the chosen dir in prefs."""  
  
    def onCreate(self):  
        extras = self.getIntent().extras or {}  
        self._prefs = extras.get("prefs") or SharedPreferences(self.appFullName)  
        start_dir = self._prefs.get_string("finger_dir", DEFAULT_FINGER_DIR)  
  
        # Placeholder screen so finish() pops THIS activity, not the one below.  
        import lvgl as lv  
        placeholder = lv.obj()  
        placeholder.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.MAIN)  
        self.setContentView(placeholder)  
  
        intent = Intent(activity_class=FingerDirBrowser,  
                        extras={"mode": "pick", "start_dir": start_dir})  
        self.startActivityForResult(intent, self._on_picked)  
  
    def _on_picked(self, result):  
        if result and result.get("result_code"):  
            paths = result.get("data", {}).get("paths", [])  
            for p in paths:  
                if p.endswith("/"):          # keep only directories  
                    editor = self._prefs.edit()  
                    editor.put_string("finger_dir", p.rstrip("/"))  
                    editor.commit()  
                    break  
        self.finish()  
  
  
class FingerSettings(Activity):  
  
    def onCreate(self):  
        prefs = SharedPreferences(self.appFullName)  
        intent = Intent(activity_class=SettingsActivity)  
        intent.putExtra("prefs", prefs)  
        intent.putExtra("settings", [  
            {"title": "Finger server", "key": "finger_enabled",  
             "ui": "radiobuttons",  
             "ui_options": [("On", "1"), ("Off", "0")],  
             "default_value": "1"},  
            {"title": "Port", "key": "finger_port",  
             "default_value": str(DEFAULT_FINGER_PORT),  
             "placeholder": "TCP port (applies after reboot)"},  
            {"title": "Finger dir", "key": "finger_dir",  
             "ui": "activity", "activity_class": FingerDirPicker,  
             "placeholder": "Browse to pick a directory"},  
        ])  
        self.startActivity(intent)