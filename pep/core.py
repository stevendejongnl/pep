"""Core inhibitor using systemd-inhibit to prevent sleep/idle."""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class PepInhibitor:
    """Manages systemd-inhibit to prevent system sleep/idle."""

    def __init__(self) -> None:
        """Initialize the inhibitor."""
        self._process: Optional[subprocess.Popen[bytes]] = None

    def enable(self) -> bool:
        """Start systemd-inhibit process to prevent sleep and idle."""
        if self._process is not None:
            logger.warning("Inhibitor already running")
            return False

        try:
            # systemd-inhibit prevents both idle timeout and manual sleep
            # --what=idle:sleep locks both sleep and idle mechanisms
            # --mode=block creates a strong inhibitor lock
            # sleep infinity keeps the process running indefinitely
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
            return True
        except FileNotFoundError:
            logger.error("systemd-inhibit not found. Is systemd installed?")
            return False
        except Exception as e:
            logger.error(f"Failed to start inhibitor: {e}")
            return False

    def disable(self) -> bool:
        """Stop the systemd-inhibit process."""
        if self._process is None:
            logger.warning("Inhibitor not running")
            return False

        try:
            # Send SIGTERM for graceful shutdown
            self._process.terminate()
            try:
                # Wait up to 2 seconds for graceful exit
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't respond
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

        # Check if process is still alive
        return self._process.poll() is None

    def cleanup(self) -> None:
        """Ensure inhibitor is stopped on exit."""
        if self.is_active():
            self.disable()
