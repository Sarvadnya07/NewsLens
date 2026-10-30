# Environment Audit & Python Specification

**Project:** NewsLens India  
**Date of Audit:** October 30, 2026  
**Auditor:** Senior Python Engineer & Windows Environment Specialist  

---

## 1. Baseline Diagnosis & Environment Identification

### System Environment
- **Operating System:** Windows 11 (win32)
- **Host Python Interpreters Discovered:**
  - `C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe` (Python 3.12.10)
  - `C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe` (Python 3.13.9)
- **Windows Python Launcher:** `py.exe` (`py -3.12`, `py -3.13`)

### Root Cause of Previous Failures
1. **Interpreter Mismatch (`requests` missing):**
   - The user's global Python 3.12 environment had incomplete packages (`requests` was uninstalled/missing in Python 3.12), whereas Python 3.13 had partial packages. When tools invoked `python` or `pytest` directly in CMD/PowerShell without specifying an environment, it resolved to Python 3.12.10 and failed with `ModuleNotFoundError: No module named 'requests'`.
2. **Terminal Shell Syntax Error:**
   - In Windows CMD, Markdown comment lines starting with `#` were accidentally passed as command invocations, causing `'#' is not recognized as an internal or external command`.

---

## 2. Canonical Virtual Environment Established

To ensure complete reproducibility and isolation from global packages, a dedicated project-local virtual environment was established using Python 3.12.10:

- **Virtual Environment Location:** `C:\Users\ASUS\Desktop\NewsLens-India\.venv`
- **Canonical Python Executable:** `.venv\Scripts\python.exe` (Python 3.12.10)
- **Canonical Pip Executable:** `.venv\Scripts\pip.exe` (pip 26.2.2)

### Core Dependencies Declared in `requirements.txt`:
```
streamlit>=1.35.0
scikit-learn>=1.5.0
pandas>=2.2.0
numpy>=1.26.0
feedparser>=6.0.10
rank_bm25>=0.2.2
requests>=2.31.0
joblib>=1.4.0
pytest>=8.0.0
ruff>=0.4.0
```
*Note: `sqlite3` is a built-in standard library module and is intentionally excluded from `requirements.txt`.*

### Pip Check Verification:
```cmd
.venv\Scripts\python.exe -m pip check
```
**Output:** `No broken requirements found.`

### Core Import Verification:
```cmd
.venv\Scripts\python.exe -c "import requests, streamlit, pandas, numpy, sklearn, feedparser, joblib, rank_bm25; print('Core imports successful')"
```
**Output:** `Core imports successful`

---

## 3. Standard Execution Commands (Windows CMD & PowerShell Compatible)

Always execute commands via the explicit virtual environment interpreter:

```cmd
:: Lint check
.venv\Scripts\python.exe -m ruff check src tests app.py

:: Format check
.venv\Scripts\python.exe -m ruff format --check src tests app.py

:: Compile check
.venv\Scripts\python.exe -m compileall -q .

:: Pytest execution
.venv\Scripts\python.exe -m pytest -v

:: Launch Streamlit app
.venv\Scripts\python.exe -m streamlit run app.py
```
