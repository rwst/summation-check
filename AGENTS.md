# AGENTS.md for Summation-Check Repository

## Build/Lint/Test Commands
- Build: pip install -r requirements.txt
- Lint: Use pylint (run: pylint **/*.py) for code linting; no project-specific command found.
- Test: No explicit tests identified; run individual tests with unittest if available (e.g., python -m unittest path/to/test.py).

## Code Style Guidelines
- Imports: Group at file top; use standard library first, then third-party (e.g., import sys, import PyQt5).
- Formatting: 4-space indentation; use docstrings for functions/modules.
- Types: Implicit via context; consider adding type hints for clarity (e.g., def function(param: str)).
- Naming: Snake_case for functions/variables (e.g., get_config_path); UPPER_CASE for constants.
- Error Handling: Use try-except blocks for IOErrors; log errors appropriately.

No Cursor or Copilot rules found in repository.

Ensure agents mimic existing patterns and follow security best practices.