# SI Proposal Studio

A Codex Agent Skill for Special Issue proposals, editor-feedback revisions and derivative Calls for Papers, cover letters, teasers and promotion drafts.

This public distribution includes **no private examples or personal records**. Both banks are empty. It preserves dual retrieval, independent Proposal/CfP style selection, official journal requirements over personal style, and three production modes. It has no standalone proposal grading mode.

## Install
Ask Codex to use skill-installer with repository `guoq01/si-proposal-studio`, path `.`, and name `si-proposal-studio`. Alternatively copy the complete folder into your Codex skills directory under that name. Invoke `$si-proposal-studio` after installation.

Requires Python 3 standard library. Semantic ranking, writing, primary-source verification and rendering are performed by the host assistant.

## Set up private data
Create a private directory outside this checkout and copy `banks/index.json` into it. Use `python3 scripts/si.py --bank /absolute/private/bank ...` for all commands. Add your own Type A (Proposal + CfP) or Type B (Proposal only) cases. Separately add verified journal requirements and official public CfP examples. Never publish populated banks or generated contexts.

## Documentation
- [Skill entrypoint](SKILL.md)
- [Complete skill document](SI_Proposal_Skill_Complete.md)
- [Usage manual](references/usage-manual.md)
- [Input form](templates/intake.md)
- [Validation report](validation-report.json)

## Checks
```sh
python3 scripts/test_si.py
python3 scripts/check_public.py
```
Tests generate artificial fixtures inside temporary directories. They require no personal samples. A passing result checks program behavior, not factual truth or current journal compliance. Missing official standards block drafting; empty style banks produce a disclosed limitation.
