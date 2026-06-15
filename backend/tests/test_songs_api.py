from fastapi.testclient import TestClient


def test_song_crud(client: TestClient) -> None:
    assert client.get("/api/songs").json() == []

    create_response = client.post(
        "/api/songs",
        json={"title": "Demo Song", "slug": "demo-song", "description": "Internal test song"},
    )
    assert create_response.status_code == 201
    song = create_response.json()
    assert song["title"] == "Demo Song"
    assert song["slug"] == "demo-song"
    assert song["status"] == "draft"

    duplicate_response = client.post("/api/songs", json={"title": "Duplicate", "slug": "demo-song"})
    assert duplicate_response.status_code == 409

    list_response = client.get("/api/songs")
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": song["id"],
            "title": "Demo Song",
            "slug": "demo-song",
            "status": "draft",
            "stemCount": 0,
            "readyStemCount": 0,
            "durationMs": None,
        }
    ]

    detail_response = client.get(f"/api/songs/{song['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["description"] == "Internal test song"

    delete_response = client.delete(f"/api/songs/{song['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/songs/{song['id']}").status_code == 404
