"""Check published counts and reproduce aggregation; this does not rerun RAPID."""
from pathlib import Path
import argparse, csv, json, math
import numpy as np
from generate_traffic import B, TEST, SEEDS, ATTACKS, CONTROLS

def analyze(result_dir):
    with (result_dir / 'test_metrics.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 750
    identifiers = set()
    for row in rows:
        row['seed'] = int(row['seed'])
        identity = (row['seed'], row['scenario'], row['method'])
        assert identity not in identifiers
        identifiers.add(identity)
        for key in ['attack_count', 'legitimate_count', 'attack_dropped', 'legitimate_dropped']:
            row[key] = int(row[key])
        for key in ['afr', 'fpr', 'residual_attack_qps', 'forwarded_qps']:
            row[key] = float(row[key]) if row[key] else None
        na, nl, ad, ld = (row[k] for k in ['attack_count', 'legitimate_count', 'attack_dropped', 'legitimate_dropped'])
        assert 0 <= ad <= na and 0 <= ld <= nl and nl > 0
        expected = dict(afr=100*ad/na if na else None, fpr=100*ld/nl,
                        residual_attack_qps=(na-ad)/TEST, forwarded_qps=(na-ad+nl-ld)/TEST)
        for key, value in expected.items():
            assert (value is None and row[key] is None) or (value is not None and math.isclose(value, row[key], abs_tol=1e-10)), (identity, key)
    with (result_dir / 'test_timeline.csv').open() as stream:
        timeline = list(csv.DictReader(stream))
    assert len(timeline) == 5400
    aliases = {'RTL_F1_F4': 'rtl_n4', 'RTL_F1_F5': 'rtl_F1_F5', 'DDiDD': 'DDiDD_0.1'}
    totals, seconds_seen = {}, set()
    for row in timeline:
        identity = (int(row['seed']), row['scenario'], aliases[row['method']])
        second_id = identity + (int(row['second']),)
        assert second_id not in seconds_seen and 0 <= second_id[-1] < TEST
        seconds_seen.add(second_id)
        totals.setdefault(identity, [0, 0, 0, 0])
        values = [int(row[k]) for k in ['attack', 'legitimate', 'attack_dropped', 'legitimate_dropped']]
        assert 0 <= values[2] <= values[0] and 0 <= values[3] <= values[1]
        totals[identity] = [a+b for a, b in zip(totals[identity], values)]
    by_id = {(r['seed'], r['scenario'], r['method']): r for r in rows}
    for identity, values in totals.items():
        row = by_id[identity]
        assert values == [row[k] for k in ['attack_count', 'legitimate_count', 'attack_dropped', 'legitimate_dropped']]
    methods = sorted({row['method'] for row in rows})
    def group(method, scenarios):
        values = [r for r in rows if r['method'] == method and r['scenario'] in scenarios]
        output = {}
        for key in ['afr', 'fpr', 'residual_attack_qps', 'forwarded_qps']:
            per_seed = [float(np.mean([r[key] for r in values if r['seed'] == seed and r[key] is not None]))
                        for seed in SEEDS if any(r['seed'] == seed and r[key] is not None for r in values)]
            if not per_seed:
                output[key] = None
            else:
                assert len(per_seed) == 5
                output[key] = dict(mean=float(np.mean(per_seed)),
                    ci95_half=float(2.776445105*np.std(per_seed, ddof=1)/math.sqrt(5)), seed_values=per_seed)
        return output
    primary = ['DDiDD_0.1', 'rtl_n4', 'rtl_F1_F5']
    summary = dict(
        main={m: group(m, ATTACKS) for m in methods if m in primary or m.startswith('rtl_without') or m.startswith('rtl_trigger')},
        cases={s: {m: group(m, [s]) for m in primary} for s in ATTACKS + CONTROLS},
        mixed={m: group(m, ['adaptive_mixed']) for m in methods if m.startswith('rtl_n') or m == 'rtl_learning_off'})
    published = json.loads((result_dir / 'summary.json').read_text())
    for section in ['main', 'cases', 'mixed']:
        assert summary[section] == published[section], section
    summary['public_verification'] = dict(metric_rows=len(rows), timeline_rows=len(timeline),
        published_aggregates_match=True, scope='Count consistency and aggregation only; private RAPID implementation not rerun.')
    return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=B / 'results')
    parser.add_argument('--output', type=Path, default=B / 'recomputed/summary.json')
    args = parser.parse_args()
    if args.output.resolve() == (args.results_dir / 'summary.json').resolve():
        parser.error('Output must differ from the published summary.')
    summary = analyze(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary['public_verification'], indent=2))

if __name__ == '__main__':
    main()
