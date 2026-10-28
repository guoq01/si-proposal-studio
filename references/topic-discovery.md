# Draft mode: journal-first topic discovery

Use this phase when the user knows only the journal, or explicitly requests SI topic research. It is part of Draft, not a fourth mode or a proposal grading tool. Read `schemas/discovery-input.schema.json` and `schemas/discovery-output.schema.json`.

## Intake and transition
Only an exact journal name OR abbreviation is required to start. Resolve the full identity and official scope by research; publisher names such as IET or IEEE alone require clarification. Do not require a title, topic, scientific gaps, keywords, GE roster, dates or submission estimate before research. Omit unknown optional keys instead of filling them with invented values. Optional preferences include domains, exclusions, lookback and candidate count. Honor an explicit request for topic research even if a preliminary title was supplied.

`draft_stage=discover` selects this phase explicitly. With auto routing, a Draft request with none of title/topic/gaps populated and no existing source Proposal enters discovery; an existing substantive topic enters writing intake. Explicit `write` retains all original required writing inputs. Revision and derivative requests never silently turn into discovery. Ask about true conflicts rather than discarding feedback or derivative requests.

## Research sub-prompt
1. Verify exact journal identity, official scope and current SI proposal/CfP requirements. Inspect the official journal bank, but an empty or outdated bank means research is needed, not that discovery must stop. Promote only verified requirements and official examples into that bank. Missing rules may remain unresolved in a research report; they still block journal-compliant Proposal writing.
2. Search official active, forthcoming and published SI pages. Default coverage is the last five years; extend backward to relevant close matches, and include announced calls regardless of age. Record dated queries, URLs, result coverage, inaccessible archives, uncertainty and each issue's status/scope. This is an operational window, not journal policy. Never interpret an unsuccessful query as a complete archive search.
3. Review recent primary research (papers, official proceedings and authoritative project/research pages), usually emphasizing the last two to three years while checking older foundations. Trace claims to sources actually opened. Distinguish peer-reviewed papers from preprints; verify titles, dates and DOI/URLs. Identify open scientific questions and enabling developments rather than rename a fashionable umbrella topic.
4. Inspect the private bank for writing patterns and tentative domain affinities only. Historical GE lists and samples do not establish current expertise, participation or commitments. Do not lock topics to past samples. Keep both banks separate and retain the official-over-style priority. Research notes and primary-paper evidence belong in the task's work directory, not a third reusable bank.
5. Propose three to five defensible candidates by default, or the requested count. If evidence supports fewer, explain why instead of filling a quota. For each provide an English title (Chinese draft if requested), scientific question, why-now rationale with primary sources, journal fit, topic boundaries, plausible community and breadth risk. Community feasibility is an evidence-based hypothesis, never a confirmed submission count.
6. For each candidate select the nearest same-journal historical SIs by problem, object, methods, applications and evaluation, not title words alone. Cite their official sources; state overlap, substantive differences and remaining risk. Qualitative low/medium/high/unknown labels describe overlap uncertainty, not proposal quality scores. A new title or new acronym is not differentiation. If no comparator is found, explicitly mark risk unknown and describe search limits; never promise absolute non-duplication.
7. Return a readable comparison and source-linked structured discovery report. Use `research_incomplete` when browsing is unavailable or essential source evidence is missing; ask for official links or dated snapshots without inventing research. Only use `awaiting_topic_selection` after journal identity/scope, research and all search categories are evidenced. Source attestations are not independent proof; verify the underlying pages.

## User selection before writing
Stop at candidate discussion. Ask which candidate to select, combine or refine. Do not silently choose one and write a complete Proposal. Once the user confirms, record `topic_selection` with candidate_id, report_digest (`si.digest(report)`) and the user's actual confirmation. Carry over supported title/topic/gaps/keywords into a writing request with `draft_stage=write`. Do not fabricate user confirmation. Refresh differentiation if the chosen scope materially changes.

Then collect only missing GE details, timeline, source community, submission estimate and constraints. Run the existing parallel style/standard retrieval again using the selected substantive topic; rank Proposal/CfP examples independently as applicable. Retrieve Top-2 only once the topic provides a meaningful semantic query. Title alternatives, full Proposal, revisions and derivative consistency use the established writing contracts.

## Commands
Use the same active bank for all operations. On a public install, keep it outside the public checkout. The Python helper does not browse; the host performs research.

```sh
python3 scripts/si.py --bank /absolute/private/bank prepare --request work/discovery-request.json --today YYYY-MM-DD --out work/discovery-plan.json
python3 scripts/si.py --bank /absolute/private/bank check --request work/discovery-request.json --output work/discovery-output.json --today YYYY-MM-DD --out work/discovery-check.json
```

Discovery prepare returns `research_required` even when journal standards are missing; it never returns submission readiness. No semantic ranking file is needed at this stage. An incomplete report can be structurally valid without being ready for topic selection. Full writing checks still require the compiled writing context and complete inputs.
