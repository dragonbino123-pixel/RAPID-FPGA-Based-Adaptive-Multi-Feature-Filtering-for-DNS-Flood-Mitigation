# Published result files

These are unchanged outputs from the experiment used in the paper, not newly generated results.

- `results/test_metrics.csv`: seed, scenario, method, attack/legitimate query counts and rejected counts,
  AFR and FPR (percent), residual attack rate and total forwarded rate (queries per second).
- `results/test_timeline.csv`: per-second attack/legitimate query counts and rejected counts for the
  main RAPID configuration, optional F5 configuration, and DDiDD.
- `results/summary.json`: per-scenario, aggregate, component, and parameter statistics; mean,
  95% interval half-width, and the five seed values. Historical private-run verification metadata
  is retained for provenance, not offered as a publicly executable test.
- `results/upstream_manifest.json`: official DDiDD archive URL, SHA-256, and adapter patch path.

Original method identifiers are preserved: `rtl_n4` is the main RAPID configuration;
`rtl_F1_F5` includes the optional fifth component; `rtl_without_F*` and `rtl_trigger_F*`
identify component analyses; `rtl_n*` and `rtl_learning_off` identify the parameter/learning
analyses; `rtl_unarmed` is the inactive control; `DDiDD_0.1` is the external baseline.
No private implementation is encoded by these labels or distributed with these data files.

Run `python3 experiments_v5/analyze_results.py` from the root for numerical checks.
New baseline runs write to `recomputed/ddidd/` and do not replace published results.
