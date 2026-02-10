# Pep Developer Guide

This document provides technical context for developing and maintaining Pep.

## Architecture Overview

Pep is a three-component system:

1. **Core Inhibitor** (`pep/core.py`) - Manages systemd-inhibit subprocess
2. **System Tray Indicator** (`pep/tray.py`) - PyGObject/GTK3/AppIndicator3 GUI
3. **Configuration** (`pep/config.py`) - JSON persistence in `~/.config/pep/`

### Component Interaction

```
main.py (orchestrator)
├── Config: Load/save ~/.config/pep/config.json
├── Core: Enable/disable systemd-inhibit subprocess
└── Tray: Display indicator, handle user clicks
    └── Callbacks: Update config, manage core state
```

## Key Design Decisions

### systemd-inhibit as the Core

**Choice:** Use `systemd-inhibit --what=idle:sleep --mode=block sleep infinity`

**Why:**
- No daemon or polling loops needed—systemd handles the lock
- Works at system level (not just X11)
- Graceful shutdown: `SIGTERM` kills the sleep process, releasing the lock
- Already installed on all systemd systems
- Simple subprocess management

**Alternatives considered:**
- `xdotool` (X11 only, fragile)
- `python-evdev` polling (complex, eats CPU)
- Custom daemon (overkill for this use case)

### JSON Configuration Storage

**Choice:** Simple JSON in `~/.config/pep/config.json`

**Why:**
- No database needed
- Human-readable and debuggable
- Atomic writes via temp file (prevents corruption)
- Dataclass-based (type-safe)

**Config schema:**
```json
{
  "enabled_by_default": true,
  "autostart": true
}
```

### PyGObject + AppIndicator3

**Choice:** Use GTK3 with AppIndicator3 for system tray

**Why:**
- Minimal dependencies (system packages only)
- Cross-desktop (works on GNOME, KDE, Xfce, etc.)
- Built-in menu support
- No need for custom icon rendering

**How it works:**
- AppIndicator3 provides the tray icon
- GTK3 menu handles clicks
- Icon name changes based on inhibitor state
- No external icon files needed (uses theme icons)

## Implementation Details

### Signal Handling (main.py)

```python
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

**Important:** Signals trigger:
1. `inhibitor.cleanup()` - Stops systemd-inhibit subprocess
2. `config.save()` - Persists state to disk
3. `sys.exit(0)` - Clean shutdown

Without cleanup, systemd-inhibit lock could persist after Pep exits (orphaned).

### Subprocess Management (core.py)

**Enable flow:**
```
Popen(["systemd-inhibit", ...]) → store process handle → return success
```

**Disable flow:**
```
SIGTERM → wait(timeout=2) → SIGKILL if timeout → poll() to verify
```

**Why two-stage kill?**
- SIGTERM lets systemd-inhibit log its exit gracefully
- Timeout prevents hanging on stuck processes
- SIGKILL ensures termination

### Menu Toggle Synchronization (tray.py)

**Challenge:** Menu item state must match inhibitor state (avoid desync)

**Solution:** `handler_block_by_func` / `handler_unblock_by_func`

```python
# When user toggles, inhibitor state changes
# Update menu without triggering its own callback:
widget.handler_block_by_func(self._on_keep_awake_toggled)
widget.set_active(new_state)
widget.handler_unblock_by_func(self._on_keep_awake_toggled)
```

### Autostart Integration (tray.py)

**On toggle:** Runs subprocess to enable/disable systemd service

```python
subprocess.run(
    ["systemctl", "--user", "enable", "pep.service"],
    check=True,
    capture_output=True
)
```

**Why not use `subprocess.Popen`?**
- We need to wait for completion (synchronous)
- We need the exit code to detect failure
- We check errors and revert menu state on failure

## Testing Strategy

### Manual Verification

1. **Inhibitor works:**
   ```bash
   systemd-inhibit --list | grep pep
   # Should show idle:sleep lock while Pep is running
   ```

2. **Toggle updates:**
   - Click "Keep Awake" off
   - Run `systemd-inhibit --list | grep pep`
   - Should see no lock
   - Click "Keep Awake" on
   - Run again, should see lock

3. **State persistence:**
   - Toggle off
   - Kill Pep
   - Start Pep again
   - Should still be off (config persisted)

4. **Autostart:**
   ```bash
   systemctl --user status pep.service  # active/running
   ```

5. **Reboot test:**
   - Reboot
   - Icon should appear automatically
   - State should be preserved

### Code Quality

```bash
make lint      # Check code style (ruff)
make typecheck # Check type hints (mypy)
make format    # Format code (ruff)
```

All three should pass before merging.

## Common Issues and Solutions

### Issue: Icon doesn't appear in tray

**Cause:** Desktop environment doesn't support AppIndicator3 or python-gobject not installed

**Fix:**
```bash
pacman -S python-gobject
# Log out and log back in (reload systemd session)
```

### Issue: systemd-inhibit --list shows no lock

**Cause:** Inhibitor subprocess crashed silently

**Solution:** Check logs in journalctl
```bash
journalctl --user -u pep.service -n 50
```

### Issue: Pep won't start on boot

**Cause:** Service not enabled or graphical session not available

**Fix:**
```bash
systemctl --user enable pep.service
# Log out and back in to start graphical session
systemctl --user status pep.service  # Should show active
```

## Future Enhancements

### Potential improvements (not implemented):

1. **Custom icons** - Create .svg cup icons instead of relying on theme
2. **Duration-based inhibit** - "Keep awake for 30 minutes" option
3. **Keyboard shortcut** - Toggle via global hotkey
4. **Sleep timer** - Countdown before auto-disabling
5. **Log viewer** - Show inhibitor activity in GUI

### Unlikely to implement:

- GUI preferences window (too much complexity)
- Wayland-specific features (Wayland support is improving)
- Monitor-specific inhibit (systemd-inhibit is system-wide)

## Dependencies

### System Packages (pre-installed)

- `python-gobject` (3.54.5-2) - GTK3 + AppIndicator3 bindings
- `systemd` - systemd-inhibit tool

### Python Dependencies (via uv)

- `ruff` - Linting and formatting
- `mypy` - Type checking
- `types-PyGObject` - Type hints for PyGObject

**Note:** No runtime dependencies beyond system packages!

## Maintenance Notes

### When to update?

- Systemd-inhibit API changes (unlikely, stable since 2014)
- GTK3 breaking changes (rare, deprecated in GTK4 era)
- Python 3.12/3.13 compatibility issues

### Backwards compatibility

- Code targets Python 3.12+
- Uses standard library only (subprocess, signal, json, pathlib)
- No pinned versions needed for system packages (compatible across versions)

### Monitoring

Check service health:
```bash
systemctl --user status pep.service
journalctl --user -u pep.service --since "1 hour ago"
```

## Related Files

- `pyproject.toml` - Project metadata and dependencies
- `pep.service` - systemd user service file
- `Makefile` - Quick development commands
- `README.md` - User-facing documentation
