# NewsLens India — Pruning & Simplification Changelog

## 1. Pass 1 Changes
- **Bytecode Purge:** Removed untracked non-venv `__pycache__` directories across the workspace.
- **Git Hygiene:** Unstaged accidentally staged `.pyc` files from git index.
- **Security Rectification:** Reverted accidental working-tree change in `src/services/news_service.py` to restore SHA-256 for manual article submission; passed Bandit SAST scan with zero issues.
- **Tooling Alignment:** Standardized `pyproject.toml` `target-version = "py312"`.
- **Git Exclusions:** Added `*.bak` and `models/backup/` to `.gitignore`.

---

## 2. Pass 2 Aggressive Pruning Changes

### 2.1 Research Submodules & Cloned Repositories
- **Backed Up Externally:** All research submodules backed up to `..\NewsLens-India-Backup-Pass2\research\`.
- **Relocated LIAR Benchmark Dataset:**
  - Copied `train.tsv`, `valid.tsv`, `test.tsv`, `README`, and `LICENSE` directly to `data/liar/`.
  - Verified exact SHA-256 checksums matching ACL 2017 provenance.
  - Created `data/liar/PROVENANCE.md`.
  - Updated `src/ml/train.py` and `tests/test_all.py` dataset path references.
- **Pruned Cloned Library Trees:**
  - Removed git submodule tracking via `git rm --cached` for `research/fake-news-detection`, `research/feedparser`, `research/gdelt-doc-api`, and `research/rank_bm25`.
  - Removed `.gitmodules` via `git rm`.
  - Deleted all cloned upstream source directories (2,575 files, 27.9 MB removed).
  - Created `research/PROVENANCE.md` recording all upstream git URLs, commit hashes, and licensing details.

### 2.2 Design Prototype Pruning
- **Backed Up Externally:** `stitch_newslens_india_platform/` backed up to `..\NewsLens-India-Backup-Pass2\stitch_newslens_india_platform\`.
- **Preserved Design Spec:** Copied textual design specification to `docs/design/DESIGN_SPECIFICATION.md`.
- **Pruned Mockups:** Removed `stitch_newslens_india_platform/` (11 files, 4.89 MB) from git tracking and working tree via `git rm -r`.

### 2.3 Dependency Decoupling
- **`requirements.txt`:** Reduced to 8 direct runtime dependencies:
  `streamlit`, `scikit-learn`, `pandas`, `numpy`, `feedparser`, `rank_bm25`, `requests`, `joblib`.
- **`requirements-dev.txt`:** Created dedicated manifest for development and CI tooling:
  `-r requirements.txt`, `pytest`, `ruff`, `bandit`.
- **CI Workflow Update:** Updated `.github/workflows/ci.yml` to install `requirements-dev.txt`.

### 2.4 Documentation Consolidation
- Consolidated first-pass audit documents into:
  - `docs/codebase/FINAL_PRUNING_REPORT.md`
  - `docs/codebase/PRUNING_CHANGELOG.md`
- Removed overlapping first-pass report documents from `docs/codebase/`.
