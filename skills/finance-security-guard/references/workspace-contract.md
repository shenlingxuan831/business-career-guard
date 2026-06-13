# Workspace Contract

Use this structure when the host project has no stronger convention:

```text
workspace/
├── 00_inbox/
│   ├── resumes/
│   ├── job_descriptions/
│   ├── projects/
│   ├── constraints/
│   ├── knowledge/
│   └── attachments/
├── 10_extracted/
│   ├── resumes/
│   ├── job_descriptions/
│   ├── evidence/
│   └── gaps/
├── 20_interview/
│   ├── question_sets/
│   ├── sessions/
│   ├── transcripts/
│   └── evaluations/
├── 30_application/
│   ├── queues/
│   ├── emails/
│   └── attachments/
├── 40_outputs/
├── 90_archive/
└── logs/
```

## Routing Rules

- Preserve user originals.
- Create a receipt containing source, destination, type, timestamp, and SHA-256.
- Do not route new active files to archive or logs.
- Do not use binary files as textual evidence until extracted.
- Keep generated outputs out of source evidence folders.

## Artifact Rules

- Extracted candidate data: `10_extracted/resumes/*.candidate.json`
- Extracted role data: `10_extracted/job_descriptions/*.role.json`
- Evidence matrix: `10_extracted/evidence/*.matrix.json`
- Gap list: `10_extracted/gaps/*.gaps.json`
- Reviewed queue: `30_application/queues/`
- Email draft: `30_application/emails/`
- Final selected attachment: `30_application/attachments/`
- Final pack and redacted manifest: `40_outputs/`

## Local Boundary

Treat the selected project root as the only writable workspace. Never accept a client-supplied path that resolves outside it.
