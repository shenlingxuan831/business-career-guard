# Release Gates

## Ready

- `SKILL.md` has valid frontmatter and precise triggers.
- No personal names, emails, phones, resumes, local paths, credentials, or real application logs are bundled.
- Scripts use portable defaults and standard dependencies where practical.
- A clean-machine or temporary-directory smoke test passes.
- External actions remain approval-gated.
- Examples are fictional and clearly labelled.
- Output schema is machine-checkable.

## Demo-Ready

- The narrow happy path works.
- Safety and privacy gates pass.
- Local setup is documented by the skill itself.
- Production login, credential storage, or hosted service operation is not complete.

## Internal-Only

- Depends on personal folders, local accounts, private resumes, or unredacted logs.
- Requires undocumented environment state.
- Cannot run outside the original repository.

## Blocked

- Secrets are stored or printed.
- Real sending can occur without dry-run and immediate confirmation.
- Unsupported personal claims are generated as fact.
- Public package contains personal data.
- The main path fails on a clean fixture.

## Acceptance Tests

1. Privacy scan detects a secret keyword and does not echo its value.
2. Public scan detects phone, email, and local user path.
3. Route command copies a fixture and writes a SHA-256 receipt.
4. Send preflight blocks without dry-run.
5. Send preflight blocks without explicit confirmation.
6. Send preflight blocks invalid recipient or missing attachment.
7. Valid fictional manifest returns `READY`.
