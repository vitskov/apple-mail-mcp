"""
AppleScript-based connector for Apple Mail.
"""

import json
import logging
import subprocess
from typing import Any

from .exceptions import (
    MailAccountNotFoundError,
    MailAppleScriptError,
    MailMailboxNotFoundError,
    MailMessageNotFoundError,
)
from .utils import escape_applescript_string, sanitize_input

logger = logging.getLogger(__name__)


class AppleMailConnector:
    """Interface to Apple Mail via AppleScript."""

    def __init__(self, timeout: int = 60) -> None:
        """
        Initialize the Mail connector.

        Args:
            timeout: Timeout in seconds for AppleScript operations
        """
        self.timeout = timeout

    def _run_applescript(self, script: str) -> str:
        """
        Execute AppleScript and return output.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string

        Raises:
            MailAppleScriptError: If script execution fails
            MailAccountNotFoundError: If account not found
            MailMailboxNotFoundError: If mailbox not found
            MailMessageNotFoundError: If message not found
        """
        try:
            logger.debug(f"Executing AppleScript: {script[:200]}...")

            result = subprocess.run(
                ["/usr/bin/osascript", "-"],
                input=script,
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"AppleScript error: {error_msg}")

                # Parse error and raise appropriate exception
                if "Can't get account" in error_msg:
                    raise MailAccountNotFoundError(error_msg)
                elif "Can't get mailbox" in error_msg:
                    raise MailMailboxNotFoundError(error_msg)
                elif "Can't get message" in error_msg:
                    raise MailMessageNotFoundError(error_msg)
                else:
                    raise MailAppleScriptError(error_msg)

            output = result.stdout.strip()
            logger.debug(f"AppleScript output: {output[:200]}...")
            return output

        except subprocess.TimeoutExpired:
            raise MailAppleScriptError(f"Script execution timeout after {self.timeout}s")
        except Exception as e:
            if isinstance(e, (MailAccountNotFoundError, MailMailboxNotFoundError,
                            MailMessageNotFoundError, MailAppleScriptError)):
                raise
            raise MailAppleScriptError(f"Unexpected error: {str(e)}")

    def list_accounts(self) -> list[dict[str, Any]]:
        """
        List all mail accounts.

        Returns:
            List of account dictionaries with name and email addresses
        """
        script = """
        tell application "Mail"
            set accountList to {}
            repeat with acc in accounts
                set accountInfo to {accountName:(name of acc), emailAddresses:(email addresses of acc)}
                set end of accountList to accountInfo
            end repeat

            -- Convert to JSON-like format
            set output to ""
            repeat with acc in accountList
                set output to output & "{name:'" & accountName of acc & "',emails:["
                repeat with addr in emailAddresses of acc
                    set output to output & "'" & addr & "',"
                end repeat
                set output to output & "]}|"
            end repeat

            return output
        end tell
        """

        result = self._run_applescript(script)

        # Parse the result
        accounts = []
        for account_str in result.split("|"):
            if not account_str:
                continue
            # Simple parsing - in production, use more robust parsing
            # For now, we'll return raw result and handle in tools
            accounts.append({"raw": account_str})

        return accounts

    def list_mailboxes(self, account: str) -> list[dict[str, Any]]:
        """
        List all mailboxes for an account.

        Args:
            account: Account name

        Returns:
            List of mailbox dictionaries

        Raises:
            MailAccountNotFoundError: If account doesn't exist
        """
        account_safe = escape_applescript_string(sanitize_input(account))

        script = f"""
        tell application "Mail"
            set accountRef to account "{account_safe}"
            set mailboxList to {{}}

            repeat with mb in mailboxes of accountRef
                set mbInfo to {{mbName:(name of mb), unreadCount:(unread count of mb)}}
                set end of mailboxList to mbInfo
            end repeat

            return mailboxList
        end tell
        """

        result = self._run_applescript(script)

        # TODO: Parse AppleScript records properly
        # For now return raw
        return [{"raw": result}]

    def search_messages(
        self,
        account: str,
        mailbox: str = "INBOX",
        sender_contains: str | None = None,
        subject_contains: str | None = None,
        read_status: bool | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for messages matching criteria.

        Args:
            account: Account name
            mailbox: Mailbox name
            sender_contains: Filter by sender
            subject_contains: Filter by subject
            read_status: Filter by read status (True=read, False=unread)
            limit: Maximum results

        Returns:
            List of message dictionaries

        Raises:
            MailAccountNotFoundError: If account doesn't exist
            MailMailboxNotFoundError: If mailbox doesn't exist
        """
        account_safe = escape_applescript_string(sanitize_input(account))
        mailbox_safe = escape_applescript_string(sanitize_input(mailbox))

        # Build whose clause
        conditions = []
        if sender_contains:
            sender_safe = escape_applescript_string(sanitize_input(sender_contains))
            conditions.append(f'sender contains "{sender_safe}"')

        if subject_contains:
            subject_safe = escape_applescript_string(sanitize_input(subject_contains))
            conditions.append(f'subject contains "{subject_safe}"')

        if read_status is not None:
            status = "true" if read_status else "false"
            conditions.append(f"read status is {status}")

        whose_clause = " and ".join(conditions) if conditions else "true"
        limit_clause = f"items 1 thru {limit} of" if limit else ""

        script = f"""
        tell application "Mail"
            set accountRef to account "{account_safe}"
            set mailboxRef to mailbox "{mailbox_safe}" of accountRef
            set matchedMessages to {limit_clause} (messages of mailboxRef whose {whose_clause})

            set resultList to {{}}
            repeat with msg in matchedMessages
                set msgId to id of msg as text
                set msgSubject to subject of msg
                set msgSender to sender of msg
                set msgDate to date received of msg as text
                set msgRead to read status of msg

                set msgData to msgId & "|" & msgSubject & "|" & msgSender & "|" & msgDate & "|" & msgRead
                set end of resultList to msgData
            end repeat

            -- Join with newlines
            set AppleScript's text item delimiters to linefeed
            set output to resultList as text
            set AppleScript's text item delimiters to ""

            return output
        end tell
        """

        result = self._run_applescript(script)

        # Parse results
        messages = []
        if result:
            for line in result.split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 5:
                    messages.append({
                        "id": parts[0],
                        "subject": parts[1],
                        "sender": parts[2],
                        "date_received": parts[3],
                        "read_status": parts[4].lower() == "true",
                    })

        return messages

    def get_message(self, message_id: str, include_content: bool = True) -> dict[str, Any]:
        """
        Get full message details.

        Args:
            message_id: Message ID
            include_content: Include message body

        Returns:
            Message dictionary

        Raises:
            MailMessageNotFoundError: If message doesn't exist
        """
        message_id_safe = escape_applescript_string(sanitize_input(message_id))

        # Note: Direct message ID lookup is tricky in AppleScript
        # We need to search through mailboxes
        # For now, we'll use a simplified approach

        content_clause = 'set msgContent to content of msg' if include_content else 'set msgContent to ""'

        script = f"""
        tell application "Mail"
            -- Search all accounts for message
            repeat with acc in accounts
                repeat with mb in mailboxes of acc
                    try
                        set msg to first message of mb whose id is {message_id_safe}

                        set msgId to id of msg as text
                        set msgSubject to subject of msg
                        set msgSender to sender of msg
                        set msgDate to date received of msg as text
                        set msgRead to read status of msg
                        set msgFlagged to flagged status of msg
                        {content_clause}

                        return msgId & "|" & msgSubject & "|" & msgSender & "|" & msgDate & "|" & msgRead & "|" & msgFlagged & "|" & msgContent
                    end try
                end repeat
            end repeat

            error "Message not found"
        end tell
        """

        result = self._run_applescript(script)

        # Parse result
        parts = result.split("|", 6)  # Max 7 parts
        if len(parts) >= 6:
            return {
                "id": parts[0],
                "subject": parts[1],
                "sender": parts[2],
                "date_received": parts[3],
                "read_status": parts[4].lower() == "true",
                "flagged": parts[5].lower() == "true",
                "content": parts[6] if len(parts) > 6 else "",
            }

        raise MailMessageNotFoundError(f"Could not parse message: {message_id}")

    def send_email(
        self,
        subject: str,
        body: str,
        to: list[str],
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> bool:
        """
        Send an email.

        Args:
            subject: Email subject
            body: Email body
            to: List of To recipients
            cc: List of CC recipients
            bcc: List of BCC recipients

        Returns:
            True if sent successfully

        Raises:
            MailAppleScriptError: If send fails
        """
        subject_safe = escape_applescript_string(sanitize_input(subject))
        body_safe = escape_applescript_string(sanitize_input(body))

        # Build recipient lists
        to_list = ", ".join(f'"{escape_applescript_string(addr)}"' for addr in to)
        cc_list = ", ".join(f'"{escape_applescript_string(addr)}"' for addr in (cc or []))
        bcc_list = ", ".join(f'"{escape_applescript_string(addr)}"' for addr in (bcc or []))

        script = f"""
        tell application "Mail"
            set theMessage to make new outgoing message with properties {{subject:"{subject_safe}", content:"{body_safe}", visible:false}}

            tell theMessage
                -- Add To recipients
                repeat with addr in {{{to_list}}}
                    make new to recipient with properties {{address:addr}}
                end repeat

                -- Add CC recipients
                repeat with addr in {{{cc_list}}}
                    make new cc recipient with properties {{address:addr}}
                end repeat

                -- Add BCC recipients
                repeat with addr in {{{bcc_list}}}
                    make new bcc recipient with properties {{address:addr}}
                end repeat

                send
            end tell

            return "sent"
        end tell
        """

        result = self._run_applescript(script)
        return result == "sent"

    def mark_as_read(self, message_ids: list[str], read: bool = True) -> int:
        """
        Mark messages as read or unread.

        Args:
            message_ids: List of message IDs
            read: True for read, False for unread

        Returns:
            Number of messages updated

        Raises:
            MailAppleScriptError: If operation fails
        """
        if not message_ids:
            return 0

        status = "true" if read else "false"

        # Build list of IDs
        id_list = ", ".join(message_ids)

        script = f"""
        tell application "Mail"
            set idList to {{{id_list}}}
            set updateCount to 0

            repeat with msgId in idList
                repeat with acc in accounts
                    repeat with mb in mailboxes of acc
                        try
                            set msg to first message of mb whose id is msgId
                            set read status of msg to {status}
                            set updateCount to updateCount + 1
                        end try
                    end repeat
                end repeat
            end repeat

            return updateCount
        end tell
        """

        result = self._run_applescript(script)
        return int(result) if result.isdigit() else 0
