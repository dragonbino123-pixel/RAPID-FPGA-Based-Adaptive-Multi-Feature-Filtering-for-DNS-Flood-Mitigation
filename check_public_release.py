"""Validate the explicit public-file allowlist and reject common confidential source formats."""
from pathlib import Path
import argparse, re, subprocess

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-index', action='store_true', help='Inspect staged Git contents instead of a clean release directory')
    args = parser.parse_args()
    if args.git_index:
        names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        files = set(filter(None, names))
        def content(name):
            return subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
    else:
        files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts}
        def content(name):
            return (ROOT / name).read_bytes()
    allowed = set(content('PUBLIC_FILES.txt').decode().splitlines())
    assert all(p and not Path(p).is_absolute() and '..' not in Path(p).parts for p in allowed)
    assert files == allowed, f'Unexpected: {sorted(files-allowed)}; missing: {sorted(allowed-files)}'
    forbidden = {'.v', '.sv', '.vh', '.svh', '.vhd', '.vhdl', '.xdc', '.xpr', '.xci', '.dcp', '.bit',
                 '.ltx', '.edf', '.edif', '.bd', '.tcl', '.vcd', '.fst', '.tex', '.bib', '.bst', '.sty',
                 '.zip', '.gz', '.tar', '.bundle', '.pdf', '.png', '.jpg'}
    for name in sorted(files):
        assert Path(name).suffix.lower() not in forbidden, name
        assert not (ROOT / name).is_symlink(), name
        value = content(name).decode('utf-8')
        if name.endswith(('.py', '.cpp', '.cc', '.patch', '.sh')):
            assert not re.search(r'(?m)^\s*module\s+[A-Za-z_]\w*\s*(?:#|\()', value), name
        assert not re.search(r'github_pat_' + r'[A-Za-z0-9_]{30,}|ghp_' + r'[A-Za-z0-9]{30,}', value), name
    print(f'Public release check passed: {len(files)} explicitly allowed files; no excluded file types or detected tokens.')

if __name__ == '__main__':
    main()
