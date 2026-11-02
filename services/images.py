"""Almacenamiento de fotos de productos (única responsabilidad: guardar y borrar archivos)."""
import os
import uuid

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


class ImageStorage:
    def __init__(self, folder: str):
        self.folder = folder

    def save(self, file_storage) -> str:
        """Guarda con nombre único y devuelve ese nombre. ValueError si el formato no se permite."""
        original = secure_filename(file_storage.filename or "")
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("Formato de imagen no permitido.")
        os.makedirs(self.folder, exist_ok=True)
        stem = original.rsplit(".", 1)[0][:40] or "producto"
        filename = f"{uuid.uuid4().hex[:12]}-{stem}.{ext}"
        file_storage.save(os.path.join(self.folder, filename))
        return filename

    def delete(self, filename: str) -> None:
        if not filename:
            return
        try:
            os.remove(os.path.join(self.folder, os.path.basename(filename)))
        except FileNotFoundError:
            pass
