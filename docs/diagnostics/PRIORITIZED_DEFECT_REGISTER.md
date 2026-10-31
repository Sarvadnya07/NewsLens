# NewsLens India — Prioritized Defect Register

## Defect Summary
- **P0 (Critical):** 0
- **P1 (High):** 1
- **P2 (Medium):** 1
- **P3 (Low):** 2

---

### Defect DEF-001 (P1 - High): TypeScript Build Failure on Unused Import
- **Symptom:** Running `cd frontend; pnpm build` fails with:
  `src/tests/AppLayout.test.tsx(3,8): error TS6133: 'React' is declared but its value is never read.`
- **Root Cause:** TypeScript strict configuration (`noUnusedLocals: true`) flags unused explicit `React` import when JSX transform (`react-jsx`) is enabled in Vite.
- **Affected File:** `frontend/src/tests/AppLayout.test.tsx:3:8`
- **Recommended Remediation:** Remove `import React from 'react';` from `frontend/src/tests/AppLayout.test.tsx` or configure `tsconfig.app.json` / `tsconfig.node.json` to exclude test files from production app bundle compilation.

---

### Defect DEF-002 (P2 - Medium): Inconsistent Scikit-Learn Unpickling Warnings
- **Symptom:** 35 warnings during pytest and API calls:
  `InconsistentVersionWarning: Trying to unpickle estimator LogisticRegression from version 1.9.1 when using version 1.7.2.`
- **Root Cause:** Model artifacts (`models/classifier.joblib`, `models/tfidf_vectorizer.joblib`) were serialized under a newer development build of scikit-learn (1.9.1) than the active runtime environment (1.7.2).
- **Affected Files:** `src/ml/predict.py:48-52`
- **Recommended Remediation:** Retrain or re-save model artifacts within the pinned scikit-learn 1.7.2 environment, or explicitly filter `InconsistentVersionWarning` in `src/ml/predict.py`.

---

### Defect DEF-003 (P3 - Low): Minor Ruff Formatting Differences in Backend Files
- **Symptom:** `py -3.13 -m ruff format --check src backend app.py tests` reports 4 files unformatted:
  - `backend/api/errors.py`
  - `backend/api/routes/analysis.py`
  - `backend/api/routes/health.py`
  - `backend/schemas/analysis.py`
- **Root Cause:** Minor multiline parameter indentation style differences. All linting rules (`ruff check`) pass with 0 errors.
- **Recommended Remediation:** Run `py -3.13 -m ruff format backend/` during the next development pass.

---

### Defect DEF-004 (P3 - Low): Bandit Security Scanner Not Installed in Global Python Environment
- **Symptom:** `py -3.13 -m bandit` returns `No module named bandit`.
- **Root Cause:** Bandit was listed in `requirements-dev.txt` but not installed in the system Python environment.
- **Recommended Remediation:** Include `bandit` in CI/CD pipeline virtual environment setup.
