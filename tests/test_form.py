from fastapi.testclient import TestClient
from psoftware.app import app
import json
import os
import pytest
from unittest.mock import patch

client = TestClient(app)

def login():
    """Realiza login para acceder a rutas protegidas."""
    client.post("/login", data={"identifier": "testuser", "password": "1234"})


def setup_module(module):
    """Se ejecuta antes de todos los tests para preparar el entorno."""

    # Crear carpetas necesarias si no existen
    os.makedirs("data", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)  

    # Crear usuario de prueba
    with open("data/users.csv", "w", encoding="utf-8") as f:
        f.write("username,email,password\n")
        f.write("testuser,test@example.com,1234\n")

    # Reiniciar películas personalizadas
    with open("data/custom_movies.json", "w", encoding="utf-8") as f:
        json.dump({"movies": []}, f)


@patch("psoftware.app.templates.TemplateResponse")
def test_add_movie_success(mock_template):
    login()
    response = client.post("/add-movie", data={
        "title": "Película Test",
        "description": "Descripción test",
        "poster": ""
    })
    assert response.status_code in [200, 302]
    mock_template.assert_called()


@patch("psoftware.app.templates.TemplateResponse")
def test_add_movie_missing_title(mock_template):
    login()
    response = client.post("/add-movie", data={
        "title": "",
        "description": "Algo",
        "poster": ""
    })
    assert response.status_code in [200, 302]
    mock_template.assert_called()


@patch("psoftware.app.templates.TemplateResponse")
def test_api_movie_create_and_delete(mock_template):
    login()
    # Crear película
    client.post("/add-movie", data={
        "title": "A borrar",
        "description": "temp",
        "poster": ""
    })

    # Obtener lista de películas desde la API
    response = client.get("/api/movie")
    assert response.status_code == 200
    movies_data = response.json()
    movies_list = movies_data.get("movies", [])

    # Verificar que la película fue agregada
    assert len(movies_list) > 0, "No se encontró ninguna película en la API después de agregarla"

    # Tomar el último ID
    movie_id = movies_list[-1]["id"]

    # Eliminar película
    delete_response = client.delete(f"/api/movie/{movie_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    mock_template.assert_called()
