"""Before images for complete synthetic observatory updates and exact rollback."""
import json
import uuid
from pathlib import Path
from core.file_transaction import FileTransaction, atomic_bytes


def managed_files(root):
    root = Path(root)
    files = []
    for directory in (root / 'data/temporal', root / 'web/research'):
        for p in directory.rglob('*'):
            if not p.is_file() or any(part.startswith('.') for part in p.relative_to(directory).parts):
                continue
            if p.name == 'run_ledger.json' or p.suffix in ('.tmp', '.writing'):
                continue
            files.append(p)
    for relative in ('web/app.js', 'web/data/temporal_communities.json'):
        if (root / relative).exists():
            files.append(root / relative)
    return files


class ObservatoryGeneration:
    def __init__(self, root, identifier=None):
        self.root = Path(root).resolve()
        self.identifier = identifier or uuid.uuid4().hex
        if not self.identifier.isalnum():
            raise ValueError('Invalid generation identifier')
        self.tx = FileTransaction(root, self.root / '.observatory_generations' / self.identifier)
        self.pending = self.root / '.observatory_pending.json'

    def prepare(self):
        self.tx.prepare(managed_files(self.root))
        atomic_bytes(self.pending, json.dumps({'generation':self.identifier}).encode())

    def restore(self, clear_pending=True):
        before = json.loads((self.tx.journal / 'undo.json').read_text())
        for path in managed_files(self.root):
            if path.relative_to(self.root).as_posix() not in before:
                path.unlink()
        self.tx.restore()
        if clear_pending:
            self.pending.unlink(missing_ok=True)

    def commit(self):
        self.tx.commit()
        self.pending.unlink(missing_ok=True)

    @classmethod
    def recover(cls, root):
        pending = Path(root) / '.observatory_pending.json'
        if pending.exists():
            generation = cls(root, json.loads(pending.read_text())['generation'])
            if not (generation.tx.journal / 'COMMITTED').exists():
                generation.restore()
            pending.unlink(missing_ok=True)
