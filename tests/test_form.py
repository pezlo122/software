from fastapi.testclient import TestClient
from psoftware.app import app, save_user, save_custom_movies, save_user
import json, os

client = TestClient(app)

def login():
    """Realiza login para acceder a rutas protegidas."""
    client.post("/login", data={"identifier": "testuser", "password": "1234"})


def setup_module(module):
    """Se ejecuta antes de todos los tests."""
    os.makedirs("data", exist_ok=True)

    # Crear usuario
    with open("data/users.csv", "w", encoding="utf-8") as f:
        f.write("username,email,password\n")
        f.write("testuser,test@example.com,1234\n")

    # Reiniciar películas personalizadas
    with open("data/custom_movies.json", "w", encoding="utf-8") as f:
        json.dump({"movies": []}, f)


def test_add_movie_success():
    login()
    response = client.post("/add-movie", data={
        "title": "Película Test",
        "description": "Descripción test",
        "poster": ""
    })
    assert response.status_code == 200 or response.status_code == 302


def test_add_movie_missing_title():
    login()
    response = client.post("/add-movie", data={
        "title": "",
        "description": "Algo",
        "poster": ""
    })
    # FastAPI permite vacíos, este test valida solo que responde bien
    assert response.status_code in [200, 302]


def test_api_movie_create_and_delete():
    # Crear
    login()
    client.post("/add-movie", data={
        "title": "A borrar",
        "description": "temp",
        "poster": ""
    })

    movies = client.get("/api/movie").json()
    movie_id = movies[-1]["id"]

    # Eliminar
    delete_response = client.delete(f"/api/movie/{movie_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
