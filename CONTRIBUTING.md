# Contributing to Apple Mail MCP

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

## Code of Conduct

This project follows a simple code of conduct:

- Be respectful and considerate
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Prioritize the project's goals and user needs

## Getting Started

### Prerequisites

- macOS 10.15 or later
- Python 3.10 or later
- Apple Mail configured with at least one account
- Git and GitHub account

### Setup Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/apple-mail-mcp.git
   cd apple-mail-mcp
   ```

3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/s-morgan-jeffries/apple-mail-mcp.git
   ```

4. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install with dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

6. **Verify setup:**
   ```bash
   pytest tests/unit/ -v
   ```

## Development Process

### Test-Driven Development (TDD)

This project uses TDD. Please follow this process:

1. **Write tests first** (RED phase)
   ```python
   def test_new_feature():
       result = new_feature()
       assert result == expected
   ```

2. **Implement minimal code** to pass tests (GREEN phase)
   ```python
   def new_feature():
       return expected
   ```

3. **Refactor** for quality (REFACTOR phase)
   ```python
   def new_feature():
       # Improved implementation
       return calculate_result()
   ```

### Branch Naming

Use descriptive branch names:

- `feature/attachment-support` - New features
- `fix/gmail-label-bug` - Bug fixes
- `docs/api-examples` - Documentation
- `test/integration-coverage` - Test improvements
- `refactor/mail-connector` - Code refactoring

### Commit Messages

Follow this format:

```
Type: Brief description (max 50 chars)

Detailed explanation of what and why (not how).
Wrap at 72 characters.

- Bullet points for multiple changes
- Reference issues: Fixes #123

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Maintenance tasks

### Before Committing

Run these checks:

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/unit/ -v

# Check coverage
pytest --cov

# Run code review (optional but recommended)
python .github/scripts/code_review_agent.py
```

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow TDD process
- Write tests first
- Implement feature
- Update documentation

### 3. Test Thoroughly

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (if applicable)
pytest tests/integration/ -v --run-integration

# Coverage check
pytest --cov --cov-report=html
```

### 4. Run Code Quality Checks

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type check
mypy src/

# Code review
python .github/scripts/code_review_agent.py --min-score 70
```

### 5. Update Documentation

Update relevant documentation:
- [ ] README.md (if user-facing changes)
- [ ] docs/TOOLS.md (if new tools added)
- [ ] docs/SETUP.md (if setup changes)
- [ ] Docstrings (for all new functions)

### 6. Commit Changes

```bash
git add .
git commit -m "feat: Add attachment support

Implements send_email_with_attachments tool.
Includes validation, error handling, and tests.

Fixes #42"
```

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Link to related issues
- Screenshots/examples if applicable
- Checklist completed

### 8. Respond to Feedback

- Address review comments
- Update code and tests
- Push additional commits
- Request re-review when ready

## Coding Standards

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints for all functions
- Write docstrings for public functions

### Example Function

```python
def search_messages(
    account: str,
    mailbox: str = "INBOX",
    sender_contains: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Search for messages matching criteria.

    Args:
        account: Account name (e.g., "Gmail", "iCloud")
        mailbox: Mailbox name (default: "INBOX")
        sender_contains: Filter by sender email or domain
        limit: Maximum results to return

    Returns:
        List of message dictionaries

    Raises:
        MailAccountNotFoundError: If account doesn't exist
        MailMailboxNotFoundError: If mailbox doesn't exist

    Example:
        >>> messages = search_messages("Gmail", sender_contains="john@example.com")
        >>> len(messages)
        5
    """
    # Implementation
    pass
```

### Security Considerations

Always:
- Validate and sanitize inputs
- Escape strings for AppleScript
- Check email address formats
- Limit bulk operations
- Log sensitive operations
- Handle errors gracefully

```python
# Good
subject_safe = escape_applescript_string(sanitize_input(subject))
script = f'set subject to "{subject_safe}"'

# Bad
script = f'set subject to "{subject}"'  # Injection risk!
```

## Testing Requirements

### Test Coverage

- Minimum 80% overall coverage
- Minimum 70% per file
- All new features must have tests
- All bug fixes must have regression tests

### Test Structure

```python
class TestNewFeature:
    """Tests for new_feature."""

    @pytest.fixture
    def setup_data(self) -> dict:
        """Create test data."""
        return {"key": "value"}

    def test_basic_functionality(self, setup_data: dict) -> None:
        """Test basic feature works."""
        result = new_feature(setup_data)
        assert result["success"] is True

    def test_error_handling(self) -> None:
        """Test error conditions."""
        with pytest.raises(ValueError):
            new_feature(invalid_input)

    @patch("module.external_call")
    def test_with_mock(self, mock_call: MagicMock) -> None:
        """Test with mocked dependencies."""
        mock_call.return_value = "mocked"
        result = new_feature()
        assert mock_call.called
```

### Integration Tests

For features that interact with Mail.app:

```python
@pytest.mark.skipif(
    "not config.getoption('--run-integration')",
    reason="Integration tests disabled"
)
def test_real_mail_operation() -> None:
    """Test with real Mail.app."""
    # Test implementation
    pass
```

## Documentation

### User-Facing Changes

Update these files for user-facing changes:

1. **README.md** - Main features and examples
2. **docs/TOOLS.md** - Tool API reference
3. **docs/SETUP.md** - Setup instructions
4. **docs/SECURITY.md** - Security implications

### Code Documentation

- Add docstrings to all public functions
- Include type hints
- Provide examples in docstrings
- Document exceptions raised

### Changelog

Update CHANGELOG.md (create if needed):

```markdown
## [Unreleased]

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description
```

## Release Process

Only maintainers can release, but here's the process:

1. **Update version** in `pyproject.toml` and `src/apple_mail_mcp/__init__.py`
2. **Update CHANGELOG.md** with release notes
3. **Run code review** with appropriate score threshold
4. **Create git tag:** `git tag -a v0.2.0 -m "Release v0.2.0"`
5. **Push tag:** `git push origin v0.2.0`
6. **Create GitHub release** with changelog
7. **Publish to PyPI** (when ready)

## Questions?

- **General questions:** [GitHub Discussions](https://github.com/s-morgan-jeffries/apple-mail-mcp/discussions)
- **Bug reports:** [GitHub Issues](https://github.com/s-morgan-jeffries/apple-mail-mcp/issues)
- **Security issues:** See [SECURITY.md](docs/SECURITY.md)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md (create if needed)
- Mentioned in release notes
- Appreciated in project documentation

Thank you for contributing! 🎉
