# Safety And Privacy Policy

## Severity

| Level | Examples | Result |
| --- | --- | --- |
| Critical | Password, SMTP authorization code, API key, session cookie | Block and remove immediately |
| High | Private resume, phone, personal email, recipient list, application log | Block public sharing; require explicit destination approval |
| Medium | Local user path, employer contact, internal filenames, inferred claim | Redact or review |
| Low | Generic example data clearly labelled fictional | Allow |

## Evidence Rules

- Candidate facts require a resume, project artifact, transcript, or explicit user confirmation.
- A JD establishes requirements only.
- Knowledge documents establish domain explanations only.
- Generated files are outputs, not source evidence.
- If evidence is missing, state the gap and weaken the claim.
- Do not invent employers, metrics, dates, responsibilities, offers, grades, tools, or outcomes.

## External Action Rules

Drafting and reviewing are reversible. Sending, uploading, publishing, changing access, and paying are external actions.

Before an external action:

1. identify the destination;
2. identify the exact data transmitted;
3. show a concise summary;
4. receive task-specific approval at action time.

For email sending, require a successful dry-run and explicit send confirmation. Never infer permission from a prior draft request.

## Credential Rules

Authorization codes and secrets may exist only in a password field, an immediate local request, or a child-process environment used for that action.

Never place them in:

- source files;
- `.env` files;
- shell history or command arguments;
- CSV or JSON manifests;
- browser storage;
- logs, transcripts, screenshots, or final messages;
- Git history or downloadable packages.

Clear the credential field after success or failure.

## Public Package Redaction

Replace:

- names with `Candidate Name`;
- emails with `candidate@example.com`;
- phones with `000-0000-0000`;
- local paths with `<workspace>/...`;
- recipient addresses with `recruiting@example.com`;
- real application records with fictional fixtures.

Remove binary resumes and application logs unless the user explicitly requests a private package.
