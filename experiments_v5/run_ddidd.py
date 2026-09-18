"""Run DDiDD on generated inputs; write new results separately from published data."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess
import numpy as np
from generate_traffic import B, DATA, SEEDS, SCENARIOS, TEST, CAPACITY, metrics, writecsv

def run_seed(seed, scenarios, data_root, output_root, keep_text=False):
    data = (data_root / str(seed)).resolve()
    out = (output_root / str(seed)).resolve()
    required = [data / name for name in ['training.bin', 'manifest.json', 'wr.train', 'hcf.train', 'fq.train']]
    required += [data / sc / name for sc in scenarios for name in ['events.bin', 'events.npz', 'manifest.json']]
    for path in required + [B / 'ddidd_adapter/ddidd', B / 'ddidd_adapter/transport']:
        if not path.is_file():
            raise FileNotFoundError(f'{path}: generate inputs and build DDiDD first')
    out.mkdir(parents=True, exist_ok=True)
    transport = B / 'ddidd_adapter/transport'
    def convert(source, target):
        subprocess.run([str(transport), str(source), str(target)], check=True)
    convert(data / 'training.bin', out / 'training.txt')
    batch_rows = []
    for sc in scenarios:
        case = out / sc
        case.mkdir(exist_ok=True)
        convert(data / sc / 'events.bin', case / 'queries.txt')
        batch_rows.append('\t'.join(str(case / n) for n in ['queries.txt', 'decisions.bytes', 'ddidd.log']))
    batch = out / 'batch.tsv'
    batch.write_text('\n'.join(batch_rows) + '\n')
    env = os.environ.copy()
    env['DDIDD_DECISIONS'] = str(out / 'training.bytes')
    env['DDIDD_BATCH_FILE'] = str(batch)
    command = [str(B / 'ddidd_adapter/ddidd'), '-r', str(out / 'training.txt'), '-s', '10000',
               '-m', str(TEST), '-b', '0', '-l', str(CAPACITY), '-w', str(data / 'wr.train'),
               '-H', str(data / 'hcf.train'), '-u', str(data / 'hcf.train'), '-F', str(data / 'fq.train'),
               '-T', '0.5', '-n', '9']
    with (out / 'training.log').open('w') as log:
        subprocess.run(command, cwd=B / 'ddidd_adapter', env=env, stdout=log, stderr=log, check=True)
    expected_training = json.loads((data / 'manifest.json').read_text())['training_count']
    assert (out / 'training.bytes').stat().st_size == expected_training
    rows, timeline = [], []
    for sc in scenarios:
        case = out / sc
        events = np.load(data / sc / 'events.npz')['events']
        manifest = json.loads((data / sc / 'manifest.json').read_text())
        assert len(events) == manifest['event_count']
        assert hashlib.sha256(events.tobytes()).hexdigest() == manifest['event_sha256']
        raw = np.fromfile(case / 'decisions.bytes', dtype='u1')
        assert len(raw) == len(events) and np.all(raw <= 1)
        drop = raw != 0
        rows.append(dict(seed=seed, scenario=sc, method='DDiDD_0.1', **metrics(events, drop)))
        for second in range(TEST):
            inside = (events['t'] >= second) & (events['t'] < second + 1)
            attack = inside & events['attack']
            legitimate = inside & ~events['attack']
            timeline.append(dict(seed=seed, scenario=sc, method='DDiDD', second=second,
                attack=int(attack.sum()), legitimate=int(legitimate.sum()),
                attack_dropped=int((attack & drop).sum()), legitimate_dropped=int((legitimate & drop).sum())))
        np.savez_compressed(case / 'decisions.npz', ddidd=raw)
        (case / 'decisions.bytes').unlink()
        if not keep_text:
            (case / 'queries.txt').unlink()
    writecsv(out / 'metrics.csv', rows)
    writecsv(out / 'timeline.csv', timeline)
    (out / 'run.json').write_text(json.dumps(dict(seed=seed, scenarios=scenarios, command=command,
        training_replayed_once_then_forked=True, training_count=expected_training), indent=2) + '\n')
    (out / 'training.bytes').unlink()
    if not keep_text:
        (out / 'training.txt').unlink()
    return rows, timeline

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, nargs='+', default=SEEDS)
    parser.add_argument('--scenarios', nargs='+', choices=SCENARIOS, default=SCENARIOS)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    parser.add_argument('--output-dir', type=Path, default=B / 'recomputed/ddidd')
    parser.add_argument('--keep-text', action='store_true')
    args = parser.parse_args()
    published = (B / 'results').resolve()
    if args.output_dir.resolve() == published or published in args.output_dir.resolve().parents:
        parser.error('Use a separate output directory; published result files are read-only inputs.')
    rows, timeline = [], []
    for seed in args.seeds:
        one, seconds = run_seed(seed, args.scenarios, args.data_dir, args.output_dir, args.keep_text)
        rows.extend(one)
        timeline.extend(seconds)
        print('DDiDD complete:', seed, flush=True)
    writecsv(args.output_dir / 'test_metrics.csv', rows)
    writecsv(args.output_dir / 'test_timeline.csv', timeline)

if __name__ == '__main__':
    main()
