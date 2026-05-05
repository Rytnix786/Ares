from __future__ import annotations

import pytest

from ares.db import crud
from ares.exceptions import PromotionError


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
async def test_rollback_champion_dry_run_and_commit(db_session, sample_run, sample_run_2):
    first = await crud.promote_champion(
        db_session,
        sample_run.model_name,
        sample_run.id,
        "tester",
        "initial promotion",
    )
    second = await crud.promote_champion(
        db_session,
        sample_run.model_name,
        sample_run_2.id,
        "tester",
        "second promotion",
    )

    dry_run = await crud.rollback_champion(
        db_session,
        sample_run.model_name,
        rolled_back_by="operator",
        reason="incident validation",
        dry_run=True,
    )

    assert dry_run["dry_run"] is True
    assert dry_run["from_champion"].id == second.id
    assert dry_run["to_run_id"] == first.champion_run_id

    committed = await crud.rollback_champion(
        db_session,
        sample_run.model_name,
        rolled_back_by="operator",
        reason="bad promotion",
    )

    active = await crud.get_active_champion(db_session, sample_run.model_name)
    assert active is not None
    assert active.champion_run_id == sample_run.id
    assert committed["champion"].action == "rollback"
    assert committed["champion"].rolled_back_from_id == second.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rollback_champion_validates_reason_and_target(db_session, sample_run, sample_run_2):
    await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester")

    with pytest.raises(PromotionError, match="rollback reason is required"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason=" ",
        )

    with pytest.raises(PromotionError, match="target evaluation run not found"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="missing target",
            target_run_id="missing-run",
        )

    with pytest.raises(PromotionError, match="target run belongs to a different model"):
        sample_run_2.model_name = "other-model"
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="wrong model",
            target_run_id=sample_run_2.id,
        )


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
