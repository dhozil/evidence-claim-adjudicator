# Submission: Evidence Claim Adjudicator

## Category
Intelligent Contracts

## Contract Name
Evidence Claim Adjudicator

## Summary
A reusable GenLayer primitive for evidence-based claim evaluation. Enables decentralized adjudication where AI validators independently assess whether submitted evidence supports, denies, or is inconclusive for a given claim.

## What Makes This Unique
- **Multi-source evidence pattern**: Structured evidence submission with content hashing
- **Confidence-quantified verdicts**: Not just binary yes/no, but graduated certainty
- **Consensus-stable adjudication**: Custom validator ensures agreement on verdicts despite LLM non-determinism
- **Built-in appeal mechanism**: Challenge bonds and appeal windows for dispute resolution
- **Reusable primitive**: Foundation for insurance, disputes, verification, and any evidence-based decision system

## How Consensus Is Used
The contract uses `gl.vm.run_nondet_unsafe()` with a custom validator function. The validator independently re-runs the adjudication and compares:
- Verdict must match exactly (supported/denied/inconclusive)
- Confidence must be within 0.15 tolerance
- Reasoning is preserved for transparency

## Technical Details
- Python-based GenLayer Intelligent Contract
- Uses `gl.nondet.exec_prompt()` for LLM evaluation
- Custom validator for consensus stability
- TreeMap for scalable state management
- Appeal bonds and time-bounded windows

## Use Case
Insurance claims, dispute resolution, content verification, freelancer assessment - any scenario where a claim needs to be evaluated against evidence with AI-powered judgment.

## Live Deployment
[To be deployed on Bradbury Testnet]

## Source Code
See `contracts/evidence_claim_adjudicator.py`
