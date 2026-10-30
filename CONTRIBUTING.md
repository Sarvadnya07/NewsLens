# Contributing to NewsLens India

Thank you for contributing to NewsLens India. Please adhere to the following workflow to ensure maintainability, security, and clean history.

## Development Workflow

1. **Clone & Environment Setup:**
   ```bash
   git clone <repo-url>
   cd NewsLens-India
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Branching Model:**
   - NewsLens India uses **GitHub Flow** (trunk-based development with short-lived feature branches).
   - Branch names follow: `feature/<topic>`, `fix/<topic>`, `docs/<topic>`.
   - Never commit directly to `master`.

3. **Submodule References:**
   - The `research/` directory contains read-only upstream reference repositories.
   - If you need them for algorithmic reference, initialize them via:
     ```bash
     git submodule update --init --recursive
     ```

4. **Quality Gates & Verification:**
   Before opening a Pull Request, verify that all linting and tests pass:
   ```bash
   ruff check src tests app.py
   ruff format --check src tests app.py
   pytest tests/
   ```

5. **Commit Message Guidelines:**
   Follow Conventional Commits format:
   - `feat(...)`: New feature or ingestion capability
   - `fix(...)`: Bug fix or model correction
   - `docs(...)`: Documentation or evaluation report update
   - `refactor(...)`: Code change that neither fixes a bug nor adds a feature
   - `test(...)`: Adding or updating test cases
   - `chore(...)`: Maintenance, dependency, or configuration updates

6. **Pull Requests:**
   - Ensure PRs are focused and conceptually coherent.
   - Do not commit binary databases (`*.db`) or compiled bytecode (`*.pyc`).
   - If UI changes are included, attach screenshots or a video demonstration in the PR description.
