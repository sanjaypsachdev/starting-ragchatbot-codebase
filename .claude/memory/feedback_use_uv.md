---
name: Always use uv, not pip
description: User requires uv for all Python package and server commands in this project
type: feedback
---

Always use `uv` to run Python and manage dependencies. Never use `pip` directly.

**Why:** User's explicit preference for this project.
**How to apply:** Use `uv sync` to install deps, `uv add <package>` to add new ones, and `uv run` to execute scripts or the server. Never suggest `pip install` or bare `python` commands.
