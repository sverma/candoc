# Security

Do not include API keys, passwords, resumes, candidate details or database exports in public issues. Report reproducible security defects privately through the repository owner's GitHub profile or private security advisory when available.

The deployed database is isolated on the Compose network. Files are private, generated names are used for storage, sessions are hashed in the database, and production cookies require HTTPS. API writes check allowed origins. Provider requests use fixed hosts and bounded timeouts; arbitrary profile URLs are never fetched.

This initial release does not verify email ownership or company identity and has no automated abuse moderation. The operator must provide a monitored contact channel and review company access before a broad public launch. AI outputs and public source metadata are untrusted. Resume claims are not verified.

Dependency inputs are pinned in Python requirements and the npm lockfile. Update, test and rebuild periodically. Never expose PostgreSQL or the internal API port publicly. Backups contain candidate data and are stored separately from source code.
