"""Bounded anonymous GitLab.com public-project observations, never code execution."""
import asyncio
import base64
import json
import re
from typing import Any, Dict, Optional
from urllib.parse import quote, unquote, urlparse

import httpx

API = "https://gitlab.com/api/v4"
MAX_RESPONSE = 1_500_000
USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,253}[A-Za-z0-9_-]$")
PROJECT_PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,254}$")
RESERVED = {"-", "api", "admin", "assets", "abuse_reports", "dashboard", "explore", "groups", "help", "import", "login", "new", "notifications", "oauth", "profile", "projects", "public", "robots.txt", "root", "search", "session", "signup", "sitemap.xml", "snippets", "unsubscribes", "uploads", "users"}


def canonical_gitlab_url(value: str) -> Optional[str]:
    if not isinstance(value, str) or not value or len(value) > 300 or value != value.strip():
        return None
    try:
        parsed = urlparse(value)
        if (parsed.scheme != "https" or parsed.netloc.lower() != "gitlab.com"
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            return None
        match = re.fullmatch(r"/([^/]+)/?", parsed.path)
        username = match.group(1).lower() if match else ""
        if (not USERNAME.fullmatch(username) or username in RESERVED or ".." in username
                or username.endswith((".git", ".atom"))):
            return None
        return "https://gitlab.com/" + username
    except (TypeError, ValueError):
        return None


def _id(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value < 10**15


def _readme_path(project: Dict[str, Any], username: str) -> Optional[str]:
    value = project.get("readme_url")
    if not value:
        return "README.md"
    if not isinstance(value, str) or len(value) > 1500:
        return None
    parsed = urlparse(value)
    if (parsed.scheme != "https" or parsed.netloc != "gitlab.com" or parsed.query
            or parsed.fragment or parsed.username or parsed.password):
        return None
    branch = project.get("default_branch")
    if not isinstance(branch, str) or not branch or len(branch) > 250 or "\\" in branch or any(part in {".", "..", ""} for part in branch.split("/")):
        return None
    path = unquote(parsed.path)
    for prefix in ("/" + username + "/" + project["path"] + "/-/blob/" + branch + "/",
                   "/" + username + "/" + project["path"] + "/blob/" + branch + "/"):
        if path.casefold().startswith(prefix.casefold()):
            relative = path[len(prefix):]
            if (not relative or len(relative) > 512 or "\\" in relative or "%" in relative
                    or any(ord(char) < 32 for char in relative)
                    or any(part in {".", "..", ""} for part in relative.split("/"))
                    or not re.fullmatch(r"readme(?:[._ -].{0,100})?", relative.rsplit("/", 1)[-1], re.I)):
                return None
            return relative
    return None


async def _json(client: httpx.AsyncClient, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    # Every caller constructs paths from fixed routes, validated numeric IDs or URL-encoded filenames.
    client.cookies.clear()
    async with client.stream("GET", API + path, params=params) as response:
        response.raise_for_status()
        if response.headers.get("content-length", "").isdigit() and int(response.headers["content-length"]) > MAX_RESPONSE:
            raise ValueError("Source response too large")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_RESPONSE:
                raise ValueError("Source response too large")
        return json.loads(bytes(body))


def _unavailable(url: str, detail: str) -> Dict[str, Any]:
    return {"status": "unavailable", "url": url, "detail": detail, "profile": {}, "repositories": [], "evidence": []}


async def fetch_gitlab_profile(url: str) -> Dict[str, Any]:
    """Caller must obtain candidate public-analysis consent before invoking this function."""
    canonical = canonical_gitlab_url(url)
    if not canonical:
        return {**_unavailable("", "Use https://gitlab.com/username for a personal public profile."), "status": "invalid"}
    username = canonical.rsplit("/", 1)[-1]

    async def fetch() -> Dict[str, Any]:
        async with httpx.AsyncClient(headers={"Accept": "application/json", "User-Agent": "Candoc-Evidence/1.0"},
                                    timeout=httpx.Timeout(7.0, connect=4.0), follow_redirects=False,
                                    trust_env=False) as client:
            users = await _json(client, "/users", {"username": username, "humans": "true", "per_page": 2})
            if not isinstance(users, list):
                raise ValueError("Invalid users response")
            matches = [user for user in users[:2] if isinstance(user, dict) and isinstance(user.get("username"), str)
                       and user["username"].lower() == username]
            if len(matches) != 1 or not _id(matches[0].get("id")):
                return _unavailable(canonical, "The public GitLab user was not found. Your evidence score is unaffected.")
            user = matches[0]
            if (any(user.get(key) is not None and user.get(key) is not False for key in ("bot", "private_profile", "locked"))
                    or user.get("state", "active") != "active"):
                return _unavailable(canonical, "This GitLab profile is private, unavailable or not a personal human account. Your evidence score is unaffected.")
            projects = await _json(client, "/users/" + str(user["id"]) + "/projects",
                                   {"visibility": "public", "order_by": "last_activity_at", "sort": "desc", "per_page": 10})
            if not isinstance(projects, list):
                raise ValueError("Invalid project response")
            repos = []
            originals = []
            seen = set()
            for project in projects[:10]:
                if not isinstance(project, dict) or not _id(project.get("id")) or project["id"] in seen:
                    continue
                namespace = project.get("namespace")
                path = project.get("path")
                if (not isinstance(namespace, dict) or namespace.get("kind") != "user"
                        or not isinstance(namespace.get("path"), str) or namespace["path"].lower() != username
                        or project.get("visibility") != "public" or project.get("forked_from_project") is not None
                        or project.get("forked_from_project_id") is not None or project.get("fork")
                        or not isinstance(path, str) or not PROJECT_PATH.fullmatch(path) or ".." in path):
                    continue
                seen.add(project["id"])
                repo = {"name": str(project.get("name") or path)[:120],
                        "description": str(project.get("description") or "")[:500],
                        "url": canonical + "/" + path, "language": "", "languages": [],
                        "archived": project.get("archived") is True}
                repos.append(repo)
                originals.append((project, repo))

            async def enrich(project: Dict[str, Any], repo: Dict[str, Any]) -> None:
                prefix = "/projects/" + str(project["id"])
                try:
                    languages = await _json(client, prefix + "/languages")
                    if isinstance(languages, dict):
                        repo["languages"] = [key[:80] for key, value in list(languages.items())[:12]
                                             if isinstance(key, str) and isinstance(value, (int, float))
                                             and not isinstance(value, bool) and 0 <= value <= 100]
                        repo["language"] = repo["languages"][0] if repo["languages"] else ""
                except (httpx.HTTPError, ValueError, TypeError):
                    pass
                file_path = _readme_path(project, username)
                if not file_path:
                    repo["readme_status"] = "unavailable"
                    return
                try:
                    readme = await _json(client, prefix + "/repository/files/" + quote(file_path, safe=""), {"ref": "HEAD"})
                    if not isinstance(readme, dict) or readme.get("encoding") != "base64":
                        raise ValueError("Invalid README response")
                    content = readme.get("content")
                    if not isinstance(content, str) or len(content) > 100_000:
                        raise ValueError("README exceeds limit")
                    decoded = base64.b64decode(re.sub(r"\s+", "", content), validate=True)
                    if len(decoded) > 75_000:
                        raise ValueError("README exceeds limit")
                    repo["readme_excerpt"] = decoded.decode("utf-8", "replace")[:12_000]
                    repo["readme_status"] = "available"
                except (httpx.HTTPError, ValueError, TypeError, UnicodeError):
                    repo["readme_status"] = "unavailable"

            await asyncio.gather(*(enrich(project, repo) for project, repo in originals[:3]))
            evidence = []
            for repo in repos[:3]:
                text = repo["name"] + (": " + repo["description"] if repo["description"] else "")
                if repo["languages"]:
                    text += " (observed languages: " + ", ".join(repo["languages"]) + ")"
                evidence.append(text[:700])
            return {"status": "available", "url": canonical,
                    "detail": "Observed up to 10 recent public projects in the personal namespace; inspected languages and README for up to 3 originals. Forks and non-public projects excluded. Ownership, authorship and code quality are unverified. This supplementary source does not change the evidence score.",
                    "profile": {"login": username}, "repositories": repos, "evidence": evidence}

    try:
        return await asyncio.wait_for(fetch(), timeout=20.0)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403, 429):
            return _unavailable(canonical, "GitLab anonymous API access is unavailable or rate limited. No authentication or bypass was attempted. Your evidence score is unaffected.")
        return _unavailable(canonical, "GitLab public data could not be read right now. Your evidence score is unaffected.")
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, TypeError, KeyError):
        return _unavailable(canonical, "GitLab public data could not be read right now. Try again later; your evidence score is unaffected.")
