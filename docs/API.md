# Candoc v2 API contract

Self-hosted reverse hiring marketplace. FastAPI + SQLAlchemy backend, React/Vite frontend. PostgreSQL production; SQLite tests/local. API `/api`, cookie sessions. JSON snake_case. Candidate controlled visibility. Assessment is evidence completeness, never hiring suitability or automatic employment decisions. Missing external accounts must never reduce score. LinkedIn content supplied by candidate; no scraping.

## Models and API
- `POST /api/auth/register` `{email,password,name,role:"candidate"|"company",company_name?}` returns `{user}`; `POST /api/auth/login` `{email,password}` returns `{user}`; `POST /api/auth/logout`; `GET /api/auth/me` `{user:null|{id,email,name,role,company_name}}`.
- `POST /api/auth/forgot-password` `{email}` returns generic `202 {detail}` with configured mail delivery, `503` uniformly if unconfigured. No account disclosure or reset token in the API response.
- `POST /api/auth/reset-password` `{token,password}` consumes a single-use 20-minute token and revokes all sessions; returns `200 {detail}` without signing in. Invalid, expired or replayed tokens return `400`.
- `GET /api/stats` `{candidates,companies,introductions}` actual counts.
- `GET /api/candidates?search=&skill=&location=&min_score=&sort=recent|score` returns `{candidates:[profile]}`. Authenticated company discovery; unauthenticated returns `{candidates:[]}`. `GET /api/candidates/{id}` returns `{candidate:profile}` authorized published profiles. Candidate profile contains `id,user_id,name,headline,location,bio,skills:[],years_experience,availability,github_url,gitlab_url,linkedin_url,visible,assessment:null|assessment,created_at`. No private contact information except accepted introductions.
- `GET /api/profile` `{profile}` candidate own; `PUT /api/profile` editable profile fields (headline, location, bio, skills array, years_experience, availability, github_url, gitlab_url, linkedin_url, linkedin_text, visible, consent_public_analysis, consent_gitlab_analysis). Name from user.
- `POST /api/profile/resume` multipart file PDF/DOCX/TXT max 5MB; returns `{profile}`; `POST /api/profile/analyze` returns `{profile}` (extract text, separately opt-in GitHub and GitLab.com APIs, LinkedIn supplied text; no paid AI required; transparent deterministic rubric).
- `POST /api/profile/linkedin/import` multipart `file` (PDF/TXT/CSV/ZIP, max 5 MB) returns `{profile}` with private `linkedin_import` containing extracted professional `text`, `filename`, `sections`, `type:"candidate_export"`, `imported_at`. Replaces the prior import and invalidates the assessment; originals are discarded.
- `DELETE /api/profile/linkedin/import` removes the imported document text/metadata and invalidates the assessment; re-upload is allowed. No LinkedIn website request is made by either endpoint.
- `GET /api/rubric` `{version,description,dimensions:[{key,label,weight,description}],limitations:[]}`.
- Assessment `{score:1..5,confidence:"low"|"medium"|"high",summary,dimensions:[{key,label,score,weight,evidence:[],improvements:[]}],strengths:[],improvements:[],sources:[{type,status,url?,detail}],analyzed_at,version}`. Five dimensions: skills_evidence .25, experience_detail .25, impact .20, project_depth .20, clarity .10. Bound scores anchored 1..5. Ignore protected traits, pedigree/prestige, gaps, followers/stars, lack of profiles. Evidence snippets auditable. No claims of verified employment; no unexplained LLM judgments.
- `POST /api/introductions` company `{candidate_id,role_title,message,salary_range?,work_mode?}` returns `{introduction}`.
- `GET /api/introductions` `{introductions:[]}` own incoming/outgoing. Introduction `{id,candidate_id,candidate_name,company_name,role_title,message,salary_range,work_mode,status:"pending"|"accepted"|"declined",created_at,contact_email?}`. Only accepted shares candidate email with sender.
- `PATCH /api/introductions/{id}` candidate `{status:"accepted"|"declined"}`.
- `DELETE /api/account` current user deletion cascade & invalidate sessions.
- `GET /api/account/export` own JSON export.
- `GET /api/health` health JSON.

Errors `{detail:"human readable message"}`. No demo users in production. Frontend can have clearly labeled sample cards on landing only; discovery must use live data. Development may have optional explicit seed command, never auto seed. Visible score label: "Evidence score". Display human review notice in rubric/detail. Password >= 12 chars. Production requires HTTPS secure cookie. Rate limit auth/upload/analyze. User consent before network enrichment. Limit extracted text, fixed GitHub/GitLab.com API hosts + validated usernames to prevent SSRF. No secrets committed. Environment in `.env.example`.

## Hiring workspace additions

See [hiring contract](HIRING-CONTRACT.md) for field definitions, enums and permission rules. Routes below are under `/api/hiring`; existing API routes are preserved.

| Resource | Routes and behavior |
| --- | --- |
| Catalogs | `GET /catalogs`: bundled countries, currencies, regions and engagement/support enums. Public; no profile data. |
| Preferences | Candidate `GET /preferences`, `PUT /preferences`: full candidate-only work and mobility preferences. Public professional profiles append `work_preferences` with consent-based sensitive fields. |
| Company | Company `GET /company`, `PUT /company`: its professional company profile. Public jobs include company information and email-control verification status. |
| Roles | `GET /jobs`, `GET /jobs/{id}` public published roles. Company `POST /jobs`, `PATCH /jobs/{id}` own roles. `mine=true` includes own drafts; closed roles cannot reopen. |
| Role filters | `search`, `engagement_type`, `work_mode`, `country`, `region`, `visa_sponsorship`, `relocation_support`, `saved`, `mine`, `status`, `limit`, `offset`; listing returns `{jobs,total}`. |
| Saved roles | Candidate `PUT /jobs/{id}/save` `{saved:bool}`. |
| Applications | Candidate `POST /jobs/{id}/apply` `{message,share_contact:false}`; company `POST /jobs/{id}/invite` `{candidate_id,message}`. One record per candidate/role. |
| Hiring workspace | Participant `GET /applications`, `GET /applications/{id}`; detail returns application, messages, interviews and offers. |
| Candidate decisions | `PATCH /applications/{id}` with `action:accept_invitation|decline_invitation|withdraw` and/or `share_contact:bool`. Sharing true requires verified email; revocation remains available. |
| Company pipeline | `PATCH /applications/{id}/stage` `{stage:reviewing|interviewing|rejected|hired}`; transitions validated, hired requires an accepted offer. |
| Messages | Participant `POST /applications/{id}/messages` `{body}`; retained history with no messaging after rejection, withdrawal or decline. |
| Interviews | Company `POST /applications/{id}/interviews`; participant `PATCH /interviews/{id}`. Company controls schedule/status, candidate controls RSVP. Rescheduling resets RSVP. Explicit timezone offsets required. |
| Offers | Company `POST /applications/{id}/offers`; participant `PATCH /offers/{id}` `{status:accepted|declined|withdrawn}`. Only candidates accept/decline; only companies withdraw. Expiry and prior responses are enforced. |
| Notifications | `GET /notifications`, `PATCH /notifications/{id}` `{read:true}`, `POST /notifications/read-all`; own recipient only. |
| Dashboard | `GET /dashboard`: actual counts, stage totals, upcoming interviews and recent applications. |

`POST /api/auth/request-verification` sends the signed-in user's own email a verification link and returns `202`; `POST /api/auth/verify-email` `{token}` consumes it, without signing in. `user.email_verified` is included in auth/export responses. Tokens are never exposed in API responses.

Candidate directory additionally supports `engagement_type`, `work_mode`, `relocation`, `sponsorship_need`, `preferred_country`, `preferred_region`, `authorization_country` and `authorization_region`. The latter two match exact, shared, current self-declarations only. Nationality is never a query criterion. `/api/account/export` now includes raw own `work_preferences` and participant-scoped `hiring` data; deletion cascades all linked new tables.
