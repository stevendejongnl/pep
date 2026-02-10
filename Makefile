.PHONY: help install dev-install run uninstall lint typecheck format clean

help:
	@echo "Pep - Keep System Awake Tool 💊"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          Install pep with systemd auto-start"
	@echo "  make dev-install      Install pep for development"
	@echo "  make run              Run pep from source"
	@echo "  make uninstall        Remove pep and clean up"
	@echo "  make lint             Run ruff linter"
	@echo "  make typecheck        Run mypy type checker"
	@echo "  make format           Format code with ruff"
	@echo "  make clean            Clean up build artifacts"

install: lint typecheck
	@echo "Installing Pep..."
	uv sync
	uv tool install --editable .
	mkdir -p ~/.config/systemd/user
	cp pep.service ~/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable pep.service
	systemctl --user start pep.service
	@echo "✓ Pep installed successfully!"
	@echo "Run 'systemctl --user status pep.service' to check status"

dev-install:
	@echo "Installing Pep for development..."
	uv sync
	uv tool install --editable .
	@echo "✓ Ready for development!"
	@echo "Run 'make run' to start pep"

run:
	uv run pep

uninstall:
	@echo "Uninstalling Pep..."
	systemctl --user stop pep.service || true
	systemctl --user disable pep.service || true
	rm -f ~/.config/systemd/user/pep.service
	systemctl --user daemon-reload
	uv tool uninstall pep || true
	@echo "✓ Pep uninstalled"

lint:
	uv run ruff check --fix pep

typecheck:
	uv run mypy pep

format:
	uv run ruff format pep

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf .mypy_cache .ruff_cache build dist
