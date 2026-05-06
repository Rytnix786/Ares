from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ares.db import crud
from ares.models.audit_log import AuditLog


@pytest.mark.asyncio
async def test_purge_audit_logs_removes_old_rows_and_keeps_new_rows(db_session) -> None:
    old_timestamp = datetime.utcnow() - timedelta(days=120)
    new_timestamp = datetime.utcnow() - timedelta(days=5)

    db_session.add(
        AuditLog(
            request_id="old-request",
            user="old-user",
            endpoint="/api/v1/old",
            method="POST",
            payload_hash="old-hash",
            result="success",
            status_code=200,
            audit_metadata={},
            timestamp=old_timestamp,
        )
    )
    db_session.add(
        AuditLog(
            request_id="new-request",
            user="new-user",
            endpoint="/api/v1/new",
            method="POST",
            payload_hash="new-hash",
            result="success",
            status_code=200,
            audit_metadata={},
            timestamp=new_timestamp,
        )
    )
    await db_session.commit()

    deleted = await crud.purge_audit_logs(db_session, older_than=datetime.utcnow() - timedelta(days=90))
    await db_session.commit()

    remaining = await crud.list_audit_logs(db_session)

    assert deleted == 1
    assert [row.request_id for row in remaining] == ["new-request"]