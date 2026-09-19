"""Local artifact manifests and change planning. Never connects to a server."""
import fnmatch
import hashlib
import re
from pathlib import Path, PurePosixPath

DEFAULT_EXCLUDES = ['.git/**','.codex/**','.agents/**','.env','.env.*','**/.env','**/.env.*',
                    'node_modules/**','__pycache__/**','**/__pycache__/**','.venv/**']


def manifest(root, excludes=()):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Artifact root must be a directory')
    files, skipped = {}, []
    import os
    for directory, dirs, names in os.walk(root, followlinks=False):
        # Prune excluded directories to avoid reading huge dependency trees.
        kept = []
        for name in dirs:
            p = Path(directory) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or root not in p.resolve().parents or any(fnmatch.fnmatchcase(rel+'/', pat) or fnmatch.fnmatchcase(rel+'/x', pat)
                                     for pat in DEFAULT_EXCLUDES + list(excludes)):
                skipped.append(rel)
            else:
                kept.append(name)
        dirs[:] = kept
        for name in names:
            p = Path(directory) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or root not in p.resolve().parents or any(fnmatch.fnmatchcase(rel, pat) for pat in DEFAULT_EXCLUDES + list(excludes)):
                skipped.append(rel)
                continue
            h = hashlib.sha256()
            before = p.stat()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024), b''):
                    h.update(chunk)
            after = p.stat()
            if before.st_mtime_ns != after.st_mtime_ns or before.st_size != after.st_size:
                raise ValueError('Artifact changed while hashing; create a stable build before planning deployment')
            files[rel] = {'sha256':h.hexdigest(),'bytes':after.st_size}
    return {'schema_version':1, 'kind':'local-artifact', 'files':files, 'excluded_count':len(skipped),
            'note':'Manifest only. It is not evidence of remote state, a backup, or deployment authorization.'}


def plan(before, after, remote_verified=False):
    for m in (before,after):
        if m.get('schema_version') != 1 or not isinstance(m.get('files'),dict):
            raise ValueError('Unsupported manifest')
        for name,v in m['files'].items():
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe manifest path')
            if not isinstance(v,dict) or not isinstance(v.get('sha256'),str) or not re.fullmatch('[0-9a-fA-F]{64}',v['sha256']):
                raise ValueError('Invalid file digest')
            if isinstance(v.get('bytes'),bool) or not isinstance(v.get('bytes'),int) or v['bytes'] < 0:
                raise ValueError('Invalid file size')
    old, new = before['files'],after['files']
    changed = sorted(k for k,v in new.items() if old.get(k,{}).get('sha256') != v['sha256'])
    removed = sorted(set(old)-set(new))
    return {'upload_candidates':changed,'remote_delete_candidates':removed,
            'unchanged_files':len(new)-len(changed), 'candidate_upload_bytes':sum(new[k]['bytes'] for k in changed),
            'remote_state_verified_by_user':bool(remote_verified),
            'ready_to_execute':False,
            'requirements':['Validate remote identity and manifest provenance; local Git state alone does not prove remote equality.',
                            'Protect uploads, database contents, secrets and other server-only state.',
                            'Review deletion candidates separately; never automatically mirror-delete persistent data.',
                            'Determine recovery coverage and protocol capabilities; verify the deployed application afterward.']}
