"""Verifica la migración sobre una base con el ESQUEMA ANTERIOR y datos reales.

Uso: python scripts/verify_migration.py <DATABASE_URL> <ruta_legacy_models.py>
Crea el esquema anterior, inserta datos, aplica `flask db upgrade`, comprueba que
los datos se conservan y que `downgrade` + `upgrade` funcionan.
"""
import importlib.util, os, subprocess, sys
from sqlalchemy import create_engine, inspect, text

url, legacy_path = sys.argv[1], sys.argv[2]
env = {**os.environ, "DATABASE_URL": url, "SECRET_KEY": "x", "FLASK_APP": "app.py"}
eng = create_engine(url)

# 1) base limpia
with eng.begin() as c:
    if eng.dialect.name == "postgresql":
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    else:
        for t in inspect(eng).get_table_names():
            c.execute(text(f'DROP TABLE IF EXISTS "{t}"'))

# 2) esquema anterior (modelos del repositorio original) + datos
from flask import Flask
spec = importlib.util.spec_from_file_location("legacy_models", legacy_path)
legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
app = Flask(__name__); app.config.update(SQLALCHEMY_DATABASE_URI=url)
legacy.db.init_app(app)
with app.app_context():
    legacy.db.create_all()
    u = legacy.User(username="ana", email="ana@x.co"); u.set_password("secreto1"); u.role = None
    adm = legacy.User(username="boss", email="boss@x.co", role="admin"); adm.set_password("secreto1")
    p = legacy.Product(name="Camisa", brand="Névora", price=50000, stock=7, category="Camisas")
    legacy.db.session.add_all([u, adm, p]); legacy.db.session.commit()
    o = legacy.Order(user_id=u.id, status="paid", total=100000)
    legacy.db.session.add(o); legacy.db.session.flush()
    legacy.db.session.add(legacy.OrderItem(order_id=o.id, product_id=p.id, quantity=2, price=50000))
    legacy.db.session.commit()
    legacy.db.session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
    legacy.db.session.execute(text("INSERT INTO alembic_version VALUES ('a1b2c3d4e5f6')"))
    legacy.db.session.commit()
print("esquema anterior creado con datos")

def flask(*args):
    r = subprocess.run([sys.executable, "-m", "flask", *args], env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr); sys.exit("FALLÓ: flask " + " ".join(args))
    return r

flask("db", "upgrade"); print("upgrade OK")
with eng.connect() as c:
    assert c.execute(text("select role from users where email='ana@x.co'")).scalar() == "user", "role NULL no se rellenó"
    assert c.execute(text("select count(*) from users")).scalar() == 2
    assert c.execute(text("select name, stock from products")).one() == ("Camisa", 7)
    row = c.execute(text("select total, municipality, payment_method, status from orders")).one()
    assert row == (100000, None, None, "paid"), row
    assert c.execute(text("select quantity, price, size_id from order_items")).one() == (2, 50000, None)
    cols = {x["name"] for x in inspect(eng).get_columns("products")}
    assert "garment_type" in cols and "product_sizes" in inspect(eng).get_table_names()
print("datos conservados OK")

flask("db", "downgrade"); print("downgrade OK")
flask("db", "upgrade"); print("re-upgrade OK")
print("MIGRACIÓN VERIFICADA en", eng.dialect.name)
