# Agent Execution Guide

Follow these strictly when working with or running agents in this repository.

## 1. Python Environment

* **Package Manager:** Use **`uv`** for all Python-related operations.
* **Virtual Environment:** Use the existing **`.venv`** directory located in the project root. Activate using the command `venv\Scripts\activate`. **Do not create a new virtual environment.**

## 3. Running Commands

Once variables are set, execute your scripts using `uv` to automatically leverage the existing virtual environment.

**Example:**

```cmd
uv run agent.py
```
