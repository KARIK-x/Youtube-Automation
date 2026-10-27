# Contributing to Shorts Studio

Thanks for your interest! Here's how to get started.

## Development setup

```bash
git clone https://github.com/KARIK-x/Youtube-Automation.git
cd Youtube-Automation
bash setup.sh
```

## Running tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

## Code style

- Python: follow PEP 8. Use type hints where practical.
- Keep functions focused and testable.
- Add tests for new features.

## Pull requests

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run the full test suite
5. Submit a PR with a clear description

## Safety rules (non-negotiable)

- Never commit secrets (OAuth tokens, API keys)
- Never upload/publish/schedule YouTube content from tests
- Never modify `~/yt-auto`
- Keep publishing in dry-run mode by default
- Never delete or overwrite existing outputs
- Never use unlicensed assets for production

## Reporting issues

Open an issue on GitHub with:
- What you expected
- What happened
- Steps to reproduce
- Your OS and Python version (`shorts check-deps` output)