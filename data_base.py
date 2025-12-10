import csv
import json
import os

# ---------------------------
# CONFIG
# ---------------------------
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
MOVIES_FILE = os.path.join(DATA_DIR, "custom_movies.json")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ================================
# USER REPOSITORY
# ================================
class UserRepository:

    @staticmethod
    def load_users():
        if not os.path.exists(USERS_FILE):
            return []

        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def user_exists(username, email):
        users = UserRepository.load_users()
        return any(u["username"] == username or u["email"] == email for u in users)

    @staticmethod
    def validate_login(identifier, password):
        users = UserRepository.load_users()
        for u in users:
            if (u["username"] == identifier or u["email"] == identifier) and u["password"] == password:
                return True
        return False

    @staticmethod
    def save_user(username, email, password):
        file_exists = os.path.exists(USERS_FILE)
        with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["username", "email", "password"])
            if not file_exists:
                writer.writeheader()
            writer.writerow({"username": username, "email": email, "password": password})


# ================================
# CUSTOM MOVIES REPOSITORY
# ================================
class CustomMovieRepository:

    @staticmethod
    def load_movies():
        if not os.path.exists(MOVIES_FILE):
            return []

        with open(MOVIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("movies", [])

    @staticmethod
    def save_movies(movies):
        with open(MOVIES_FILE, "w", encoding="utf-8") as f:
            json.dump({"movies": movies}, f, indent=4, ensure_ascii=False)

    @staticmethod
    def add_movie(title, description, poster):
        movies = CustomMovieRepository.load_movies()
        new_id = max([m["id"] for m in movies], default=100000) + 1

        movies.append({
            "id": new_id,
            "title": title,
            "description": description,
            "poster": poster
        })

        CustomMovieRepository.save_movies(movies)
        return new_id

    @staticmethod
    def delete_movie(movie_id):
        movies = CustomMovieRepository.load_movies()
        new_list = [m for m in movies if m["id"] != movie_id]

        if len(new_list) == len(movies):
            return False  # No existía

        CustomMovieRepository.save_movies(new_list)
        return True


# ================================
# MOVIE RATINGS (LIKE / DISLIKE)
# ================================
class RatingRepository:

    @staticmethod
    def load_ratings():
        if not os.path.exists(RATINGS_FILE):
            return {}

        with open(RATINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_ratings(ratings):
        with open(RATINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ratings, f, indent=4, ensure_ascii=False)

    @staticmethod
    def rate_movie(user, movie_id, rating):
        """
        rating = 1 (like)
        rating = -1 (dislike)
        """
        ratings = RatingRepository.load_ratings()

        if user not in ratings:
            ratings[user] = {}

        ratings[user][str(movie_id)] = rating

        RatingRepository.save_ratings(ratings)
        return True

    @staticmethod
    def get_user_rating(user, movie_id):
        ratings = RatingRepository.load_ratings()
        user_ratings = ratings.get(user, {})
        return user_ratings.get(str(movie_id), 0)
