# Operational Runbook: Disaster Recovery & Incident Response

This runbook documents deterministic recovery procedures for repository incidents, branch corruption, bad merges, and secret exposure.

---

## 1. Secret Exposure Protocol

If any API credential, token, or private key is accidentally committed:

> [!CAUTION]
> **Revoke first.** Removing a secret from Git history does NOT make it safe. The secret must be invalidated at the provider immediately.

### Execution Sequence:
1. **Revoke & Invalidate:** Revoke the exposed credential immediately at the third-party provider dashboard (e.g. cloud provider, database, API service).
2. **Assess Exposure:** Check access logs and query audits for unauthorized usage between commit time and revocation time.
3. **Quarantine & Replace:** Generate and deploy fresh credentials into the environment configuration (`.env`).
4. **Purge from Git History (Coordinated):**
   Use `git-filter-repo` (never use deprecated `git filter-branch`):
   ```bash
   pip install git-filter-repo
   git filter-repo --invert-paths --path <path-to-sensitive-file>
   ```
5. **Coordinate Upstream Push:** Notify all contributors before force-pushing the rewritten history to `master`. Contributors must re-clone or reset their local branches.

---

## 2. Reflog Recovery (Accidental Reset or Branch Deletion)

Git retains local unreferenced commits in the reflog for at least 30 days before garbage collection runs.

### Scenario A: Accidental `git reset --hard`
To recover your working tree and HEAD after an accidental hard reset:
1. Inspect the reference log:
   ```bash
   git reflog show HEAD
   ```
2. Locate the commit SHA immediately prior to the reset (e.g. `HEAD@{1}`).
3. Restore the branch tip:
   ```bash
   git reset --hard HEAD@{1}
   ```

### Scenario B: Accidental Branch Deletion
If a branch was deleted (`git branch -D feature/lost-branch`):
1. Find the commit SHA where the deleted branch tip was:
   ```bash
   git reflog
   ```
2. Recreate the branch from that commit:
   ```bash
   git branch feature/lost-branch <commit-sha>
   ```

---

## 3. Reverting Public / Shared Commits

On shared branches (`master`), **never use `git reset --hard` and force-push** to undo changes. Always produce a forward revert commit:

```bash
# Revert a single commit cleanly
git revert <bad-commit-sha>

# If reverting a merge commit (specifying parent 1)
git revert -m 1 <bad-merge-sha>

# Run tests and verify
pytest tests/
git push origin master
```

---

## 4. Release Tagging & Immutability Standard

All releases must use annotated tags to record cryptographic tagger identity, timestamp, and release notes:

```bash
# Create an annotated release tag
git tag -a v1.0.0 -m "Release v1.0.0: NewsLens India Intelligence Platform"

# Verify tag annotation
git show v1.0.0

# Push tag to remote
git push origin v1.0.0
```

Release tags on GitHub should be protected via GitHub Ruleset (`refs/tags/v*` - block deletion and update).
