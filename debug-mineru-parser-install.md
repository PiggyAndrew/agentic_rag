# Debug Session: mineru-parser-install

Status: OPEN

## User Symptom
- `LightRAG initialization failed: Parser 'mineru' is not properly installed`
- User states `mineru` has already been installed and the project uses a `uv` managed virtual environment named `agentic_rag`

## Falsifiable Hypotheses
1. The process that launches `raganything_example.py` is not using the `uv` environment interpreter where `mineru` is installed.
2. The code checks for a different import name or package entry point than the one actually installed by the user.
3. `mineru` is installed, but optional extras or transitive dependencies required by the parser probe are missing, so the probe still fails.
4. The installation exists in one Python environment, but `PATH`/`VIRTUAL_ENV`/`sys.executable` for the running process points to another environment.
5. The parser detection logic in `RAG-Anything` is too strict or outdated for the currently installed `mineru` package layout.

## Evidence To Collect
- Exact parser detection code path
- Active Python executable when reproducing
- `uv` environment package list / `mineru` visibility
- Import test result for the symbols expected by the code

## Evidence Collected
- `raganything/parser.py` checks installation with `subprocess.run(["mineru", "--version"])`, not a plain Python import.
- In `d:\GitHub\agentic_rag\backend\RAG-Anything`, `uv run python` resolves:
  - `sys.executable = ...\backend\RAG-Anything\.venv\Scripts\python.exe`
  - `PATH_mineru = ...\backend\RAG-Anything\.venv\Scripts\mineru.EXE`
  - `spec_mineru` present
  - `uv pip show mineru` reports version `3.1.15`
- In the same environment, `subprocess.run(["mineru", "--version"])` returns code `1` with stderr `Failed to canonicalize script path`.
- In `d:\GitHub\agentic_rag`, `uv run python` resolves:
  - `sys.executable = ...\agentic_rag\.venv\Scripts\python.exe`
  - `PATH_mineru = None`
  - `spec_mineru = None`
- In plain root `python`, `spec_mineru` is present from user-site Python 3.13 packages, but `PATH_mineru = None`.

## Analysis
- Hypothesis 1 partially confirmed: launch location still matters because the root environment does not contain `mineru`.
- Hypothesis 4 confirmed: the active interpreter and PATH differ across launch locations.
- Hypothesis 3 confirmed: the parser check can fail even when the package is installed, because the CLI entry point itself exits non-zero.
- Hypothesis 2 rejected for now: the installed module name matches `mineru`.
- Hypothesis 5 updated: the installation check is valid, but the Windows `uv` environment appears to have a broken script launcher for `mineru`.

## Root Cause
- There are two separate problems:
  1. The root `agentic_rag` environment does not contain the `mineru` CLI.
  2. Even in `backend\RAG-Anything`, the installed `mineru` console script fails on Windows with `Failed to canonicalize script path`, so `check_installation()` still reports it as unavailable.

## Recommended Fix
- Rebuild the `backend\RAG-Anything` virtual environment on Windows (`.venv` + `uv sync`) so the `mineru` script launcher is regenerated.
- Then run the example from `d:\GitHub\agentic_rag\backend\RAG-Anything` using that project's `uv` environment.
- Only if you intentionally launch from the repository root, install `mineru` into the root environment too.
