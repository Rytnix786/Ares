from __future__ import annotations

import pytest

from ares.db import crud


@pytest.mark.integration
@pytest.mark.asyncio
async def test_crud_round_trip(db_session, sample_run):
    fetched = await crud.get_evaluation_run(db_session, sample_run.id)
    assert fetched is not None
    assert fetched.id == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_promote_and_export_champion(db_session, sample_run):
    champion = await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester", "integration")
    assert champion.is_active is True
    exported = await crud.export_champions(db_session)
    assert exported["champions"][0]["champion_run_id"] == sample_run.id
    history = await crud.list_champion_history(db_session, sample_run.model_name)
    assert history[0].champion_run_id == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_drift_report(db_session):
    report = await crud.create_drift_report(
        db_session,
        model_name="default-model",
        feature="confidence",
        kl_divergence=0.2,
        psi=0.3,
        is_alerting=True,
        severity="warning",
        payload={"source": "test"},
    )
    reports = await crud.list_drift_reports(db_session, model_name="default-model")
    assert reports[0].id == report.id