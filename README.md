# Candoc

**Companies apply to people. People find their next opportunity.** An open-source hiring platform for permanent work, contracts, freelancing and consulting, with private candidate profiles, resume evidence review and a shared hiring workspace.

Live application: [candoc.org](https://candoc.org) · Source: [sverma/candoc](https://github.com/sverma/candoc)

Candidates upload their own resume, review a transparent **1–5 document evidence score**, and choose whether companies can discover their profile. Companies publish roles or invite discoverable candidates; candidates can apply directly. Applications provide messages, interviews, offers and a human-controlled pipeline. Contact email sharing in applications requires an explicit candidate opt-in; legacy introductions release contact after acceptance.

## Included

- Candidate and company signup/login with Argon2id password hashes, revocable cookie sessions, origin checks and request limits.
- Password recovery via expiring, single-use email links. A successful reset revokes every session; reset tokens are stored only as hashes.
- Email verification with single-use 24-hour links, required to publish roles or share a candidate's contact email in applications. Verification confirms email control, not company identity.
- Public, searchable roles for permanent, contract, freelance, consulting, temporary, internship, apprenticeship and volunteer work; remote/hybrid/onsite arrangements, time commitment, duration, hours, skill requirements and compensation in ISO currencies at hourly through project/yearly rates.
- Optional visa sponsorship and relocation support, each with available/case-by-case/unavailable/unspecified states and explanatory terms. Geographic restrictions and support filters are separate from legal eligibility.
- Candidate preferences for engagement types, preferred countries/regions, availability, notice, hours, compensation, languages and timezone. Optional nationality and country/region authorization declarations have independent sharing controls; permit notes always stay private.
- Company profiles, draft/published/paused/closed role lifecycle, saved roles, direct applications and company invitations. A private candidate can explicitly share a professional profile with an application without publishing it in discovery.
- Participant-only hiring conversations, interview scheduling/rescheduling with timezone-aware timestamps and candidate RSVP, expiring offers with candidate accept/decline, and explicit company hiring confirmation after an accepted offer.
- Live pipeline/dashboard counts, upcoming interviews, and a shared Updates feed for introductions and hiring events. Introduction send/receive and accept/decline events reach their participants, with unread controls and direct links. Updates refresh every 30 seconds while visible, on focus, or using Refresh. Full account export and cascade deletion include these events.
- PDF, DOCX and UTF-8 TXT resume extraction, private originals, bounded file sizes and document expansion.
- Five weighted evidence criteria with traceable excerpts and improvement suggestions.
- Optional public GitHub and GitLab.com API enrichment: repository/project descriptions, languages, and README excerpts. No follower/star scoring; account ownership and contribution are unverified.
- Candidate-uploaded LinkedIn profile PDF, TXT, professional CSV, or data-export ZIP, with extracted text review, replacement and removal. Pasted LinkedIn text remains supported. Profile URLs are references; no automated LinkedIn scraping.
- Optional, separately consented OpenAI semantic commentary with source-checked quotations. The API key stays on the server. No key is included in this repository.
- Candidate search, introduction inbox, accept/decline, account export and permanent live-account deletion.
- Responsive React frontend, FastAPI API, PostgreSQL storage, Docker Compose and nginx HTTPS deployment.

## Assessment boundaries

The numeric score describes evidence in a document; it is not a person's quality, verified proficiency, employability, or suitability for a role. It is deterministic and does not change when GitHub or GitLab is missing or unavailable. AI commentary adds context and questions; it never silently changes the numeric score. Human review is required for employment decisions.

The initial rubric is English-language and heuristic. Keyword coverage, document formatting, extraction and writing style can affect results. It has not been validated as a predictor of job performance. Resume/LinkedIn statements and GitHub/GitLab authorship are not independently verified. Scanned PDFs require OCR before upload. See [evaluation details](docs/EVALUATION.md).

## Local development

Use Python 3.12+ and Node 24+.

```sh
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd backend
APP_URL=http://localhost:5173 UPLOAD_DIR=./data/resumes .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite forwards `/api` to the local API. Development defaults to SQLite. There are no seeded users or invented live statistics.

```sh
cd backend
.venv/bin/python -m pytest -q
cd ../frontend
npm run build
```

## Server deployment

The deployed service directory is `/opt/candock`; the internal Compose project and volume names retain `candock` across brand changes so data is not lost. Public branding is **Candoc**. The API and database have no public ports. The frontend binds only `127.0.0.1:8280`, behind the host nginx TLS proxy.

1. Copy this source to `/opt/candock` on an Ubuntu host with Docker Compose and nginx.
2. Copy `.env.example` to `.env`, set a random hexadecimal `POSTGRES_PASSWORD`, the HTTPS `APP_URL`, and optional provider credentials. Set file mode `600`. Use URL-safe database passwords because they are interpolated into `DATABASE_URL`.
3. Point your domain's A record to the server. Adapt the hostname in `deploy/nginx-http.conf`, install it in nginx, and obtain a certificate with certbot webroot at `/var/www/candock-acme`.
4. Install the matching `deploy/nginx-https.conf`, run `nginx -t`, then reload nginx. Configure a certbot deploy hook to reload nginx after renewal.
5. Run `docker compose up -d --build`. Check `docker compose ps` and `/api/health` through HTTPS.

Do not run `docker compose config` into shared logs: the resolved configuration contains secrets. Never commit `.env`, database volumes, original resumes, or backups. One API worker is intentional: request limits are process-local. Before scaling workers or replicas, move limits and analysis concurrency control to shared storage.

## AI configuration and privacy

Set `OPENAI_API_KEY` and `AI_MODEL` in the server-only `.env`, then recreate the API: `docker compose up -d --force-recreate api`. The default model is `gpt-6-luna`, configurable without a source change. Provider model access and rates depend on your account. Requests have bounded input/output and timeouts; provider failure leaves the rubric result usable. A separate profile checkbox explicitly authorizes sending document excerpts to OpenAI. Without permission no AI request is made; public GitHub and GitLab permissions are separate from AI consent and from each other.

OpenAI requests use `store: false`; this is not a guarantee of zero provider retention. Consult your provider's current data policies and account controls. The adapter strips recognized contact/demographic metadata, but this is not exhaustive anonymization. Candidates must review their documents and assessment before making their profile visible.

LinkedIn integration uses files and text supplied by the candidate. The app extracts only allowlisted professional fields from supported ZIP CSV files, discards the original upload, and retains the extracted text and import metadata privately. It never fetches the LinkedIn profile URL. Companies are self-registered; email control can be verified, but company identity is not verified. Moderation tooling, multilingual/OCR extraction, automated employment verification and calibration against real hiring outcomes are outside this release.

## Hiring and mobility

Candidates manage **Work preferences**, companies manage **Company profile** and **Roles**, and both use the hiring dashboard and application workspace. Companies verify their email under **Account & privacy** before publishing. Existing profiles and introductions continue to work; hiring data uses additive tables with no automatic publication or demographic defaults.

Country/territory labels and supported currencies are bundled ISO catalogs. Regions such as EU, EEA and APAC are geographic declarations; citizenship never creates a work-rights claim, and region selection never proves legal permission in a member country. Authorization is self-declared and unverified. Only explicitly shared, current country/region declarations can match corresponding recruiter filters; exact scopes are matched without inferring one from another. Expired declarations remain visible with an expiry marker when shared. There is no nationality search filter.

Nationality, work rights, sponsorship and relocation preferences are stored separately from resume evidence. They do not change scores and are never passed from preferences to AI review. Candidates control profile visibility and application email sharing; revoking sharing prevents future API disclosure but cannot erase information a recipient has already exported. Withdrawing an application does not erase its participant-visible conversation history. Account deletion removes linked live records for both parties, including the conversation; retained backups follow the policy below.

Offers record proposed terms and a candidate's response. They do not provide electronic signatures, payment/escrow, payroll, invoicing, background checks, immigration advice or verification, benefits administration or an employer-of-record service. Consulting/freelance engagements use the same proposal, conversation and offer workflow; project delivery and payments are arranged separately. The current company account represents one recruiter/company, without team seats or organization RBAC. Notifications are in-app; only verification and recovery use transactional email. Calendar links and meeting locations are stored, not synchronized with an external calendar. See [API](docs/API.md) and [release verification](docs/RELEASE.md).

## GitLab.com profiles

Candidates can add `https://gitlab.com/username` under **My profile → Work beyond your resume** and enable **GitLab public analysis**. The GitHub checkbox does not authorize GitLab access. Run an assessment to read up to ten recently active public projects in the supplied user's personal namespace; README excerpts and languages are inspected for up to three original projects. Private/internal projects, forks, group contributions, and self-managed GitLab hosts are outside this integration. Account ownership and authorship are not verified.

The integration uses fixed GitLab.com REST API endpoints without credentials, does not clone or execute code, and reports inaccessible/rate-limited sources honestly. Source observations are supplementary: popularity and account availability do not change the deterministic score. Sending relevant excerpts to OpenAI still requires the separate AI checkbox. Removing the URL or changing permissions invalidates the prior assessment. Existing profiles default to an empty GitLab URL and no GitLab permission; an additive connection table preserves existing profile data.

## LinkedIn export import

On a desktop browser, candidates can open their own LinkedIn profile, choose **More** or **Resources**, then **Save to PDF** if the feature is available. LinkedIn documents language/member availability limits. For an archive, use **Settings & Privacy → Data Privacy → How LinkedIn uses your data → Download your data**, select professional categories, and request the archive.

Upload the PDF, TXT, supported professional CSV, or ZIP (maximum 5 MB) under **My profile → Work beyond your resume**. Review the extracted text, then run an assessment. Replacing or removing an import clears the old assessment so stale evidence is not displayed. The profile URL is optional and never fetched.

ZIP parsing reads only supported professional CSV categories and allowlisted columns; messages, connections, contacts, account history and unrelated personal fields are ignored. The archive is bounded, is never extracted to disk, and is discarded after parsing. Only professional text and metadata are stored, included in account export and deleted with the import/account. PDF and TXT are unstructured; review them for sensitive or confidential material before assessment or publication. Uploads are self-supplied and do not independently verify LinkedIn ownership, employment or accuracy.

Export help: [Save a profile as PDF](https://www.linkedin.com/help/linkedin/answer/a541960), [Download your LinkedIn data](https://www.linkedin.com/help/linkedin/answer/a1339364).

## Password recovery email

The login page links to `/forgot-password`. A candidate or company submits its account email, receives a link, chooses and confirms a new password, then logs in normally. Links expire after 20 minutes, work once, and are superseded by a newer request. A successful reset revokes all sessions and all outstanding links. Tokens appear in URL fragments, so they are not included in normal HTTP request/access logs. The reset page removes the fragment after loading; reopen the email if you refresh before finishing.

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY` (`ssl` or `starttls`), `SMTP_FROM`, and, where required, paired `SMTP_USERNAME`/`SMTP_PASSWORD` in the server-only `.env`, then recreate the API. TLS certificate verification is required. Use an authorized sender; possession of an unrelated application's credentials is not permission to reuse them.

If mail is unconfigured, the endpoint gives the same unavailable response for every address. When configured, requests receive an identical acceptance message whether an account exists. Unknown accounts receive no email. Known-account delivery is attempted in the background; transport failures discard the token and log a generic operational warning. Acceptance is not proof of inbox delivery. Delivery tasks are process-local best effort and are not a durable queue; request a new link after a restart or transport outage. Per-address/IP request limits and submission limits restrict abuse.

## Operations, backup and restore

Docker restart policies restore services after host restart. `docker compose logs --tail=100 api` shows operational errors without provider keys. Health checks cover API/database availability. Host TLS certificates renew through certbot; nginx must reload following renewal.

When upgrading from a release that did not connect introductions to Updates, run `docker compose exec -T api python - < deploy/backfill_introduction_updates.py` after the new API is healthy. This idempotent repair creates missing sent/received entries at the original introduction timestamps, preserves existing read states, and never resends introductions/emails or changes their status. Historical response times were not recorded, so the repair does not invent acceptance/decline timestamps; opening the introduction shows its current status.

Install `deploy/candoc-backup.service` and `.timer` under `/etc/systemd/system/`, then enable `candoc-backup.timer`. Backups run at approximately **08:45 India time** daily, retain seven days locally, and are root-only in `/var/backups/candock`. They include sensitive data. Deleted accounts can remain in these retained backups for up to seven days; do not silently restore deleted accounts. Off-server backup replication is not configured.

To restore into a stopped API, identify a backup directory, stop `api web`, and pipe the database gzip into `docker compose exec -T db psql -U candock -d candock` against an empty database. Restore `resumes.tar.gz` into the API's `/data` volume, set ownership `10001:10001`, then start services. Restoration is destructive to the target database and must be reviewed carefully. The release smoke test verifies workflows; restore into a separate environment before relying on a disaster recovery procedure.

## Open source

MIT licensed application code. Dependencies and bundled catalog data retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md). All secrets, user records and uploaded documents are excluded from source releases. See [LICENSE](LICENSE) and [SECURITY.md](SECURITY.md).
