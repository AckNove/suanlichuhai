> Status: DRAFT v1.0 (2026-11-16). Not for external distribution until CEO approval.
> **Sample template. All figures are hypothetical and do not represent any real supplier quotation.**
> Use: shows clients how we structure a procurement proposal; internal reference for drafting one.
> Internal ID 08

# Sample Procurement Proposal (Hypothetical Case)

## 0. How to read this document

- The client, suppliers A/B/C, parameters, timelines and pricing mechanisms below are **entirely hypothetical** and exist only to demonstrate proposal structure.
- GPU models, counts, networking and delivery terms are **illustrative assumptions**. They do not correspond to any real capacity or available inventory.
- The pricing row describes **charging mechanisms only**, not amounts. Any real project requires a formal supplier quotation and case-by-case verification.
- This document is not a quotation, an offer, a supply commitment or a compliance opinion.

---

## 1. Client and scenario (hypothetical)

**Sample client:** a Southeast Asia-based video-generation AI company (fictional; referred to as "Client S"), a team of several dozen people building a short-form video generation product for marketing and film use.

**Background (assumed):**
- Training its next-generation video model and needs a single 64-GPU H100-class training cluster.
- Planning a six-month engagement: pre-training for the first four months, then fine-tuning and inference validation for two.
- Roughly several hundred TB of training data, mostly in object storage in Southeast Asia; engineers distributed across two countries.
- No hard data-residency requirement, but training jobs must be auditable, the cluster stable, and failure recovery fast.
- Budget range has been confirmed, but the client wants to see structure and risk before discussing price.

## 2. Requirement breakdown (illustrative)

| Dimension | Requirement (assumed) | Note |
|---|---|---|
| Workload | Video-generation model pre-training + fine-tuning | Inference may follow |
| Precision | Mainly BF16, some FP8 experiments | Driver and framework support required |
| GPU model | H100-class (80GB) | Same-generation equivalent acceptable after benchmarking |
| Scale | 64 GPUs in a single cluster (8 nodes × 8 GPUs) | No cross-cluster stitching |
| Interconnect | Intra-node NVLink/NVSwitch; inter-node InfiniBand or high-bandwidth RoCE | Measured bandwidth required |
| Storage | Parallel file system, several hundred TB, high throughput | Data migration support needed |
| Delivery | Start within 2–4 weeks of contract; phased ramp-up acceptable | First 32 GPUs, remainder within two weeks |
| Duration | Six months, renewable | Price-lock terms to be negotiated |
| Location | Southeast Asia preferred; mainland China possible subject to cross-border and compliance review | Client to confirm data path |
| Billing | Hourly or monthly; long commitment in exchange for better pricing | Mechanism subject to supplier quotation |
| Compliance | Export controls, cross-border data, client sector rules to be checked | We flag items; we do not conclude |

## 3. Options comparison (A/B/C all hypothetical)

| Dimension | Option A: Singapore hosted cluster | Option B: Malaysia self-built facility, managed | Option C: Mainland China cluster with cross-border access |
|---|---|---|---|
| Location | Singapore (assumed) | Johor, Malaysia (assumed) | An intelligent-computing centre in mainland China (assumed) |
| GPU | H100 80GB (assumed) | H100 80GB (assumed) | H100-class mixed domestic/imported (assumed; to be verified) |
| Scale | 64-GPU single cluster | 64-GPU single cluster, expandable to 128 | 64-GPU single cluster |
| Network | IB 200G/400G (assumed; to be measured) | RoCE + IB mix (assumed) | IB (assumed; cross-border link to be assessed) |
| Delivery | 2–3 weeks (assumed) | 3–5 weeks (assumed; racks and installation included) | 2–4 weeks (assumed) |
| Storage | Managed parallel storage, elastic | Storage purchased or leased separately | Local parallel storage; cross-border transfer to be assessed |
| Pricing mechanism | Hourly or monthly; commitment discount | Per-cluster monthly, power and racks included; operations extra | Hourly or monthly; cross-border link and compliance costs extra |
| Main risks | Single region, higher price, capacity authenticity unverified | Longer delivery, unclear operations boundary, local compliance to confirm | Cross-border latency and data path, export-control and compliance uncertainty |
| Our initial view | Best fit on delivery and network; higher price | Potentially best cost; delivery and operations risk must be managed | Attractive cost and elasticity, but the most compliance preconditions |

> Every parameter, timeline and mechanism above is an **assumption** included to demonstrate the comparison method. Any real proposal must rest on written supplier evidence and verification results.

## 4. Recommendation and rationale

**Recommended: Option A as first choice, Option B as fallback, and Option C retained only if the client accepts a cross-border compliance review as a precondition.**

Rationale:
1. **Fit:** A's delivery timeline and network shape come closest to the requirement for a single 64-GPU cluster running continuous training for six months.
2. **Manageable risk:** A sits in a region the client knows, with shorter data paths and support response, making SLA terms easier to attach.
3. **Negotiability:** A offers a commitment-discount mechanism suited to a six-month term; B's cost advantage has to be weighed against longer delivery and greater operational involvement.
4. **Why keep C:** C has potential on unit cost and elasticity, but cross-border data paths and export controls are hard constraints. Compliance screening must come first.

**A recommendation is not a commitment.** The final choice depends on verification results, formal quotations, SLA terms and the client's own compliance judgement.

## 5. Risks and mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Supplier capacity cannot be verified | Delivery delay | Require installation evidence, monitoring screenshots, third-party validation; ramp in phases |
| Measured bandwidth below specification | Lower training efficiency | Benchmark before contract; write acceptance tests into the SLA |
| Phased delivery interrupts training | Project delay | Run small-scale validation on the first 32 GPUs; migrate after the second batch |
| Cross-border data path unclear | Compliance risk | Map the path and disclose in writing; client and its counsel decide |
| Opaque pricing mechanism | Budget overrun | Itemised quotations and billing definitions; price-adjustment clause |
| Single-region failure | Training interruption | Backup and recovery plan; off-site checkpointing |

## 6. Next steps

1. Client confirms the requirement table and priorities (location, cross-border data, acceptance of same-generation alternatives).
2. We verify A/B/C across the five verification dimensions and issue conclusions (VERIFIED / REJECTED / insufficient information).
3. Verified suppliers provide formal quotations and SLA drafts.
4. We issue the final comparison and risk note; the client decides.
5. If we proceed: client and supplier contract and settle directly; we provide commercial coordination and ongoing procurement management.

## 7. Statements

- This document is a sample template and constitutes no quotation, offer or supply commitment.
- The data, suppliers and client described are fictional and must not be cited as a real case.
- Compliance-related content is limited to our verification checklist and risk flags; it is not legal advice. Clients should obtain their own professional legal advice.
- Any arrangement involving cross-border data or export controls requires CEO approval and professional review before it is described externally.
