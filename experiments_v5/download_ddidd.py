"""Fetch the exact official DDiDD release used by RAPID's comparison."""
from pathlib import Path
import argparse, hashlib, json, shutil, urllib.request

def main():
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / 'results/upstream_manifest.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-file', type=Path, help='Use an existing official archive instead of downloading')
    args = parser.parse_args()
    target = base / 'vendor/ddidd-0.1.tar.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if target.exists():
        if digest(target) != manifest['sha256']:
            raise SystemExit('Existing DDiDD archive does not match the recorded release hash.')
        print('Verified existing DDiDD 0.1 archive.')
        return
    temporary = target.with_suffix('.gz.part')
    try:
        if args.from_file:
            shutil.copyfile(args.from_file, temporary)
        else:
            with urllib.request.urlopen(manifest['url'], timeout=60) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
        if digest(temporary) != manifest['sha256']:
            raise SystemExit('DDiDD archive hash mismatch; the expected version was not obtained.')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print('DDiDD 0.1 archive downloaded/copied and SHA-256 verified.')

if __name__ == '__main__':
    main()
