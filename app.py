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
os.makedirs("data", exist_ok=True)

# -----------------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------------
def set_flash(request: Request, message: str, category: str = "info"):
    """Guarda un mensaje flash en la sesión."""
    request.session["flash"] = {"message": message, "category": category}


def pop_flash(request: Request):
    """Obtiene y elimina el mensaje flash de la sesión."""
    return request.session.pop("flash", None)

def require_user(request: Request):
    """Devuelve el usuario logueado o None si no hay sesión."""
    user = request.session.get("user")
    if not user:
        set_flash(request, "Debes iniciar sesión para acceder a esta sección.", "error")
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

# -----------------------------------------------------------------------------------
# RUTAS PRINCIPALES (LOGIN / REGISTER)
# -----------------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse("/login")

@app.get("/login")
def login_page(request: Request):
    flash = pop_flash(request)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "flash": flash}
    )

@app.post("/login")
def login_action(
    request: Request,
    identifier: str = Form(),
    password: str = Form()
):
    # Validación de credenciales
    if validate_login(identifier, password):
        # Guardar usuario en sesión
        request.session["user"] = identifier

        # Mensaje flash opcional de bienvenida
        set_flash(request, f"Bienvenido, {identifier}!", "success")

        return RedirectResponse("/dashboard", status_code=302)

    # Si las credenciales NO son válidas
    set_flash(request, "Credenciales inválidas. Intente nuevamente.", "error")
    return RedirectResponse("/login", status_code=302)


@app.get("/register")
def register_page(request: Request):
    flash = pop_flash(request)
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "flash": flash}
    )

@app.post("/register")
def register_action(
    request: Request,
    username: str = Form(),
    email: str = Form(),
    password: str = Form()
):
    if user_exists(username, email):
        set_flash(request, "El usuario o el correo ya están registrados.", "error")
        return RedirectResponse("/register", status_code=302)

    save_user(username, email, password)
    set_flash(request, "Registro exitoso. Ahora puedes iniciar sesión.", "success")
    return RedirectResponse("/login", status_code=302)

# -----------------------------------------------------------------------------------
# DASHBOARD CON PAGINACIÓN
# -----------------------------------------------------------------------------------

@app.get("/dashboard")
def dashboard(request: Request, page: int = 1, query: str = ""):

    # ==========================
    # PROTEGER RUTA (requerido RNF4)
    # ==========================
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # ==========================
    # MENSAJE FLASH (si existe)
    # ==========================
    flash = pop_flash(request)

    # Parámetros para TMDB
    params = {
        "api_key": TMDB_API_KEY,
        "language": "es-ES",
        "sort_by": "popularity.desc",
        "page": page
    }

    # Buscar o descubrir películas
    if query:
        params["query"] = query
        tmdb_movies = requests.get(
            f"{TMDB_BASE_URL}/search/movie", params=params
        ).json().get("results", [])
    else:
        tmdb_movies = requests.get(
            f"{TMDB_BASE_URL}/discover/movie", params=params
        ).json().get("results", [])

    # Películas personalizadas
    custom_movies = load_custom_movies()

    # Paginación segura
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1

    # ==========================
    # RESPUESTA
    # ==========================
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "movies_api": tmdb_movies,
            "custom_movies": custom_movies,
            "page": page,
            "prev_page": prev_page,
            "next_page": next_page,
            "query": query,
            "user": current_user,
            "flash": flash,   # <<< indispensable para mensajes
        }
    )

# -----------------------------------------------------------------------------------
# DETALLE DE PELÍCULA
# -----------------------------------------------------------------------------------

@app.get("/movie/{movie_id}")
def movie_detail(request: Request, movie_id: int):
    # ==========================
    # PROTEGER RUTA
    # ==========================
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    # ==========================
    # MENSAJE FLASH (si existe)
    # ==========================
    flash = pop_flash(request)

    # ==========================
    # CONSULTAR DETALLES DE LA PELÍCULA
    # ==========================
    movie = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "es-ES"}
    ).json()

    # ==========================
    # CONSULTAR RECOMENDACIONES
    # ==========================
    recommendations = requests.get(
        f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations",
        params={"api_key": TMDB_API_KEY, "language": "es-ES"}
    ).json().get("results", [])

    # ==========================
    # RETORNAR TEMPLATE
    # ==========================
    return templates.TemplateResponse(
        "movie.html",
        {
            "request": request,
            "movie": movie,
            "recommendations": recommendations,
            "user": current_user,
            "flash": flash
        }
    )

# -----------------------------------------------------------------------------------
# AGREGAR PELÍCULA PERSONALIZADA
# -----------------------------------------------------------------------------------

@app.get("/add-movie")
def add_page(request: Request):
    # Proteger ruta
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    flash = pop_flash(request)

    return templates.TemplateResponse(
        "add_movie.html",
        {
            "request": request,
            "flash": flash,
            "user": current_user
        }
    )

@app.post("/add-movie")
def add_custom_movie(
    request: Request,
    title: str = Form(),
    description: str = Form(),
    poster: str = Form(None)
):
    # Proteger ruta
    current_user = require_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    movies = load_custom_movies()
    new_id = max([m["id"] for m in movies], default=100000) + 1

    movies.append({
        "id": new_id,
        "title": title,
        "description": description,
        "poster": poster or "https://via.placeholder.com/300x450?text=No+Image"
    })

    save_custom_movies(movies)

    set_flash(request, "Película agregada correctamente.", "success")
    return RedirectResponse("/dashboard", status_code=302)


# -----------------------------------------------------------------------------------
# API REST
# -----------------------------------------------------------------------------------
# Estos endpoints trabajan sobre las PELÍCULAS PERSONALIZADAS
# que se guardan en data/custom_movies.json
# -----------------------------------------------------------------------------------

@app.get("/api/movie")
def api_list_movies():
    return load_custom_movies()

@app.get("/api/movie/{movie_id}")
def api_get_movie(movie_id: int):
    movie = next((m for m in load_custom_movies() if m["id"] == movie_id), None)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

@app.delete("/api/movie/{movie_id}")
def api_delete_movie(movie_id: int):
    """
    DELETE /api/movie/{id}
    Elimina una película personalizada por id.
    """
    movies = load_custom_movies()
    new_movies = [m for m in movies if m["id"] != movie_id]

    # Si no cambió el tamaño, es que no existía
    if len(new_movies) == len(movies):
        raise HTTPException(status_code=404, detail="Movie not found")

    save_custom_movies(new_movies)
    return {"status": "deleted", "id": movie_id}

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    set_flash(request, "Sesión cerrada correctamente.", "success")
    return RedirectResponse("/login", status_code=302)


# -----------------------------------------------------------------------------------
# ARRANQUE DEL SERVIDOR (para ejecutar python app.py directamente)
# -----------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
