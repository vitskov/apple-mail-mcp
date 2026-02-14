"""Unit tests for server-side send confirmation behavior."""

from pathlib import Path
from typing import Any

import pytest

from apple_mail_mcp import server


class DummyMail:
    """Simple mail stub to assert call behavior."""

    def __init__(self, send_result: bool = True, attachment_result: bool = True) -> None:
        self.send_result = send_result
        self.attachment_result = attachment_result
        self.send_calls = 0
        self.attachment_calls = 0

    def send_email(
        self,
        subject: str,
        body: str,
        to: list[str],
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> bool:
        self.send_calls += 1
        return self.send_result

    def send_email_with_attachments(
        self,
        subject: str,
        body: str,
        to: list[str],
        attachments: list[Path],
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> bool:
        self.attachment_calls += 1
        return self.attachment_result


@pytest.fixture
def valid_send(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make recipient validation deterministic for tests."""
    monkeypatch.setattr(
        server,
        "validate_send_operation",
        lambda to, cc, bcc: (True, ""),
    )


def test_send_email_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    valid_send: None,
) -> None:
    """Send should fail closed without explicit confirmation."""
    dummy = DummyMail(send_result=True)
    monkeypatch.setattr(server, "mail", dummy)

    result = server.send_email.fn(
        subject="Test",
        body="Body",
        to=["recipient@example.com"],
    )

    assert result["success"] is False
    assert result["error_type"] == "confirmation_required"
    assert result["confirmation_required"] is True
    assert dummy.send_calls == 0


def test_send_email_confirmed_success(
    monkeypatch: pytest.MonkeyPatch,
    valid_send: None,
) -> None:
    """Confirmed send should call connector and return success."""
    dummy = DummyMail(send_result=True)
    monkeypatch.setattr(server, "mail", dummy)

    result = server.send_email.fn(
        subject="Test",
        body="Body",
        to=["recipient@example.com"],
        confirmed=True,
    )

    assert result["success"] is True
    assert dummy.send_calls == 1


def test_send_email_confirmed_false_result_is_error(
    monkeypatch: pytest.MonkeyPatch,
    valid_send: None,
) -> None:
    """Connector false return should map to send_error."""
    dummy = DummyMail(send_result=False)
    monkeypatch.setattr(server, "mail", dummy)

    result = server.send_email.fn(
        subject="Test",
        body="Body",
        to=["recipient@example.com"],
        confirmed=True,
    )

    assert result["success"] is False
    assert result["error_type"] == "send_error"
    assert dummy.send_calls == 1


def test_send_email_with_attachments_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    valid_send: None,
    tmp_path: Path,
) -> None:
    """Attachment send should fail closed without confirmation."""
    dummy = DummyMail(attachment_result=True)
    monkeypatch.setattr(server, "mail", dummy)
    attachment = tmp_path / "doc.txt"
    attachment.write_text("content")

    result = server.send_email_with_attachments.fn(
        subject="Test",
        body="Body",
        to=["recipient@example.com"],
        attachments=[str(attachment)],
    )

    assert result["success"] is False
    assert result["error_type"] == "confirmation_required"
    assert result["confirmation_required"] is True
    assert dummy.attachment_calls == 0


def test_send_email_with_attachments_false_result_is_error(
    monkeypatch: pytest.MonkeyPatch,
    valid_send: None,
    tmp_path: Path,
) -> None:
    """Connector false return should map to send_error for attachments."""
    dummy = DummyMail(attachment_result=False)
    monkeypatch.setattr(server, "mail", dummy)
    attachment = tmp_path / "doc.txt"
    attachment.write_text("content")

    result = server.send_email_with_attachments.fn(
        subject="Test",
        body="Body",
        to=["recipient@example.com"],
        attachments=[str(attachment)],
        confirmed=True,
    )

    assert result["success"] is False
    assert result["error_type"] == "send_error"
    assert dummy.attachment_calls == 1
