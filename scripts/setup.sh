#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3.8}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "Python 3.8 was not found. Install Python 3.8 or set PYTHON to its executable." >&2
    exit 1
fi

if ! "$python_bin" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 8))'; then
    echo "CompilerGym setup expects Python 3.8; $python_bin reports: $("$python_bin" --version)" >&2
    exit 1
fi

venv_python="$repo_root/.venv/bin/python"
if [[ -x "$venv_python" ]]; then
    if ! "$venv_python" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 8))'; then
        echo "Existing .venv is not Python 3.8. Remove it and rerun this script." >&2
        exit 1
    fi
else
    "$python_bin" -m venv "$repo_root/.venv"
fi

# CompilerGym pins Gym 0.21, whose PyPI source package requires legacy build tooling.
"$venv_python" -m pip install \
    "pip<24.1" \
    "setuptools==65.5.0" \
    "wheel==0.38.4"
"$venv_python" -m pip install \
    --no-build-isolation \
    --no-use-pep517 \
    "gym==0.21.0"
"$venv_python" -m pip install -r "$repo_root/requirements.txt"

echo
echo "Python environment ready at $repo_root/.venv"
echo "Activate it with: source .venv/bin/activate"
echo "The exporter also needs llvm-dis-17 on PATH to generate .ll files."
