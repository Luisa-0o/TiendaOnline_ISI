"""Repara una base de datos que venía del proyecto de libros (tabla 'books').

Problema que soluciona:
    column cart_items.product_id does not exist
    column order_items.product_id does not exist

Qué hace:
  - CONSERVA: users (usuarios) y products (prendas que ya creaste).
  - BORRA:    books, carts, cart_items, orders, order_items
              (carritos y pedidos de prueba que apuntaban a libros).
  - Vuelve a crear las tablas borradas con el esquema nuevo (product_id).

Uso (con el entorno virtual activado y el .env configurado):
    python fix_db.py
"""
from sqlalchemy import inspect, text
from app import app
from models import db

TABLAS_A_BORRAR = ["cart_items", "order_items", "orders", "carts", "books"]

with app.app_context():
    insp = inspect(db.engine)
    existentes = [t for t in TABLAS_A_BORRAR if insp.has_table(t)]
    print("Base de datos:", db.engine.url.render_as_string(hide_password=True))
    print("Se conservarán: users, products")
    print("Se borrarán estas tablas (y sus datos):", ", ".join(existentes) or "(ninguna)")

    if input("¿Continuar? Escribe SI para confirmar: ").strip().upper() != "SI":
        print("Cancelado. No se modificó nada.")
        raise SystemExit(0)

    cascade = " CASCADE" if db.engine.dialect.name == "postgresql" else ""
    with db.engine.begin() as conn:
        for tabla in existentes:
            conn.execute(text(f'DROP TABLE IF EXISTS "{tabla}"{cascade}'))
            print("  borrada:", tabla)

    db.create_all()  # recrea carts, cart_items, orders, order_items con product_id
    print("Listo. Tablas actuales:", ", ".join(sorted(inspect(db.engine).get_table_names())))
