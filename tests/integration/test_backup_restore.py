from __future__ import annotations

from scripts.backup import create_backup
from scripts.restore import validate_backup


def test_backup_restore_manifest(tmp_path) -> None:
    backup = create_backup(str(tmp_path / "backup.json"))
    assert validate_backup(str(backup))["version"] == 1
