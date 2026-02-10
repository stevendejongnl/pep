"""Configuration persistence for Pep."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PepConfig:
    """Pep configuration stored in ~/.config/pep/config.json."""

    enabled_by_default: bool = True
    autostart: bool = True

    @classmethod
    def load(cls) -> "PepConfig":
        """Load configuration from file or return defaults."""
        config_path = cls._get_config_path()

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                # Invalid JSON or unexpected keys, use defaults
                return cls()
        return cls()

    def save(self) -> None:
        """Persist configuration to file (atomic write via temp file)."""
        config_path = self._get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write using temp file
        temp_path = config_path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(asdict(self), f, indent=2)
            temp_path.replace(config_path)
        except Exception:
            # Clean up temp file if something goes wrong
            if temp_path.exists():
                temp_path.unlink()
            raise

    @staticmethod
    def _get_config_path() -> Path:
        """Get the configuration file path."""
        config_dir = Path(os.path.expanduser("~/.config/pep"))
        return config_dir / "config.json"
