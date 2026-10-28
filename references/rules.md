# Rule engine and gate ownership

| Rule | Action | Enforced by |
|---|---|---|
| Required input absent/wrong type | Block; list exact field | input schema + prepare |
| Revision/derivation source missing | Block | prepare |
| Journal identity ambiguous, missing, expired or conflicting | Block | exact normalized name/alias lookup + date gate |
| Journal official status only asserted in metadata | Read primary snapshot and verify provenance | host; scripts cannot prove authority |
| Semantic Top-2 | Rank every case, require unique IDs and reasons | host semantic scores + compile |
| Type B CfP style | Never inject | compile type gate + filtered files |
| Private styles conflict with mandatory official format | Official sections/order/limits win | main prompt + output checker |
| Duplicate/wrong-order/missing sections | Fail | check |
| Word/character limits and figure/table equivalents | Count known rules | check; custom/page limits need host |
| Feedback omission | Fail | check issue IDs; host checks actual fixes |
| GE identities, factual claims, novelty, ethics, contacts | Evidence-led verification | host and evidence ledger |
| Overlap / breadth | Search log and reasoned comparison | host; ready gate requires recorded audit |
| CfP/proposal identity consistency | Compare title/topics/dates/roster/instructions | host; explicit checklist |
| Publishing or outreach | Requires explicit task authorization | host; scripts do not send |

Official record freshness uses a per-record review_after date chosen based on source stability; no universal expiry is asserted as journal policy. Recent requirements can change even within that interval, so refresh when evidence suggests change. Conflicting mandatory sources remain unresolved until an authoritative exception or clarification is obtained. Public examples cannot silently repeal rules.

The dependency-free validator implements the JSON Schema keywords used in this package: type, properties, required, additionalProperties, items, minItems, minLength, pattern, enum, minimum, maximum, uniqueItems. It is not a general-purpose JSON Schema engine. The schemas can also be validated by any Draft 2020-12 validator. Source dates and semantic facts require separate checks.

## Release gate upgrades
Context is bound to request, source record and date; current active bank is rechecked. All mandatory rules and format conventions need source-linked, artifact-bound attestations at ready status. Blank sections, missing required attachments, mode/language mismatches, unresolved revisions and unsupported identity/date manifests fail. Pages/custom/unknown counters remain pending until a current measurement is recorded. Facts require claim-to-source anchors; primary-source verification is required for literature and novelty. The engine validates provenance structure, not the truth of supplied evidence.
