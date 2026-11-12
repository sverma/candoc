"""Opt-in, bounded public GitHub observations. Never fetch arbitrary profile URLs."""
import asyncio
import base64
import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx


USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
MAX_RESPONSE = 1_500_000


def github_username(value: str) -> Optional[str]:
    """Accept a GitHub user URL or bare username, never host aliases or subpaths."""
    value = (value or "").strip()
    if USERNAME.fullmatch(value):
        return value if "--" not in value else None
    try:
        parsed = urlparse(value)
        if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            return None
        pieces = parsed.path.strip("/").split("/")
        if len(pieces) != 1 or not USERNAME.fullmatch(pieces[0]) or "--" in pieces[0]:
            return None
        return pieces[0]
    except ValueError:
        return None


async def _json(client: httpx.AsyncClient, path: str) -> Dict[str, Any]:
    # Paths are constructed only from validated GitHub identifiers. Redirects are disabled.
    async with client.stream("GET", "https://api.github.com" + path) as response:
        response.raise_for_status()
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_RESPONSE:
                raise ValueError("GitHub response exceeded the source size limit")
        import json
        return json.loads(bytes(body))


async def fetch_github_profile(url: str) -> Dict[str, Any]:
    """Return source observations, or a descriptive unavailable status on failure.

    The caller MUST obtain candidate consent before invoking this function. This reads
    public metadata/READMEs, does not clone or execute code, and cannot establish account
    ownership, employment, programming ability, or authorship of a repository.
    """
    username = github_username(url)
    if not username:
        return {"status": "invalid", "url": "", "detail": "Use https://github.com/username.",
                "repositories": [], "evidence": []}
    canonical = "https://github.com/" + username
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Candoc-Evidence/1.0",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(8.0),
                                    follow_redirects=False, trust_env=False) as client:
            profile = await _json(client, "/users/" + username)
            if profile.get("type") != "User":
                return {"status": "unavailable", "url": canonical,
                        "detail": "This URL identifies an organization, not a person.",
                        "repositories": [], "evidence": []}
            raw_repos = await _json(client, "/users/" + username + "/repos?sort=updated&per_page=10")
            if not isinstance(raw_repos, list):
                raise ValueError("Unexpected GitHub repository response")
            repos = []
            for item in raw_repos:
                name = str(item.get("name", ""))
                owner = str(item.get("owner", {}).get("login", ""))
                if (not REPOSITORY.fullmatch(name) or owner.lower() != username.lower()
                        or item.get("fork") or item.get("private")):
                    continue
                repos.append({"name": name, "description": str(item.get("description") or "")[:500],
                              "language": str(item.get("language") or "")[:80],
                              "url": canonical + "/" + name,
                              "archived": bool(item.get("archived")),
                              "updated_at": str(item.get("updated_at") or "")[:40]})

            async def enrich(repo: Dict[str, Any]) -> None:
                path = "/repos/" + username + "/" + repo["name"]
                try:
                    readme = await _json(client, path + "/readme")
                    if readme.get("encoding") == "base64":
                        encoded = str(readme.get("content", ""))
                        if len(encoded) <= 100_000:
                            decoded = base64.b64decode(encoded, validate=False).decode("utf-8", "replace")
                            repo["readme_excerpt"] = decoded[:12_000]
                except (httpx.HTTPError, ValueError, KeyError):
                    repo["readme_status"] = "unavailable"
                try:
                    languages = await _json(client, path + "/languages")
                    repo["languages"] = [str(key)[:80] for key in list(languages)[:12]]
                except (httpx.HTTPError, ValueError, KeyError):
                    repo["languages"] = []

            await asyncio.gather(*(enrich(repo) for repo in repos[:3]))
            observations = []
            for repo in repos[:3]:
                detail = repo["name"]
                if repo.get("description"):
                    detail += ": " + repo["description"]
                if repo.get("languages"):
                    detail += " (observed languages: " + ", ".join(repo["languages"]) + ")"
                observations.append(detail[:700])
            return {"status": "available", "url": canonical,
                    "detail": "Observed up to 10 recently updated public repositories; inspected README and languages for up to 3 original repositories. Ownership and authorship are unverified. These observations do not change the evidence score.",
                    "profile": {"login": str(profile.get("login", username))[:80],
                                "bio": str(profile.get("bio") or "")[:500]},
                    "repositories": repos, "evidence": observations}
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code in (403, 429):
            detail = "GitHub is rate limiting public access. Try again later; your evidence score is unaffected."
        elif code == 404:
            detail = "The public GitHub account was not found. Your evidence score is unaffected."
        else:
            detail = "GitHub could not be read right now. Your evidence score is unaffected."
        return {"status": "unavailable", "url": canonical, "detail": detail,
                "repositories": [], "evidence": []}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {"status": "unavailable", "url": canonical,
                "detail": "GitHub could not be read right now. Try again later; your evidence score is unaffected.",
                "repositories": [], "evidence": []}
