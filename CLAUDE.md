# Pep Developer Guide

Technical context for developing and maintaining Pep. For user-facing documentation (installation, usage, project structure, troubleshooting), see [README.md](README.md).

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

**How it works:**
- AppIndicator3 provides the tray icon
- GTK3 menu handles clicks
- Custom SVG pill icons in `icons/` (loaded via `set_icon_theme_path`)
- Icon name changes based on inhibitor state

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

## Manual Verification

1. **Inhibitor works:**
   ```bash
   systemd-inhibit --list | grep pep
   # Should show idle:sleep lock while Pep is running
   ```

2. **Toggle updates:**
   - Click "Keep Awake" off → `systemd-inhibit --list | grep pep` → no lock
   - Click "Keep Awake" on → run again → lock present

3. **State persistence:**
   - Toggle off → kill Pep → start Pep again → should still be off

4. **Autostart:**
   ```bash
   systemctl --user status pep.service  # active/running
   ```

5. **Reboot test:**
   - Reboot → icon should appear automatically → state preserved

## Future Enhancements

### Potential improvements (not implemented):

1. **Duration-based inhibit** - "Keep awake for 30 minutes" option
2. **Keyboard shortcut** - Toggle via global hotkey
3. **Sleep timer** - Countdown before auto-disabling
4. **Log viewer** - Show inhibitor activity in GUI

### Unlikely to implement:

- GUI preferences window (too much complexity)
- Wayland-specific features (Wayland support is improving)
- Monitor-specific inhibit (systemd-inhibit is system-wide)

## Version Management

Version is tracked in three files that must stay in sync:
- `pyproject.toml` (`version = "x.y.z"`)
- `pep/__init__.py` (`__version__ = "x.y.z"`)
- `aur/PKGBUILD` (`pkgver=x.y.z`)

Use `make bump VERSION=x.y.z` to update all three at once.

## Maintenance Notes

### When to update?

- Systemd-inhibit API changes (unlikely, stable since 2014)
- GTK3 breaking changes (rare, deprecated in GTK4 era)
- Python 3.12/3.13 compatibility issues

### Backwards compatibility

- Code targets Python 3.12+
- Uses standard library only (subprocess, signal, json, pathlib)
- No pinned versions needed for system packages (compatible across versions)
