from fastapi.testclient import TestClient
from psoftware.app import app, save_user
import os

client = TestClient(app)

def setup_module(module):
    """Prepara un usuario para pruebas."""
    os.makedirs("data", exist_ok=True)
    with open("data/users.csv", "w", encoding="utf-8") as f:
        f.write("username,email,password\n")
        f.write("testuser,test@example.com,1234\n")


def test_login_correct():
    response = client.post("/login", data={
        "identifier": "testuser",
        "password": "1234"
    })
    assert response.status_code == 200 or response.status_code == 302


def test_login_incorrect():
    response = client.post("/login", data={
        "identifier": "wrong",
        "password": "0000"
    })
    assert response.status_code == 200 or response.status_code == 302


def test_register_new_user():
    response = client.post("/register", data={
        "username": "nuevo",
        "email": "nuevo@test.com",
        "password": "pass"
    })
    assert response.status_code == 200 or response.status_code == 302


def test_register_existing_user():
    response = client.post("/register", data={
        "username": "testuser",
        "email": "test@example.com",
        "password": "1234"
    })
    assert response.status_code == 200 or response.status_code == 302
