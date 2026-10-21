"""Carga prendas de ejemplo en el catálogo de Névora Moda!

Uso:
    python seed_products.py

Solo inserta si la tabla de productos está vacía, así que es seguro ejecutarlo
más de una vez. Las prendas se crean sin foto (se muestra la imagen por
defecto); puedes subirles fotos desde Admin → Gestionar Productos → Editar.
"""
from app import app
from models import db, Product

PRODUCTS = [
    # name, brand, category, price, stock, description
    ("Camisa Oxford Azul",        "Névora Basics",  "Camisas",     89900, 25, "Camisa de algodón manga larga, corte regular."),
    ("Camiseta Básica Blanca",    "Névora Basics",  "Camisas",     39900, 60, "Camiseta cuello redondo 100% algodón."),
    ("Blusa Floral Primavera",    "Urban Bloom",    "Camisas",     69900, 18, "Blusa ligera con estampado floral."),
    ("Jean Slim Fit Azul Oscuro", "Denim Co.",      "Pantalones", 129900, 30, "Jean de corte slim con elastano para mayor comodidad."),
    ("Pantalón Cargo Verde",      "Urban Bloom",    "Pantalones", 119900, 20, "Pantalón cargo con bolsillos laterales."),
    ("Jogger Deportivo Negro",    "Active Line",    "Pantalones",  79900, 35, "Jogger en tela afelpada, ideal para el día a día."),
    ("Tenis Urbanos Blancos",     "StepUp",         "Zapatos",    199900, 15, "Tenis casuales con suela de goma antideslizante."),
    ("Botines de Cuero Café",     "StepUp",         "Zapatos",    249900, 10, "Botines de cuero genuino con cierre lateral."),
    ("Sandalias Confort",         "Sol & Playa",    "Zapatos",     89900, 22, "Sandalias de plantilla acolchada."),
    ("Cinturón de Cuero Negro",   "Névora Basics",  "Accesorios",  59900, 40, "Cinturón clásico con hebilla metálica."),
    ("Gorra Deportiva",           "Active Line",    "Accesorios",  34900, 50, "Gorra ajustable de algodón."),
    ("Bufanda Tejida Gris",       "Urban Bloom",    "Accesorios",  44900, 28, "Bufanda suave tejida a mano."),
    ("Vestido Midi Negro",        "Urban Bloom",    "Vestidos",   159900, 12, "Vestido midi elegante para toda ocasión."),
    ("Chaqueta Denim",            "Denim Co.",      "Chaquetas",  179900, 14, "Chaqueta de jean clásica con botones metálicos."),
]

with app.app_context():
    db.create_all()
    if Product.query.count() > 0:
        print("Ya existen productos en la base de datos; no se insertó nada.")
    else:
        for name, brand, category, price, stock, description in PRODUCTS:
            db.session.add(Product(name=name, brand=brand, category=category,
                                   price=price, stock=stock, description=description))
        db.session.commit()
        print(f"Se insertaron {len(PRODUCTS)} prendas de ejemplo.")
