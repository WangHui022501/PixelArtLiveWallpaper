#!/usr/bin/env python3
"""
Pixel World Wallpaper App
Requirements: pip install pywebview
"""
import webview, base64, ctypes, os, sys, datetime, subprocess

_DIR      = os.path.dirname(os.path.abspath(__file__))
_PID_FILE = os.path.join(_DIR, "wallpaper_live.pid")


def _downloads_dir():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(d, exist_ok=True)
    return d


def _ffmpeg_to_mp4(src, dst):
    try:
        cmd = ["ffmpeg", "-i", src, "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", dst]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return r.returncode == 0 and os.path.exists(dst)
    except Exception:
        return False


def _is_pid_alive(pid):
    try:
        SYNCHRONIZE = 0x100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def _kill_pid(pid):
    try:
        PROCESS_TERMINATE = 0x0001
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def _read_pid_file():
    try:
        return int(open(_PID_FILE).read().strip())
    except Exception:
        return None


def _write_pid_file(pid):
    try:
        open(_PID_FILE, "w").write(str(pid))
    except Exception:
        pass


def _remove_pid_file():
    try:
        os.remove(_PID_FILE)
    except Exception:
        pass


class WallpaperAPI:

    def set_wallpaper(self, data_url):
        try:
            _, enc = data_url.split(",", 1)
            data = base64.b64decode(enc)
            tmp  = os.environ.get("TEMP") or os.path.expanduser("~")
            path = os.path.join(tmp, "pixel_world_wallpaper.png")
            open(path, "wb").write(data)
            ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
            return {"ok": bool(ok), "path": path} if ok else {"ok": False, "error": "API returned 0"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_live_wallpaper(self, cfg_b64="e30="):
        old_pid = _read_pid_file()
        if old_pid and _is_pid_alive(old_pid):
            _kill_pid(old_pid)
        _remove_pid_file()
        try:
            script = os.path.join(_DIR, "wallpaper_live.py")
            if not os.path.exists(script):
                return {"ok": False, "error": "wallpaper_live.py not found"}
            proc = subprocess.Popen([sys.executable, script, cfg_b64])
            _write_pid_file(proc.pid)
            return {"ok": True, "pid": proc.pid}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop_live_wallpaper(self):
        pid = _read_pid_file()
        if pid:
            _kill_pid(pid)
            _remove_pid_file()
        return {"ok": True}

    def live_wallpaper_running(self):
        pid = _read_pid_file()
        if pid and _is_pid_alive(pid):
            return {"running": True, "pid": pid}
        if pid:
            _remove_pid_file()
        return {"running": False}

    def save_video(self, b64_data):
        try:
            data = base64.b64decode(b64_data)
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            webm = os.path.join(_downloads_dir(), "pixel_world_" + ts + ".webm")
            open(webm, "wb").write(data)
            mp4 = webm.replace(".webm", ".mp4")
            if _ffmpeg_to_mp4(webm, mp4):
                os.remove(webm)
                return {"ok": True, "path": mp4, "format": "mp4"}
            return {"ok": True, "path": webm, "format": "webm"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_screen_size(self):
        try:
            w = ctypes.windll.user32.GetSystemMetrics(0)
            h = ctypes.windll.user32.GetSystemMetrics(1)
            return {"w": w, "h": h}
        except Exception:
            return {"w": 1920, "h": 1080}


def main():
    html_file = os.path.join(_DIR, "healing-pixel-art.html")
    if not os.path.exists(html_file):
        print("ERROR: healing-pixel-art.html not found at", html_file)
        input("Press Enter to exit...")
        sys.exit(1)

    url    = "file:///" + html_file.replace("\\", "/")
    api    = WallpaperAPI()
    screen = api.get_screen_size()
    win_w  = max(900, int(screen["w"] * 0.70))
    win_h  = max(600, int(screen["h"] * 0.70))

    webview.create_window(
        title="Pixel World",
        url=url,
        js_api=api,
        width=win_w,
        height=win_h,
        min_size=(700, 450),
        background_color="#000000",
        easy_drag=False,
    )
    # Live wallpaper process is NOT terminated on exit - it persists intentionally.
    webview.start(debug=False)


if __name__ == "__main__":
    main()
