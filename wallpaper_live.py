#!/usr/bin/env python3
"""
Pixel World -- Live Wallpaper Process

Wallpaper Engine trick (correct approach):
  1. Send 0x052C to Progman -- Progman creates an empty WorkerW child.
  2. Find all WorkerW children of Progman.
  3. Pick the one WITHOUT SHELLDLL_DefView (the empty one = wallpaper layer).
  4. SetParent our window into that WorkerW.
  Result: our window is a child of WorkerW which is a child of Progman,
  placed BELOW SHELLDLL_DefView in Progman's child Z-order.
  Icons (in SHELLDLL_DefView) appear above us; DWM wallpaper appears behind us.
"""
import sys, os, time, ctypes, ctypes.wintypes, threading
import webview

_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallpaper_live.log")

def _log(msg):
    line = "[{}] {}".format(time.strftime("%H:%M:%S"), msg)
    print(line)
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class LiveAPI:
    def __init__(self, cfg_b64):
        self._cfg = cfg_b64
    def get_config(self):
        return self._cfg


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                   ctypes.wintypes.HWND,
                                   ctypes.wintypes.LPARAM)


def _get_rect(u32, hwnd):
    r = ctypes.wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def _find_hwnd_by_pid(u32, pid):
    result    = [None]
    best_area = [0]
    def _cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd): return True
        if u32.GetParent(hwnd): return True
        proc = ctypes.c_ulong(0)
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
        if proc.value != pid: return True
        l, t, r, b = _get_rect(u32, hwnd)
        area = (r - l) * (b - t)
        if area > best_area[0]:
            best_area[0] = area
            result[0] = hwnd
        return True
    u32.EnumWindows(WNDENUMPROC(_cb), 0)
    return result[0]


def _setup_workerw(u32):
    """
    Return (progman, workerw) where workerw is the empty WorkerW child of Progman
    suitable for hosting the live wallpaper window.
    Returns (progman, None) if no suitable WorkerW child is found.
    """
    progman = u32.FindWindowW("Progman", None)
    if not progman:
        _log("ERROR: Progman not found")
        return None, None
    _log("Progman={}".format(progman))

    # Trigger WorkerW creation inside Progman
    res = ctypes.c_ulong(0)
    u32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(res))
    time.sleep(0.2)
    u32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(res))
    time.sleep(0.5)

    # Enumerate all direct children of Progman and log them
    prev = None
    idx  = 0
    while True:
        child = u32.FindWindowExW(progman, prev, None, None)
        if not child:
            break
        buf = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(child, buf, 64)
        has_sdv = bool(u32.FindWindowExW(child, None, "SHELLDLL_DefView", None))
        _log("  Progman child[{}] hwnd={} class={} has_SHELLDLL_DefView={}".format(
            idx, child, buf.value, has_sdv))
        prev = child
        idx += 1

    # Find WorkerW children of Progman without SHELLDLL_DefView
    workerw = None
    prev = None
    while True:
        child = u32.FindWindowExW(progman, prev, "WorkerW", None)
        if not child:
            break
        has_sdv = bool(u32.FindWindowExW(child, None, "SHELLDLL_DefView", None))
        _log("WorkerW child={} has_SDV={}".format(child, has_sdv))
        if not has_sdv:
            workerw = child   # empty WorkerW = our wallpaper layer
        prev = child

    if workerw:
        _log("Using wallpaper WorkerW={}".format(workerw))
    else:
        _log("No empty WorkerW child found -- will try top-level HWND_BOTTOM fallback")

    return progman, workerw


def _embed():
    u32  = ctypes.windll.user32
    pid  = os.getpid()
    sw   = u32.GetSystemMetrics(0)
    sh   = u32.GetSystemMetrics(1)
    _log("embed PID={}  screen={}x{}".format(pid, sw, sh))

    # Wait for our pywebview window (must be top-level and visible)
    hwnd = None
    for i in range(80):
        hwnd = _find_hwnd_by_pid(u32, pid)
        if hwnd:
            _log("own HWND={} after {:.1f}s".format(hwnd, i * 0.25))
            break
        time.sleep(0.25)

    if not hwnd:
        _log("ERROR: own window not found")
        return

    time.sleep(1.5)   # let WebView2 finish first paint before reparenting

    progman, workerw = _setup_workerw(u32)
    if not progman:
        return

    # ── Strip window chrome ────────────────────────────────────────────────────
    GWL_STYLE    = -16
    GWL_EXSTYLE  = -20
    style   = u32.GetWindowLongW(hwnd, GWL_STYLE)
    exstyle = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    WS_CAPTION        = 0x00C00000
    WS_THICKFRAME     = 0x00040000
    WS_EX_TOOLWINDOW  = 0x00000080
    WS_EX_APPWINDOW   = 0x00040000
    WS_EX_NOACTIVATE  = 0x08000000
    u32.SetWindowLongW(hwnd, GWL_STYLE,   style   & ~(WS_CAPTION | WS_THICKFRAME))
    u32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                       (exstyle | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW)

    SWP_NOSIZE     = 0x0001
    SWP_NOMOVE     = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    HWND_NOTOPMOST = ctypes.c_void_p(-2)
    HWND_BOTTOM    = ctypes.c_void_p(1)

    # Clear TOPMOST before any Z-order work
    u32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                     SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)

    if workerw:
        # ── PRIMARY: SetParent into empty WorkerW child of Progman ─────────────
        # This is the standard Wallpaper Engine technique.
        # Our window becomes a child of WorkerW which is below SHELLDLL_DefView
        # in Progman's child stack, so icons appear above our animation.
        old = u32.SetParent(hwnd, workerw)
        _log("SetParent to WorkerW: old_parent={}".format(old))
        ok = u32.MoveWindow(hwnd, 0, 0, sw, sh, True)
        _log("MoveWindow ok={}".format(ok))

        # Re-apply after short delay (WebView2 may reposition)
        time.sleep(0.6)
        u32.MoveWindow(hwnd, 0, 0, sw, sh, True)
        _log("Done (WorkerW mode)")

        # Keep alive; re-assert size every 5 s
        while True:
            time.sleep(5.0)
            u32.MoveWindow(hwnd, 0, 0, sw, sh, False)

    else:
        # ── FALLBACK: HWND_BOTTOM top-level (icons will be ABOVE our window) ──
        # This works on systems where 0x052C creates no WorkerW child.
        # The animation is visible but may appear above icons -- still better
        # than nothing.
        ok = u32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, sw, sh,
                              SWP_NOACTIVATE | SWP_SHOWWINDOW)
        _log("Fallback HWND_BOTTOM ok={}".format(ok))
        _log("Done (fallback mode -- icons may overlap)")

        while True:
            time.sleep(2.0)
            u32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                             SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
            u32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, sw, sh,
                             SWP_NOACTIVATE | SWP_SHOWWINDOW)


def main():
    try:
        open(_log_path, "w").close()
    except Exception:
        pass

    cfg_b64 = sys.argv[1] if len(sys.argv) > 1 else "e30="
    _log("start cfg_len={}".format(len(cfg_b64)))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file  = os.path.join(script_dir, "healing-pixel-art.html")
    if not os.path.exists(html_file):
        _log("ERROR: html not found")
        sys.exit(1)

    url = "file:///" + html_file.replace("\\", "/") + "#wallpaper"

    u32 = ctypes.windll.user32
    sw  = u32.GetSystemMetrics(0)
    sh  = u32.GetSystemMetrics(1)

    webview.create_window(
        title="Pixel World Live",
        url=url,
        js_api=LiveAPI(cfg_b64),
        width=sw, height=sh,
        frameless=True,
        background_color="#000000",
    )
    threading.Thread(target=_embed, daemon=True).start()
    webview.start(debug=False)
    _log("exit")


if __name__ == "__main__":
    main()
