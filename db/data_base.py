import psycopg2

def get_db():
    return psycopg2.connect(
        host="localhost",
        database="cineapp",
        user="postgres",
        password="postgres",
        port=5432
    )
