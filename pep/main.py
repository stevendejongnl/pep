"""Main entry point for Pep."""

import logging
import signal
import sys

from .config import PepConfig
from .core import PepInhibitor
from .tray import PepTrayIndicator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point for Pep."""
    try:
        # Load configuration
        config = PepConfig.load()
        logger.info(
            f"Config loaded: enabled_by_default={config.enabled_by_default}, "
            f"autostart={config.autostart}"
        )

        # Create inhibitor
        inhibitor = PepInhibitor()

        # Apply initial state
        if config.enabled_by_default:
            if inhibitor.enable():
                logger.info("Keep-awake enabled on startup")
            else:
                logger.warning("Failed to enable keep-awake on startup")

        # Create tray indicator with callback
        def on_state_changed(enabled: bool) -> None:
            """Called when toggle state changes."""
            config.enabled_by_default = enabled
            config.save()
            logger.info(f"State changed: enabled={enabled}")

        indicator = PepTrayIndicator(inhibitor, config, on_state_changed)

        # Register signal handlers for cleanup
        def signal_handler(signum: int, frame: object) -> None:
            """Handle signals for graceful shutdown."""
            logger.info(f"Signal {signum} received, shutting down")
            inhibitor.cleanup()
            config.save()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start the GTK main loop
        logger.info("Starting Pep")
        indicator.run()

        return 0

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
