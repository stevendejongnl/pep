"""Core inhibitor using systemd-inhibit to prevent sleep/idle and screen blanking."""

import logging
import re
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_xset_dpms(output: str) -> Optional[tuple[int, int, int, int]]:
    """Parse xset q output to extract DPMS and screensaver timeouts.

    Returns (standby, suspend, off, screensaver_timeout) or None on failure.
    """
    standby = suspend = off = 0
    screensaver_timeout = 0

    # Parse DPMS timeouts: "  Standby: 600    Suspend: 600    Off: 600"
    dpms_match = re.search(
        r"Standby:\s+(\d+)\s+Suspend:\s+(\d+)\s+Off:\s+(\d+)", output
    )
    if dpms_match:
        standby = int(dpms_match.group(1))
        suspend = int(dpms_match.group(2))
        off = int(dpms_match.group(3))

    # Parse screensaver timeout: "  timeout:  600    cycle:  600"
    ss_match = re.search(r"timeout:\s+(\d+)\s+cycle:", output)
    if ss_match:
        screensaver_timeout = int(ss_match.group(1))

    if not dpms_match and not ss_match:
        return None

    return (standby, suspend, off, screensaver_timeout)


class PepInhibitor:
    """Manages systemd-inhibit and screen blanking prevention."""

    def __init__(self) -> None:
        """Initialize the inhibitor."""
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._screensaver_cookie: Optional[int] = None
        self._dpms_fallback_active: bool = False
        self._original_dpms: Optional[tuple[int, int, int, int]] = None

    def enable(self) -> bool:
        """Start systemd-inhibit process to prevent sleep, idle, and screen blanking."""
        if self._process is not None:
            logger.warning("Inhibitor already running")
            return False

        try:
            self._process = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--what=idle:sleep",
                    "--who=pep",
                    "--why=User requested keep-awake",
                    "--mode=block",
                    "sleep",
                    "infinity",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Inhibitor enabled (PID: {self._process.pid})")
        except FileNotFoundError:
            logger.error("systemd-inhibit not found. Is systemd installed?")
            return False
        except Exception as e:
            logger.error(f"Failed to start inhibitor: {e}")
            return False

        self._enable_screen_inhibit()
        return True

    def _enable_screen_inhibit(self) -> None:
        """Prevent screen blanking via D-Bus ScreenSaver API, falling back to xset."""
        # Try D-Bus org.freedesktop.ScreenSaver first
        try:
            from gi.repository import Gio, GLib

            bus = Gio.bus_get_sync(Gio.BusType.SESSION)
            result = bus.call_sync(
                "org.freedesktop.ScreenSaver",
                "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver",
                "Inhibit",
                GLib.Variant("(ss)", ("pep", "User requested keep-awake")),
                GLib.VariantType("(u)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            self._screensaver_cookie = result.unpack()[0]
            logger.info(
                f"Screen blanking inhibited via D-Bus (cookie: {self._screensaver_cookie})"
            )
            return
        except Exception as e:
            logger.debug(f"D-Bus ScreenSaver inhibit failed: {e}")

        # Fall back to xset
        try:
            output = subprocess.run(
                ["xset", "q"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if output.returncode == 0:
                self._original_dpms = _parse_xset_dpms(output.stdout)
                if self._original_dpms:
                    logger.debug(f"Saved original DPMS settings: {self._original_dpms}")

            subprocess.run(
                ["xset", "s", "off", "-dpms"],
                check=True,
                capture_output=True,
                timeout=5,
            )
            self._dpms_fallback_active = True
            logger.info("Screen blanking inhibited via xset fallback")
        except FileNotFoundError:
            logger.warning("xset not found — screen blanking prevention unavailable")
        except Exception as e:
            logger.warning(f"xset fallback failed: {e}")

    def _disable_screen_inhibit(self) -> None:
        """Re-enable screen blanking by releasing D-Bus inhibit or restoring xset."""
        if self._screensaver_cookie is not None:
            try:
                from gi.repository import Gio, GLib

                bus = Gio.bus_get_sync(Gio.BusType.SESSION)
                bus.call_sync(
                    "org.freedesktop.ScreenSaver",
                    "/org/freedesktop/ScreenSaver",
                    "org.freedesktop.ScreenSaver",
                    "UnInhibit",
                    GLib.Variant("(u)", (self._screensaver_cookie,)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                )
                logger.info(
                    f"Screen blanking D-Bus inhibit released (cookie: {self._screensaver_cookie})"
                )
            except Exception as e:
                logger.warning(f"Failed to release D-Bus inhibit: {e}")
            self._screensaver_cookie = None

        if self._dpms_fallback_active:
            try:
                if self._original_dpms:
                    standby, suspend, off, ss_timeout = self._original_dpms
                    subprocess.run(
                        ["xset", "dpms", str(standby), str(suspend), str(off)],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    subprocess.run(
                        ["xset", "s", str(ss_timeout)],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    logger.info(f"Restored original DPMS settings: {self._original_dpms}")
                else:
                    subprocess.run(
                        ["xset", "+dpms", "s", "on"],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    logger.info("Re-enabled DPMS with defaults")
            except Exception as e:
                logger.warning(f"Failed to restore xset settings: {e}")
            self._dpms_fallback_active = False
            self._original_dpms = None

    def disable(self) -> bool:
        """Stop the systemd-inhibit process and restore screen blanking."""
        if self._process is None:
            logger.warning("Inhibitor not running")
            return False

        self._disable_screen_inhibit()

        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.warning("Inhibitor did not respond to SIGTERM, forcing kill")
                self._process.kill()
                self._process.wait()

            self._process = None
            logger.info("Inhibitor disabled")
            return True
        except Exception as e:
            logger.error(f"Failed to stop inhibitor: {e}")
            return False

    def is_active(self) -> bool:
        """Check if the inhibitor process is running."""
        if self._process is None:
            return False

        return self._process.poll() is None

    def cleanup(self) -> None:
        """Ensure inhibitor is stopped on exit."""
        if self.is_active():
            self.disable()
        else:
            # Screen inhibit may still be active even if systemd process died
            self._disable_screen_inhibit()
