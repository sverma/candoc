# Candoc hiring workspace release contract

Keep existing resume/GitHub/GitLab/LinkedIn/introductions functionality. New persistence is additive tables with on-delete cascades; no destructive migration. Public content must be intentionally published. JSON snake_case, errors `{detail}`. Real data only. All employment decisions are explicit user actions. Nationality and work-right declarations NEVER enter rubric or AI sources.

## Ownership

- Marketplace agent: backend/app/hiring.py, hiring_models.py, hiring_schemas.py, backend/tests/test_hiring.py. Jobs, companies, applications, invitations, saved jobs, messaging, interviews, offers, notifications, dashboard.
- Preferences agent: backend/app/preferences.py, preference_models.py, preference_schemas.py, countries.py, backend/tests/test_preferences.py; frontend/src/Preferences.jsx. Candidate work/mobility preferences and company-facing consent-aware summary. May supply a documented integration patch to main owner; DO NOT edit main.py or frontend main.jsx.
- Frontend agent: frontend/src/Hiring.jsx, hiring.css, main.jsx integration/nav, styles as needed. Full roles/workspace/company/pipeline/notifications flows. Integrate Preferences component by documented interface. Keep existing flows.
- Root: backend main.py glue and auth/email verification new files, frontend Verification.jsx, docs/deploy/QA/release. Root supplies catalogs if needed in coordination.

Factories avoid circular imports: new modules expose `build_router()` which imports `.main` dependencies INSIDE factory; root calls after all existing main functions are defined. `Base.metadata.create_all` must see all new models before startup. Existing session get_db/current_user/candidate_user/company_user/profile_json/rate_limit remain shared.

## Shared catalogs

GET `/api/hiring/catalogs` => `{countries:[{code,name}],regions:[{code,name}],currencies:[{code,name}],engagement_types:[{value,label}],work_modes:[...],time_commitments:[...]}`. Preference agent supplies `catalogs()` and country/region/currency validators for BOTH routers. Full ISO countries; a region is geographic scope, never a legal entitlement. Explicit region records: EU, EEA, EUROPE, NORTH_AMERICA, SOUTH_AMERICA, APAC, MIDDLE_EAST, AFRICA, GLOBAL. Codes distinct from countries. Do not infer citizenship/authorization from geography.

Enums: engagement `permanent|contract|freelance|consulting|temporary|internship|apprenticeship|volunteer`; work_mode `remote|hybrid|onsite`; time_commitment `full_time|part_time|flexible`; support `not_specified|available|case_by_case|not_available`; pay period `hour|day|week|month|year|project`; level `any|entry|junior|mid|senior|lead|executive`.

## Candidate preferences (preferences agent)

GET/PUT `/api/hiring/preferences` => `{preferences}` candidate only; fields:
`engagement_types:[]`, `work_modes:[]`, `time_commitment:"flexible"`, `preferred_countries:[]`, `preferred_regions:[]`, `nationalities:[]` ISO country codes (optional), `work_authorizations:[{scope_type:"country"|"region",scope_code,status:"unrestricted"|"permit_held"|"needs_sponsorship"|"unknown",valid_until:null|YYYY-MM-DD,notes:""}]`, `share_work_authorization:false`, `share_nationality:false`, `sponsorship_need:"not_required"|"required"|"discuss"|"not_specified"`, `willing_to_relocate:false`, `relocation_countries:[]`, `relocation_regions:[]`, `timezone:""`, `languages:[{name,proficiency:"basic"|"conversational"|"professional"|"native"}]`, `available_from:null|date`, `notice_days:null|0..365`, `hours_per_week:null|0..168`, `compensation_min:null|number`, `compensation_max:null|number`, `currency:""`, `pay_period:"year"`, `portfolio_url:""`, `preferred_title:""`.
Private by default. `professional_preferences(profile_id,db)` returns company-safe summary (exclude nationality/authorizations unless corresponding explicit flag, exclude permit notes by default). Root adds `work_preferences` to profile_json ONLY explicitly shared safe data; own profile receives full via preferences endpoint. No demographic/nationality directory filters. Expose self-declared authorization scope country/region filter only if shared, never auto reject/rank. Expired declaration marked expired; not legal verification. `export_preferences(user,db)` for account export. FK cascade removes data.

Preferences.jsx default export `Preferences({api})`, self-contained fetch/save; named `MobilitySummary({preferences})` display company-facing summary; uses catalog endpoint + actual API fields. Standalone page `/app/preferences`.

## Company profile and jobs (marketplace agent)

GET/PUT `/api/hiring/company` => `{company}` company only. Fields `name,website,industry,size,headquarters,about` plus `email_verified` from verification helper if available. Public company JSON contains no account email.
GET `/api/hiring/jobs?search=&engagement_type=&work_mode=&country=&region=&visa_sponsorship=&relocation_support=&saved=&mine=&status=&limit=30&offset=0` => `{jobs:[],total}`. Public lists only published; own mine includes drafts/paused/closed; filters enums; saved candidate only. No nationality filtering.
GET `/api/hiring/jobs/{id}` => `{job}` published public or owner, applicant access retains closed role context without exposing drafts to strangers.
POST `/api/hiring/jobs`, PATCH `/api/hiring/jobs/{id}` => `{job}` owned company only. Job fields `id,title,description,engagement_type,time_commitment,work_mode,country_codes:[],region_codes:[],city,compensation_min,max,currency,pay_period,duration_months:null|number,hours_per_week:null|number,skills:[],experience_level,visa_sponsorship,visa_details,relocation_support,relocation_details,status:"draft"|"published"|"paused"|"closed",company_id,company_name,company,created_at,updated_at,application_count(owner only),saved(own candidate)`. Require coherent compensation and ISO codes; published onsite/hybrid needs country. All types supported. Draft defaults. Close/paused disallows new apply/invite but existing workspace stays.
PUT `/api/hiring/jobs/{id}/save` `{saved:bool}` => `{saved}` own candidate.

## Applications and reverse invitations (marketplace agent)

POST `/api/hiring/jobs/{id}/apply` candidate `{message,share_contact:false}` => `{application}`; only published, unique job+candidate.
POST `/api/hiring/jobs/{id}/invite` company owner `{candidate_id,message}` => `{application}` stage invited; candidate must be discoverable. Reverse hiring preserved.
GET `/api/hiring/applications?job_id=&stage=` => `{applications:[]}` current participant only. Row includes id/job/title/company/candidate name/stage/created_at, safe professional profile when authorized, no email without share_contact.
GET `/api/hiring/applications/{id}` => `{application,messages:[],interviews:[],offers:[]}` participant only; candidate cannot see company-only draft offers if any.
PATCH `/api/hiring/applications/{id}` candidate `{action:"accept_invitation"|"decline_invitation"|"withdraw",share_contact?:bool}` => `{application}`.
PATCH `/api/hiring/applications/{id}/stage` owned company `{stage:"reviewing"|"interviewing"|"rejected"|"hired"}` => `{application}` valid transitions; hired only after accepted offer. Terminal records cannot silently reopen. Active statuses invited/applied/reviewing/interviewing/offer; terminal hired/rejected/withdrawn/declined.
Candidate accepting invitation grants professional-profile visibility to the hiring team for that application; directory privacy otherwise remains. Only share_contact true shares email; can revoke for future reads, cannot retract prior disclosures. No resume originals shared automatically.

POST `/api/hiring/applications/{id}/messages` `{body}` => `{message}` participant only, bounded/rate limited; messages in-app only.
POST `/api/hiring/applications/{id}/interviews` company `{starts_at:ISO-awareUTC,duration_minutes:15..240,location_or_url,notes}` => `{interview}`; active application only. PATCH `/api/hiring/interviews/{id}` company reschedule/cancel/complete OR candidate `{rsvp:"accepted"|"declined"}`. Rescheduling resets RSVP. Validate timestamps and safe links; no external calendar/email execution.

Closing an application as withdrawn, declined, rejected or hired cancels pending scheduled interviews and preserves their history. Completed interviews remain unchanged. Messages remain available after hiring, but closed declined/rejected/withdrawn conversations are read-only.
POST `/api/hiring/applications/{id}/offers` company `{summary,compensation_min,max,currency,pay_period,start_date:null|date,expires_at:null|awareISO,visa_sponsorship,visa_details,relocation_support,relocation_details}` => `{offer}` sent, moves stage offer, only one active sent offer at a time. Terms are a hiring record; formal contract execution/payments are not implemented. PATCH `/api/hiring/offers/{id}` candidate `{status:"accepted"|"declined"}` or company `{status:"withdrawn"}`; honor expiry, idempotent/replay-safe actions. Accepted offer permits explicit company mark hired. Preserve history. Do not auto-hire based on profile/score/nationality.

GET `/api/hiring/notifications` => `{notifications:[],unread_count}` recipient only; PATCH `/notifications/{id}` `{read:true}`; POST `/notifications/read-all`. Create notifications for apply/invite/stage/message/interview/offer actions; no external SMTP sends.

The same feed includes original introduction sent/received and accept/decline events. Introduction events carry `introduction_id` and cascade-delete with that source. Feed ordering/cap/read controls/dashboard/export span both notification tables. A unique introduction/recipient/event key makes backfills and repeated event recording idempotent. Historical creation events retain their original timestamp; historical response timestamps are not fabricated.
GET `/api/hiring/dashboard` => actual role-specific counts/pipeline/upcoming items.
`export_hiring(user,db)` returns all own company/jobs/applications/messages/interviews/offers/notifications/saved jobs for root export integration. FK cascades delete records with deleted participants. Tests must prove tenant isolation, complete transitions, expiry/RSVP, draft privacy, consent, validation, no inference from nationality.

## Email verification (root)

Root adds GET user.email_verified, POST `/api/auth/request-verification`, POST `/api/auth/verify-email` `{token}`. Additive hashed token storage. Email verification proves email control only, never company identity. Root will coordinate optional publish/apply/contact gates after testing; do not block new endpoint implementation waiting for this. No demographic info into AI or evidence scores.

## Frontend integration (frontend agent)

Hiring.jsx exports `JobsPage({api,user})`, `JobDetail({api,user})`, `CompanyProfile({api,user})`, `HiringDashboard({api,user})`, `ApplicationsPage({api,user})`, `ApplicationDetail({api,user})`, `NotificationsPage({api,user})`, `RoleEditor({api,user})` if separate. Routes public `/jobs`, `/jobs/:id`; app `/app/jobs`, `/app/jobs/new`, `/app/jobs/:id/edit`, `/app/hiring`, `/app/applications`, `/app/applications/:id`, `/app/company`, `/app/preferences`, `/app/notifications`. Add nav by role and public roles link. Main passes api/user into standalone components. Use responsive existing Candoc design, accessible actual forms, real empty/loading/error states. Role list/forms, pipeline, messages, RSVP, offers, invite-candidate-from-role flow all API-backed. Existing introductions remain. Root Verification.jsx integration specs will follow.
