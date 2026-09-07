"""Conformance regression guard against the official KoSIT XRechnung test suite.

Runs every positive reference instance from ``itplr-kosit/xrechnung-testsuite``
(vendored under ``specs/xrechnung/testsuite/``, Apache-2.0) through the package's
local ``XRECHNUNG`` Schematron chain (CEN EN 16931 base + XRechnung CIUS overlay)
and asserts it validates clean.

Why this exists: the suite caught two real defects in the previously bundled
rules — (1) the XRechnung CII path borrowed the FeRD Factur-X ``en16931_cii``
stylesheet, which rejects the XRechnung BT-24 profile URN and so failed *every*
XRechnung CII invoice (``FX-SCH-A-000556``); and (2) the EN 16931 base ruleset
(v2026-01-31) had drifted out of sync with the XRechnung CIUS overlay (v2.6.0).
Both were fixed by sourcing the whole set from the version-matched
``validator-configuration-xrechnung`` v2026-08-31 release and pointing the
XRECHNUNG CII chain at the genuine CEN CII base (``en16931_cii_cen``).

Scope: the suite's ``extension`` and ``cvd`` instances are *different* XRechnung
profiles (BT-24 ``…:extension:xrechnung_3.0`` / ``…:xrechnung:cvd_0.9``) that
KoSIT validates under their own scenarios with a different ruleset. This package
targets standard XRechnung 3.0 CIUS, so those instances are marked ``xfail`` —
they are kept in the corpus for completeness, not asserted against.

Requires the optional ``[xslt2]`` extra (Saxon-HE); skipped otherwise.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from mcp_einvoicing_de.tools.invoice_validate import _validate_local
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax

_SAXON_AVAILABLE = importlib.util.find_spec("saxonche") is not None

_TESTSUITE_DIR = Path(__file__).parent.parent / "specs" / "xrechnung" / "testsuite" / "test"

# BT-24 profiles KoSIT validates under a separate scenario / ruleset that this
# package does not implement. Instances under these directories are kept in the
# vendored corpus but not asserted against (xfail, non-strict).
_OUT_OF_PROFILE_DIRS = frozenset({"extension", "cvd"})


def _collect_instances() -> list:
    """Return pytest params for every vendored reference instance."""
    params = []
    for path in sorted(_TESTSUITE_DIR.rglob("*.xml")):
        rel = path.relative_to(_TESTSUITE_DIR)
        out_of_profile = _OUT_OF_PROFILE_DIRS.intersection(part.lower() for part in rel.parts)
        marks = (
            [
                pytest.mark.xfail(
                    reason=(
                        f"{'/'.join(sorted(out_of_profile))} is a separate XRechnung "
                        "profile (own KoSIT scenario/ruleset); package targets standard "
                        "XRechnung 3.0 CIUS"
                    ),
                    strict=False,
                )
            ]
            if out_of_profile
            else []
        )
        params.append(pytest.param(path, id=str(rel), marks=marks))
    return params


_INSTANCES = _collect_instances()


def test_corpus_is_present() -> None:
    """Guard against a silently-empty vendored corpus (path drift)."""
    assert len(_INSTANCES) >= 80, (
        f"Expected the full KoSIT XRechnung test corpus under {_TESTSUITE_DIR}, "
        f"found {len(_INSTANCES)} instances"
    )


@pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
@pytest.mark.parametrize("instance_path", _INSTANCES)
def test_official_instance_validates_clean(instance_path: Path) -> None:
    """Each official positive XRechnung instance must pass the XRECHNUNG chain."""
    xml_bytes = instance_path.read_bytes()
    syntax = detect_invoice_syntax(xml_bytes).value

    result = asyncio.run(_validate_local(xml_bytes, "XRECHNUNG", syntax))

    if not result.is_valid:
        detail = "; ".join(
            f"[{getattr(e, 'source', '?')}] {e.rule_id}: {e.text[:80]}" for e in result.errors
        )
        pytest.fail(f"{instance_path.name} ({syntax}) failed validation: {detail}")
