from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os, json, csv, requests

# -----------------------------------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------------------------------

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

TMDB_API_KEY = "41d18781051e38c1a3a35fa10bfbc9b2"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

DATA_FILE = os.path.join("data", "users.csv")
CUSTOM_MOVIES_FILE = os.path.join("data", "custom_movies.json")
LIKES_FILE = os.path.join("data", "likes.json")
os.makedirs("data", exist_ok=True)

# -----------------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------------

def set_flash(request: Request, message: str, category: str = "info"):
    request.session["flash"] = {"message": message, "category": category}

def pop_flash(request: Request):
    return request.session.pop("flash", None)

def require_user(request: Request):
    user = request.session.get("user")
    if not user:
        set_flash(request, "Debes iniciar sesión.", "error")
    return user

def load_users():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_user(username, email, password):
    file_exists = os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "email", "password"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"username": username, "email": email, "password": password})

def validate_login(identifier, password):
    users = load_users()
    for u in users:
        if (u["username"] == identifier or u["email"] == identifier) and u["password"] == password:
            return True
    return False

def user_exists(username, email):
    users = load_users()
    return any(u["username"] == username or u["email"] == email for u in users)

def load_custom_movies():
    if not os.path.exists(CUSTOM_MOVIES_FILE):
        return []
    with open(CUSTOM_MOVIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("movies", [])

def save_custom_movies(movies):
    with open(CUSTOM_MOVIES_FILE, "w", encoding="utf-8") as f:
        json.dump({"movies": movies}, f, indent=4, ensure_ascii=False)

def load_likes():
    if not os.path.exists(LIKES_FILE):
        return {}
    with open(LIKES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_likes(likes):
    with open(LIKES_FILE, "w", encoding="utf-8") as f:
        json.dump(likes, f, indent=4, ensure_ascii=False)

# -----------------------------------------------------------------------------------
# LOGIN / REGISTER
# -----------------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/login")
def login_page(request: Request):
    flash = pop_flash(request)
    return templates.TemplateResponse("login.html", {"request": request, "flash": flash, "user": request.session.get("user")})

@app.post("/login")
def login_action(request: Request, identifier: str = Form(), password: str = Form()):
    if validate_login(identifier, password):
        request.session["user"] = identifier
        set_flash(request, f"Bienvenido, {identifier}!", "success")
        return RedirectResponse("/dashboard", status_code=302)
    set_flash(request, "Credenciales inválidas.", "error")
    return RedirectResponse("/login", status_code=302)

@app.get("/register")
def register_page(request: Request):
    flash = pop_flash(request)
    return templates.TemplateResponse("register.html", {"request": request, "flash": flash, "user": request.session.get("user")})

@app.post("/register")
def register_action(request: Request, username: str = Form(), email: str = Form(), password: str = Form()):
    if user_exists(username, email):
        set_flash(request, "Usuario o correo ya registrado.", "error")
        return RedirectResponse("/register", status_code=302)
    save_user(username, email, password)
    set_flash(request, "Registro exitoso.", "success")
    return RedirectResponse("/login", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    set_flash(request, "Sesión cerrada.", "success")
    return RedirectResponse("/login", status_code=302)

# -----------------------------------------------------------------------------------
# DASHBOARD CON TMDB Y CUSTOM MOVIES
# -----------------------------------------------------------------------------------

@app.get("/dashboard")
def dashboard(request: Request, page: int = 1, query: str = ""):
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    flash = pop_flash(request)

    # TMDB
    params = {"api_key": TMDB_API_KEY, "language": "es-ES", "sort_by": "popularity.desc", "page": page}
    if query:
        params["query"] = query
        tmdb_movies = requests.get(f"{TMDB_BASE_URL}/search/movie", params=params).json().get("results", [])
    else:
        tmdb_movies = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params).json().get("results", [])

    # Custom
    custom_movies = load_custom_movies()
    all_movies = tmdb_movies + custom_movies

    # Likes
    likes_data = load_likes()
    likes_map = {}
    for m in all_movies:
        likes_map[str(m["id"])] = sum(1 for u, ids in likes_data.items() if m["id"] in ids)

    prev_page = page - 1 if page > 1 else None
    next_page = page + 1

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "movies_api": tmdb_movies,
        "custom_movies": custom_movies,
        "page": page,
        "prev_page": prev_page,
        "next_page": next_page,
        "query": query,
        "user": current_user,
        "flash": flash,
        "likes_map": likes_map
    })

# -----------------------------------------------------------------------------------
# DETALLE DE PELÍCULA
# -----------------------------------------------------------------------------------

@app.get("/movie/{movie_id}")
def movie_detail(request: Request, movie_id: int):
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    flash = pop_flash(request)

    movie = next((m for m in load_custom_movies() if m["id"] == movie_id), None)
    trailer_key = None
    if not movie:
        resp = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
        movie = resp.json()
        # Trailer
        trailer_resp = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/videos", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
        videos = trailer_resp.json().get("results", [])
        trailer = next((v for v in videos if v["site"]=="YouTube" and v["type"]=="Trailer"), None)
        trailer_key = trailer["key"] if trailer else None

    # Likes
    likes_data = load_likes()
    likes = sum(1 for ids in likes_data.values() if movie_id in ids)

    return templates.TemplateResponse("movie.html", {
        "request": request,
        "movie": movie,
        "recommendations": [],
        "user": current_user,
        "flash": flash,
        "likes": likes,
        "trailer_key": trailer_key
    })

# -----------------------------------------------------------------------------------
# AGREGAR PELÍCULA PERSONALIZADA
# -----------------------------------------------------------------------------------

@app.get("/add-movie")
def add_page(request: Request):
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)
    flash = pop_flash(request)
    return templates.TemplateResponse("add_movie.html", {"request": request, "flash": flash, "user": current_user})

@app.post("/add-movie")
def add_custom_movie(request: Request, title: str = Form(default=""), description: str = Form(default=""), poster: str = Form(default=None)):
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    movies = load_custom_movies()
    new_id = max([m["id"] for m in movies], default=100000) + 1
    movies.append({
        "id": new_id,
        "title": title or "Sin título",
        "description": description or "Sin descripción",
        "poster": poster or "https://via.placeholder.com/300x450?text=No+Image"
    })
    save_custom_movies(movies)
    set_flash(request, "Película agregada.", "success")
    return RedirectResponse("/dashboard", status_code=302)

# -----------------------------------------------------------------------------------
# LIKES
# -----------------------------------------------------------------------------------

@app.post("/api/like/{movie_id}")
def like_movie(request: Request, movie_id: int):
    user = require_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    likes_data = load_likes()
    user_likes = likes_data.get(user, [])
    if movie_id not in user_likes:
        user_likes.append(movie_id)
    likes_data[user] = user_likes
    save_likes(likes_data)
    return {"status": "ok"}

# -----------------------------------------------------------------------------------
# ADMIN PANEL
# -----------------------------------------------------------------------------------

@app.get("/admin")
def admin_panel(request: Request):
    current_user = require_user(request)
    if not current_user or current_user != "admin":
        set_flash(request, "Acceso denegado.", "error")
        return RedirectResponse("/login", status_code=302)

    flash = pop_flash(request)
    likes_data = load_likes()
    custom_movies = load_custom_movies()

    admin_likes_list = []
    for user, movie_ids in likes_data.items():
        for mid in movie_ids:
            movie_info = next((m for m in custom_movies if m["id"]==mid), None)
            if not movie_info:
                resp = requests.get(f"{TMDB_BASE_URL}/movie/{mid}", params={"api_key": TMDB_API_KEY, "language": "es-ES"})
                if resp.status_code == 200:
                    data = resp.json()
                    movie_info = {"id": mid, "title": data.get("title", f"ID {mid}")}
                else:
                    movie_info = {"id": mid, "title": f"ID {mid}"}
            admin_likes_list.append({"user": user, "movie_id": movie_info["id"], "title": movie_info["title"]})

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": current_user,
        "flash": flash,
        "likes_list": admin_likes_list
    })

@app.post("/admin/delete-like/{user}/{movie_id}")
def admin_delete_like(request: Request, user: str, movie_id: int):
    current_user = require_user(request)
    if not current_user or current_user != "admin":
        set_flash(request, "Acceso denegado.", "error")
        return RedirectResponse("/login", status_code=302)

    likes_data = load_likes()
    user_likes = likes_data.get(user, [])
    if movie_id in user_likes:
        user_likes.remove(movie_id)
        likes_data[user] = user_likes
        save_likes(likes_data)
        set_flash(request, f"Like eliminado para {user}.", "success")
    else:
        set_flash(request, "No se encontró el like.", "error")

    return RedirectResponse("/admin", status_code=302)
