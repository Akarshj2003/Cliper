---
trigger: always_on
description: Professional Git and Repository Management Rules for ClipViral
---

# Professional Git Workflow Rules

1. **Verify Integrity Before Commit**:
   - Run backend test suite (`python -m pytest tests -v`).
   - Run frontend build check (`npm run build` in `/web`).
   - Never push failing code.

2. **Commit Hygiene**:
   - Use conventional commit messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
   - Ensure `.gitignore` is respected (no `.db`, `.next/`, `node_modules/`, `storage/`, `__pycache__/`).
   - Include the step number and primary files changed in the extended message.

3. **Remote Sync & Push**:
   - Remote URL: `https://github.com/Akarshj2003/Cliper.git`
   - Push to `origin main` at the completion of each approved step in Section 11 of the README.
