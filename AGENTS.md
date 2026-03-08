# Agent Execution Guide

Follow these strictly when working with or running agents in this repository.

## 1. Python Environment

* **Package Manager:** Use **`uv`** for all Python-related operations.
* **Virtual Environment:** Use the existing **`.venv`** directory located in the project root. Activate using the command `venv\Scripts\activate`. **Do not create a new virtual environment.**

## 2. Running Commands

Once variables are set, execute your scripts using `uv` to automatically leverage the existing virtual environment.

**Example:**

```cmd
uv run agent.py
```

## 3. Running Frontend/Backend

- **Frontend:** Must activate backend (API) before frontend. Use `src\api\.venv\Scripts\activate.bat` to activate the backend environment, then run `python clean.py --confirm && uvicorn app.main:app --reload --reload-exclude 'reference-implementations/*' --reload-exclude '*.log' --reload-exclude '.venv/*'` to start the backend.
- **Frontend:** Activate venv using `src\api\.venv\Scripts\activate.bat` and run `npm run dev`