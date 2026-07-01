# XAUUSD Lab Agent Guide

This file is the entry point for future Codex threads working in this repository.

Before substantial work, read:

- [README.md](README.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/WORKFLOW.md](docs/WORKFLOW.md)

## Working Rules

- Inspect the existing implementation before proposing or making changes.
- Treat the repository, tests, configuration, README, CHANGELOG, and Git history as the durable evidence for what exists.
- Preserve raw market data unchanged. Never edit downloaded CSV files in `data_raw/`.
- Use UTC internally unless local time is being explicitly displayed.
- Reuse shared modules such as `candle_filters.py` and `session_tools.py` instead of duplicating calculations.
- Keep Python readable for a beginner who is learning the project.
- Add or update tests for behavioural changes.
- Run the full test suite before declaring work complete:

```powershell
python -m unittest discover -s tests
```

- Update relevant documentation when behaviour changes.
- Use small date ranges and existing fixtures during feature testing.
- Avoid downloading large historical ranges during ordinary development tests.
- Never commit generated raw CSV data, generated reports, logs, caches, or temporary artifacts.
- Inspect Git status before and after work.
- Avoid unrelated refactoring or feature additions without approval.
- If documentation and code contradict each other, stop and report the contradiction instead of silently choosing one.

