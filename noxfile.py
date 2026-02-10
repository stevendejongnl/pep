"""Development automation with Nox."""

import nox

nox.options.default_venv_backend = "uv|virtualenv"


@nox.session
def lint(session: nox.Session) -> None:
    """Run ruff linter."""
    session.install("ruff")
    session.run("ruff", "check", "pep")


@nox.session
def format(session: nox.Session) -> None:
    """Format code with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "pep")


@nox.session
def typecheck(session: nox.Session) -> None:
    """Run mypy type checker."""
    session.install("mypy", "types-PyGObject")
    session.run("mypy", "pep")


@nox.session
def all(session: nox.Session) -> None:
    """Run all checks."""
    session.notify("lint")
    session.notify("typecheck")
