"""System tray indicator using AppIndicator3 and GTK."""

import logging
import subprocess
from typing import Callable

try:
    import gi  # type: ignore[import-not-found]

    gi.require_version("Gtk", "3.0")
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3, Gtk  # type: ignore[import-not-found]
except ImportError as e:
    raise RuntimeError(
        "GTK3 and AppIndicator3 are required. Install: python-gobject"
    ) from e

from .config import PepConfig
from .core import PepInhibitor

logger = logging.getLogger(__name__)


class PepTrayIndicator:
    """System tray indicator with toggle menu."""

    # Icon names for different states
    ICON_FULL = "pep-cup-full"
    ICON_EMPTY = "pep-cup-empty"

    def __init__(
        self,
        inhibitor: PepInhibitor,
        config: PepConfig,
        on_state_changed: Callable[[bool], None],
    ) -> None:
        """Initialize the tray indicator.

        Args:
            inhibitor: PepInhibitor instance
            config: PepConfig instance
            on_state_changed: Callback when state changes (takes bool: enabled)
        """
        self._inhibitor = inhibitor
        self._config = config
        self._on_state_changed = on_state_changed

        # Create the indicator
        self._indicator = AppIndicator3.Indicator.new(
            "pep",
            self._get_icon_name(),
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self._menu_items: dict[str, Gtk.CheckMenuItem] = {}
        self._setup_menu()

    def _get_icon_name(self) -> str:
        """Get the current icon name based on inhibitor state."""
        return self.ICON_FULL if self._inhibitor.is_active() else self.ICON_EMPTY

    def _setup_menu(self) -> None:
        """Build the GTK menu."""
        menu = Gtk.Menu()

        # Keep Awake toggle
        keep_awake_item = Gtk.CheckMenuItem(label="Keep Awake")
        keep_awake_item.set_active(self._inhibitor.is_active())
        keep_awake_item.connect("toggled", self._on_keep_awake_toggled)
        self._menu_items["keep_awake"] = keep_awake_item
        menu.append(keep_awake_item)

        # Separator
        separator1 = Gtk.SeparatorMenuItem()
        menu.append(separator1)

        # Start on Boot toggle
        autostart_item = Gtk.CheckMenuItem(label="Start on Boot")
        autostart_item.set_active(self._config.autostart)
        autostart_item.connect("toggled", self._on_autostart_toggled)
        self._menu_items["autostart"] = autostart_item
        menu.append(autostart_item)

        # Separator
        separator2 = Gtk.SeparatorMenuItem()
        menu.append(separator2)

        # Quit option
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        self._indicator.set_menu(menu)

    def _on_keep_awake_toggled(self, widget: Gtk.CheckMenuItem) -> None:
        """Handle keep awake toggle."""
        enabled = widget.get_active()

        if enabled:
            success = self._inhibitor.enable()
            if not success:
                # Revert the toggle if enable failed
                widget.handler_block_by_func(self._on_keep_awake_toggled)
                widget.set_active(False)
                widget.handler_unblock_by_func(self._on_keep_awake_toggled)
                return
        else:
            success = self._inhibitor.disable()
            if not success:
                # Revert the toggle if disable failed
                widget.handler_block_by_func(self._on_keep_awake_toggled)
                widget.set_active(True)
                widget.handler_unblock_by_func(self._on_keep_awake_toggled)
                return

        self._update_icon()
        self._on_state_changed(enabled)

    def _on_autostart_toggled(self, widget: Gtk.CheckMenuItem) -> None:
        """Handle autostart toggle."""
        enabled = widget.get_active()
        self._config.autostart = enabled
        self._config.save()

        # Enable or disable the systemd service
        try:
            if enabled:
                subprocess.run(
                    ["systemctl", "--user", "enable", "pep.service"],
                    check=True,
                    capture_output=True,
                )
                logger.info("Autostart enabled")
            else:
                subprocess.run(
                    ["systemctl", "--user", "disable", "pep.service"],
                    check=True,
                    capture_output=True,
                )
                logger.info("Autostart disabled")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to toggle autostart: {e}")
            # Revert the toggle on failure
            widget.handler_block_by_func(self._on_autostart_toggled)
            widget.set_active(not enabled)
            widget.handler_unblock_by_func(self._on_autostart_toggled)

    def _on_quit(self, widget: Gtk.MenuItem) -> None:
        """Handle quit menu item."""
        logger.info("Quit requested")
        Gtk.main_quit()

    def _update_icon(self) -> None:
        """Update the tray icon based on inhibitor state."""
        icon_name = self._get_icon_name()

        # Try to set a theme icon first
        self._indicator.set_icon_full(icon_name, icon_name)

        # Update the keep awake menu item
        keep_awake_item = self._menu_items.get("keep_awake")
        if keep_awake_item:
            is_active = self._inhibitor.is_active()
            keep_awake_item.handler_block_by_func(self._on_keep_awake_toggled)
            keep_awake_item.set_active(is_active)
            keep_awake_item.handler_unblock_by_func(self._on_keep_awake_toggled)

    def run(self) -> None:
        """Start the GTK main loop."""
        logger.info("Starting system tray indicator")
        Gtk.main()
