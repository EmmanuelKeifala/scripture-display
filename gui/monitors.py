"""Monitor discovery so the display can be put fullscreen on a chosen screen.

Tk's own '-fullscreen' attribute on Windows tends to jump back to the primary
monitor (particularly with mixed display scaling), so we ask Windows directly
for each monitor's rectangle and size the window to it ourselves.
"""
import sys
from dataclasses import dataclass


@dataclass
class Monitor:
    index: int
    x: int
    y: int
    width: int
    height: int
    primary: bool

    @property
    def label(self):
        tag = ", main" if self.primary else ""
        return f"Screen {self.index} ({self.width}x{self.height}{tag})"

    def contains(self, px, py):
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


def enable_dpi_awareness():
    """Must run before the Tk root is created.

    Without this Windows hands an unaware app scaled, inconsistent coordinates
    for monitors with different scaling, and windows land on the wrong screen.
    """
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def list_monitors(tk_widget=None):
    if sys.platform == "win32":
        try:
            monitors = _list_windows_monitors()
            if monitors:
                return monitors
        except Exception as e:
            print(f"[monitors] Could not enumerate monitors: {e}")
    # Fallback: a single screen as Tk sees it
    if tk_widget is not None:
        return [Monitor(1, 0, 0, tk_widget.winfo_screenwidth(), tk_widget.winfo_screenheight(), True)]
    return []


def _list_windows_monitors():
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

    MONITORINFOF_PRIMARY = 1
    user32 = ctypes.windll.user32
    found = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
    )

    def callback(hmonitor, hdc, rect, lparam):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            r = info.rcMonitor
            found.append((r.left, r.top, r.right - r.left, r.bottom - r.top,
                          bool(info.dwFlags & MONITORINFOF_PRIMARY)))
        return True

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)

    # Primary first, then left-to-right, matching how people think of "screen 2"
    found.sort(key=lambda m: (not m[4], m[0], m[1]))
    return [Monitor(i + 1, *m) for i, m in enumerate(found)]
