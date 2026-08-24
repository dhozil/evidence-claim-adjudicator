"""Direct-mode tests for the EvidenceClaimAdjudicator contract.

Covers: deposit-gated submission, evidence committed with a content hash,
evidence binding (tampered hash rejected), claimant/owner-only adjudication,
appeal bond flow with grounded overturn reasoning, finalize timeout, and the
claimant's deposit recovery paths (cancel + withdraw) so no funds are locked.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta

from gltest.direct import create_address

DEPOSIT = 1000000000000000000  # 1 token
BOND = 2 * DEPOSIT

EV_URL = "https://evidence.example.com/ledger"
EV_BODY = "The ledger shows the payment was received on record A."
EV_HASH = hashlib.sha256(EV_BODY.encode("utf-8")).hexdigest()

VERDICT_JSON = json.dumps(
    {
        "verdict": "supported",
        "confidence": 90,
        "reasoning": "The evidence ev0 (https://evidence.example.com/ledger) confirms the payment was received.",
    }
)


def _warp_days(vm, days):
    raw = vm._datetime.replace("Z", "").replace("+00:00", "")
    base = datetime.fromisoformat(raw)
    vm.warp((base + timedelta(days=days)).isoformat())


def _submit(contract, vm, claimant):
    vm.sender = claimant
    vm.value = DEPOSIT
    return contract.submit_claim(
        title="Payment received?",
        description="Was the invoice paid?",
        claim_text="The payment was received on record A.",
        criteria="Evidence must confirm the payment on the ledger.",
    )


def _add_evidence(contract, vm, claimant, cid):
    vm.sender = claimant
    return contract.add_evidence(
        claim_id=cid,
        url=EV_URL,
        content_hash=EV_HASH,
        content_snapshot=EV_BODY,
        description="Public ledger entry.",
    )


def test_submit_claim_requires_deposit(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")

    direct_vm.sender = claimant
    direct_vm.value = 0
    with direct_vm.expect_revert("Insufficient adjudication deposit"):
        contract.submit_claim("T", "D", "C", "criteria")


def test_add_evidence_binds_content_hash(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    cid = _submit(contract, direct_vm, claimant)

    # Tampered snapshot must be rejected (analysis is bound to committed content).
    direct_vm.sender = claimant
    with direct_vm.expect_revert("does not match the committed content"):
        contract.add_evidence(cid, EV_URL, EV_HASH, "A DIFFERENT content!", "desc")

    direct_vm.sender = claimant
    with direct_vm.expect_revert("64-char sha256"):
        contract.add_evidence(cid, EV_URL, "bogus", EV_BODY, "desc")

    eid = _add_evidence(contract, direct_vm, claimant, cid)
    assert eid is not None
    assert contract.get_evidence(eid)["verified"] is True


def test_add_evidence_claimant_only(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    other = create_address("other")
    cid = _submit(contract, direct_vm, claimant)

    direct_vm.sender = other
    with direct_vm.expect_revert("Only claimant"):
        contract.add_evidence(cid, EV_URL, EV_HASH, EV_BODY, "desc")


def test_adjudicate_only_claimant_or_owner(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    other = create_address("other")
    cid = _submit(contract, direct_vm, claimant)
    _add_evidence(contract, direct_vm, claimant, cid)

    direct_vm.sender = claimant
    contract.request_adjudication(cid)

    # A stranger cannot force adjudication.
    direct_vm.sender = other
    with direct_vm.expect_revert("Only the claimant or the owner"):
        contract.adjudicate(cid)

    direct_vm.mock_llm(re.escape("evidence-based claim adjudicator"), VERDICT_JSON)
    direct_vm.sender = claimant
    result = contract.adjudicate(cid)
    assert result["verdict"] == "supported"
    assert result["status"] == "verdict_rendered"


def test_cancel_before_verdict_refunds_deposit(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    other = create_address("other")
    cid = _submit(contract, direct_vm, claimant)

    direct_vm.sender = other
    with direct_vm.expect_revert("Only claimant"):
        contract.cancel_claim(cid)

    direct_vm.sender = claimant
    contract.cancel_claim(cid)
    claim = contract.get_claim(cid)
    assert claim["finalized"] is True
    assert claim["status"] == "finalized"


def test_withdraw_deposit_after_finalize(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    cid = _submit(contract, direct_vm, claimant)
    _add_evidence(contract, direct_vm, claimant, cid)

    direct_vm.sender = claimant
    contract.request_adjudication(cid)
    direct_vm.mock_llm(re.escape("evidence-based claim adjudicator"), VERDICT_JSON)
    verdict = contract.adjudicate(cid)
    assert verdict["status"] == "verdict_rendered"

    # cannot withdraw before finalize
    direct_vm.sender = claimant
    with direct_vm.expect_revert("not finalized"):
        contract.withdraw_deposit(cid)

    # warp past the appeal window and finalize
    _warp_days(direct_vm, 10)
    contract.finalize_claim(cid)
    contract.withdraw_deposit(cid)
    with direct_vm.expect_revert("already refunded"):
        contract.withdraw_deposit(cid)


def test_appeal_overturn_returns_bond(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    challenger = create_address("challenger")
    cid = _submit(contract, direct_vm, claimant)
    _add_evidence(contract, direct_vm, claimant, cid)

    direct_vm.sender = claimant
    contract.request_adjudication(cid)
    direct_vm.mock_llm(re.escape("evidence-based claim adjudicator"), VERDICT_JSON)
    contract.adjudicate(cid)

    # challenger appeals with a substantive factual argument
    direct_vm.sender = challenger
    direct_vm.value = BOND
    contract.appeal(cid, "Record A was not on the ledger; verify via public record.")

    # review overturns: reasoning must be grounded in an evidence anchor
    overturn = json.dumps(
        {
            "action": "overturned",
            "new_verdict": "denied",
            "confidence": 85,
            "reasoning": "Evidence ev0 (https://evidence.example.com/ledger) does not show the payment.",
        }
    )
    direct_vm.mock_llm(re.escape("appellate evidence adjudicator"), overturn)
    direct_vm.sender = challenger
    result = contract.review_appeal(cid)
    assert result["appeal_outcome"] == "overturned"
    assert result["verdict"] == "denied"
    assert result["finalized"] is True


def test_unreviewed_appeal_times_out(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/evidence_claim_adjudicator.py")
    claimant = create_address("claimant")
    challenger = create_address("challenger")
    cid = _submit(contract, direct_vm, claimant)
    _add_evidence(contract, direct_vm, claimant, cid)

    direct_vm.sender = claimant
    contract.request_adjudication(cid)
    direct_vm.mock_llm(re.escape("evidence-based claim adjudicator"), VERDICT_JSON)
    contract.adjudicate(cid)

    direct_vm.sender = challenger
    direct_vm.value = BOND
    contract.appeal(cid, "The source document is inconsistent with the verdict.")

    # cannot finalize while the appeal review window is open
    direct_vm.sender = claimant
    with direct_vm.expect_revert("review window still open"):
        contract.finalize_claim(cid)

    # warp well past both appeal and review windows -> finalize, bond returned
    _warp_days(direct_vm, 40)
    contract.finalize_claim(cid)
    claim = contract.get_claim(cid)
    assert claim["appeal_outcome"] == "upheld_by_timeout"
    assert claim["finalized"] is True
    contract.withdraw_deposit(cid)