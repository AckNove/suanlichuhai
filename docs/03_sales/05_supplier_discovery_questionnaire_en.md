> Status: DRAFT v1.0 (2026-11-16). Not for external distribution until CEO approval.
> Use: supplier discovery interviews (first or second call). Read aloud as written; record answers in the supplier file.
> Internal ID 05

# Supplier Discovery Questionnaire (30 Questions · Read-Aloud Ready)

## How to use

- **Duration:** 30–45 minutes. Five minutes of context, 30 minutes of questions, five minutes to confirm next steps.
- **Ask in order.** Skip an item only when the supplier explicitly declines. Probe with "Could you be more specific?" or "Is there any document I could look at?"
- **Do not lead.** Never ask "You must have plenty of GPUs?" and never suggest numbers for the supplier to confirm.
- **Record the wording.** For model names, unit counts, lead times and pricing mechanics, record what the supplier says verbatim; do not round up or paraphrase in flattering terms.
- **Never commit.** Do not promise buyer volume, a closed deal, a fee or a purchase quantity during the interview.
- **Status tag required:** every answer gets one of `Confirmed (evidence)` / `Verbal only` / `To be confirmed` / `Not applicable`.
- **Within 24 hours:** send the supplier a written recap for confirmation and update the supplier's status (LEAD → RESEARCHED → NEEDS_VERIFICATION).

---

## A. Entity and authorization (Q1–Q5)

**Q1. Could you confirm the full company name, registration number and year of incorporation?**
Record: ________ | Evidence: ________ | Status: ________
Probe: Is the entity I am speaking with the same entity that would sign the contract?

**Q2. What is your role in this capacity — owner, authorized agent, or something else?**
Record: ________ | Status: ________
Probe: If you are an agent, which customer types and regions does the authorization cover?

**Q3. If you are an agent or reseller, can you provide the authorization document? When does it expire?**
Record: ________ | Evidence: ________ | Status: ________

**Q4. Do any of these GPUs fall under export-control restrictions? What is your self-assessment status?**
Record: ________ | Status: ________
Note: we do not participate in any arrangement that circumvents export controls; this question defines the serviceable scope.

**Q5. Have you signed any compliance statement or export-control undertaking? Can you share a copy?**
Record: ________ | Evidence: ________ | Status: ________

---

## B. Capacity (Q6–Q15)

**Q6. Which GPU models do you have available for sale, and roughly how many units of each?**
Record: ________ | Status: ________

**Q7. Which facilities are these GPUs in? Which city or campus?**
Record: ________ | Evidence: ________ | Status: ________

**Q8. Is this mainly a training cluster or an inference cluster? Any mixed workloads?**
Record: ________ | Status: ________

**Q9. What is the largest single-cluster size you can deliver? What are the intra-node and inter-node interconnect options (NVLink / PCIe / IB / RoCE)?**
Record: ________ | Status: ________

**Q10. What is the storage setup — capacity, type and throughput?**
Record: ________ | Status: ________

**Q11. How much is deployed, how much is sellable, and how much is currently utilized? Can you separate the three?**
Record: ________ | Status: ________

**Q12. Do you have console screenshots, monitoring screenshots or deployment evidence you can share?**
Record: ________ | Evidence: ________ | Status: ________

**Q13. From signing to usable capacity, what is the typical lead time?**
Record: ________ | Status: ________

**Q14. How is the SLA defined — availability commitment, incident response time and remedies?**
Record: ________ | Evidence: ________ | Status: ________

**Q15. Have you had any major outages recently? What are the failure rate and mean time to recovery?**
Record: ________ | Status: ________

---

## C. Commercial terms (Q16–Q21)

**Q16. What is the pricing mechanism — hourly, annual, per-cluster, or something else? What is the billing unit?**
Record: ________ | Status: ________

**Q17. Does pricing step down with volume or duration? How are the tiers structured?**
Record: ________ | Status: ________
Note: record the mechanism only. Do not ask for a floor price and do not make any pricing commitment.

**Q18. What is the minimum order and minimum contract term?**
Record: ________ | Status: ________

**Q19. What are the payment terms — prepayment, monthly, or credit? Which currency do you settle in?**
Record: ________ | Status: ________

**Q20. How is invoicing handled? Can you invoice an overseas entity or issue a proforma invoice?**
Record: ________ | Status: ________

**Q21. Do you have a standard contract template? How are the SLA, termination and data-responsibility clauses drafted?**
Record: ________ | Evidence: ________ | Status: ________

---

## D. Overseas capability (Q22–Q26)

**Q22. Have you served overseas customers? Which regions?**
Record: ________ | Status: ________

**Q23. Can you contract with an overseas entity? What would the contracting and settlement path look like?**
Record: ________ | Status: ________

**Q24. If customer data sits outside China, how is the data path currently handled?**
Record: ________ | Status: ________
Note: factual mapping only — we do not make compliance judgments.

**Q25. Do you run sanctions-list or export-control screening? How often?**
Record: ________ | Status: ________

**Q26. How do you support overseas customers — time-zone coverage, language, operations response time?**
Record: ________ | Status: ________

---

## E. Cooperation and decision chain (Q27–Q30)

**Q27. Would you accept a non-exclusive arrangement?**
Record: ________ | Status: ________

**Q28. Would you accept success-based or project-based cooperation?**
Record: ________ | Status: ________
Note: fee mechanics are not discussed in this round; they are agreed case by case in writing once a specific project exists.

**Q29. Who decides what capacity is sellable, who sets pricing, and who signs contracts?**
Record: ________ | Status: ________

**Q30. For next steps, can you provide a document set (business license, authorization, facility evidence, SLA template) and arrange a technical call?**
Record: ________ | Evidence: ________ | Status: ________

---

## Recording rules (during and after the interview)

1. **Four status values:** `Confirmed (evidence)` / `Verbal only` / `To be confirmed` / `Not applicable`. Verbal statements without evidence must never be recorded as confirmed.
2. **Evidence grading:** HIGH (official document / verifiable console) / MEDIUM (screenshot / third-party account) / LOW (verbal description) / UNVERIFIED (no source).
3. **Verbatim first:** record numbers and commitments as stated; label paraphrases as "paraphrased".
4. **Never fill gaps:** leave unknown fields empty. Do not infer from general market knowledge.
5. **No adjectives:** do not write "abundant capacity" or "strong capabilities"; record facts only.
6. **Stay within authority:** no quoting, no purchase commitments, no signing, no payments during the interview.

## After the interview

### 1. Capacity profile (one page)

- Entity and authorization status:
- Sellable models and quantities:
- Facility locations and network:
- Lead time and SLA:
- Pricing mechanism and payment:
- Overseas service capability:
- Main risks and gaps:
- Recommended status: `NEEDS_VERIFICATION` / `INSUFFICIENT_INFO` / `REJECTED`

### 2. Five-dimension initial score (1–5 each, for internal triage only)

| Dimension | Score | Basis |
|---|---|---|
| Entity and authorization clarity | /5 | |
| Verifiability of capacity | /5 | |
| Model and capacity fit | /5 | |
| Delivery and network reliability | /5 | |
| Commercial and compliance completeness | /5 | |
| **Total** | **/25** | |

Triage (internal): 20 or above → proceed to formal verification; 15–19 → insufficient information, set a deadline to supplement; below 15 → do not pursue for now. The score is a triage aid, not a substitute for the verification checklist.

### 3. Next steps

- [ ] Send the interview recap within 24 hours and ask the supplier to confirm
- [ ] Collect missing evidence (business license, authorization, facility evidence, SLA)
- [ ] Update the supplier record and status
- [ ] If proceeding to verification, use the Supplier Verification Checklist (09)
