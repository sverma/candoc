# Release verification

## Hiring platform expansion — 12 November 2026

Version 2 adds eight engagement types, searchable roles and saved roles, company profiles, candidate work/mobility preferences, reverse invitations and direct applications, a participant-only conversation/pipeline, interviews with RSVP, offers, in-app notifications and email-control verification. Existing accounts, assessments and introductions are preserved; all new storage is additive.

- **285 backend tests passed**, including 41 preference/catalog/privacy cases, 23 hiring cases and five email-verification cases. The frontend production build passed locally and in the Linux deployment container. A TestClient deprecation warning remains in the test toolchain; no test failed.
- A public HTTPS/PostgreSQL smoke check covered all eight engagement types, drafts and publication, company email-verification gates, visa/relocation and saved-role filters, a private-profile application, contact sharing and revocation, company invitations, messages, interview scheduling/rescheduling/RSVP, offers, explicit hire, notifications, account export and cascade deletion.
- Real verification messages were accepted by the existing encrypted SMTP service for Resend's simulated-delivery sink. Concurrent public submissions consumed each verification link once; concurrent offer creation produced exactly one active offer. This proves provider acceptance and application behavior, not delivery to every real-world inbox.
- Browser review checked company and candidate dashboards, a contract-role draft with hourly compensation and support terms, an application message, a timezone-aware interview, offer creation/confirmation, candidate RSVP, privacy defaults and preference saving. Desktop and 390-pixel layouts were inspected; the reviewed browser session reported no console errors/warnings. This is not an exhaustive accessibility, browser or device audit.
- Independent review found and fixed stale application/role data during route changes and pending interviews stranded after hiring. Record identity guards prevent actions against another displayed record. Hiring now cancels scheduled interviews while preserving completed history.
- A pre-upgrade private backup completed. All synthetic accounts and linked hiring records were removed; the three original accounts remained and hiring test tables returned to zero. Sensitive preference fields never enter scoring/AI; private notes remain candidate-only and recruiter filters cannot infer authorization from nationality.

Offers are recorded proposals/responses, with formal contracts, signatures, payroll, payments, immigration verification, external calendar sync and organization team seats outside this release. Work rights and company identity remain unverified; email verification establishes email control only. See README for the detailed operating boundaries.

## Initial release

Deployed on 12 November 2026 to the requested server, with an isolated Compose project and PostgreSQL database. Primary URL: https://candoc.org. The www hostname and temporary bootstrap hostname redirect to the primary site.

## Evidence collected

- 216 backend/evaluation/provider/parser/recovery/export/GitLab tests passed on the patched dependency set.
- Python dependency audit reported no known vulnerabilities for the selected requirements; npm installation audit also reported none.
- Production frontend built successfully in the server's Linux container.
- A live HTTPS workflow verified candidate/company signup, resume upload, assessment, discoverability, introduction, acceptance, private contact release, JSON export and account deletion.
- One live OpenAI analysis completed with six supported observations. Its reported token usage was 504 input and 676 output tokens. Quotes were checked against supplied text; this does not validate the interpretations or the overall assessment.
- Disposable synthetic accounts and introductions were deleted; live counts returned to their baseline.
- The real GitHub API returned six public repository summaries and three README excerpts for its example account. No authorship or employment was inferred.
- Desktop and narrow-screen landing/methodology views were reviewed; browser console had no observed warnings/errors during that review. This is not an exhaustive accessibility or cross-browser audit.
- HTTPS returns a valid certificate, security headers, and a working health endpoint. The API/database are not directly exposed on public ports.
- The first private database/upload backup completed successfully. A daily timer retains seven days locally; no off-server replication or full restore drill has been performed.
- The other four existing hosted applications continued to return HTTP 200 after deployment.
- LinkedIn export import is deployed for candidate PDF/TXT/CSV/ZIP uploads. The live HTTPS test verified professional-field extraction, exclusion of messages/connections/birth/address fields, assessment integration, private full-text access, replacement, removal and disposable-account cleanup. A browser ZIP upload also succeeded and displayed the extracted experience and skills; no console errors were observed during this review.
- Password recovery was added after the initial deployment. A live-database test sent a reset link and password-change notification through real encrypted SMTP to Resend's documented simulated-delivery address. Both were accepted; the test verified old-password rejection, new-password login, session revocation, token replay rejection and account cleanup. This confirms provider acceptance, not delivery to every real-world inbox.
- Recovery currently uses the operator-authorized existing Resend account and its already verified sender, displayed as Candoc. A new Candoc-domain sender has not been provisioned. No new provider credentials or permissions were created.
- The recovery screens built successfully. Their initial browser interaction check was unavailable; the backend/SMTP integration and public endpoint checks completed independently. Browser access was restored for the later LinkedIn upload review.

## Scope of this release

The numeric 1–5 assessment is a transparent heuristic score of document evidence. Optional OpenAI commentary provides deeper qualitative observations but does not change that score. Neither feature verifies employment, skill level, identity, source ownership or hiring suitability. LinkedIn uses candidate-uploaded PDF/TXT/CSV/ZIP exports and pasted content. URLs are references only; no LinkedIn website request is made. Scores are not calibrated against job performance.

The initial release did not verify company identity or email ownership. The expansion above adds email-control verification; company identity verification, moderation tooling, OCR, multilingual review and a calibrated hiring model remain outside this release. See README and EVALUATION for operating limits.
