from fastapi.testclient import TestClient
from psoftware.app import app

client = TestClient(app)

def test_404_api_movie_not_found():
    response = client.get("/api/movie/99999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_delete_movie_not_found():
    response = client.delete("/api/movie/555555")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_protected_route_without_login():
    response = client.get("/dashboard")
    # Se redirige a login
    assert response.status_code in [200, 302]


def test_invalid_route():
    response = client.get("/ruta_que_no_existe")
    assert response.status_code == 404
