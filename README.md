# Névora Moda! – Tienda de ropa en línea

Tienda minimalista (inspirada en el estilo de las grandes tiendas de moda, sin copiar su marca ni su código) construida con **Flask, SQLAlchemy, Flask-Login, Flask-WTF, Jinja2 y Bootstrap 5**. Desarrollo en SQLite, producción en PostgreSQL.

## Funcionalidades
- **Catálogo público** (sin iniciar sesión): categorías, búsqueda, filtros combinables (categoría, tipo de prenda, rango de precio, disponibilidad, talla), orden y paginación.
- **Detalle de producto** con fotos, descripción, precio, tallas reales y disponibilidad.
- **Carrito persistente sin cuenta**: cookie firmada (30 días). Al iniciar sesión o registrarse se fusiona con el carrito del usuario sin duplicados. El carrito no reserva inventario; el servidor revalida precios y existencias.
- **Inicio de sesión solo al pagar.** El carrito se conserva durante todo el proceso.
- **Entrega solo en Medellín, Bello y Envigado**: desplegable obligatorio, validado en el formulario y otra vez en el servidor al crear el pedido. Los datos de entrega se guardan con el pedido.
- **Pagos simulados** (Visa, MasterCard, Efecty). No se procesan pagos reales ni se guardan datos de tarjeta; solo el nombre del medio.
- Historial de pedidos, cancelación (restituye stock), factura imprimible.
- Registro, login, cierre de sesión (POST), cambio de contraseña, categorías favoritas y recomendaciones.
- **Panel de administración** separado (`/admin/`): productos (con tallas y stock por talla), usuarios, pedidos y cambio de estado. Los usuarios normales reciben 403.

## Estructura
```
app.py, config.py, extensions.py, cli.py, security.py, forms.py, models.py
blueprints/   shop, cart, auth, checkout, admin
services/     catalog, cart, orders, payments, delivery, products, users, images, recommendations, reports, factory
templates/    base, shop/, auth/, admin/, errors/
static/       css/nevora.css, js/nevora.js, vendor/ (Bootstrap local, sin CDN)
migrations/   Alembic (Flask-Migrate)
tests/        pytest (179 pruebas)
docs/ARQUITECTURA.md   correspondencia con SOLID
```

## Puesta en marcha
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt                     # solo ejecutar: requirements.txt
cp .env.example .env                                    # edita SECRET_KEY (y DATABASE_URL en producción)
export FLASK_APP=app:app
```
**Base nueva:** `flask init-db` (crea las tablas y marca la migración al día).
**Base existente (datos previos):** haz una copia de seguridad y ejecuta `flask db upgrade`. La migración `b7e1c2a9d4f3` solo agrega columnas/tablas y conserva los datos.

```bash
flask create-admin            # crea (o promueve) un administrador
python seed_products.py       # opcional: productos de ejemplo (sin fotos; usan imagen por defecto)
flask run                     # desarrollo
gunicorn app:app              # producción
```
Sin `DATABASE_URL` se usa SQLite local (`nevora_dev.sqlite3`). El registro público **nunca** crea administradores.

## Pruebas
```bash
pytest                                              # SQLite en memoria
TEST_DATABASE_URL=postgresql://user:pass@host/db pytest   # contra PostgreSQL (base vacía/desechable)
python scripts/verify_migration.py <DATABASE_URL> <legacy_models.py>   # verifica migración con datos heredados
```

## Notas de migración desde la versión anterior
- Rutas nuevas: `/catalogo`, `/producto/<id>`, `/cart/`, `/payment/<order_id>`, `/admin/...`. El cierre de sesión ahora es POST.
- `fix_db.py` y `transfer_users.py` se movieron a `scripts/legacy/` (no usar). `make_admin.py` se reemplazó por `flask create-admin`.
- Los documentos de `docs/` distintos de `ARQUITECTURA.md` describen la versión anterior.
- **Seguridad:** si alguna vez se subió un `.env` con credenciales al repositorio, rota esas contraseñas.
