# Contributing to Pytron Kit

Thanks for contributing to `pytron-kit`.

## Local development setup

### 1) Python environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[core]"
pip install pytest pytest-asyncio ruff
```

> `.[core]` comes from `pyproject.toml` and installs the core runtime dependencies used in development and tests.

### 2) Frontend stack (for apps/examples with a `frontend/` folder)

Pytron delegates frontend tasks to your package manager provider:

```bash
# install frontend dependencies
pytron frontend --provider npm install

# build frontend assets
pytron frontend --provider npm build
```

For hot reload while developing an app:

```bash
pytron run app.py --dev
# or with chrome/electron engine
pytron run app.py --dev --chrome
```

### 3) Optional native toolchain (only when touching Rust/native parts)

Install Rust and run type checks for changed crates:

```bash
cargo check --manifest-path pytron/engines/native/Cargo.toml
cargo check --manifest-path pytron/pack/secure_loader/Cargo.toml
```

## Validate your changes locally

Run the same core checks used by CI:

```bash
ruff check .
pytest
```

Use targeted tests first when possible, for example:

```bash
pytest tests/test_cli.py
```

## Pull request workflow

1. Create a focused branch from the latest default branch.
2. Make one scoped change set per PR.
3. Run lint/tests above before opening the PR.
4. Fill out the PR template with a clear description, related issue, and validation steps.

### Branch naming suggestions

- `fix/<short-description>`
- `feat/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

## Contributor expectations

- Keep PRs small and reviewable.
- Add or update tests when behavior changes.
- Avoid unrelated refactors in the same PR.
- Ask for help in the issue/PR thread if blocked for more than ~30 minutes.

### Communication cadence

- Maintainers aim to acknowledge new contributor questions within 2 business days.
- If a PR is waiting on maintainer feedback for more than 5 business days, leave a polite follow-up comment.

## Maintainer guide: triaging `good first issue`

Use `good first issue` only when all of the following are true:

- Task is safely completable in ~1–3 hours.
- Scope is concrete and includes likely file paths.
- Acceptance criteria and verification commands are explicit.
- No architecture-sensitive changes are required.

### Labeling and handoff checklist

- Apply both `good first issue` and `help wanted`.
- Add one area label when relevant (for example: `documentation`, `tests`, `frontend`, `python`).
- Include an out-of-scope section to prevent scope creep.
- When a newcomer asks to take it, assign quickly and add a first-step comment.
- If there is no progress update after ~10–14 days, unassign politely so others can pick it up.

## Code of conduct

Please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in all interactions.
