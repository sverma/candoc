# Initial release verification

Deployed on 12 November 2026 to the requested server, with an isolated Compose project and PostgreSQL database. Primary URL: https://candoc.org. The www hostname and temporary bootstrap hostname redirect to the primary site.

## Evidence collected

- 59 backend/evaluation/provider/parser tests passed on the patched dependency set.
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

## Scope of this release

The numeric 1–5 assessment is a transparent heuristic score of document evidence. Optional OpenAI commentary provides deeper qualitative observations but does not change that score. Neither feature verifies employment, skill level, identity, source ownership or hiring suitability. LinkedIn uses candidate-supplied content, not unrestricted URL scraping. Scores are not calibrated against job performance.

Company and email ownership verification, password recovery/delivery, moderation tooling, OCR, multilingual review and a calibrated hiring model remain outside this initial release. See README and EVALUATION for operating limits.
