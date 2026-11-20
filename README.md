# decisionphase

## Exporting CompilerGym LLVM datasets

The exporter writes CompilerGym LLVM benchmark bitcode to
`data/compiler_gym/bitcode/` and the LLVM 17 textual IR produced from it to
`data/compiler_gym/llvm-ir/`. Generated files are ignored by Git.

### Prerequisites

- Python 3.8, as used by CompilerGym's installation guide.
- LLVM 17 with the `llvm-dis-17` executable available on `PATH` (see the
  [LLVM 17 releases](https://github.com/llvm/llvm-project/releases/tag/llvmorg-17.0.6)).
- CompilerGym 0.2.5, installed in the virtual environment by the setup script.

The pinned CompilerGym package supplies the LLVM service used by this workflow.
When building CompilerGym from source instead, upstream requires exactly LLVM
10.0.0.
Follow the [CompilerGym installation guide](https://github.com/facebookresearch/CompilerGym/blob/development/INSTALL.md)
for that version and the platform-specific build dependencies. The Python
requirements file does not install system LLVM tools.
The setup script pins legacy pip, setuptools, and wheel versions and installs
Gym 0.21 separately because that upstream release has invalid package metadata
for current build tools.

### Setup and run

Install Python 3.8 and LLVM 17 for your platform, making sure `llvm-dis-17` is
on `PATH`. On Ubuntu, LLVM 17 is available with:

```sh
sudo apt-get install llvm-17 llvm-17-tools
```

If Python 3.8 is not named `python3.8`, pass its executable path through
`PYTHON`. Then run:

```sh
./scripts/setup.sh
source .venv/bin/activate
python scripts/export_compilergym.py
```

For example: `PYTHON=/path/to/python3.8 ./scripts/setup.sh`.

By default, the script exports all finite datasets. Select one dataset or
inspect available datasets with:

```sh
python scripts/export_compilergym.py --list-datasets
python scripts/export_compilergym.py --dataset npb-v0
```

The default all-datasets export skips datasets with unknown or unbounded size
(currently the `generator://` datasets). To export a finite sample from one,
specify it with `--dataset` and a `--limit`, for example
`--dataset generator://csmith-v0 --limit 5`. Finite datasets may also be very
large; `--limit 5` processes at most five benchmarks from each selected
dataset. To extract bitcode without converting it yet, use `--no-convert`.
To convert previously extracted bitcode without starting CompilerGym, use:

```sh
python scripts/export_compilergym.py --convert-only
```

Existing files are left untouched by default. Pass `--force` to overwrite
them. The exporter rejects benchmark payloads that are empty or are not LLVM
bitcode rather than writing incorrectly named files.