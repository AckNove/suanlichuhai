> Status: DRAFT v1.0 (2026-11-16). Not for external distribution until CEO approval.
> Use: 25-item supplier verification across five dimensions. Conclusions rest on evidence, not assurances.
> Internal ID 09

# Supplier Verification Checklist (25 Items)

## How to use

- **Sequence:** entity and authority first, then resource authenticity, then capacity, delivery and commercial terms. If the first two dimensions fail, do not continue.
- **Principle:** ask for evidence item by item. "Definitely available", "arriving soon" and "internal information" are not evidence.
- **Recording:** log evidence ID, source, date and reviewer for each item. Verbal information is marked `verbal` and cannot support a pass.
- **Output:** VERIFIED / PARTIALLY VERIFIED / REJECTED / INSUFFICIENT INFO only. No performance or compliance assurances externally.
- **Escalation:** any external representation, lead upgrade or quotation requires CEO approval.

## Dimension 1: Entity and authority (1.1–1.5)

| No. | Item | Method | Evidence required | Pass criteria | If it fails |
|---|---|---|---|---|---|
| 1.1 | Business licence and good standing | Search the national enterprise credit system; check the licence | Licence scan, unified social credit code, search screenshot | Entity active, business scope relevant, no abnormal status | Mark as REJECTED candidate; do not proceed |
| 1.2 | Contracting entity consistency | Compare contract, invoicing and resource-holding entities | Names of all three plus relationship explanation | Consistent, or a documented authorisation chain | Request authorisation; no contract without it |
| 1.3 | Resource ownership or resale right | Check title, lease, operating agreement or resale authorisation | Title deed, lease, cooperation agreement or authorisation (redacted) | Proves the right to provide the resource externally | Red line: REJECTED if unproven |
| 1.4 | Affiliates and agency layers | Map equity and authorisation chain; ask directly | Relationship statement, agency-layer diagram | Clear layers, no undisclosed sub-delegation | Downgrade to watch list; require written disclosure |
| 1.5 | Export control and sanctions self-check | Written declaration plus end-user/end-use confirmation | Signed self-check declaration, end-user statement | Complete, no circumvention language | Red line: no cross-border arrangement may proceed |

## Dimension 2: Resource authenticity (2.1–2.5)

| No. | Item | Method | Evidence required | Pass criteria | If it fails |
|---|---|---|---|---|---|
| 2.1 | Data centre and rack existence | Site visit or video walkthrough; verify geolocation | Time- and location-stamped photos/video | Locatable and revisitable | Remote-only material → partial verification |
| 2.2 | Rack installation and asset list | Match installation orders to asset numbers | Installation order, device serial list | Numbers map to racks and ports | Require installation evidence |
| 2.3 | Live GPU evidence | Remote spot check plus monitoring/scheduler screenshots | `nvidia-smi` or scheduler screenshot with timestamp | Hardware live and model matches | Cannot verify live → REJECTED |
| 2.4 | Third-party cross-check | Carrier, IDC, customer or on-site third party | Written confirmation or contactable reference | At least one independent source corroborates | Self-report only → evidence graded LOW |
| 2.5 | Verifiable customer case | Request redacted contract pages or a reference call | Redacted contract, customer reference | Contactable; cooperation fact verifiable | Do not use in external materials |

## Dimension 3: Capacity and models (3.1–3.5)

| No. | Item | Method | Evidence required | Pass criteria | If it fails |
|---|---|---|---|---|---|
| 3.1 | Model and memory list | Compare asset list with live units | Model, memory, generation, firmware list | Same generation/class as required, or clearly substitutable | Model mismatch → reassess requirement |
| 3.2 | Installed vs sellable count | Asset list plus scheduler cross-check | Separate counts for installed, sellable, reserved | Sellable ≥ requirement, or phased delivery works | Insufficient sellable → downgrade or defer |
| 3.3 | Occupancy and prior sales | Ask plus cross-check | Utilisation rate, contracted volume (redacted) | Consistent with sellable claims; no double-selling | Contradictions → pause verification |
| 3.4 | Expansion and delivery capability | Expansion plan, procurement and delivery records | Expansion timetable, historical delivery record | Executable plan and prior delivery | Verbal plan only → mark to be confirmed |
| 3.5 | Health and spare parts | Failure rate, spares inventory, maintenance record | Last six months of faults and repairs | Acceptable failure rate; spares assured | No records → require trial run |

## Dimension 4: Delivery and network (4.1–4.5)

| No. | Item | Method | Evidence required | Pass criteria | If it fails |
|---|---|---|---|---|---|
| 4.1 | Delivery timeline and process | Request a delivery plan; review milestones | Rack, installation, acceptance and handover schedule | Timeline acceptable; milestones clear | Timeline mismatch → record as risk |
| 4.2 | SLA and availability | Review SLA draft and historical uptime | SLA terms, uptime record, remedy mechanism | Clear SLA with remedies | No SLA → does not enter the options paper |
| 4.3 | Network and interconnect testing | Measured test or third-party report | Bandwidth, latency, packet loss, topology | Meets required thresholds | Untested → make acceptance testing a condition |
| 4.4 | Storage and data migration | Check capacity, throughput, migration plan | Storage spec, migration test results | Capacity and throughput adequate; migration executable | Plan missing → make it a precondition |
| 4.5 | Operations and support | Ask about on-call, ticketing, response | Ops manual, SLA response times, contacts | 24/7 reachable; defined response | No ops assurance → downgrade |

## Dimension 5: Commercial and compliance (5.1–5.5)

| No. | Item | Method | Evidence required | Pass criteria | If it fails |
|---|---|---|---|---|---|
| 5.1 | Pricing mechanism and billing | Request itemised quotation and billing rules | Quote, billing unit, minimum spend, price-adjustment clause | Complete and free of hidden charges | Unclear → require re-quotation |
| 5.2 | Payment terms and invoicing | Check currency, credit terms, invoicing capability | Payment terms, invoicing details, sample invoice | Can invoice; credit terms acceptable | Cannot invoice → affects settlement path |
| 5.3 | Data residency and security | Ask about location, encryption, access control | Data-flow diagram, residency statement, security policy | Meets client residency requirement | If not → client must confirm acceptance |
| 5.4 | Cross-border data and export-control clauses | Review contract and data-processing terms | Cross-border clauses, DPA, control declaration | Clear clauses; liability definable | Unclear → legal review first; no assurances |
| 5.5 | Liability, insurance and exit | Review liability cap, insurance, termination | Contract draft, insurance certificate, exit mechanism | Liability and exit acceptable | Clearly one-sided → negotiate or walk away |

## Scoring sheet

- Per item: 2 = sufficient evidence; 1 = partial evidence; 0 = no evidence / failed.
- Maximum 50 points.

| Dimension | Items | Score |
|---|---|---|
| 1. Entity and authority | 5 | /10 |
| 2. Resource authenticity | 5 | /10 |
| 3. Capacity and models | 5 | /10 |
| 4. Delivery and network | 5 | /10 |
| 5. Commercial and compliance | 5 | /10 |
| **Total** | 25 | **/50** |

## Decision rules

**Red-line items (any 0 → REJECTED):** 1.1 licence, 1.3 resource ownership, 1.5 export-control declaration, 2.3 live GPU evidence, 5.4 cross-border clauses.

**VERIFIED (may enter the options paper):** total ≥ 40; all red-line items ≥ 1; all of 1.1–1.5 ≥ 1; no unmitigated HIGH risk; key evidence (1.3, 2.2, 2.3, 4.2, 5.1) supported by HIGH-grade evidence.

**PARTIALLY VERIFIED (may be retained, with a deadline):** total 30–39; or one key item at 1 that can be closed within ten business days.

**REJECTED (terminate):** any red-line item at 0; total < 30; refusal to provide core evidence; evidence of forgery or double-selling.

**INSUFFICIENT INFO (hold):** documentation incomplete but the supplier is cooperating and no red line has failed.

## Evidence grading

- **HIGH:** original documents, system screenshots, live measurement, written third-party confirmation.
- **MEDIUM:** formal supplier documents, contactable references.
- **LOW:** verbal statements, brochures, public reports.
- **UNVERIFIED:** cannot be checked.

> Verification records, scores and conclusions are internal. Externally, state only the fact of "verified" or "insufficient information". Do not disclose evidence details and do not make compliance assurances.
