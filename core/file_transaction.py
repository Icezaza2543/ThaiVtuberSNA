"""Recoverable file-set transactions for explicitly synthetic local sandboxes.

A durable undo image precedes writes. The COMMITTED marker is the decision point:
recovery restores the before image without it and keeps the after image with it.
Readers/writers must recover under the same advisory lock before opening files.
This is process-crash recovery, not a promise about hardware power-loss durability.
"""
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.writing')
    with tmp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


@contextmanager
def exclusive_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


class FileTransaction:
    def __init__(self, root, journal):
        self.root = Path(root).resolve()
        self.journal = Path(journal).resolve()
        if not self.journal.is_relative_to(self.root):
            raise ValueError('Journal must be inside transaction root')

    def target(self, rel):
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root) or p.is_relative_to(self.journal):
            raise ValueError('Invalid transaction target')
        return p

    def prepare(self, paths):
        if (self.journal / 'undo.json').exists():
            raise RuntimeError('Unrecovered transaction')
        self.journal.mkdir(parents=True, exist_ok=True)
        entries = {}
        for i, path in enumerate(sorted(set(map(Path, paths)))):
            rel = path.resolve().relative_to(self.root).as_posix()
            p = self.target(rel)
            name = str(i) if p.is_file() else None
            if name is not None:
                atomic_bytes(self.journal / name, p.read_bytes())
            entries[rel] = name
        atomic_bytes(self.journal / 'undo.json', json.dumps(entries, sort_keys=True).encode())

    def commit(self):
        atomic_bytes(self.journal / 'COMMITTED', b'1')

    def restore(self):
        entries = json.loads((self.journal / 'undo.json').read_text())
        for rel, name in entries.items():
            p = self.target(rel)
            if name is None:
                p.unlink(missing_ok=True)
            else:
                atomic_bytes(p, (self.journal / name).read_bytes())

    def recover(self):
        if (self.journal / 'undo.json').exists() and not (self.journal / 'COMMITTED').exists():
            self.restore()
        self.cleanup()

    def cleanup(self):
        if self.journal.exists():
            shutil.rmtree(self.journal)
