# Usage Manual

## Included state and installation
Both banks ship empty. Add private examples and verified official journal sources locally before personalized journal-compliant drafting. Missing official sources block generation.

Place the complete `si-proposal-studio` directory in your Codex skills directory, retaining banks/. Invoke `$si-proposal-studio`. The default Python helper uses only Python 3 standard-library modules. Source DOCX parsing for future intake uses the host's document capability; the retrieval helper does not require Word or an embedding API. Work files belong in a task's work/ directory, not in the installed Skill directory.

Keep your populated banks outside this public repository. Pass `--bank /absolute/private/bank` before every subcommand. Initialize that folder by copying the empty banks/index.json into it. The helper creates record subdirectories during ingestion. Never commit private sources, biographies, contact details, populated indices or generated contexts. Installed and exported copies are snapshots; choose one active local bank and back it up before updates.

## Add data
X: “Add this private sample as Type A (Proposal + CfP)” or “Type B (Proposal only).” Host parses documents and builds a directory with record.json, Proposal paradigm, optional eligible CfP paradigm, raw extraction, sources and hashes. Then:

```sh
python3 scripts/si.py --bank /absolute/private/bank ingest --kind X --source /absolute/path/to/prepared-sample
```

Y: “Add these official TNSM SI instructions and public CfP examples to the journal bank.” Host verifies source provenance, encodes exact journal aliases, rule strength, formats, limits, dates and source snapshots in journal.schema.json. Then:

```sh
python3 scripts/si.py --bank /absolute/private/bank ingest --kind Y --source /absolute/path/to/journal-record.json
```

`ingest` validates structure and writes the appropriate independent bank. It cannot authenticate a website or a human assertion. Set pending if unverified. Use a versioned ID for updates and explicitly retire the former active index entry after preserving its record. Two active matching entries block retrieval. Avoid simultaneous bank writers. No private document is reclassified into an official source just because it quotes a rule.

## Draft / revise / derive
Natural-language requests are normalized to schemas/input.schema.json. Mode 1: “Draft a new SI proposal for [exact journal].” Mode 2: “Revise this proposal against these editor comments.” Mode 3: “Generate a CfP and EiC cover letter from this proposal.” English is default; specify Chinese for a Chinese draft. Full required data may be resolved from a confirmed source rather than asked again.

Run from the Skill folder (replace paths and date with your actual request and user-local date):

```sh
python3 scripts/si.py --bank /absolute/private/bank prepare --request /absolute/task/work/request.json --today 2026-10-28 --out /absolute/task/work/prepare.json
python3 scripts/si.py --bank /absolute/private/bank compile --request /absolute/task/work/request.json --rankings /absolute/task/work/rankings.json --today 2026-10-28 --out /absolute/task/work/context.json
python3 scripts/si.py --bank /absolute/private/bank check --request /absolute/task/work/request.json --context /absolute/task/work/context.json --output /absolute/task/work/output.json --today 2026-10-28 --out /absolute/task/work/check.json
```

Between prepare and compile, the host executes the semantic-ranking sub-prompt and writes rankings.json. This is an intentional local two-stage pipeline: deterministic concept/keyword candidate ordering plus model semantic judgment, not a claimed embedding search. It scores every case in the active local bank, including cross-journal matches. No API keys, embeddings or network calls are required by the helper. Both style and standards reads run concurrently. `--bank /path/to/bank` before the subcommand selects an alternate independent bank for testing or updates.

Compile injects overall semantic Top-2 into FEW_SHOT_STYLE_EXAMPLES. For CfP it adds up to two separately labeled eligible Type A CfP paradigms, ranked separately using their CfP paradigms. Type B contributes scope/motivation only; it never supplies a CfP exemplar. Standards use exact normalized aliases, not topic similarity. IoTM and IoT-J must never share a rule record. IET alone is not a journal identity.

## Outputs and gates
Deliver readable requested artifacts plus output.json and a separate editorial report. Official format governs section count/order/terminology/limits; the nine-section personal baseline is a content inventory used only where compatible. Three title alternatives are editorial options, not three titles forced into a journal form. Draft/revise outputs include the proposal; derivative mode includes only requested derivatives. Mode 2 includes editor responses and the trace table.

A missing official bank entry produces a request for guidelines and official CfP examples. Prepare still returns private candidates, but no compliant draft is released. Low relevance of the two best samples is disclosed, not hidden by pretending they match. Semantic source verification, overlap analysis, factual evidence and page-layout validation remain host tasks. `mechanical_checks_pass` is not factual certification.

## Official record fields
Use schemas/journal.schema.json as the input contract. Required sources have IDs, official URLs, titles, snapshot_text and retrieval dates. formats.proposal and formats.cfp each specify section_order, required_sections, strict_sections, terminology, limits, format_notes and source_ids. A limit identifies target section or *, unit, min/max, source_id and counting_notes. Empty limits means no explicit numerical limit found, not an unlimited official guarantee. rules distinguish mandatory/recommendation/example_convention. official_cfp_examples preserve actual public example text and dates/unknowns. verified_on and review_after control freshness; unresolved_conflicts block use.

## Validation and limitations
Run `python3 scripts/test_si.py` for isolated synthetic cases. Test fixtures are not official sources and never enter production banks. Local checks verify input gates, official precedence, length/order constraints, feedback trace, retrieval and Type B exclusions. The host must verify sources and semantic fit; no automatic script can establish GE achievements, novelty or current editorial policy. This package does not create a proposal merely to demonstrate itself.

## Version 1.1 validation contract
Existing core input keys are preserved. Optional GE email/ORCID/role/consent and source fields are now accepted. Timeline entries allow exact date OR a tentative window; confirmed dates and explicit after dependencies are checked. Journal records can require extra input paths and derivative attachments. The form is not an excuse to re-ask already confirmed facts.

Rankings now require `candidate_digest` from prepare and, when a CfP is requested or required by the journal, `cfp_rankings` for eligible Type A cases. Old ranking/context files must be regenerated. No raw historical paragraphs are injected into the writing context; curated paradigms and provenance flags are used instead.

Ready outputs additionally need rule_checks, check_evidence, fact_claims and appropriate manual_checks. Evidence must anchor exact artifact text and identify sources; current user-provided facts can remain user_supplied, but literature/novelty assertions need verified primary sources. Output artifact kinds now include editor_response, which is a revision deliverable, not a fourth mode. See output schema and the main prompt for the complete contract.

To compute the artifact hash for a host-reviewed rule or rendered limit, import scripts/si.py and call `digest(artifact_dict)`. Use source IDs from the matched journal record. Limit IDs are `limit:proposal:0`, etc.; format checks are `format:proposal`/`format:cfp`. The host remains responsible for checking actual rendered pages, all claim coverage and source authenticity. A digest only invalidates an old attestation after the artifact changes.

Run check with the current user-local date and the SAME bank used for prepare/compile. Changed inputs, changed active rules, unresolved mandatory rules, blank required sections, pending manual counts, unmapped facts and unresolved editor issues prevent ready status. Structured validation is not a standalone review/score function.

Journal updates must retain original snapshots and explicit override provenance. `required_section` rules are enforced in addition to the ordered format; source IDs, section sets, ranges and dates are validated on both ingestion and retrieval. Unknown counting methods remain manual instead of silently using an unsuitable tokenizer. Inputs marked pending/unknown are never promoted to verified by ingestion.
