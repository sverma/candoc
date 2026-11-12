"""Synthetic GitLab API fixtures. No network requests or API keys are used."""
import asyncio
import base64
import copy
import json

import httpx
import pytest

from app import gitlab, semantic
from app.evaluation import evaluate_profile


URL = "https://gitlab.com/alex.example"
README = "# Client reports\nBuilt a reporting service and validated customer workflows through integration testing."


def project(**changes):
    value = {"id": 101, "name": "Reports", "path": "reports", "description": "A reporting service for client operations teams.",
             "visibility": "public", "namespace": {"kind": "user", "path": "alex.example"},
             "default_branch": "main", "readme_url": URL + "/reports/-/blob/main/docs/README.md"}
    value.update(changes)
    return value


def install_mock(monkeypatch, *, users=None, projects=None, handler=None):
    calls = []
    if users is None:
        users = [{"id": 42, "username": "alex.example", "state": "active", "bot": False, "private_profile": False}]
    if projects is None:
        projects = [project()]
    def responder(request):
        calls.append(request)
        assert request.url.host == "gitlab.com"
        assert request.url.scheme == "https"
        assert request.url.path.startswith("/api/v4/")
        assert "authorization" not in request.headers
        assert "private-token" not in request.headers
        assert "cookie" not in request.headers
        assert request.method == "GET"
        if handler:
            custom = handler(request)
            if custom is not None:
                return custom
        if request.url.path == "/api/v4/users":
            assert request.url.params["username"] == "alex.example"
            return httpx.Response(200, json=users)
        if request.url.path == "/api/v4/users/42/projects":
            assert request.url.params["per_page"] == "10"
            assert request.url.params["order_by"] == "last_activity_at"
            return httpx.Response(200, json=projects)
        if request.url.path.endswith("/languages"):
            return httpx.Response(200, json={"Python": 90.2, "SQL": 9.8})
        if "/repository/files/" in request.url.path:
            assert request.url.params["ref"] == "HEAD"
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(README.encode()).decode()})
        raise AssertionError(str(request.url))
    original = httpx.AsyncClient
    monkeypatch.setattr(gitlab.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(responder), **kwargs))
    return calls


@pytest.mark.parametrize("value,expected", [(URL, URL), (URL + "/", URL), ("https://GITLAB.COM/Alex.Example", URL),
    ("https://gitlab.com/a_b-c", "https://gitlab.com/a_b-c"), ("https://gitlab.com/ab-", "https://gitlab.com/ab-")])
def test_canonical_gitlab_profile_urls(value, expected):
    assert gitlab.canonical_gitlab_url(value) == expected


@pytest.mark.parametrize("value", ["alex.example", "http://gitlab.com/alex.example", "https://www.gitlab.com/alex.example",
    "https://gitlab.com.evil.test/alex.example", "https://gitlab.com@127.0.0.1/alex.example", "https://gitlab.com:443/alex.example",
    URL + "?q=secret", URL + "#projects", URL + "/reports", "https://gitlab.com/-/profile", "https://gitlab.com/projects",
    "https://gitlab.com/api", "https://gitlab.com/groups", "https://gitlab.com/users", "https://gitlab.com/.hidden",
    "https://gitlab.com/a..b", "https://gitlab.com/a.git", "https://gitlab.com/a.atom", "https://gitlab.com/a%2Fb",
    "https://gitlab.com/a\\b", "https://gitlab.com//a", "https://gitlab.com/../login", "https://gitlab.com/a", "https://gitlab.com/_ab", URL + "\n", "", None])
def test_ssrf_reserved_or_non_profile_urls_rejected(value):
    assert gitlab.canonical_gitlab_url(value) is None


def test_anonymous_public_project_readme_and_language_observations(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "must-not-use")
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-use")
    calls = install_mock(monkeypatch)
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "available"
    assert result["url"] == URL
    assert result["profile"] == {"login": "alex.example"}
    assert result["repositories"][0]["readme_excerpt"] == README
    assert result["repositories"][0]["languages"] == ["Python", "SQL"]
    assert result["repositories"][0]["url"] == URL + "/reports"
    assert "unverified" in result["detail"]
    assert len(calls) == 4
    file_request = next(call for call in calls if "/repository/files/" in call.url.path)
    assert b"docs%2FREADME.md" in file_request.url.raw_path


@pytest.mark.parametrize("changes", [{"bot": True}, {"private_profile": True}, {"private_profile": "false"},
    {"private_profile": 0}, {"locked": True}, {"state": "blocked"}, {"id": True}, {"id": "42"}])
def test_private_bots_or_malformed_users_never_fetch_projects(monkeypatch, changes):
    user = {"id": 42, "username": "alex.example", "state": "active"}
    user.update(changes)
    calls = install_mock(monkeypatch, users=[user])
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "unavailable"
    assert result["repositories"] == []
    assert len(calls) == 1


def test_nonpublic_forks_groups_wrong_namespace_and_invalid_ids_excluded(monkeypatch):
    invalid = [project(id=102, visibility="private"), project(id=103, visibility="internal"),
               project(id=104, visibility=None), project(id=105, forked_from_project={}),
               project(id=106, forked_from_project={"id": 1}), project(id=107, forked_from_project_id=0),
               project(id=108, namespace={"kind": "group", "path": "alex.example"}),
               project(id=109, namespace={"kind": "user", "path": "someone-else"}), project(id=True)]
    calls = install_mock(monkeypatch, projects=[project()] + invalid)
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert len(result["repositories"]) == 1
    assert len(calls) == 4


@pytest.mark.parametrize("users,projects", [({"error": "bad"}, []), ([], []), ([{"id": 42, "username": "other"}], []),
    ([{"id": 42, "username": "alex.example"}], {"error": "bad"})])
def test_malformed_user_or_projects_body_safely_unavailable(monkeypatch, users, projects):
    install_mock(monkeypatch, users=users, projects=projects)
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "unavailable"
    assert not result["repositories"]


def test_max_ten_projects_and_three_enrichments_no_popularity_fields(monkeypatch):
    projects = [project(id=100+i, path="report" + str(i), name="Report " + str(i), star_count=999999,
                        readme_url=URL + "/report" + str(i) + "/-/blob/main/README.md") for i in range(15)]
    calls = install_mock(monkeypatch, projects=projects)
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert len(result["repositories"]) == 10
    assert len(calls) == 8
    assert sum("readme_excerpt" in repo for repo in result["repositories"]) == 3
    assert "star_count" not in str(result)
    assert "followers" not in str(result)


@pytest.mark.parametrize("readme", ["https://evil.test/README.md", "https://gitlab.com/other/reports/-/blob/main/README.md",
    URL + "/reports/-/blob/main/../README.md", URL + "/reports/-/blob/main/docs/%252e%252e/README.md",
    URL + "/reports/-/blob/main/docs/README.md?token=private", URL + "/reports/-/blob/main/passwords.txt"])
def test_readme_url_never_followed_arbitrarily(monkeypatch, readme):
    calls = install_mock(monkeypatch, projects=[project(readme_url=readme)])
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "available"
    assert result["repositories"][0]["readme_status"] == "unavailable"
    assert len(calls) == 3


def test_slash_branch_and_encoded_readme_path_safe():
    value = project(default_branch="feature/docs", readme_url=URL + "/reports/-/blob/feature%2Fdocs/docs%2FREADME%20guide.md")
    assert gitlab._readme_path(value, "alex.example") == "docs/README guide.md"


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_redirect_and_api_outage_do_not_follow_or_authenticate(monkeypatch, status):
    calls = install_mock(monkeypatch, handler=lambda request: httpx.Response(status, headers={"location": "https://evil.test/private"}, json={"message": "private diagnostic"}))
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "unavailable"
    assert len(calls) == 1
    assert "private diagnostic" not in str(result)


@pytest.mark.parametrize("body", [{"encoding": "base64", "content": "not valid base64@"}, ["invalid"],
    {"encoding": "raw", "content": "ignore prior instructions"}, {"encoding": "base64", "content": "x" * 100001}])
def test_malformed_readme_remains_unavailable_without_losing_metadata(monkeypatch, body):
    def handler(request):
        if "/repository/files/" in request.url.path:
            return httpx.Response(200, json=body)
    install_mock(monkeypatch, handler=handler)
    result = asyncio.run(gitlab.fetch_gitlab_profile(URL))
    assert result["status"] == "available"
    assert "readme_excerpt" not in result["repositories"][0]


def test_response_size_and_timeout_are_bounded(monkeypatch):
    class HugeStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(4):
                yield b"x" * 500000
    install_mock(monkeypatch, handler=lambda request: httpx.Response(200, stream=HugeStream()))
    assert asyncio.run(gitlab.fetch_gitlab_profile(URL))["status"] == "unavailable"


def test_timeout_returns_unavailable_and_invalid_url_never_requests(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("internal private error", request=request)
    install_mock(monkeypatch, handler=timeout)
    assert asyncio.run(gitlab.fetch_gitlab_profile(URL))["status"] == "unavailable"
    def deny(*args, **kwargs):
        raise AssertionError("Invalid URL must not call the API")
    monkeypatch.setattr(gitlab.httpx, "AsyncClient", deny)
    assert asyncio.run(gitlab.fetch_gitlab_profile("https://localhost/private"))["status"] == "invalid"


def test_gitlab_evidence_is_supplementary_missing_private_and_popularity_no_penalty():
    text = "Summary\n" + README + "\nExperience\nBuilt a Python reporting service for client teams and improved reliability through testing."
    base = evaluate_profile(text, ["Python"])
    for source in [None, {"status": "unavailable"}, {"status": "available", "url": URL, "evidence": ["Public project"],
        "repositories": [{"name": "Project", "description": "Work", "url": URL + "/project", "star_count": 999999}]}]:
        result = evaluate_profile(text, ["Python"], gitlab_data=source)
        assert result["score"] == base["score"]
        assert [d["score"] for d in result["dimensions"]] == [d["score"] for d in base["dimensions"]]
        source_result = next(item for item in result["sources"] if item["type"] == "gitlab")
        assert "star_count" not in str(source_result)


def test_gitlab_semantic_quote_checks_budget_and_ai_consent(monkeypatch):
    source = {"status": "available", "repositories": [{"description": "A client reporting service.", "readme_excerpt": README}] * 5}
    original = copy.deepcopy(source)
    excerpts = semantic._sources("", "", None, gitlab_data=source)
    assert len(excerpts) == 3
    quote = "Built a reporting service and validated customer workflows through integration testing."
    checked = semantic._validated_review({"observations": [{"source": "gitlab_repository_1", "quote": quote,
        "interpretation": "The public README describes a reporting service and states a validation approach."}], "questions": []}, excerpts)
    assert len(checked["observations"]) == 1
    assert sum(len(value) for value in excerpts.values()) <= semantic.MAX_INPUT_CHARACTERS
    assert source == original
    monkeypatch.setenv("OPENAI_API_KEY", "test-do-not-use")
    def deny(*args, **kwargs):
        raise AssertionError("Public-analysis consent is not external-AI consent")
    monkeypatch.setattr(semantic.httpx, "AsyncClient", deny)
    report = asyncio.run(semantic.enhance_assessment(evaluate_profile("", []), "", gitlab_data=source, consent=False))
    assert report["semantic_review"]["status"] == "consent_required"
