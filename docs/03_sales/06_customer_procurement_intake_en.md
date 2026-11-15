> Status: DRAFT v1.0 (2026-11-16). Not for external distribution until CEO approval.
> Use: customer procurement intake (first or second call), to define the requirement and grade the lead.
> Internal ID 06

# Customer Procurement Intake (20 Questions + Scoring and Qualification Rules)

## How to use

- **Duration:** 30–45 minutes for the first call. The customer may answer in two sessions.
- **Sequence:** workload and model first, then specification, location/compliance, budget and decision process. Do not open with budget.
- **Recording:** write down what the customer says. Do not fill in blanks for them. Mark anything uncertain as `To be confirmed`.
- **Stay within authority:** do not quote prices, promise availability, promise delivery dates or criticize incumbent suppliers.
- **Output:** a usable Requirement Summary plus a lead grade based on the rules below.

---

## A. Workload and model (Q1–Q4)

**Q1. What is the primary workload — training, fine-tuning, inference, rendering, simulation, or a mix?**
Record: ________ | Status: ________ | Notes: ________

**Q2. What model type and parameter scale? Context length? Is it MoE or multimodal?**
Record: ________ | Status: ________

**Q3. What stage are you at — pre-training, post-training/fine-tuning, inference in production, or continuous iteration?**
Record: ________ | Status: ________

**Q4. What precision is required (FP8 / FP16 / BF16 / FP32)? Do you have a performance benchmark (tokens/s, images or video generation speed)?**
Record: ________ | Status: ________

## B. Compute specification (Q5–Q9)

**Q5. Do you have a GPU preference, and why? If an equivalent alternative improves delivery or cost, would you accept it?**
Record: ________ | Status: ________

**Q6. How many GPUs do you need? Single cluster or multiple? Could you take delivery in phases?**
Record: ________ | Status: ________

**Q7. How long do you need it for? When must you start? Are there peaks (for example an intensive training push before launch)?**
Record: ________ | Status: ________

**Q8. Cluster size and interconnect: how large is the single cluster? What intra-node and inter-node networking do you need (NVLink, InfiniBand, RoCE)? What bandwidth?**
Record: ________ | Status: ________

**Q9. Storage and data: how much capacity and throughput? How large is the training dataset? How is data uploaded and downloaded? Do you need high-speed parallel storage?**
Record: ________ | Status: ________

## C. Location, compliance, timeline and budget (Q10–Q14)

**Q10. Location and data residency: any country or region restriction? Must data stay in-country or in a specific jurisdiction?**
Record: ________ | Status: ________

**Q11. Compliance requirements: export controls, sector regulation, cross-border data, audit, or security-grading obligations?**
Record: ________ | Status: ________

**Q12. Timeline: when is the earliest you need capacity? What lead time can you tolerate?**
Record: ________ | Status: ________

**Q13. Budget: what is the approximate budget range or cost target? Which billing model do you prefer (hourly / annual / per-cluster)?**
Record: ________ | Status: ________

**Q14. Current setup and pain points: whose capacity do you use today? What is not working (price, stability, delivery, compliance, support)?**
Record: ________ | Status: ________

## D. Decision and procurement (Q15–Q19)

**Q15. Decision process: who initiates, who evaluates, who approves, who signs? How many stages and how long?**
Record: ________ | Status: ________

**Q16. Preferred procurement form: hourly, annual, per-cluster, reserved instances, or a mix? Would a framework agreement with on-demand orders work?**
Record: ________ | Status: ________

**Q17. Contracting and settlement: where is the contracting entity? What payment terms and currency do you expect? Do you need invoices?**
Record: ________ | Status: ________

**Q18. Supplier screening criteria: what would disqualify a supplier outright (jurisdiction, GPU model, SLA, data path)?**
Record: ________ | Status: ________

**Q19. Success criteria: how will you judge that this project worked (performance, unit cost, delivery speed, stability, auditability)?**
Record: ________ | Status: ________

## E. Next step (Q20)

**Q20. Next step: can you share a more detailed workload description or benchmark results? Would a technical call work? When would you like the first draft plan?**
Record: ________ | Status: ________

---

## Field conventions

Four fields per question:

| Field | Rule |
|---|---|
| Record | Customer's own words for key points; keep original units; write "unknown" where unclear |
| Status | `Confirmed` / `Verbal only` / `To be confirmed` / `Not applicable` |
| Source | Customer verbal / customer document / our inference (inferences must be labelled) |
| Impact | Effect on the plan: screening criterion / price factor / compliance gate / none |

## Information completeness score (0–2 per dimension)

| Dimension | 0 | 1 | 2 | Score |
|---|---|---|---|---|
| Workload and model | Not stated | Type only | Type + scale + stage + precision | /2 |
| GPU model and count | Not stated | Preference, no count | Model + count + substitutability | /2 |
| Duration and start date | Not stated | Rough timing | Start/end + peaks + lead-time tolerance | /2 |
| Cluster and network | Not stated | Size only | Size + interconnect + bandwidth | /2 |
| Storage and data | Not stated | Capacity only | Capacity + throughput + transfer path | /2 |
| Location and residency | Not stated | Regional preference | Defined jurisdiction + residency rule | /2 |
| Compliance | Not stated | General mention | Specific regulation / audit / export-control items | /2 |
| Budget and billing | Not stated | Range only | Range + billing preference | /2 |
| Decision process | Not stated | Process exists | Decision-maker + stages + timing | /2 |
| Success criteria | Not stated | General | Measurable indicators | /2 |
| **Total** | | | | **/20** |

## "Insufficient information" rules

Grade a lead `INSUFFICIENT_INFO` — and do not move it to the plan stage — if any of the following applies:

1. **Any of the five required items is missing:** workload type, GPU model (or acceptable alternative), GPU count (or order of magnitude), duration/start date, budget range.
2. **No decision path:** the decision-maker or process cannot be identified and the customer declines to explain.
3. **Location/compliance unknown and potentially a hard constraint:** the customer cannot state residency or compliance requirements, and those could eliminate most options.
4. **Completeness score below 12/20.**
5. **Internally contradictory requirement:** for example 64 H100-class GPUs in a single cluster, delivered within two weeks, at a budget well below market, with no willingness to adjust any element.

Handling after grading:

| Grade | Status | Action |
|---|---|---|
| Insufficient information | `INSUFFICIENT_INFO` | Send a gap list, allow five business days; archive if not returned |
| Broadly complete | `NEEDS_VERIFICATION` | Begin sourcing and supplier verification |
| Complete with budget/timing/decision-maker clear | `VERIFIED` | Prepare the options comparison; escalate per internal process |
| Clearly not a fit | `NOT_MATCHED` | Explain in writing; keep the door open for the future |

## Requirement summary template (output within 24 hours)

- Customer and contact:
- Workload and model:
- Specification (GPU model/count/cluster/network/storage):
- Location and data residency:
- Compliance requirements and open items:
- Timeline and lead-time tolerance:
- Budget range and billing preference:
- Current setup and pain points:
- Decision process and decision-maker:
- Disqualifiers:
- Information gaps (ordered by impact):
- Recommended status: ________
- Next step and owner: ________

> Reminder: label every inference and its source. Never present unconfirmed customer statements as established requirements, and never disclose information about other customers.
