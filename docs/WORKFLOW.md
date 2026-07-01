# Workflow

This project is built in small milestones.

## Roles

- ChatGPT acts as project director, planning partner, learning support, and reviewer.
- Codex implements narrowly scoped repository tasks.
- VS Code is used to inspect files, run commands and tests, review Source Control, commit, and sync.
- GitHub is the version-controlled source of truth.
- Repository documentation is the durable project memory.
- Conversation context is useful working memory, but it is not authoritative.

## Milestone Rhythm

Each completed milestone should be:

- manually checked;
- tested;
- reviewed in VS Code Source Control;
- committed;
- synced to GitHub before the next milestone starts.

Behaviour changes should include relevant tests and documentation updates.

## Future Codex Threads

Future Codex threads should:

1. Read `AGENTS.md`.
2. Read `README.md`, `CHANGELOG.md`, and the docs in `docs/`.
3. Inspect the repository structure and relevant source files.
4. Inspect recent Git history if Git is available.
5. Run the full test suite before editing:

```powershell
python -m unittest discover -s tests
```

6. Summarize their understanding before substantial edits.
7. Make the smallest change that satisfies the approved task.
8. Run the full test suite again before declaring completion.
9. Report changed files, test results, and any uncertainty.

## Learning Support

The user is learning Python and project development. Explanations and completion reports should be clear, concrete, and beginner-friendly. Do not conceal uncertainty. If code, tests, documentation, or Git history disagree, report the disagreement plainly.

## Development Discipline

- Prefer small date ranges and existing January 2024 fixtures during development tests.
- Avoid downloading large historical ranges during ordinary feature work.
- Do not add unrelated features while implementing a requested milestone.
- Do not refactor unrelated code without approval.
- Do not commit or sync unless the user asks.

