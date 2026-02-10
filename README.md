# Pep 💊

A lightweight, custom keep-awake system tray tool that replaces the broken caffeine service.

## What is Pep?

Pep is a minimalist system tray application that prevents your system from sleeping or going idle. It uses `systemd-inhibit` under the hood to create a strong sleep lock, and provides a simple toggle in your system tray to control the behavior.

**Why "Pep"?** It's Dutch slang for amphetamine/speed—a playful reference to keeping your system awake and energized.

## Features

✨ **Simple system tray indicator** - Shows whether keep-awake is active
🎛️ **Easy toggle** - Enable/disable from the tray menu
⚡ **Auto-start capability** - Starts automatically on login (configurable)
📦 **Minimal dependencies** - Uses system packages (no external libs needed)
💾 **Persistent state** - Remembers your preference across reboots

## Requirements

- **Arch Linux** (or Arch-based distro) with systemd and D-Bus
- **Python 3.12+**
- **python-gobject** (system package for GTK/AppIndicator)
- **systemd** (with systemd-inhibit)

## Installation

### From AUR (recommended)

```bash
yay -S pep
```

Then enable and start the service:

```bash
systemctl --user enable --now pep.service
```

### From source

```bash
git clone https://github.com/stevendejongnl/pep.git
cd pep
make install
```

This will:
1. Sync dependencies with uv
2. Install Pep as a command-line tool
3. Set up the systemd service for auto-start
4. Start Pep immediately

### Development Install

```bash
git clone https://github.com/stevendejongnl/pep.git
cd pep
make dev-install
make run
```

## Usage

### Running Pep

Once installed, Pep starts automatically on login. You can also run it manually:

```bash
pep
```

### System Tray Menu

The tray icon provides a menu with:

- **Keep Awake** [✓] - Toggle the inhibitor on/off
- **Start on Boot** [✓] - Toggle systemd auto-start
- **Quit** - Exit Pep

The icon appearance changes based on state:
- Full cup ☕ = Keep-awake is active
- Empty cup ☕ = Keep-awake is disabled

### Managing Auto-Start

**Enable auto-start:**
```bash
systemctl --user enable pep.service
systemctl --user start pep.service
```

**Disable auto-start:**
```bash
systemctl --user disable pep.service
systemctl --user stop pep.service
```

**Check status:**
```bash
systemctl --user status pep.service
systemctl --user is-enabled pep.service
```

## Uninstallation

### AUR package

```bash
yay -R pep
```

### From source

```bash
make uninstall
```

This will:
1. Stop and disable the systemd service
2. Remove the service file
3. Uninstall Pep

## Development

### Project Structure

```
pep/
├── pep/
│   ├── __init__.py          # Package metadata
│   ├── core.py              # systemd-inhibit subprocess management
│   ├── tray.py              # System tray indicator with AppIndicator3
│   ├── config.py            # State persistence (~/.config/pep/config.json)
│   └── main.py              # Entry point and orchestration
├── pep.service              # systemd user service
├── pyproject.toml           # uv project configuration
├── Makefile                 # Quick commands
├── noxfile.py               # Development automation
├── README.md                # This file
└── CLAUDE.md                # Developer documentation
```

### Running Tests

```bash
make lint          # Run ruff linter
make typecheck     # Run mypy type checker
make format        # Format code with ruff
```

### Development Workflow

1. **Make changes** to files in `pep/`
2. **Run linter & type checker:**
   ```bash
   make lint typecheck
   ```
3. **Test manually:**
   ```bash
   make run
   ```
4. **Check systemd-inhibit is working:**
   ```bash
   systemd-inhibit --list | grep pep
   ```

## Technical Details

### How It Works

1. **Core Inhibitor** (`pep/core.py`):
   - Spawns `systemd-inhibit` subprocess with `--what=idle:sleep` to lock both idle timeout and manual sleep
   - Manages process lifecycle (enable/disable/cleanup)

2. **Tray Indicator** (`pep/tray.py`):
   - Uses PyGObject to create GTK3 menu with AppIndicator3
   - Provides visual feedback via icon changes
   - Handles user interactions (toggles)

3. **Configuration** (`pep/config.py`):
   - Stores state in `~/.config/pep/config.json`
   - Persists across reboots

4. **Systemd Integration** (`pep.service`):
   - User-level service (no root required)
   - Auto-starts on graphical session login
   - Restarts on failure

### Verification

Check that Pep is actively inhibiting sleep:

```bash
# List all inhibitors
systemd-inhibit --list | grep pep

# Should show something like:
# WHAT        WHO  WHY                           MODE
# idle:sleep  pep  User requested keep-awake   block
```

## Troubleshooting

### Icon not showing in system tray

1. Ensure you're using a desktop environment with appindicator support (GNOME, KDE, Xfce, etc.)
2. Check that `python-gobject` is installed:
   ```bash
   pacman -Q python-gobject
   ```

### Pep not starting on boot

1. Check service status:
   ```bash
   systemctl --user status pep.service
   ```
2. Check logs:
   ```bash
   journalctl --user -u pep.service -n 20
   ```
3. Verify autostart is enabled:
   ```bash
   systemctl --user is-enabled pep.service
   ```

### systemd-inhibit not found

Install systemd (it's usually included):
```bash
pacman -S systemd
```

## License

MIT

## Author

Steven de Jong
