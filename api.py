from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter(prefix="/api")

CUSTOM_MOVIES_FILE = os.path.join("data", "custom_movies.json")

# -----------------------------
# Helper functions
# -----------------------------
def load_custom_movies():
    if not os.path.exists(CUSTOM_MOVIES_FILE):
        return []
    with open(CUSTOM_MOVIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("movies", [])

def save_custom_movies(movies):
    with open(CUSTOM_MOVIES_FILE, "w", encoding="utf-8") as f:
        json.dump({"movies": movies}, f, indent=4, ensure_ascii=False)

# -----------------------------
# 📌 GET – listar todas las películas personalizadas
# -----------------------------
@router.get("/movies")
def get_movies():
    return {"custom_movies": load_custom_movies()}

# -----------------------------
# 📌 GET – obtener una película por ID
# -----------------------------
@router.get("/movie/{movie_id}")
def get_movie(movie_id: int):
    movies = load_custom_movies()
    for m in movies:
        if m["id"] == movie_id:
            return m
    raise HTTPException(status_code=404, detail="Película no encontrada")

# -----------------------------
# 📌 POST – agregar película personalizada
# -----------------------------
@router.post("/movie/add")
def add_movie(title: str, description: str, poster: str = None):
    movies = load_custom_movies()
    new_id = max([m["id"] for m in movies], default=100000) + 1

    new_movie = {
        "id": new_id,
        "title": title,
        "description": description,
        "poster": poster or "https://via.placeholder.com/300x450?text=No+Image"
    }

    movies.append(new_movie)
    save_custom_movies(movies)

    return {"message": "Película agregada correctamente", "movie": new_movie}

# -----------------------------
# 📌 DELETE – eliminar película personalizada
# -----------------------------
@router.delete("/movie/{movie_id}")
def delete_movie(movie_id: int):
    movies = load_custom_movies()
    updated = [m for m in movies if m["id"] != movie_id]

    if len(updated) == len(movies):
        raise HTTPException(status_code=404, detail="Película no encontrada para eliminar")

    save_custom_movies(updated)
    return {"message": "Película eliminada con éxito"}
