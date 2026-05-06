"""Alert delivery and dispatch service."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.models import AlertEvent
from ares.notifier.slack import send_slack_message
from ares.notifier.webhook import send_webhook

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Dispatches alerts through configured channels with deduplication."""

    def __init__(self, slack_webhook_url: str | None = None, webhook_url: str | None = None):
        """Initialize alert dispatcher.
        
        Args:
            slack_webhook_url: Optional Slack webhook URL for notifications
        """
        self.slack_webhook_url = slack_webhook_url
        self.webhook_url = webhook_url
        self.logger = logger

    async def dispatch_alert(
        self,
        db_session: AsyncSession,
        alert: AlertEvent,
        channels: list[str] | None = None,
    ) -> dict:
        """Dispatch an alert through configured channels with deduplication.
        
        Args:
            db_session: Database session
            alert: AlertEvent to dispatch
            channels: List of channels to send to (default: ['webhook', 'slack'])
            
        Returns:
            dict with 'status', 'channels_sent', 'errors' if any
        """
        channels = channels or ["webhook"]
        result: dict[str, object] = {
            "status": "pending",
            "alert_id": alert.id,
            "channels_sent": [],
            "errors": [],
        }
        channels_sent: list[str] = []
        errors: list[str] = []

        # Check for duplicate alert (deduplication)
        if await self._is_duplicate(db_session, alert):
            self.logger.info(
                f"Alert {alert.id} is duplicate of recent alert, skipping dispatch"
            )
            result["status"] = "deduplicated"
            return result

        try:
            for channel in channels:
                try:
                    if channel == "slack" and self.slack_webhook_url:
                        await self._send_slack(alert)
                        channels_sent.append("slack")
                    elif channel == "webhook":
                        await self._send_webhook(alert)
                        channels_sent.append("webhook")
                except Exception as e:
                    error_msg = f"Error sending to {channel}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

            result["channels_sent"] = channels_sent
            result["errors"] = errors
            result["status"] = "dispatched" if channels_sent else "failed"
            return result

        except Exception as e:
            self.logger.error(f"Error dispatching alert {alert.id}: {e}", exc_info=True)
            result["status"] = "failed"
            errors.append(str(e))
            result["errors"] = errors
            return result

    async def _is_duplicate(
        self, db_session: AsyncSession, alert: AlertEvent, window_minutes: int = 60
    ) -> bool:
        """Check if similar alert was sent recently.
        
        Uses content hash and time window for deduplication.
        """
        try:
            # Generate alert hash for content-based deduplication
            alert_hash = self._generate_alert_hash(alert)
            cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)

            stmt = (
                select(AlertEvent)
                .where(AlertEvent.event_type == alert.event_type)
                .where(AlertEvent.model_name == alert.model_name)
                .where(AlertEvent.severity == alert.severity)
                .where(AlertEvent.created_at >= cutoff_time)
                .where(AlertEvent.id != alert.id)
                .order_by(AlertEvent.created_at.desc())
                .limit(1)
            )
            result = await db_session.execute(stmt)
            recent = result.scalar_one_or_none()

            if recent:
                recent_hash = self._generate_alert_hash(recent)
                return alert_hash == recent_hash

            return False
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return False

    @staticmethod
    def _generate_alert_hash(alert: AlertEvent) -> str:
        """Generate content hash for deduplication."""
        content = f"{alert.event_type}:{alert.model_name}:{alert.severity}:{alert.message}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _send_slack(self, alert: AlertEvent) -> None:
        """Send alert to Slack."""
        if not self.slack_webhook_url:
            raise ValueError("Slack webhook URL not configured")

        message = f"🚨 ARES Alert: {alert.event_type} | {alert.model_name} | {alert.severity.upper()} | {alert.message}"
        await send_slack_message(self.slack_webhook_url, message)
        logger.info(f"Alert {alert.id} sent to Slack")

    async def _send_webhook(self, alert: AlertEvent) -> None:
        """Send alert via webhook."""
        if not self.webhook_url:
            return
        payload = {
            "alert_id": alert.id,
            "event_type": alert.event_type,
            "model_name": alert.model_name,
            "severity": alert.severity,
            "status": alert.status,
            "message": alert.message,
            "source": alert.source,
            "payload": alert.payload,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }

        await send_webhook(self.webhook_url, payload)
        logger.info(f"Alert {alert.id} sent via webhook")


class AlertRuleEngine:
    """Evaluates conditions to trigger alerts."""

    def __init__(self) -> None:
        """Initialize alert rule engine."""
        self.logger = logger

    async def check_drift_threshold(
        self,
        db_session: AsyncSession,
        model_name: str,
        drift_metric: str,
        value: float,
        threshold: float,
    ) -> AlertEvent | None:
        """Check if drift metric exceeds threshold and create alert if needed.
        
        Args:
            db_session: Database session
            model_name: Model name
            drift_metric: Metric name (e.g., 'psi', 'kl_divergence')
            value: Current metric value
            threshold: Alert threshold
            
        Returns:
            AlertEvent if threshold exceeded, None otherwise
        """
        if value > threshold:
            alert = AlertEvent(
                event_type="drift_threshold_breach",
                model_name=model_name,
                severity="high",
                status="open",
                source="drift_monitor",
                message=f"Drift metric {drift_metric} exceeded threshold: {value:.4f} > {threshold:.4f}",
                payload={
                    "metric": drift_metric,
                    "value": value,
                    "threshold": threshold,
                    "model_name": model_name,
                },
            )
            db_session.add(alert)
            await db_session.flush()
            self.logger.warning(
                f"Drift alert created for {model_name}: {drift_metric}={value:.4f}"
            )
            return alert

        return None

    async def check_evaluation_failure(
        self, db_session: AsyncSession, model_name: str, error: str
    ) -> AlertEvent:
        """Create alert for evaluation failure.
        
        Args:
            db_session: Database session
            model_name: Model name
            error: Error message
            
        Returns:
            Created AlertEvent
        """
        alert = AlertEvent(
            event_type="evaluation_failed",
            model_name=model_name,
            severity="critical",
            status="open",
            source="evaluator",
            message=f"Evaluation failed for {model_name}: {error}",
            payload={"model_name": model_name, "error": error},
        )
        db_session.add(alert)
        await db_session.flush()
        self.logger.error(f"Evaluation failure alert created for {model_name}")
        return alert
