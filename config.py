import os
from dotenv import load_dotenv

# Cargar las variables del .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-por-defecto")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("❌ La variable DATABASE_URL no está definida en el archivo .env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-por-defecto")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), 'static', 'uploads'))

