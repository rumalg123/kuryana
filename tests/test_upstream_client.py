"""Offline regression tests for MyDramaList HTTP client behavior."""
import asyncio

from app.handlers.parser import Parser


def test_success_uses_working_client_settings(monkeypatch):
    requested = {}

    class FakeClient:
        def __init__(self, **kwargs):
            requested["options"] = kwargs

        def get(self, url, headers):
            requested["url"] = url
            requested["headers"] = headers
            return type("Response", (), {
                "status_code": 200, "headers": {},
                "text": "<html><body>Success</body></html>",
            })()

    monkeypatch.setattr("app.handlers.parser.primp.Client", FakeClient)
    result = asyncio.run(Parser.scrape("803562-merry-berry-love", "page"))

    assert result.ok is True
    assert result.status_code == 200
    assert requested["options"] == {
        "impersonate": "chrome_131", "impersonate_os": "linux"
    }
    assert "Chrome/85.0.4183.123" in requested["headers"]["User-Agent"]
    assert requested["headers"]["Referer"] == "https://mydramalist.com/"
    assert requested["url"] == "https://mydramalist.com/803562-merry-berry-love"


def test_challenge_returns_useful_error(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def get(self, url, headers):
            return type("Response", (), {
                "status_code": 403,
                "headers": {"cf-mitigated": "challenge"},
                "text": "<html><title>Just a moment...</title></html>",
            })()

    monkeypatch.setattr("app.handlers.parser.primp.Client", FakeClient)
    result = asyncio.run(Parser.scrape("803562-merry-berry-love", "page"))

    assert result.ok is False
    assert result.status_code == 502
    assert result.res_get_err() == {
        "error": True,
        "code": 502,
        "description": "MyDramaList returned a Cloudflare challenge",
    }


def test_normal_404_keeps_site_error_description(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def get(self, url, headers):
            return type("Response", (), {
                "status_code": 404,
                "headers": {},
                "text": (
                    '<div class="app-body"><div class="box-body">'
                    "<h1>The requested page was not found</h1>"
                    "<p>You can see this page because the URL you are accessing "
                    "cannot be found.</p></div></div>"
                ),
            })()

    monkeypatch.setattr("app.handlers.parser.primp.Client", FakeClient)
    result = asyncio.run(Parser.scrape("missing-title", "page"))

    assert result.ok is False
    assert result.status_code == 404
    assert result.res_get_err() == {
        "error": True,
        "code": 404,
        "description": {
            "title": "The requested page was not found",
            "info": "You can see this page because the URL you are accessing cannot be found.",
        },
    }
