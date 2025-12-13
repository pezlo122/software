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
# UTILIDADES
# -----------------------------------------------------------------------------------

def set_flash(request: Request, message: str, category: str = "info"):
    request.session["flash"] = {"message": message, "category": category}

def pop_flash(request: Request):
    return request.session.pop("flash", None)

def require_user(request: Request):
    return request.session.get("user")

# -----------------------------------------------------------------------------------
# USUARIOS
# -----------------------------------------------------------------------------------

def load_users():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_user(username, email, password):
    exists = os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "email", "password"])
        if not exists:
            writer.writeheader()
        writer.writerow({"username": username, "email": email, "password": password})

def validate_login(identifier, password):
    for u in load_users():
        if (u["username"] == identifier or u["email"] == identifier) and u["password"] == password:
            return u["username"]   # 👈 SIEMPRE USERNAME
    return None

def user_exists(username, email):
    return any(u["username"] == username or u["email"] == email for u in load_users())

# -----------------------------------------------------------------------------------
# LIKES
# -----------------------------------------------------------------------------------

def load_likes():
    if not os.path.exists(LIKES_FILE):
        return {}
    with open(LIKES_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_likes(data):
    with open(LIKES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# -----------------------------------------------------------------------------------
# ROOT / AUTH
# -----------------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "flash": pop_flash(request), "user": None}
    )

@app.post("/login")
def login_action(request: Request, identifier: str = Form(), password: str = Form()):
    username = validate_login(identifier, password)
    if username:
        request.session["user"] = username
        set_flash(request, f"Bienvenido {username}", "success")
        return RedirectResponse("/dashboard", status_code=302)

    set_flash(request, "Credenciales inválidas", "error")
    return RedirectResponse("/login", status_code=302)

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "flash": pop_flash(request), "user": None}
    )

@app.post("/register")
def register_action(request: Request,
                    username: str = Form(),
                    email: str = Form(),
                    password: str = Form()):
    if user_exists(username, email):
        set_flash(request, "Usuario o correo ya registrado", "error")
        return RedirectResponse("/register", status_code=302)

    save_user(username, email, password)
    set_flash(request, "Registro exitoso", "success")
    return RedirectResponse("/login", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    set_flash(request, "Sesión cerrada", "success")
    return RedirectResponse("/login", status_code=302)

# -----------------------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------------------

@app.get("/dashboard")
def dashboard(request: Request, page: int = 1, query: str = ""):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    params = {
        "api_key": TMDB_API_KEY,
        "language": "es-ES",
        "page": page
    }

    if query:
        params["query"] = query
        movies = requests.get(f"{TMDB_BASE_URL}/search/movie", params=params).json()["results"]
    else:
        movies = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params).json()["results"]

    likes = load_likes()
    likes_map = {str(m["id"]): sum(m["id"] in v for v in likes.values()) for m in movies}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "movies_api": movies,
        "page": page,
        "prev_page": page - 1 if page > 1 else None,
        "next_page": page + 1,
        "query": query,
        "user": user,
        "flash": pop_flash(request),
        "likes_map": likes_map
    })

# -----------------------------------------------------------------------------------
# DETALLE PELÍCULA
# -----------------------------------------------------------------------------------

@app.get("/movie/{movie_id}")
def movie_detail(request: Request, movie_id: int):
    user = require_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    movie = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "es-ES"}
    ).json()

    likes = sum(movie_id in v for v in load_likes().values())

    return templates.TemplateResponse("movie.html", {
        "request": request,
        "movie": movie,
        "recommendations": [],
        "likes": likes,
        "user": user,
        "flash": pop_flash(request),
        "trailer_key": None
    })

# -----------------------------------------------------------------------------------
# LIKE API
# -----------------------------------------------------------------------------------

@app.post("/api/like/{movie_id}")
def like_movie(request: Request, movie_id: int):
    user = require_user(request)
    if not user:
        raise HTTPException(status_code=401)

    likes = load_likes()
    likes.setdefault(user, [])

    if movie_id not in likes[user]:
        likes[user].append(movie_id)

    save_likes(likes)
    return {"status": "ok"}

# -----------------------------------------------------------------------------------
# ADMIN
# -----------------------------------------------------------------------------------

@app.get("/admin")
def admin_panel(request: Request):
    user = require_user(request)
    if user != "admin":
        set_flash(request, "Acceso denegado", "error")
        return RedirectResponse("/login", status_code=302)

    likes = load_likes()
    rows = []

    for u, ids in likes.items():
        for mid in ids:
            r = requests.get(
                f"{TMDB_BASE_URL}/movie/{mid}",
                params={"api_key": TMDB_API_KEY, "language": "es-ES"}
            )
            title = r.json().get("title", f"ID {mid}") if r.status_code == 200 else f"ID {mid}"
            rows.append({"user": u, "movie_id": mid, "title": title})

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "likes_list": rows,
        "flash": pop_flash(request)
    })

@app.post("/admin/delete-like/{username}/{movie_id}")
def delete_like(request: Request, username: str, movie_id: int):
    user = require_user(request)
    if user != "admin":
        return RedirectResponse("/login", status_code=302)

    likes = load_likes()
    if username in likes and movie_id in likes[username]:
        likes[username].remove(movie_id)
        save_likes(likes)
        set_flash(request, "Like eliminado", "success")

    return RedirectResponse("/admin", status_code=302)
