from fastapi.testclient import TestClient


def test_song_crud(client: TestClient) -> None:
    assert client.get(f"/api/organizations/{client.organization_id}/admin/songs").json() == []

    create_response = client.post(
        f"/api/organizations/{client.organization_id}/admin/songs",
        json={"title": "Demo Song", "artist": "Demo Artist", "slug": "demo-song", "description": "Internal test song"},
    )
    assert create_response.status_code == 201
    song = create_response.json()
    assert song["title"] == "Demo Song"
    assert song["artist"] == "Demo Artist"
    assert song["slug"] == "demo-song"
    assert song["status"] == "draft"
    assert song["originalKey"] == 0

    duplicate_response = client.post(f"/api/organizations/{client.organization_id}/admin/songs", json={"title": "Duplicate", "slug": "demo-song"})
    assert duplicate_response.status_code == 409

    list_response = client.get(f"/api/organizations/{client.organization_id}/admin/songs")
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": song["id"],
            "title": "Demo Song",
            "artist": "Demo Artist",
            "slug": "demo-song",
            "status": "draft",
            "originalKey": 0,
            "stemCount": 0,
            "readyStemCount": 0,
            "durationMs": None,
        }
    ]

    detail_response = client.get(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["description"] == "Internal test song"

    update_response = client.patch(
        f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}",
        json={"title": "Renamed Song", "artist": "Renamed Artist", "originalKey": 5},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Renamed Song"
    assert updated["artist"] == "Renamed Artist"
    assert updated["originalKey"] == 5

    delete_response = client.delete(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}").status_code == 404
