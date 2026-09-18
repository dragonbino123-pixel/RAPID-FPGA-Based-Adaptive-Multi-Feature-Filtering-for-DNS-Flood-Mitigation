# RAPID: FPGA-Based Adaptive Multi-Feature Filtering for DNS Flood Mitigation

[中文版](README_zh.md)

This repository contains the public software and experimental results accompanying RAPID.
It provides synthetic traffic generation, tools for evaluating the official DDiDD 0.1 baseline,
and scripts for checking the published result tables.

**RAPID's FPGA implementation is confidential and is not distributed.** This includes RTL,
hardware project files, bitstreams, simulation wrappers, testbenches, and hardware diagnostics.
The manuscript sources and paper build tools are also excluded.

## Public contents

| Path | Purpose |
| --- | --- |
| `experiments_v5/generate_traffic.py` | Synthetic legitimate queries, seven attack scenarios, five benign controls, and DDiDD training statistics |
| `experiments_v5/download_ddidd.py`, `prepare_ddidd.py`, `build_ddidd.sh`, `ddidd_adapter/` | Version-pinned retrieval, documented baseline adaptation, build, and label-free query transport |
| `experiments_v5/run_ddidd.py` | Independent DDiDD evaluation without RAPID binaries or decision files |
| `experiments_v5/results/` | Published per-run metrics, per-second counts, aggregate statistics, and DDiDD release metadata |
| `experiments_v5/analyze_results.py` | Recompute metrics from counts, cross-check timelines, and reproduce aggregate statistics |
| `experiments_v5/PROTOCOL.md` | Synthetic workload and evaluation protocol |
| `PUBLIC_FILES.txt`, `check_public_release.py` | Explicit publication allowlist and release checks |

The original method identifiers in CSV/JSON are retained for provenance. `rtl_n4` identifies
RAPID's main configuration; it does not indicate that RTL is included in this release.
Reported RAPID results were obtained using a private implementation. These files allow result
analysis, but **do not enable independent reruns of RAPID, its ablations, or hardware throughput tests**.
The 1.1-Tb/s hardware measurement is separate from the synthetic-query selectivity evaluation.

## Quick start

Use Python 3.11 or later and NumPy 2.3.5. DDiDD replay additionally requires a C++11 compiler
and a POSIX system (Linux or macOS; the adapter uses `fork`). From this repository's root:

```sh
python3 -m pip install -r experiments_v5/requirements.txt
python3 experiments_v5/analyze_results.py
```

This verifies all 750 published metric rows and 5,400 timeline rows and writes a separate
`experiments_v5/recomputed/summary.json`. It checks numerical consistency, not the private detector.

To generate one full input case and run DDiDD:

```sh
python3 experiments_v5/download_ddidd.py
sh experiments_v5/build_ddidd.sh
python3 experiments_v5/generate_traffic.py --seeds 20260611 --scenarios adaptive_mixed
python3 experiments_v5/run_ddidd.py --seeds 20260611 --scenarios adaptive_mixed
```

If using a virtual environment, activate it first; `build_ddidd.sh` uses `python3` by default,
or the interpreter selected by the `PYTHON` environment variable. For offline setup, pass
`--from-file /path/to/ddidd-0.1.tar.gz` to the download helper. Its SHA-256 must match the manifest.

Omit `--seeds` and `--scenarios` in both commands to generate and evaluate all five seeds and
twelve scenarios. Full inputs need roughly 30 GB, with additional space for baseline replay.
Allow at least 40 GB of free storage. Runs are sequential to limit peak memory and temporary files.
Generated inputs and new baseline results are ignored by Git. New results go under `recomputed/`;
the published CSV/JSON files are preserved.

Seeds 20260611–20260615 are pseudorandom initialization values, not dates of collected traffic.
The workload is synthetic; it is not an operator trace. All seven attack cases for one seed share
the same legitimate background. No evaluation labels are given to DDiDD.

## Release checks

```sh
python3 check_public_release.py --git-index
```

Run this after staging an intended release. Only paths explicitly listed in `PUBLIC_FILES.txt`
are allowed. The default `.gitignore` also excludes everything outside that allowlist.
Do not publish private development archives or import their Git history into this repository.

## License and third-party code

Original public utilities are covered by [LICENSE](LICENSE). DDiDD is fetched from its authors;
its source archive and generated executable are not bundled. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
The public license does not grant access to, or rights in, the undistributed confidential FPGA implementation.
