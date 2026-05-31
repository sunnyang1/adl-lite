"""
Integration tests for adl_lite.lark bridge using real lark-cli.

Requires: lark-cli installed and authenticated.
Safe: uses --dry-run where possible (no real docs/messages created).

Covers:
    - lark/client: find_lark_cli, run_lark_cli (auth_status, docs +create, im +messages-send)
    - lark/publish: publish_file dry_run (v1, v2, with title, nonexistent file)
    - lark/announce: announce dry_run
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite.lark.announce import announce
from adl_lite.lark.client import (
    LarkCliError,
    LarkCliNotFoundError,
    auth_status,
    find_lark_cli,
    run_lark_cli,
)
from adl_lite.lark.publish import (
    PublishResult,
    _relative_file_ref,
    publish_file,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
CAPITAL_TRAP = EXAMPLES_DIR / "capital_reflux_trap.md"

# ---------------------------------------------------------------------------
# Skip marker if lark-cli not available
# ---------------------------------------------------------------------------

lark_cli_available = True
try:
    find_lark_cli()
except LarkCliNotFoundError:
    lark_cli_available = False

requires_lark = pytest.mark.skipif(
    not lark_cli_available,
    reason="lark-cli not installed or authenticated",
)


# ===========================================================================
# lark/client.py
# ===========================================================================


@requires_lark
class TestClientIntegration:
    def test_auth_status(self):
        status = auth_status()
        assert isinstance(status, dict)
        assert "appId" in status or "identities" in status

    def test_docs_create_dry_run(self):
        """lark-cli docs +create --dry-run should not create a real doc."""
        content_ref = _relative_file_ref(CAPITAL_TRAP)
        payload = run_lark_cli(
            [
                "docs",
                "+create",
                "--api-version",
                "v2",
                "--doc-format",
                "markdown",
                "--content",
                content_ref,
                "--dry-run",
            ]
        )
        assert isinstance(payload, dict)

    def test_im_send_dry_run(self):
        """lark-cli im +messages-send --dry-run should not send a real message."""
        payload = run_lark_cli(
            [
                "im",
                "+messages-send",
                "--chat-id",
                "oc_fake_test",
                "--markdown",
                "Dry-run test message.",
                "--dry-run",
            ]
        )
        assert isinstance(payload, dict)

    def test_invalid_command_raises(self):
        with pytest.raises(LarkCliError):
            run_lark_cli(["nonexistent-command"])

    def test_nonexistent_path_raises(self):
        with pytest.raises(LarkCliNotFoundError):
            find_lark_cli("/nonexistent/lark-cli")


# ===========================================================================
# lark/publish.py
# ===========================================================================


@requires_lark
class TestPublishIntegration:
    def test_dry_run_v2(self):
        result = publish_file(CAPITAL_TRAP, dry_run=True)
        assert isinstance(result, PublishResult)
        assert result.dry_run is True
        assert result.adl_id == "disc-capital-trap"
        assert result.doc_id == "(dry-run)"

    def test_dry_run_with_title(self):
        result = publish_file(CAPITAL_TRAP, title="Custom Title", dry_run=True)
        assert result.title == "Custom Title"

    def test_dry_run_v1(self):
        result = publish_file(CAPITAL_TRAP, api_version="v1", dry_run=True)
        assert result.dry_run is True

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            publish_file("/nonexistent/file.md", dry_run=True)


# ===========================================================================
# lark/announce.py
# ===========================================================================


@requires_lark
class TestAnnounceIntegration:
    def test_dry_run(self):
        result = announce(
            str(CAPITAL_TRAP),
            chat_id="oc_fake_test_chat",
            dry_run=True,
        )
        assert result.adl_id == "disc-capital-trap"
        assert result.dry_run is True
        assert result.template == "discovery_broadcast"

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            announce("/nonexistent/file.md", chat_id="oc_test", dry_run=True)
