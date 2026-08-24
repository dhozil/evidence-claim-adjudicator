<div align="center">

# Evidence Claim Adjudicator

**Decentralized, evidence-based claim adjudication — AI validators decide `supported` / `denied` / `inconclusive` with consensus.**

![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-6a4cff)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Status](https://img.shields.io/badge/status-live%20on%20studionet-2ea44f)
![Tests](https://img.shields.io/badge/tests-8%20passed-2ea44f)

[Live Contract](https://explorer-studio.genlayer.com/address/0xD276B031f1518821c4A9e2B6cDb0030016DDf77f) ·
[GenLayer Docs](https://docs.genlayer.com)

</div>

---

## Why

Many decisions depend on *evidence*: insurance claims, payment disputes, authenticity checks. Proof-of-judgment that lives entirely on-chain was impossible before GenLayer. This primitive binds claims to **committed evidence** and lets validator consensus produce a trusted verdict with reasoning.

## Live Deployment

| | |
|---|---|
| **Contract** | [EvidenceClaimAdjudicator](https://explorer-studio.genlayer.com/address/0xD276B031f1518821c4A9e2B6cDb0030016DDf77f) |
| **Address** | `0xD276B031f1518821c4A9e2B6cDb0030016DDf77f` |
| **Network** | GenLayer studionet (chain `61999`) |
| **Status** | ✅ deployed + audited on-chain |

## Highlights

- ⚖️ **Consensus verdict** — `supported` / `denied` / `inconclusive` with confidence, agreed by validators
- 🔗 **Evidence binding** — `sha256(content) == committed hash` verified at submission; reasoning must cite real evidence anchors
- 🧑⚖️ **Authenticated cases** — only the claimant adds evidence; only claimant/owner adjudicates
- 💰 **No locked funds** — deposit cancel before verdict; `withdraw_deposit` after finalize; appeal bonds always returnable
- 🤝 **Appeals that work** — bonded appeal, grounded overturn (validators verify the reason), reviewer bounty on uphold, timeout escape

## How It Works

```
submit_claim (payable deposit) ──► add_evidence (committed content hashes)
      │
      ▼
request_adjudication ──► adjudicate (claimant/owner; LLM consensus)
      │
      ├── supported ──────────── case won
      ├── denied ─────────────── case lost
      └── inconclusive ───────── retry / finalize
      │
      ▼        optional
appeal (bond) ──► review_appeal (overturn must be reason-grounded)
      │
      ▼
finalize_claim ──► withdraw_deposit
```

## Methods

| Role | Method | Guard |
|---|---|---|
| Claimant | `submit_claim` *(payable)*, `add_evidence`, `request_adjudication`, `cancel_claim`, `withdraw_deposit` | claimant-only |
| Claimant / Owner | `adjudicate` | claimant or owner |
| Challenger (any) | `appeal` *(payable, bonded)* | substantive reason + bond |
| Any | `review_appeal`, `finalize_claim` | bounded by timeouts |
| Any | `get_claim`, `get_claim_evidence`, `get_evidence`, `get_stats` | read-only |

## Security Model

- Evidence content binding `sha256(snapshot) == hash` at submission
- **Appeals are decided on evidence, not stored text**: the stored reasoning is kept for transparency but is **not** fed into the appeal review — appeal consensus judges the claim, the submitted evidence and the appeal argument directly
- Grounded reasoning: adjudication/appeal reasoning must reference submitted evidence anchors (URL or evidence id) - validated by consensus
- Strict status transitions - no double adjudication
- Bounded lifecycle - unreviewed appeals and inconclusive cases time out; no stranded deposits/bonds

## Deploy

```bash
genlayer deploy --contract contracts/evidence_claim_adjudicator.py
```

Constructor (optional):

```bash
genlayer deploy --contract contracts/evidence_claim_adjudicator.py \
    --args '{"adjudication_deposit": 1000000000000000000}'
```

## Test

```bash
pip install -r requirements.txt
pytest tests/
```