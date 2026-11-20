#!/usr/bin/env python3
"""Export CompilerGym LLVM benchmarks as bitcode and LLVM 17 textual IR."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "compiler_gym"
BITCODE_MAGIC = (b"BC\xc0\xde", b"\xde\xc0\x17\x0b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default="all",
        help=(
            "CompilerGym dataset name (default: all finite datasets); "
            "use --list-datasets to see options"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output root (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of benchmarks to export, useful for a small trial run",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List datasets available in CompilerGym and exit",
    )
    parser.add_argument(
        "--convert-only",
        action="store_true",
        help="Convert existing .bc files under OUTPUT_DIR without starting CompilerGym",
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        help="Only extract .bc files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.convert_only and args.no_convert:
        parser.error("--convert-only and --no-convert cannot be used together")
    return args


def require_llvm_dis() -> str:
    executable = shutil.which("llvm-dis-17")
    if executable is None:
        raise RuntimeError(
            "llvm-dis-17 was not found on PATH. Install LLVM 17 and retry."
        )

    result = subprocess.run(
        [executable, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"\bLLVM version\s+(\d+)", result.stdout + result.stderr)
    if not match or match.group(1) != "17":
        version_output = (result.stdout + result.stderr).strip()
        raise RuntimeError(
            f"Expected llvm-dis-17 to report LLVM version 17; got: {version_output}"
        )
    return executable


def output_path(root: Path, dataset_name: str, benchmark_uri: str, suffix: str) -> Path:
    prefix = "benchmark://"
    dataset = (
        dataset_name[len(prefix) :]
        if dataset_name.startswith(prefix)
        else dataset_name
    )
    safe_dataset = quote(dataset, safe="-_.")
    safe_uri = quote(benchmark_uri, safe="")
    return root / safe_dataset / f"{safe_uri}.{suffix}"


def load_compiler_gym():
    try:
        import compiler_gym
    except ImportError as error:
        raise RuntimeError(
            f"Unable to import CompilerGym ({error}). Run scripts/setup.sh first."
        ) from error
    return compiler_gym


def extract_dataset(
    dataset_name: str,
    output_dir: Path,
    limit: Optional[int],
    force: bool,
) -> int:
    compiler_gym = load_compiler_gym()

    with compiler_gym.make("llvm-v0") as env:
        if dataset_name in {"all", "*"}:
            datasets = list(env.datasets)
            if limit is None:
                unbounded = [dataset for dataset in datasets if dataset.size == 0]
                datasets = [dataset for dataset in datasets if dataset.size != 0]
                if unbounded:
                    skipped_names = ", ".join(dataset.name for dataset in unbounded)
                    print(
                        f"Skipping unbounded or unknown-size datasets "
                        f"({skipped_names}); "
                        "select one explicitly and pass --limit to export a sample.",
                        file=sys.stderr,
                    )
        else:
            lookup_name = (
                dataset_name
                if "://" in dataset_name
                else f"benchmark://{dataset_name}"
            )
            try:
                datasets = [env.datasets[lookup_name]]
            except LookupError as error:
                available = ", ".join(dataset.name for dataset in env.datasets)
                raise RuntimeError(
                    f"Unknown dataset {dataset_name!r}. Available datasets: {available}"
                ) from error
            if datasets[0].size == 0 and limit is None:
                raise RuntimeError(
                    f"Dataset {datasets[0].name} has unknown or unbounded size; "
                    "pass --limit to export a finite sample."
                )

        exported = 0
        for dataset in datasets:
            dataset_count = 0
            for benchmark in dataset.benchmarks():
                if limit is not None and dataset_count >= limit:
                    break

                uri = str(benchmark.uri)
                destination = output_path(
                    output_dir / "bitcode", dataset.name, uri, "bc"
                )
                if destination.exists() and not force:
                    print(f"Skipping existing {destination}")
                    dataset_count += 1
                    continue

                contents = benchmark.proto.program.contents
                if not contents:
                    raise RuntimeError(f"Benchmark has no embedded program data: {uri}")
                if not contents.startswith(BITCODE_MAGIC):
                    raise RuntimeError(
                        f"Benchmark is not LLVM bitcode and cannot be saved as .bc: {uri}"
                    )

                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
                print(f"Extracted {uri} -> {destination}")
                dataset_count += 1
                exported += 1

            print(f"{dataset.name}: {dataset_count} benchmark(s) processed")

    return exported


def convert_bitcode(output_dir: Path, llvm_dis: str, force: bool) -> int:
    bitcode_dir = output_dir / "bitcode"
    if not bitcode_dir.is_dir():
        raise RuntimeError(f"No bitcode directory found: {bitcode_dir}")

    converted = 0
    for source in sorted(bitcode_dir.rglob("*.bc")):
        destination = output_dir / "llvm-ir" / source.relative_to(bitcode_dir)
        destination = destination.with_suffix(".ll")
        if destination.exists() and not force:
            print(f"Skipping existing {destination}")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [llvm_dis, "-o", str(destination), str(source)],
            check=True,
        )
        print(f"Converted {source} -> {destination}")
        converted += 1

    return converted


def main() -> int:
    args = parse_args()
    try:
        if args.list_datasets:
            compiler_gym = load_compiler_gym()
            with compiler_gym.make("llvm-v0") as env:
                for dataset in env.datasets:
                    print(dataset.name)
            return 0

        if not args.convert_only:
            extract_dataset(args.dataset, args.output_dir, args.limit, args.force)

        if not args.no_convert:
            llvm_dis = require_llvm_dis()
            convert_bitcode(args.output_dir, llvm_dis, args.force)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
