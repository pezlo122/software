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
    """
    Verifica que acceder a /dashboard sin login redirige a /login.
    """
    # No seguimos redirecciones para capturar la cabecera Location
    response = client.get("/dashboard", follow_redirects=False)
    # Debe devolver un 307 (o 302) de redirección
    assert response.status_code in [302, 307]
    # La cabecera Location debe apuntar a /login
    assert response.headers["location"].endswith("/login")


def test_invalid_route():
    response = client.get("/ruta_que_no_existe")
    assert response.status_code == 404
