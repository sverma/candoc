# Candoc v1 API contract

Self-hosted reverse hiring marketplace. FastAPI + SQLAlchemy backend, React/Vite frontend. PostgreSQL production; SQLite tests/local. API `/api`, cookie sessions. JSON snake_case. Candidate controlled visibility. Assessment is evidence completeness, never hiring suitability or automatic employment decisions. Missing external accounts must never reduce score. LinkedIn content supplied by candidate; no scraping.

## Models and API
- `POST /api/auth/register` `{email,password,name,role:"candidate"|"company",company_name?}` returns `{user}`; `POST /api/auth/login` `{email,password}` returns `{user}`; `POST /api/auth/logout`; `GET /api/auth/me` `{user:null|{id,email,name,role,company_name}}`.
- `POST /api/auth/forgot-password` `{email}` returns generic `202 {detail}` with configured mail delivery, `503` uniformly if unconfigured. No account disclosure or reset token in the API response.
- `POST /api/auth/reset-password` `{token,password}` consumes a single-use 20-minute token and revokes all sessions; returns `200 {detail}` without signing in. Invalid, expired or replayed tokens return `400`.
- `GET /api/stats` `{candidates,companies,introductions}` actual counts.
- `GET /api/candidates?search=&skill=&location=&min_score=&sort=recent|score` returns `{candidates:[profile]}`. Authenticated company discovery; unauthenticated returns `{candidates:[]}`. `GET /api/candidates/{id}` returns `{candidate:profile}` authorized published profiles. Candidate profile contains `id,user_id,name,headline,location,bio,skills:[],years_experience,availability,github_url,linkedin_url,visible,assessment:null|assessment,created_at`. No private contact information except accepted introductions.
- `GET /api/profile` `{profile}` candidate own; `PUT /api/profile` editable profile fields (headline, location, bio, skills array, years_experience, availability, github_url, linkedin_url, linkedin_text, visible, consent_public_analysis). Name from user.
- `POST /api/profile/resume` multipart file PDF/DOCX/TXT max 5MB; returns `{profile}`; `POST /api/profile/analyze` returns `{profile}` (extract text, opt-in GitHub API, LinkedIn supplied text; no paid AI required; transparent deterministic rubric).
- `GET /api/rubric` `{version,description,dimensions:[{key,label,weight,description}],limitations:[]}`.
- Assessment `{score:1..5,confidence:"low"|"medium"|"high",summary,dimensions:[{key,label,score,weight,evidence:[],improvements:[]}],strengths:[],improvements:[],sources:[{type,status,url?,detail}],analyzed_at,version}`. Five dimensions: skills_evidence .25, experience_detail .25, impact .20, project_depth .20, clarity .10. Bound scores anchored 1..5. Ignore protected traits, pedigree/prestige, gaps, followers/stars, lack of profiles. Evidence snippets auditable. No claims of verified employment; no unexplained LLM judgments.
- `POST /api/introductions` company `{candidate_id,role_title,message,salary_range?,work_mode?}` returns `{introduction}`.
- `GET /api/introductions` `{introductions:[]}` own incoming/outgoing. Introduction `{id,candidate_id,candidate_name,company_name,role_title,message,salary_range,work_mode,status:"pending"|"accepted"|"declined",created_at,contact_email?}`. Only accepted shares candidate email with sender.
- `PATCH /api/introductions/{id}` candidate `{status:"accepted"|"declined"}`.
- `DELETE /api/account` current user deletion cascade & invalidate sessions.
- `GET /api/account/export` own JSON export.
- `GET /api/health` health JSON.

Errors `{detail:"human readable message"}`. No demo users in production. Frontend can have clearly labeled sample cards on landing only; discovery must use live data. Development may have optional explicit seed command, never auto seed. Visible score label: "Evidence score". Display human review notice in rubric/detail. Password >= 12 chars. Production requires HTTPS secure cookie. Rate limit auth/upload/analyze. User consent before network enrichment. Limit extracted text, fixed GitHub host + validated username to prevent SSRF. No secrets committed. Environment in `.env.example`.
