from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.server as server


def _matches_filter(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, value in query.items():
        if isinstance(value, dict) and "$in" in value:
            if doc.get(key) not in value["$in"]:
                return False
        else:
            if doc.get(key) != value:
                return False
    return True


def _apply_projection(doc: dict[str, Any], projection: dict[str, int] | None) -> dict[str, Any]:
    if not projection:
        return deepcopy(doc)
    out = deepcopy(doc)
    if projection.get("_id") == 0:
        out.pop("_id", None)
    return out


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    async def to_list(self, limit: int):
        return [deepcopy(d) for d in self._docs[:limit]]


class FakeCollection:
    def __init__(self):
        self.docs: list[dict[str, Any]] = []

    async def find_one(self, query: dict[str, Any], projection: dict[str, int] | None = None):
        for doc in self.docs:
            if _matches_filter(doc, query):
                return _apply_projection(doc, projection)
        return None

    async def insert_one(self, doc: dict[str, Any]):
        self.docs.append(deepcopy(doc))
        return SimpleNamespace(inserted_id=doc.get("id"))

    def find(self, query: dict[str, Any], projection: dict[str, int] | None = None):
        out = []
        for doc in self.docs:
            if _matches_filter(doc, query):
                out.append(_apply_projection(doc, projection))
        return FakeCursor(out)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        for idx, doc in enumerate(self.docs):
            if _matches_filter(doc, query):
                updated = deepcopy(doc)
                for key, value in (update.get("$set") or {}).items():
                    updated[key] = value
                self.docs[idx] = updated
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)


class FakeDB:
    def __init__(self):
        self.users = FakeCollection()
        self.songs = FakeCollection()
        self.albums = FakeCollection()


class TruthyCrashLegacyDB:
    """Mimics pymongo db truthiness behavior (raises on bool evaluation)."""

    def __init__(self):
        self.users = FakeCollection()

    def __bool__(self):  # pragma: no cover - explicitly behavior-based
        raise NotImplementedError("Database objects do not implement truth value testing")


class FakeCompletions:
    @staticmethod
    def create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[-1]["content"] if messages else ""

        if "Field: title" in prompt:
            content = "Midnight Drive"
        elif "Field: music_prompt" in prompt:
            content = (
                "A tight 110 BPM electronic-pop groove with warm analog bass and sidechained synth pads. "
                "Build from sparse verse textures into a bright chorus hook with layered vocal harmonies."
            )
        elif "Field: genres" in prompt:
            content = "Electronic, Pop"
        elif "Field: vocal_languages" in prompt:
            content = "English"
        elif "Field: lyrics" in prompt:
            content = "A late-night confidence anthem built around motion, city lights, and release."
        elif "Field: artist_inspiration" in prompt:
            content = "The Weeknd, Dua Lipa"
        elif "Field: video_style" in prompt:
            content = (
                "Urban night visuals with moving handheld shots, practical neon lighting, and rhythmic edits "
                "that hit with each kick."
            )
        elif "Field: duration" in prompt:
            content = "52s"
        else:
            content = "Creative suggestion"

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class FakeOpenAI:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


@pytest.fixture()
def test_client(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "legacy_db", None)
    monkeypatch.setattr(server, "openai_client", FakeOpenAI())
    monkeypatch.setattr(server, "OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(server, "REPLICATE_API_TOKEN", None)
    monkeypatch.setattr(server, "MUSICGEN_API_URL", None)
    monkeypatch.setattr(server, "MUSICGEN_API_KEY", None)
    monkeypatch.setattr(server, "RECENT_SUGGESTIONS", {})
    return TestClient(server.app)


def _signup_and_login(client: TestClient):
    signup_payload = {"name": "Flow User", "mobile": "9990001111"}
    signup_res = client.post("/api/auth/signup", json=signup_payload)
    assert signup_res.status_code == 200, signup_res.text

    login_res = client.post("/api/auth/login", json={"mobile": signup_payload["mobile"]})
    assert login_res.status_code == 200, login_res.text
    return login_res.json()


def test_auth_and_dashboard_flow(test_client: TestClient):
    user = _signup_and_login(test_client)
    dashboard = test_client.get(f"/api/dashboard/{user['id']}")
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert payload["songs"] == []
    assert payload["albums"] == []


@pytest.mark.parametrize(
    "field, expected_key",
    [
        ("title", "Midnight Drive"),
        ("music_prompt", "BPM"),
        ("genres", "Electronic"),
        ("vocal_languages", "__valid_language__"),
        ("lyrics", "hook"),
        ("artist_inspiration", "Weeknd"),
        ("video_style", "Urban"),
        ("duration", "s"),
    ],
)
def test_field_specific_suggestions(test_client: TestClient, field: str, expected_key: str):
    payload = {
        "field": field,
        "current_value": "",
        "context": {
            "music_prompt": "dark electronic pop with punchy drums",
            "genres": ["Electronic", "Pop"],
            "lyrics": "",
            "artist_inspiration": "",
            "duration_seconds": 45,
        },
    }
    res = test_client.post("/api/suggest", json=payload)
    assert res.status_code == 200, res.text
    suggestion = res.json()["suggestion"]
    assert suggestion
    if expected_key == "__valid_language__":
        assert suggestion == "Instrumental" or suggestion in server.LANGUAGE_KNOWLEDGE_BASE
    else:
        assert expected_key.lower() in suggestion.lower()
    if field == "lyrics":
        assert "once upon a time" not in suggestion.lower()


def test_song_create_and_video_fallback(test_client: TestClient):
    user = _signup_and_login(test_client)
    create_payload = {
        "title": "",
        "music_prompt": "dark electronic pop with sidechained bass and tight drums",
        "genres": ["Electronic", "Pop"],
        "duration_seconds": 45,
        "vocal_languages": ["Instrumental"],
        "lyrics": "",
        "artist_inspiration": "The Weeknd",
        "generate_video": False,
        "video_style": "",
        "user_id": user["id"],
    }
    create_res = test_client.post("/api/songs/create", json=create_payload)
    assert create_res.status_code == 200, create_res.text
    song = create_res.json()
    assert song["id"]
    assert song["audio_url"]
    assert song["title"]

    video_res = test_client.post(f"/api/songs/{song['id']}/generate-video?user_id={user['id']}")
    assert video_res.status_code == 200, video_res.text
    video_payload = video_res.json()
    assert video_payload["status"] in {"generated", "processing"}

    status_res = test_client.get(f"/api/songs/{song['id']}/video-status?user_id={user['id']}")
    assert status_res.status_code == 200, status_res.text
    status_payload = status_res.json()
    assert status_payload["video_status"] in {"completed", "processing", "pending"}


def test_album_create_and_album_video_generation(test_client: TestClient):
    user = _signup_and_login(test_client)
    album_payload = {
        "title": "Road Lights",
        "music_prompt": "",
        "genres": ["Electronic"],
        "vocal_languages": ["English"],
        "lyrics": "",
        "artist_inspiration": "Dua Lipa",
        "generate_video": True,
        "video_style": "Night drive aesthetic",
        "num_songs": 2,
        "user_id": user["id"],
        "album_songs": [
            {
                "title": "",
                "music_prompt": "energetic opener with punchy synth bass and big chorus",
                "genres": ["Electronic", "Pop"],
                "duration_seconds": 40,
                "vocal_languages": ["English"],
                "lyrics": "",
                "artist_inspiration": "The Weeknd",
                "video_style": "Neon city run",
            },
            {
                "title": "",
                "music_prompt": "dreamy closer with wide pads and gentle arpeggios",
                "genres": ["Electronic", "Ambient"],
                "duration_seconds": 55,
                "vocal_languages": ["Instrumental"],
                "lyrics": "",
                "artist_inspiration": "Tycho",
                "video_style": "Soft cinematic haze",
            },
        ],
    }
    album_res = test_client.post("/api/albums/create", json=album_payload)
    assert album_res.status_code == 200, album_res.text
    album = album_res.json()
    assert album["id"]
    assert len(album["songs"]) == 2

    gen_res = test_client.post(f"/api/albums/{album['id']}/generate-videos?user_id={user['id']}")
    assert gen_res.status_code == 200, gen_res.text
    gen_payload = gen_res.json()
    assert gen_payload["total_videos_generated"] == 2

    dashboard = test_client.get(f"/api/dashboard/{user['id']}")
    assert dashboard.status_code == 200, dashboard.text
    data = dashboard.json()
    assert len(data["albums"]) >= 1
    assert data["albums"][0]["id"] == album["id"]


def test_replicate_url_extraction_callable_url():
    class FakeOutput:
        @staticmethod
        def url():
            return "https://replicate.delivery/output.mp4"

    extracted = server._extract_replicate_media_url(FakeOutput())
    assert extracted == "https://replicate.delivery/output.mp4"


def test_legacy_db_bool_regression(monkeypatch):
    fake_db = FakeDB()
    legacy = TruthyCrashLegacyDB()
    legacy_user = {
        "id": "legacy-user-1",
        "name": "Legacy User",
        "mobile": "1234500000",
        "created_at": "2026-02-16T00:00:00+00:00",
    }
    legacy.users.docs.append(legacy_user)

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "legacy_db", legacy)
    monkeypatch.setattr(server, "openai_client", FakeOpenAI())
    monkeypatch.setattr(server, "OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(server, "MUSICGEN_API_URL", None)
    monkeypatch.setattr(server, "MUSICGEN_API_KEY", None)
    monkeypatch.setattr(server, "REPLICATE_API_TOKEN", None)
    monkeypatch.setattr(server, "RECENT_SUGGESTIONS", {})

    client = TestClient(server.app)

    # Health endpoint should not crash on legacy_db truthiness checks.
    health_res = client.get("/api/health")
    assert health_res.status_code == 200, health_res.text
    assert health_res.json()["status"] == "healthy"

    # Login should use legacy lookup path safely.
    login_res = client.post("/api/auth/login", json={"mobile": legacy_user["mobile"]})
    assert login_res.status_code == 200, login_res.text
    assert login_res.json()["id"] == legacy_user["id"]
