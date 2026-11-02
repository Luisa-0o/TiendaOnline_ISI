"""Carga prendas de ejemplo en el catálogo de Névora Moda!

Uso:
    python seed_products.py

Solo inserta si la tabla de productos está vacía, así que es seguro ejecutarlo más de una vez.
Las prendas se crean SIN foto (la tienda muestra una imagen por defecto): sube las fotos reales
desde Admin → Productos → Editar. Las que tienen tallas calculan sus existencias totales a partir de ellas.
"""
from app import app
from extensions import db
from models import Product, ProductSize

ROPA = {"S": 6, "M": 8, "L": 6, "XL": 3}
JEAN = {"28": 4, "30": 8, "32": 8, "34": 5}
CALZADO = {"36": 2, "38": 4, "40": 5, "42": 3}

PRODUCTS = [
    # nombre, marca, categoría, tipo de prenda, precio, existencias (si no tiene tallas), tallas, descripción
    ("Camisa Oxford Azul",        "Névora Basics", "Camisas",    "Camisa",   89900, None, ROPA,    "Camisa de algodón manga larga, corte regular."),
    ("Camiseta Básica Blanca",    "Névora Basics", "Camisas",    "Camiseta", 39900, None, ROPA,    "Camiseta cuello redondo 100% algodón."),
    ("Blusa Floral Primavera",    "Urban Bloom",   "Camisas",    "Blusa",    69900, None, ROPA,    "Blusa ligera con estampado floral."),
    ("Jean Slim Fit Azul Oscuro", "Denim Co.",     "Pantalones", "Jean",    129900, None, JEAN,    "Jean de corte slim con elastano para mayor comodidad."),
    ("Pantalón Cargo Verde",      "Urban Bloom",   "Pantalones", "Cargo",   119900, None, JEAN,    "Pantalón cargo con bolsillos laterales."),
    ("Jogger Deportivo Negro",    "Active Line",   "Pantalones", "Jogger",   79900, None, ROPA,    "Jogger en tela afelpada, ideal para el día a día."),
    ("Tenis Urbanos Blancos",     "StepUp",        "Zapatos",    "Tenis",   199900, None, CALZADO, "Tenis casuales con suela de goma antideslizante."),
    ("Botines de Cuero Café",     "StepUp",        "Zapatos",    "Botines", 249900, None, CALZADO, "Botines de cuero genuino con cierre lateral."),
    ("Sandalias Confort",         "Sol & Playa",   "Zapatos",    "Sandalias", 89900, None, CALZADO, "Sandalias de plantilla acolchada."),
    ("Cinturón de Cuero Negro",   "Névora Basics", "Accesorios", "Cinturón",  59900, 40, None,    "Cinturón clásico con hebilla metálica."),
    ("Gorra Deportiva",           "Active Line",   "Accesorios", "Gorra",     34900, 50, None,    "Gorra ajustable de algodón."),
    ("Bufanda Tejida Gris",       "Urban Bloom",   "Accesorios", "Bufanda",   44900, 28, None,    "Bufanda suave tejida a mano."),
    ("Vestido Midi Negro",        "Urban Bloom",   "Vestidos",   "Vestido",  159900, None, ROPA,   "Vestido midi elegante para toda ocasión."),
    ("Chaqueta Denim",            "Denim Co.",     "Chaquetas",  "Chaqueta", 179900, None, ROPA,   "Chaqueta de jean clásica con botones metálicos."),
]

with app.app_context():
    db.create_all()
    if Product.query.count() > 0:
        print("Ya existen productos en la base de datos; no se insertó nada.")
    else:
        for name, brand, category, garment, price, stock, sizes, description in PRODUCTS:
            product = Product(name=name, brand=brand, category=category, garment_type=garment, price=price,
                              description=description, stock=stock or 0)
            if sizes:
                product.sizes = [ProductSize(label=label, stock=qty) for label, qty in sizes.items()]
                product.stock = sum(sizes.values())
            db.session.add(product)
        db.session.commit()
        print(f"Se insertaron {len(PRODUCTS)} prendas de ejemplo (sin fotos).")
