"""Integration tests for Alembic migrations."""

from __future__ import annotations

import pytest
from alembic.config import Config

from alembic import command


@pytest.fixture
def setup_alembic(tmp_path):
    test_db_url = f"sqlite+aiosqlite:///{(tmp_path / 'migration_test.db').as_posix()}"
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text(
        f"""[alembic]
script_location = {('alembic')}
sqlalchemy.url = {test_db_url}
"""
    )
    return alembic_ini


def test_add_mlflow_error_category_up_down(setup_alembic):
    config = Config(str(setup_alembic))
    command.upgrade(config, "0003_add_api_keys_table")
    command.upgrade(config, "0004_add_mlflow_error_category")
    command.downgrade(config, "0003_add_api_keys_table")


def test_add_webhooks_table_up_down(setup_alembic):
    config = Config(str(setup_alembic))
    command.upgrade(config, "0005_add_webhooks_table")
    command.downgrade(config, "0004_add_mlflow_error_category")


@pytest.mark.integration
class TestMigrations:
    """Test that migrations can be applied and rolled back."""

    @pytest.fixture(autouse=True)
    def setup_alembic(self, tmp_path):
        """Setup Alembic configuration for testing."""
        test_db_url = f"sqlite+aiosqlite:///{(tmp_path / 'migration_test.db').as_posix()}"
        
        # Create minimal alembic.ini
        alembic_ini = tmp_path / "alembic.ini"
        alembic_ini.write_text(
            f"""[alembic]
script_location = {('alembic')}
sqlalchemy.url = {test_db_url}
"""
        )
        
        return alembic_ini

    def test_migration_up_down_cycle(self, setup_alembic):
        """Test that migrations can be applied and rolled back."""
        config = Config(str(setup_alembic))
        
        # Get current version
        command.current(config, verbose=True)
        
        # Upgrade to head
        command.upgrade(config, "head")
        
        command.current(config, verbose=True)
        
        # Rollback to base
        command.downgrade(config, "base")
        
        command.downgrade(config, "base")
        
        # Upgrade back to head
        command.upgrade(config, "head")
        
        command.current(config, verbose=True)

    def test_migration_history_consistency(self, setup_alembic):
        """Test that migration history is consistent."""
        config = Config(str(setup_alembic))
        
        # Get history
        command.history(config, verbose=True)

        command.upgrade(config, "head")
        
        # Should not raise any errors
        command.check(config)

    def test_migration_idempotency(self, setup_alembic):
        """Test that applying the same migration twice is idempotent."""
        config = Config(str(setup_alembic))
        
        # Upgrade to head
        command.upgrade(config, "head")
        
        # Try to upgrade again (should be no-op)
        command.upgrade(config, "head")
        
        command.current(config, verbose=True)
