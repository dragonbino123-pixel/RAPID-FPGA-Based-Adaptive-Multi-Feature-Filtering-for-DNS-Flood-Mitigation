# Public workload and evaluation protocol

## Synthetic legitimate queries

The observation point is a DNS service ingress. This is a query-arrival model, not a measured
operator trace or a client/cache/network simulation. Every event has unit weight.

- 320 consecutive resolver IPv4 addresses. For indices 0–159, source weight is `10 + i % 17`;
  other resolvers have weight 1. Weights are normalized before sampling.
- Each resolver receives one fixed IP-header TTL, selected from 43/44/49/50/51/55/56/57.
  IP-header TTL is distinct from DNS resource-record cache TTL.
- 180 seeded domains under com/net/org/edu, with rank probabilities proportional to rank^(-1.1).
- Prefix probabilities for www/api/cdn/mail/auth/ns/login are .60/.15/.10/.06/.04/.02/.03.
- For each second s, query count is Poisson with mean
  `50000 * (1 + 0.10 * sin(2*pi*(s+0.5)/120))`; timestamps are uniform within that second.
- A 300-second legitimate training prefix occupies [-300,0); each test occupies [0,30).
- Five pseudorandom seeds, 20260611–20260615, initialize independent repetitions. They are not dates.

Ordinary source paths and query vocabulary are consistent across training and testing.
All seven attacks for one seed reuse exactly the same legitimate events. Generator sampling
does not consult detector decisions, feature hashes, or target scores. The public generator's
sampling functions are unchanged from those used to produce the published experiment inputs.

## Attack scenarios

| Scenario identifier | Attack workload |
| --- | --- |
| `fixed_qname_flood` | 200k queries/s to three fixed names; one fifth use distinct new sources |
| `random_subdomain_flood` | 200k queries/s with random labels under victim-zone.invalid; one quarter use distinct new sources |
| `spoofed_source_flood` | 200k queries/s; two thirds use new sources, the remainder use known sources with TTL offsets; random names |
| `compromised_resolver_burst` | 200k queries/s from 18 known resolvers, with random names |
| `ttl_consistent_evasion` | 90k queries/s from the least-active 160 known resolvers, preserving source TTLs, with random names |
| `low_rate_distributed` | 200k queries/s, each from a distinct new source, with random names |
| `adaptive_mixed` | Four components at 40k queries/s each plus an 8k component, combining fixed names, new sources, TTL changes, concentrated sources, and random queries |

Five legitimate-only controls are reported separately: unchanged ordinary traffic; 1.2% of queries
from four new fixed-TTL resolvers; 1% with a new left label; a persistent +1 TTL change for resolver
index 100 at t=15 s; and an independent 50% legitimate demand increase. These controls are not
averaged into the attack-comparison FPR.

## DDiDD baseline

The baseline uses the authors' official DDiDD 0.1 archive, pinned by the SHA-256 recorded in
`results/upstream_manifest.json`. The adapter preserves its filtering and deployment logic,
changes event transport to a label-free text stream, records decisions, fixes const correctness,
and initializes otherwise uninitialized training-record fields. All edits are shown in
`ddidd_adapter/upstream.patch`; generated upstream sources are not bundled.

The configuration is T=0.5, n=9, capacity=100k queries/s, default FQ settings, the original
five-standard-deviation WR bound, and a fixed IANA TLD snapshot. Training statistics include
all complete integer-aligned 1–256-second windows, including zero counts. The 300-second
prefix covers all nine windows but is shorter than the DDiDD paper's recommended training durations.
Comparisons therefore describe this tested configuration, not every possible baseline tuning.

Runtime initialization replays the legitimate prefix once and forks one child per test case.
Each child starts from the same prefix state; test cases do not share adapted test state.
The serializer omits attack/legitimate labels. Binary fields are timestamp (float64), IPv4 (uint32),
IP TTL (uint8), and query name (48 bytes), packed to 61 bytes per query on little-endian hosts.

## Results and reproducibility boundary

The published results contain 750 per-run metric rows and 5,400 per-second count rows. AFR is
100 times dropped attack queries divided by attack queries. FPR is 100 times dropped legitimate
queries divided by legitimate queries. Residual attack rate and total forwarded rate divide their
respective remaining counts by 30 seconds. AFR is undefined for benign-only controls.

Aggregate means give each scenario equal weight within a seed, then each seed equal weight.
95% intervals use the five seed means and t critical value 2.776445105. `analyze_results.py`
recomputes these statistics and checks that timeline totals agree with the published counts.
The `verification` object in the original `summary.json` records checks from the original private
experiment; it is not a claim that those private implementation checks can be rerun here.

RAPID's FPGA sources and their simulation/validation infrastructure are confidential and excluded.
Consequently, this release can regenerate workload inputs, execute DDiDD, and reproduce result
aggregation. It cannot regenerate RAPID decisions or independently verify its hardware throughput.
The published hardware throughput measurement and synthetic selectivity runs are distinct experiments.
