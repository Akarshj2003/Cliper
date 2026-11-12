# Agent Workflow & Engineering Guidelines (Cliper / ClipViral)

## 1. Professional Git Protocol
The AI assistant must act as a Senior Staff Engineer managing version control for this repository:

### Commit Standards
- **Format**: Conventional Commits:
  - `feat(<scope>): <short description>`
  - `fix(<scope>): <short description>`
  - `test(<scope>): <short description>`
  - `docs(<scope>): <short description>`
  - `refactor(<scope>): <short description>`
  - `chore(<scope>): <short description>`
- **Content**: Never commit secrets (.env), credentials, compiled binaries, large video media (*.mp4, *.mov), or local cache (.next, __pycache__, *.db).
- **Quality Gate**: Before any commit or push, run `pytest` in `backend` and `npm run build` in `web` to ensure zero regressions.

### Branching & Release Cadence
- `main` branch tracks verified, working milestones.
- Feature branches `feature/step<N>-<name>` are created for non-trivial modifications.
- After every completed milestone review, commit changes with clear release notes and push to `origin main`.

### Push Automation
- Always verify remote status (`git status`, `git log --oneline -n 3`).
- When user approves a step or asks to push, sync and push cleanly to `https://github.com/Akarshj2003/Cliper.git`.
