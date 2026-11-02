# Névora Moda! – Tienda de ropa en línea

Tienda de ropa minimalista construida con **Flask**. Cualquier persona puede explorar el catálogo y armar un carrito sin crear cuenta; el inicio de sesión solo se pide al pagar. Incluye registro y cuentas de usuario, pedidos con entrega restringida a **Medellín, Bello y Envigado**, pagos **simulados**, facturas imprimibles y un panel de administración.

> Proyecto académico de *Ingeniería de Software*. Su estilo visual es sobrio e inspirado en las grandes tiendas de moda, sin copiar su marca, imágenes ni código.

## Contenido
1. [Qué hace](#1-qué-hace)
2. [Tecnologías](#2-tecnologías)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Cómo funciona por dentro](#4-cómo-funciona-por-dentro)
5. [Base de datos](#5-base-de-datos)
6. [Rutas de la aplicación](#6-rutas-de-la-aplicación)
7. [Instalación y puesta en marcha](#7-instalación-y-puesta-en-marcha)
8. [Configuración (`.env`)](#8-configuración-env)
9. [Comandos útiles](#9-comandos-útiles)
10. [Pruebas](#10-pruebas)
11. [Seguridad](#11-seguridad)
12. [Principios SOLID](#12-principios-solid)
13. [Despliegue](#13-despliegue)
14. [Problemas frecuentes](#14-problemas-frecuentes)
15. [Notas de la versión y migración](#15-notas-de-la-versión-y-migración)

---

## 1. Qué hace

### Para quien compra
- **Catálogo público** sin necesidad de cuenta, con paginación de 12 prendas por página.
- **Búsqueda** por nombre y **filtros combinables**: categoría, tipo de prenda, rango de precio, disponibilidad y talla. Hay botón para limpiar filtros.
- **Orden** por novedades, precio (menor a mayor y mayor a menor) y nombre A-Z.
- **Detalle de producto:** foto, nombre, marca, descripción, precio, categoría, tipo de prenda, tallas (solo si el producto las tiene realmente), disponibilidad, cantidad y botón de agregar al carrito. Muestra además prendas relacionadas.
- **Inicio tipo vitrina:** banner principal, novedades, más vendidos, categorías y pie de página con datos de contacto (opcionales).
- **Carrito sin cuenta:** se guarda en una cookie firmada por 30 días, así que sobrevive al cierre del navegador. Muestra el número de artículos en el encabezado. Se puede cambiar la cantidad y quitar prendas.
- **Fusión del carrito:** al iniciar sesión o registrarse, el carrito de visitante se une al del usuario sin duplicados y respetando existencias.
- **El carrito no reserva inventario.** Las existencias se comprueban de nuevo al pagar.
- **Compra:** el inicio de sesión se pide solo al pagar. Se llenan los datos de entrega (nombre del destinatario, celular, municipio, dirección, barrio, código postal opcional y notas). Después se paga con un método simulado y se obtiene confirmación y factura.
- **Pedidos:** historial, detalle, cancelación (que devuelve el stock) y factura imprimible.
- **Cuenta:** registro, inicio y cierre de sesión, cambio de contraseña y elección de **dos categorías favoritas**, que alimentan las **recomendaciones**.

### Para quien administra (`/admin/`)
- **Panel de resumen** con indicadores del negocio y avisos de existencias bajas.
- **Productos:** crear, editar y eliminar, con foto, categoría, tipo de prenda y tallas con su stock (se escriben como `S:10, M:15, L:8`).
- **Usuarios:** crear, editar y eliminar, con protecciones para no quedarse sin administradores.
- **Pedidos:** lista, detalle y cambio de estado (pendiente de pago, pagado, enviado, entregado o cancelado).
- Las páginas de administración están visualmente separadas de la tienda y los usuarios normales no pueden entrar (reciben un 403).

### Reglas de negocio importantes
- **Solo se entrega en Medellín, Bello y Envigado.** El municipio se elige de una lista cerrada y se valida en tres capas: el formulario, el servidor y el momento de crear el pedido.
- **Nunca se confía en el navegador:** el precio y el stock se leen siempre de la base de datos al comprar.
- **Pagos simulados:** Visa, MasterCard y Efecty. No se procesan pagos reales ni se guardan datos de tarjeta; solo queda el nombre del método.
- **Rol de usuario:** el registro público siempre crea usuarios normales. Un administrador se crea únicamente con `flask create-admin` o lo asigna otro administrador.

---

## 2. Tecnologías

| Área | Herramienta |
|---|---|
| Lenguaje | Python 3 |
| Framework web | Flask 3 |
| Base de datos y ORM | SQLAlchemy 2 con Flask-SQLAlchemy. SQLite en desarrollo, PostgreSQL en producción (`psycopg2`) |
| Migraciones | Alembic con Flask-Migrate |
| Sesiones de usuario | Flask-Login |
| Formularios y CSRF | Flask-WTF / WTForms (con `email-validator`) |
| Plantillas | Jinja2 |
| Interfaz | Bootstrap 5.3 e íconos de Bootstrap, guardados localmente (sin CDN) |
| Servidor de producción | Gunicorn |
| Variables de entorno | python-dotenv |
| PDF | ReportLab (incluida en `requirements.txt`) |
| Pruebas | pytest |

Las versiones exactas están en `requirements.txt`. `requirements-dev.txt` añade pytest.

---

## 3. Estructura del proyecto

```
TiendaOnline_ISI/
├── app.py                 Fábrica de la aplicación (create_app) y punto de entrada
├── config.py              Configuración leída del entorno
├── extensions.py          db, migrate, csrf y login_manager
├── models.py              Tablas: User, Product, ProductSize, Cart, CartItem, Order, OrderItem
├── forms.py               Formularios y sus validaciones
├── security.py            Control de acceso por rol y redirecciones seguras
├── cli.py                 Comandos: flask init-db y flask create-admin
├── seed_products.py       Carga productos de ejemplo (opcional)
├── blueprints/            Rutas (delgadas: delegan en services/)
│   ├── shop.py            Inicio, catálogo, detalle de producto
│   ├── cart.py            Carrito
│   ├── auth.py            Registro, login, cuenta, contraseña, favoritos
│   ├── checkout.py        Entrega, pago, pedidos, factura
│   └── admin.py           Panel de administración
├── services/              Reglas de negocio (casi sin dependencias de Flask)
│   ├── catalog.py         Filtros, orden, paginación, destacados
│   ├── cart.py            Carrito de visitante (cookie) y de usuario (base de datos)
│   ├── delivery.py        Municipios permitidos y validación de datos de entrega
│   ├── orders.py          Crear, pagar, cancelar y cambiar estado de pedidos
│   ├── payments.py        Pasarelas simuladas de pago
│   ├── products.py        Alta/edición de productos y tallas
│   ├── users.py           Reglas de cuentas y administración de usuarios
│   ├── images.py          Guardado seguro de imágenes subidas
│   ├── recommendations.py Recomendaciones según categorías favoritas
│   ├── reports.py         Indicadores del panel de administración
│   └── factory.py         Raíz de composición: arma los servicios
├── templates/             Páginas HTML (base, shop/, auth/, admin/, errors/)
├── static/
│   ├── css/nevora.css     Estilos propios
│   ├── js/nevora.js       Confirmaciones, indicador de carga, formulario de pago
│   ├── vendor/            Bootstrap local
│   └── uploads/           Fotos de productos subidas desde el panel
├── migrations/            Migraciones de base de datos (Alembic)
├── scripts/
│   ├── verify_migration.py  Prueba la migración con datos de la versión anterior
│   └── legacy/            Scripts antiguos, solo de referencia (no usar)
├── tests/                 Pruebas automáticas con pytest
├── docs/                  Documentación (ver ARQUITECTURA.md)
├── .env.example           Plantilla de variables de entorno
├── requirements.txt       Dependencias para ejecutar
└── requirements-dev.txt   Dependencias para desarrollar y probar
```

---

## 4. Cómo funciona por dentro

### Flujo general
```
Navegador → blueprints (rutas) → services (reglas) → models → base de datos
```
- Los **blueprints** leen la petición, llaman a un servicio y devuelven una página.
- Los **services** contienen las reglas de negocio y se pueden probar sin levantar el servidor.
- Los **models** definen las tablas.
- **`services/factory.py`** crea y conecta los servicios; es el único lugar donde se decide qué pieza concreta se usa.

### Arranque (`app.py`)
`create_app()` carga la configuración, comprueba la `SECRET_KEY` (en producción no arranca sin ella), conecta las extensiones, registra los blueprints, los filtros de plantilla (`cop` para precios como `$89.900` y `join_es`), los manejadores de error 403/404/413/500 y los comandos de consola. Con SQLite crea las tablas sola la primera vez.

### Carrito (`services/cart.py`)
- **Visitante:** `CookieCartStore` guarda solo producto, talla y cantidad en una cookie firmada con `itsdangerous` (`HttpOnly`, `SameSite=Lax`, 30 días). Los precios nunca viajan en la cookie.
- **Usuario con sesión:** `DatabaseCartStore` guarda el carrito en las tablas `carts` y `cart_items`.
- Ambos implementan la misma interfaz (`CartStore`), por lo que `CartService` funciona igual con cualquiera.
- Límites: hasta 50 líneas y 20 unidades por línea.
- Una función de respuesta (`apply_cart_cookie`) escribe o borra la cookie al final de cada petición.

### Catálogo (`services/catalog.py`)
Cada filtro (búsqueda, categoría, tipo de prenda, rango de precio, disponibilidad, talla) es una clase pequeña con un método `apply()`. `build_filters` las combina. Los parámetros de la URL se limpian antes de usarse, y los caracteres especiales de la búsqueda se escapan.

### Entrega (`services/delivery.py`)
`DeliveryPolicy` es la única fuente de verdad sobre los municipios y las reglas de los datos de entrega. La usan tanto el formulario como `OrderService`, de modo que una petición manipulada a mano también es rechazada.

### Pedidos (`services/orders.py`)
`place_order` hace todo en **una sola transacción**:
1. Normaliza y valida los datos de entrega.
2. Comprueba que el carrito no esté vacío.
3. Vuelve a leer cada producto de la base y verifica que exista, tenga talla válida y alcance el stock.
4. Crea el pedido con el **precio vigente** y copia la talla en cada línea.
5. Descuenta las existencias con `UPDATE ... WHERE stock >= cantidad`, que es seguro ante compras simultáneas.
6. Vacía el carrito y confirma. Si algo falla, se deshace todo.

Además, `pay` cobra con la pasarela elegida, `cancel` y `change_status` devuelven el stock al cancelar (un pedido cancelado no se reactiva) y `last_shipping` recuerda los datos de entrega del último pedido para no pedirlos otra vez.

Estados de un pedido: **Pendiente de pago → Pagado → Enviado → Entregado**, o **Cancelado** (se puede cancelar mientras esté pendiente o pagado).

### Pagos (`services/payments.py`)
`PaymentGateway` es la interfaz; `SimulatedCardGateway` (Visa, MasterCard) valida el formato del número y la fecha de vencimiento, y `SimulatedCashGateway` (Efecty) representa el pago en punto físico. `PaymentGatewayRegistry` las registra por código. Agregar otro medio de pago no requiere cambiar `OrderService`.

### Cuentas y roles
`AccountService` (`services/users.py`) concentra las reglas de usuarios. `security.py` ofrece `admin_required` (sin sesión → login, usuario normal → 403) e `is_safe_url` (evita redirecciones a otros sitios después del login).

### Recomendaciones y reportes
`RecommendationService` sugiere prendas con stock de las categorías favoritas del usuario. `ReportService` calcula los datos del panel de administración.

### Interfaz
Plantillas con herencia (`base.html` y parciales reutilizables), Bootstrap local y CSS propio. Incluye enlace para saltar al contenido, etiquetas en todos los campos, mensajes de error asociados a cada campo, textos alternativos en imágenes, navegación con teclado, indicadores de carga, respeto por `prefers-reduced-motion` y estilos de impresión para la factura.

---

## 5. Base de datos

| Tabla | Contenido |
|---|---|
| `users` | Usuario, correo, `password_hash`, rol (`user` o `admin`) y dos categorías favoritas |
| `products` | Nombre, marca, precio, stock total, descripción, categoría, tipo de prenda y foto |
| `product_sizes` | Talla y stock por producto (el stock total del producto es la suma) |
| `carts` / `cart_items` | Carrito de usuarios con sesión (producto, talla, cantidad) |
| `orders` | Usuario, estado, total, fecha, datos de entrega y método de pago |
| `order_items` | Líneas del pedido con precio congelado, cantidad y talla |
| `alembic_version` | Control interno de migraciones (no tocar) |

Las contraseñas se guardan con hash, nunca en texto plano. Las claves foráneas y restricciones tienen nombres estables definidos en `extensions.py`.

### Migraciones
Los cambios de estructura se hacen con Alembic. La migración `b7e1c2a9d4f3` (*tallas, entrega y pago*) solo **agrega** columnas y tablas (tipo de prenda, tallas, datos de entrega, método de pago, rol obligatorio) y es reversible. `scripts/verify_migration.py` la prueba con datos de la versión anterior y se verificó en SQLite y PostgreSQL.

> La cadena de migraciones antigua no sirve para crear una base **desde cero**. Por eso una base nueva se crea con `flask init-db` (crea las tablas y las marca al día) y una base con datos usa `flask db upgrade`.

---

## 6. Rutas de la aplicación

### Tienda (públicas)
| Ruta | Descripción |
|---|---|
| `/` | Inicio |
| `/catalogo` | Catálogo con filtros, orden y paginación |
| `/producto/<id>` | Detalle de producto |
| `/cart/` | Ver carrito. Además `/cart/add/<id>`, `/cart/update/<id>` y `/cart/remove/<id>` (POST) |
| `/test-db` | Comprueba la conexión a la base de datos |

### Cuenta
| Ruta | Descripción |
|---|---|
| `/register`, `/login` | Registro e inicio de sesión |
| `/logout` | Cierre de sesión (POST) |
| `/cuenta` | Datos de la cuenta |
| `/change-password` | Cambiar contraseña |
| `/select-favs` | Elegir categorías favoritas |

### Compra (requieren sesión)
| Ruta | Descripción |
|---|---|
| `/checkout` | Datos de entrega |
| `/payment/<id_pedido>` | Pago simulado (`/payment` redirige al último pedido pendiente) |
| `/orders/<id>/confirmation` | Confirmación |
| `/orders`, `/orders/<id>` | Historial y detalle |
| `/orders/<id>/cancel` | Cancelar (POST) |
| `/invoice/<id>` | Factura imprimible |

### Administración (solo administradores)
`/admin/` (resumen), `/admin/products` (+ `create`, `edit/<id>`, `delete/<id>`), `/admin/users` (+ `add`, `edit/<id>`, `delete/<id>`) y `/admin/orders` (+ `<id>` y `<id>/status`).

---

## 7. Instalación y puesta en marcha

Requisitos: Python 3.10 o superior.

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\activate

# 2. Dependencias
pip install -r requirements-dev.txt   # solo para ejecutar: requirements.txt

# 3. Configuración
cp .env.example .env               # Windows: copy .env.example .env
#    edita SECRET_KEY (y DATABASE_URL si usas PostgreSQL)

# 4. Aplicación para el comando flask
export FLASK_APP=app:app           # Windows (PowerShell): $env:FLASK_APP = "app:app"
```

### Base de datos nueva
```bash
flask init-db                      # crea las tablas y las marca como migradas
flask create-admin                 # pide usuario, correo y contraseña
python seed_products.py            # opcional: 14 prendas de ejemplo
flask run                          # http://127.0.0.1:5000
```

### Base de datos existente (con datos de la versión anterior)
```bash
# 1. Haz una copia de seguridad antes de continuar
flask db upgrade                   # aplica la migración sin borrar datos
flask create-admin                 # el primer usuario ya no es administrador automáticamente
flask run
```
Los productos antiguos quedan sin tallas ni tipo de prenda; se completan desde `/admin/products`.

### Con SQLite o PostgreSQL
Si `DATABASE_URL` está vacío se usa SQLite local (`nevora_dev.sqlite3`). Para PostgreSQL define, por ejemplo, `DATABASE_URL=postgresql://usuario:clave@host:5432/base`.

---

## 8. Configuración (`.env`)

Copia `.env.example` a `.env` y **nunca lo subas al repositorio**.

| Variable | Para qué sirve |
|---|---|
| `APP_ENV` | `development` (por defecto) o `production`. En producción la cookie de sesión es `Secure` y la app exige `SECRET_KEY` |
| `SECRET_KEY` | Clave que firma las sesiones y la cookie del carrito. Usa una cadena larga y aleatoria |
| `DATABASE_URL` | Conexión a la base. Vacía = SQLite local. Acepta el esquema antiguo `postgres://` |
| `UPLOAD_FOLDER` | Carpeta de fotos subidas (por defecto `static/uploads`) |
| `STORE_CONTACT_EMAIL`, `_PHONE`, `_ADDRESS`, `_HOURS` | Datos del pie de página. Si no se definen, no se muestran |
| `TEST_DATABASE_URL` | Opcional: base PostgreSQL desechable para correr las pruebas |

Valores fijos en `config.py`: municipios permitidos, tamaño máximo de imagen (5 MB), formatos de imagen (jpg, jpeg, png, webp), duración y límites del carrito, 12 productos por página y umbral de stock bajo (5 unidades).

---

## 9. Comandos útiles

| Comando | Qué hace |
|---|---|
| `flask run` | Servidor de desarrollo |
| `flask init-db` | Crea las tablas en una base vacía; no modifica una base que ya tiene tablas |
| `flask create-admin` | Crea un administrador o promueve a un usuario existente por su correo |
| `flask db upgrade` | Aplica las migraciones a una base existente |
| `flask db migrate -m "mensaje"` | Genera una migración nueva tras cambiar `models.py` |
| `python seed_products.py` | Inserta productos de ejemplo solo si la tabla de productos está vacía |
| `gunicorn app:app` | Servidor de producción |

---

## 10. Pruebas

```bash
pytest                                                        # SQLite en memoria
TEST_DATABASE_URL=postgresql://user:pass@host/db pytest       # contra PostgreSQL (base vacía y desechable)
python scripts/verify_migration.py <DATABASE_URL> <legacy_models.py>   # migración con datos antiguos
```

El conjunto tiene **179 pruebas** que cubren catálogo y filtros, carrito y su fusión, registro e inicio de sesión, validación de entrega, checkout, pagos, cancelaciones, panel de administración y principios SOLID. Se ejecutaron con éxito sobre SQLite y PostgreSQL 16.

> **Advertencia:** `TEST_DATABASE_URL` debe apuntar a una base desechable, nunca a la de producción.

---

## 11. Seguridad
- **CSRF** en todos los formularios.
- **Contraseñas** con hash (Werkzeug).
- **Control de roles en el servidor** (`admin_required` y una comprobación previa en todo el blueprint de administración).
- **Registro público** sin privilegios de administrador.
- **Validación en el servidor** de entrega, cantidades, precios y existencias; lo que envía el navegador nunca se acepta sin comprobar.
- **Cookies** `HttpOnly` y `SameSite=Lax`; `Secure` en producción. La cookie del carrito está firmada y no contiene precios.
- **Redirecciones seguras** tras el login (`is_safe_url`).
- **Subida de imágenes:** solo jpg, jpeg, png y webp, hasta 5 MB, con nombres únicos generados por el servidor.
- **Pagos simulados:** no se almacenan datos bancarios.
- **Consultas** con SQLAlchemy (parámetros enlazados) y escape de comodines en las búsquedas.

---

## 12. Principios SOLID

| Principio | Evidencia |
|---|---|
| **S** – Responsabilidad única | Cada servicio hace una cosa: `DeliveryPolicy` (municipios), `OrderService` (pedidos), `CatalogService` (consultas), `ImageService` (imágenes) |
| **O** – Abierto/cerrado | Un medio de pago nuevo es una subclase de `PaymentGateway`; un filtro nuevo es una clase con `apply()`; nuevos municipios se agregan en la configuración |
| **L** – Sustitución de Liskov | `CookieCartStore` y `DatabaseCartStore` son intercambiables; todas las pasarelas cumplen el mismo contrato |
| **I** – Segregación de interfaces | `OrderService` depende solo del `Protocol` `CheckoutCart`, no de todo el carrito |
| **D** – Inversión de dependencias | Los servicios reciben sesión, almacenes y pasarelas por constructor; `factory.py` los compone |

`tests/test_solid.py` comprueba varios de estos puntos. El detalle está en [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

---

## 13. Despliegue
1. Define `APP_ENV=production`, una `SECRET_KEY` larga y aleatoria y `DATABASE_URL` en el entorno del proveedor (no en el repositorio).
2. Haz copia de seguridad de la base y ejecuta `flask db upgrade`.
3. Crea un administrador con `flask create-admin`.
4. Ejecuta `gunicorn app:app`.
5. Usa HTTPS: en producción la cookie de sesión se marca como `Secure`.
6. Guarda `static/uploads/` en un almacenamiento persistente, o define `UPLOAD_FOLDER`.

---

## 14. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Could not open requirements file` | Estás una carpeta por encima. Entra a la carpeta que contiene `requirements.txt` |
| `column products.garment_type does not exist` | La base aún tiene el esquema antiguo. Haz copia de seguridad y ejecuta `flask db upgrade` |
| `flask init-db` dice que la base ya tiene tablas | Es lo esperado: no modifica bases existentes. Usa `flask db upgrade` |
| `Import "flask" could not be resolved` en el editor | El editor usa otro Python. Selecciona el intérprete de `.venv` (VS Code: *Python: Select Interpreter*) |
| `SECRET_KEY` insegura en el aviso | Define `SECRET_KEY` en `.env`. En producción es obligatoria |
| PowerShell bloquea `activate` | `Set-ExecutionPolicy -Scope Process RemoteSigned` |
| `/admin/` devuelve 403 | Tu usuario no es administrador. Usa `flask create-admin` con tu correo |

---

## 15. Notas de la versión y migración
- **Rutas nuevas:** `/catalogo`, `/producto/<id>`, `/cart/`, `/payment/<id_pedido>` y `/admin/...`. El cierre de sesión ahora es POST.
- **Administradores:** el primer usuario registrado ya no es administrador automáticamente; usa `flask create-admin`. Reemplaza al antiguo `make_admin.py`.
- **Base de desarrollo:** ahora es `nevora_dev.sqlite3` (antes `db.sqlite3`, que se conserva sin tocar).
- **Scripts antiguos:** `fix_db.py` (ejecuta `DROP TABLE`) y `transfer_users.py` (incompatible con SQLAlchemy 2) están en `scripts/legacy/` solo como referencia.
- **Documentación antigua:** los archivos de `docs/` distintos de `ARQUITECTURA.md` describen la versión anterior y llevan un aviso.
- **Fotos:** los productos de ejemplo no traen foto y usan la imagen por defecto; sube las reales desde el panel.
- **Seguridad:** si alguna vez se subió un `.env` con credenciales al repositorio, cambia esas contraseñas de inmediato.
