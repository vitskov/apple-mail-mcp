"""
FastMCP server for Apple Mail integration.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from .exceptions import (
    MailAccountNotFoundError,
    MailAppleScriptError,
    MailMailboxNotFoundError,
    MailMessageNotFoundError,
)
from .mail_connector import AppleMailConnector
from .security import (
    operation_logger,
    require_confirmation,
    validate_bulk_operation,
    validate_send_operation,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("apple-mail")

# Initialize mail connector
mail = AppleMailConnector()


@mcp.tool()
def list_mailboxes(account: str) -> dict[str, Any]:
    """
    List all mailboxes for an account.

    Args:
        account: Account name (e.g., "Gmail", "iCloud")

    Returns:
        Dictionary containing mailboxes list

    Example:
        >>> list_mailboxes("Gmail")
        {"mailboxes": [{"name": "INBOX", "unread_count": 5}, ...]}
    """
    try:
        logger.info(f"Listing mailboxes for account: {account}")

        mailboxes = mail.list_mailboxes(account)

        operation_logger.log_operation(
            "list_mailboxes",
            {"account": account},
            "success"
        )

        return {
            "success": True,
            "account": account,
            "mailboxes": mailboxes,
        }

    except MailAccountNotFoundError as e:
        logger.error(f"Account not found: {e}")
        return {
            "success": False,
            "error": f"Account '{account}' not found",
            "error_type": "account_not_found",
        }
    except Exception as e:
        logger.error(f"Error listing mailboxes: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown",
        }


@mcp.tool()
def search_messages(
    account: str,
    mailbox: str = "INBOX",
    sender_contains: str | None = None,
    subject_contains: str | None = None,
    read_status: bool | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Search for messages matching criteria.

    Args:
        account: Account name (e.g., "Gmail", "iCloud")
        mailbox: Mailbox name (default: "INBOX")
        sender_contains: Filter by sender email/domain
        subject_contains: Filter by subject keywords
        read_status: Filter by read status (true=read, false=unread)
        limit: Maximum results to return (default: 50)

    Returns:
        Dictionary containing matching messages

    Example:
        >>> search_messages("Gmail", sender_contains="john@example.com", read_status=False, limit=10)
        {"success": True, "messages": [...], "count": 5}
    """
    try:
        logger.info(
            f"Searching messages in {account}/{mailbox} with filters: "
            f"sender={sender_contains}, subject={subject_contains}, read={read_status}"
        )

        messages = mail.search_messages(
            account=account,
            mailbox=mailbox,
            sender_contains=sender_contains,
            subject_contains=subject_contains,
            read_status=read_status,
            limit=limit,
        )

        operation_logger.log_operation(
            "search_messages",
            {
                "account": account,
                "mailbox": mailbox,
                "filters": {
                    "sender": sender_contains,
                    "subject": subject_contains,
                    "read_status": read_status,
                },
            },
            "success"
        )

        return {
            "success": True,
            "account": account,
            "mailbox": mailbox,
            "messages": messages,
            "count": len(messages),
        }

    except (MailAccountNotFoundError, MailMailboxNotFoundError) as e:
        logger.error(f"Not found error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "not_found",
        }
    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown",
        }


@mcp.tool()
def get_message(message_id: str, include_content: bool = True) -> dict[str, Any]:
    """
    Get full details of a specific message.

    Args:
        message_id: Message ID from search results
        include_content: Include message body (default: true)

    Returns:
        Dictionary containing message details

    Example:
        >>> get_message("12345")
        {"success": True, "message": {...}}
    """
    try:
        logger.info(f"Getting message: {message_id}")

        message = mail.get_message(message_id, include_content=include_content)

        operation_logger.log_operation(
            "get_message",
            {"message_id": message_id},
            "success"
        )

        return {
            "success": True,
            "message": message,
        }

    except MailMessageNotFoundError as e:
        logger.error(f"Message not found: {e}")
        return {
            "success": False,
            "error": f"Message '{message_id}' not found",
            "error_type": "message_not_found",
        }
    except Exception as e:
        logger.error(f"Error getting message: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown",
        }


@mcp.tool()
def send_email(
    subject: str,
    body: str,
    to: list[str],
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    """
    Send an email via Apple Mail.

    IMPORTANT: This operation requires user confirmation before sending.

    Args:
        subject: Email subject
        body: Email body (plain text)
        to: List of recipient email addresses
        cc: List of CC recipients (optional)
        bcc: List of BCC recipients (optional)

    Returns:
        Dictionary indicating success or failure

    Example:
        >>> send_email(
        ...     subject="Meeting Follow-up",
        ...     body="Thanks for the great meeting!",
        ...     to=["alice@example.com"],
        ...     cc=["bob@example.com"]
        ... )
        {"success": True, "message": "Email sent successfully"}
    """
    try:
        # Validate operation
        is_valid, error_msg = validate_send_operation(to, cc, bcc)
        if not is_valid:
            logger.error(f"Validation failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "validation_error",
            }

        # Require confirmation
        confirmation_details = {
            "subject": subject,
            "to": to,
            "cc": cc or [],
            "bcc": bcc or [],
            "body_preview": body[:100] + "..." if len(body) > 100 else body,
        }

        logger.info(f"Requesting confirmation to send email: {subject}")
        logger.info(f"Recipients: {to}, CC: {cc}, BCC: {bcc}")

        # In production, this should actually block and wait for user confirmation
        # For now, we'll proceed but log the confirmation requirement
        if not require_confirmation("send_email", confirmation_details):
            operation_logger.log_operation(
                "send_email",
                confirmation_details,
                "cancelled"
            )
            return {
                "success": False,
                "error": "User cancelled operation",
                "error_type": "cancelled",
            }

        # Send the email
        result = mail.send_email(
            subject=subject,
            body=body,
            to=to,
            cc=cc,
            bcc=bcc,
        )

        operation_logger.log_operation(
            "send_email",
            {"subject": subject, "to": to, "cc": cc, "bcc": bcc},
            "success"
        )

        return {
            "success": True,
            "message": "Email sent successfully",
            "details": {
                "subject": subject,
                "recipients": len(to) + len(cc or []) + len(bcc or []),
            },
        }

    except MailAppleScriptError as e:
        logger.error(f"Error sending email: {e}")
        operation_logger.log_operation(
            "send_email",
            {"subject": subject},
            "failure"
        )
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}",
            "error_type": "send_error",
        }
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown",
        }


@mcp.tool()
def mark_as_read(message_ids: list[str], read: bool = True) -> dict[str, Any]:
    """
    Mark messages as read or unread.

    Args:
        message_ids: List of message IDs to update
        read: True to mark as read, False to mark as unread (default: true)

    Returns:
        Dictionary indicating success and number of messages updated

    Example:
        >>> mark_as_read(["12345", "12346"], read=True)
        {"success": True, "updated": 2}
    """
    try:
        # Validate bulk operation
        is_valid, error_msg = validate_bulk_operation(len(message_ids), max_items=100)
        if not is_valid:
            logger.error(f"Validation failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "validation_error",
            }

        logger.info(f"Marking {len(message_ids)} messages as {'read' if read else 'unread'}")

        count = mail.mark_as_read(message_ids, read=read)

        operation_logger.log_operation(
            "mark_as_read",
            {"count": len(message_ids), "read": read},
            "success"
        )

        return {
            "success": True,
            "updated": count,
            "requested": len(message_ids),
        }

    except Exception as e:
        logger.error(f"Error marking messages: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "unknown",
        }


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Apple Mail MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
