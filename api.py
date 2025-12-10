from fastapi import APIRouter, HTTPException
from data_base import CustomMovieRepository, RatingRepository
import requests
import os

router = APIRouter(prefix="/api")

TMDB_API_KEY = "41d18781051e38c1a3a35fa10bfbc9b2"
TMDB_BASE_URL = "https://api.themoviedb.org/3"


# ============================
# GET ALL CUSTOM MOVIES
# ============================
@router.get("/movies")
def get_movies():
    return {"movies": CustomMovieRepository.load_movies()}


# ============================
# GET MOVIE BY ID
# ============================
@router.get("/movie/{movie_id}")
def get_movie(movie_id: int):
    movies = CustomMovieRepository.load_movies()
    movie = next((m for m in movies if m["id"] == movie_id), None)

    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    return movie


# ============================
# ADD CUSTOM MOVIE
# ============================
@router.post("/movie/add")
def add_movie(title: str, description: str, poster: str = None):
    poster = poster or "https://via.placeholder.com/300x450?text=No+Image"
    new_id = CustomMovieRepository.add_movie(title, description, poster)

    return {"message": "created", "id": new_id}


# ============================
# DELETE CUSTOM MOVIE
# ============================
@router.delete("/movie/{movie_id}")
def delete_movie(movie_id: int):
    ok = CustomMovieRepository.delete_movie(movie_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {"message": "deleted", "id": movie_id}


# ============================
# LIKE / DISLIKE MOVIE
# ============================
@router.post("/movie/{movie_id}/rate")
def rate_movie(movie_id: int, user: str, rating: int):
    """
    rating:
      1  = like
     -1  = dislike
    """
    if rating not in [-1, 1]:
        raise HTTPException(status_code=400, detail="Invalid rating")

    RatingRepository.rate_movie(user, movie_id, rating)

    return {"message": "rating updated"}


# ============================
# GET TRAILER VIA TMDB
# ============================
@router.get("/movie/{movie_id}/trailer")
def get_trailer(movie_id: int):
    r = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}/videos",
        params={"api_key": TMDB_API_KEY, "language": "es-ES"}
    ).json()

    videos = r.get("results", [])
    trailers = [v for v in videos if v["type"] == "Trailer" and v["site"] == "YouTube"]

    if not trailers:
        raise HTTPException(status_code=404, detail="Trailer not found")

    youtube_key = trailers[0]["key"]
    youtube_url = f"https://www.youtube.com/embed/{youtube_key}"

    return {"trailer_url": youtube_url}
