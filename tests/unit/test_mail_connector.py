"""Unit tests for mail connector."""

from unittest.mock import MagicMock, patch

import pytest

from apple_mail_mcp.exceptions import (
    MailAccountNotFoundError,
    MailAppleScriptError,
    MailMailboxNotFoundError,
    MailMessageNotFoundError,
)
from apple_mail_mcp.mail_connector import AppleMailConnector


class TestAppleMailConnector:
    """Tests for AppleMailConnector."""

    @pytest.fixture
    def connector(self) -> AppleMailConnector:
        """Create a connector instance."""
        return AppleMailConnector(timeout=30)

    @patch("subprocess.run")
    def test_run_applescript_success(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test successful AppleScript execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="result",
            stderr=""
        )

        result = connector._run_applescript("test script")
        assert result == "result"

        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0] == ["/usr/bin/osascript", "-"]

    @patch("subprocess.run")
    def test_run_applescript_account_not_found(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test account not found error."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Can't get account \"NonExistent\""
        )

        with pytest.raises(MailAccountNotFoundError):
            connector._run_applescript("test script")

    @patch("subprocess.run")
    def test_run_applescript_mailbox_not_found(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test mailbox not found error."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Can't get mailbox \"NonExistent\""
        )

        with pytest.raises(MailMailboxNotFoundError):
            connector._run_applescript("test script")

    @patch("subprocess.run")
    def test_run_applescript_timeout(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        with pytest.raises(MailAppleScriptError, match="timeout"):
            connector._run_applescript("test script")

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_list_mailboxes(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test listing mailboxes."""
        mock_run.return_value = "mailbox data"

        result = connector.list_mailboxes("Gmail")
        assert len(result) > 0

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_basic(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test basic message search."""
        mock_run.return_value = "12345|Test Subject|sender@example.com|Mon Jan 1 2024|false"

        result = connector.search_messages("Gmail", "INBOX")

        assert len(result) == 1
        assert result[0]["id"] == "12345"
        assert result[0]["subject"] == "Test Subject"
        assert result[0]["sender"] == "sender@example.com"
        assert result[0]["read_status"] is False

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_with_filters(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test message search with filters."""
        mock_run.return_value = ""

        connector.search_messages(
            "Gmail",
            "INBOX",
            sender_contains="john@example.com",
            subject_contains="meeting",
            read_status=False,
            limit=10
        )

        # Verify the script includes filter conditions
        call_args = mock_run.call_args[0][0]
        assert 'sender contains "john@example.com"' in call_args
        assert 'subject contains "meeting"' in call_args
        assert "read status is false" in call_args
        assert "items 1 thru 10" in call_args

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_get_message(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test getting a message."""
        mock_run.return_value = "12345|Subject|sender@example.com|Mon Jan 1 2024|true|false|Message body"

        result = connector.get_message("12345", include_content=True)

        assert result["id"] == "12345"
        assert result["subject"] == "Subject"
        assert result["content"] == "Message body"
        assert result["read_status"] is True
        assert result["flagged"] is False

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_send_email_basic(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test sending a basic email."""
        mock_run.return_value = "sent"

        result = connector.send_email(
            subject="Test",
            body="Test body",
            to=["recipient@example.com"]
        )

        assert result is True

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_send_email_with_cc_bcc(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test sending email with CC and BCC."""
        mock_run.return_value = "sent"

        result = connector.send_email(
            subject="Test",
            body="Test body",
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )

        assert result is True

        # Verify script includes recipients
        call_args = mock_run.call_args[0][0]
        assert "recipient@example.com" in call_args
        assert "cc@example.com" in call_args
        assert "bcc@example.com" in call_args

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_mark_as_read(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test marking messages as read."""
        mock_run.return_value = "2"

        result = connector.mark_as_read(["12345", "12346"], read=True)

        assert result == 2

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_mark_as_unread(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Test marking messages as unread."""
        mock_run.return_value = "1"

        result = connector.mark_as_read(["12345"], read=False)

        assert result == 1

        # Verify script sets read status to false
        call_args = mock_run.call_args[0][0]
        assert "set read status of msg to false" in call_args

    def test_mark_as_read_empty_list(self, connector: AppleMailConnector) -> None:
        """Test marking with empty list."""
        result = connector.mark_as_read([])
        assert result == 0


class TestSearchMessagesExchangeFallback:
    """Tests for Exchange account fallback in search_messages."""

    @pytest.fixture
    def connector(self) -> AppleMailConnector:
        """Create a connector instance."""
        return AppleMailConnector(timeout=30)

    @pytest.fixture
    def direct_result(self) -> str:
        """Sample pipe-delimited result from _search_messages_direct."""
        return (
            "101|Meeting Notes|alice@exchange.com|Mon Jan 1 2024|true\n"
            "102|Project Update|bob@exchange.com|Tue Jan 2 2024|false\n"
            "103|Lunch Plans|carol@exchange.com|Wed Jan 3 2024|true"
        )

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_exchange_fallback(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Verify that when whose-based script raises Exchange error, fallback is used."""
        # First call (whose-based) fails with Exchange error
        # Second call (direct index-based) succeeds
        mock_run.side_effect = [
            MailAppleScriptError("Illegal comparison or logical (-1726)"),
            "101|Subject|sender@exchange.com|Mon Jan 1 2024|false",
        ]

        result = connector.search_messages("ExchangeAccount", "INBOX")

        assert len(result) == 1
        assert result[0]["id"] == "101"
        # Account should now be cached
        assert "ExchangeAccount" in connector._whose_unsupported_accounts
        # Two calls: first whose (failed), then direct
        assert mock_run.call_count == 2

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_exchange_fallback_cant_get_items(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Verify fallback triggers on 'Can't get items' whose error."""
        mock_run.side_effect = [
            MailAppleScriptError("Can't get items 1 thru 50 of messages whose true"),
            "101|Subject|sender@exchange.com|Mon Jan 1 2024|false",
        ]

        result = connector.search_messages("ExchangeAccount", "INBOX")

        assert len(result) == 1
        assert "ExchangeAccount" in connector._whose_unsupported_accounts

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_exchange_cached(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Verify second call skips directly to fallback (no whose attempt)."""
        # Pre-populate the cache
        connector._whose_unsupported_accounts.add("ExchangeAccount")

        mock_run.return_value = "101|Subject|sender@exchange.com|Mon Jan 1 2024|false"

        result = connector.search_messages("ExchangeAccount", "INBOX")

        assert len(result) == 1
        # Only one call — went straight to direct fetch
        assert mock_run.call_count == 1
        # Verify it used the direct script (no 'whose' clause)
        call_args = mock_run.call_args[0][0]
        assert "whose" not in call_args
        assert "messages 1 thru" in call_args

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_direct_filtering(
        self, mock_run: MagicMock, connector: AppleMailConnector, direct_result: str
    ) -> None:
        """Verify Python-side sender/subject/read_status filtering works."""
        connector._whose_unsupported_accounts.add("ExchangeAccount")
        mock_run.return_value = direct_result

        # Filter by sender
        result = connector.search_messages(
            "ExchangeAccount", "INBOX", sender_contains="alice"
        )
        assert len(result) == 1
        assert result[0]["sender"] == "alice@exchange.com"

        # Filter by subject
        mock_run.return_value = direct_result
        result = connector.search_messages(
            "ExchangeAccount", "INBOX", subject_contains="project"
        )
        assert len(result) == 1
        assert result[0]["subject"] == "Project Update"

        # Filter by read_status=False (unread only)
        mock_run.return_value = direct_result
        result = connector.search_messages(
            "ExchangeAccount", "INBOX", read_status=False
        )
        assert len(result) == 1
        assert result[0]["id"] == "102"

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_direct_limit(
        self, mock_run: MagicMock, connector: AppleMailConnector, direct_result: str
    ) -> None:
        """Verify limit is respected after filtering."""
        connector._whose_unsupported_accounts.add("ExchangeAccount")
        mock_run.return_value = direct_result

        # All 3 messages match (no filter), but limit=2
        result = connector.search_messages(
            "ExchangeAccount", "INBOX", limit=2
        )
        assert len(result) == 2

    @patch.object(AppleMailConnector, "_run_applescript")
    def test_search_messages_imap_no_fallback(
        self, mock_run: MagicMock, connector: AppleMailConnector
    ) -> None:
        """Verify IMAP accounts still use whose path without fallback."""
        mock_run.return_value = "12345|Test Subject|sender@gmail.com|Mon Jan 1 2024|false"

        result = connector.search_messages("Gmail", "INBOX")

        assert len(result) == 1
        # Only one call — whose-based succeeded
        assert mock_run.call_count == 1
        # Verify it used the whose-based script
        call_args = mock_run.call_args[0][0]
        assert "whose" in call_args
        # Gmail should NOT be in the unsupported set
        assert "Gmail" not in connector._whose_unsupported_accounts
