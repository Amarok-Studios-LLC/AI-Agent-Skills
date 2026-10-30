#!/usr/bin/env python3
"""Install an individual skill globally; optional integration is explicit."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    skills_root=Path(__file__).resolve().parent/'skills'
    available=sorted(d.name for d in skills_root.iterdir() if d.is_dir() and not d.is_symlink() and (d/'SKILL.md').is_file())
    p.add_argument('--skill',choices=available,default='codex-token-steward')
    p.add_argument('--codex-home',type=Path,default=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex')))
    p.add_argument('--integrate',action='store_true',help='Explicitly enable the selected skill global instructions/integration')
    p.add_argument('--upgrade',action='store_true',help='Replace a previously installed copy of this skill')
    a=p.parse_args()
    source=skills_root/a.skill
    destination=a.codex_home.expanduser().resolve()/'skills'/a.skill
    if destination.is_symlink():
        p.error('Refusing to overwrite a symlink; inspect the installation manually')
    files=[f for f in source.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc']
    if destination.exists():
        marker=destination/'SKILL.md'
        if not marker.exists() or 'name: '+a.skill not in marker.read_text(encoding='utf-8'):
            p.error('Existing directory is not an identified installation of this skill')
        same=all((destination/f.relative_to(source)).is_file() and
                 hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256((destination/f.relative_to(source)).read_bytes()).digest()
                 for f in files)
        if not same and not a.upgrade:
            p.error('Different installation already exists; review changes and use --upgrade if intended')
    for f in files:
        out=destination/f.relative_to(source)
        if out.is_symlink() or destination not in out.resolve().parents:
            p.error('Unsafe destination path; refusing to follow a symlink outside the skill')
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(f,out)
    print('Installed: '+str(destination))
    if a.integrate:
        entrypoints={'codex-token-steward':'steward.py','software-engineering-toolkit':'toolkit.py'}
        if a.skill not in entrypoints:
            p.error('This skill has no global integration; plain installation is available')
        subprocess.run([sys.executable,str(destination/'scripts'/entrypoints[a.skill]),'--codex-home',str(a.codex_home.resolve()),'install-integration'],check=True)
    print('Available on the next turn. Start a new task to load changed global instructions/configuration.')
    return 0


if __name__=='__main__':
    sys.exit(main())
