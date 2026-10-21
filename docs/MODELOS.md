# 🗄️ Modelos de Base de Datos

Documentación detallada de todos los modelos y relaciones de base de datos de la aplicación.

---

## 📌 User (Usuarios)

**Tabla**: `users`  
**Descripción**: Almacena información de usuarios registrados

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único del usuario |
| `username` | String(80) | UNIQUE, NOT NULL | Nombre de usuario (único para cada cuenta) |
| `email` | String(120) | UNIQUE, NOT NULL | Correo electrónico (único y validado) |
| `password_hash` | Text | NOT NULL | Contraseña encriptada con werkzeug |
| `role` | String(20) | DEFAULT 'user' | Rol del usuario ('user' o 'admin') |
| `fav_category1` | String(50) | NULLABLE | Primera categoría favorita para recomendaciones |
| `fav_category2` | String(50) | NULLABLE | Segunda categoría favorita para recomendaciones |

### Índices
- `username` (UNIQUE)
- `email` (UNIQUE)

### Métodos Python

#### `set_password(password: str) -> None`
```python
def set_password(self, password):
    """Encripta y guarda la contraseña en password_hash"""
    self.password_hash = generate_password_hash(password)
```
- Usa `werkzeug.security.generate_password_hash`
- Se llama al registrarse o cambiar contraseña

#### `check_password(password: str) -> bool`
```python
def check_password(self, password):
    """Verifica si la contraseña es correcta"""
    return check_password_hash(self.password_hash, password)
```
- Compara contraseña con hash
- Se usa en login y cambio de contraseña

#### `is_admin` (Propiedad)
```python
@property
def is_admin(self):
    """Retorna True si el usuario es administrador"""
    return self.role == 'admin'
```
- Acceso: `user.is_admin`
- Retorna: `True` si `role == 'admin'`, `False` en caso contrario

### Relaciones

#### `orders` (Relación 1:N)
```
User ──── Order
(1)        (N)
```
- Un usuario puede tener múltiples pedidos
- Acceso: `user.orders`
- Ordenados por: `Order.id DESC`

#### `cart` (Relación 1:1)
```
User ──── Cart
(1)        (1)
```
- Un usuario tiene exactamente un carrito
- Acceso: `user.cart`
- Creado automáticamente al agregar primer item

### Restricciones de Negocio

1. **Primer usuario es admin**
   ```python
   if User.query.count() == 0:
       user.role = 'admin'
   ```

2. **Username único**
   - Validación en formulario RegisterForm
   - Error: "El nombre de usuario ya existe."

3. **Email único y válido**
   - Validación con `email-validator`
   - Error: "El email ya está en uso."

4. **Contraseña mínimo 6 caracteres**
   - Validación en formulario
   - Se recomienda mayor seguridad

### Ciclo de Vida

```
[Registro] → Crear User
    ↓
[Validar datos]
    ↓
[Encriptar contraseña]
    ↓
[¿Primer usuario?] → [Marcar como admin]
    ↓
[Guardar en BD]
    ↓
[Auto-login] → [Redirige a /select-favs]
```

---

## 👕 Product (Productos)

**Tabla**: `products`  
**Descripción**: Catálogo de productos disponibles para compra

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único |
| `name` | String(120) | NOT NULL | Nombre de la prenda |
| `brand` | String(120) | NOT NULL | Marca de la prenda |
| `price` | Float | NOT NULL | Precio de venta |
| `stock` | Integer | NOT NULL | Cantidad disponible |
| `description` | Text | NULLABLE | Descripción de la prenda |
| `category` | String(50) | NULLABLE | Categoría (para filtros y recomendaciones) |
| `image_filename` | String(255) | NULLABLE | Nombre del archivo de imagen en `static/uploads/` |

### Validaciones

- **price**: Debe ser ≥ 0
- **stock**: Debe ser ≥ 0 (entero)
- **name**: Máximo 120 caracteres
- **brand**: Máximo 120 caracteres

### Métodos Python

#### `image_url() -> str`
```python
def image_url(self):
    """Retorna la URL de la imagen o una por defecto"""
    if self.image_filename:
        return url_for('static', filename=f'uploads/{self.image_filename}')
    return url_for('static', filename='no_image.png')
```
- Retorna: URL de imagen o imagen por defecto
- Uso: En templates para mostrar imagen

### Relaciones

#### `cartitems` (Relación 1:N)
```
Product ──── CartItem
(1)        (N)
```
- Un producto puede estar en múltiples carritos
- Acceso: `product.cartitems`

#### `orderitems` (Relación 1:N)
```
Product ──── OrderItem
(1)        (N)
```
- Un producto puede estar en múltiples pedidos
- Acceso: `product.orderitems`

### Restricciones de Negocio

1. **No se puede eliminar si tiene pedidos**
   ```python
   if OrderItem.query.filter_by(product_id=product.id).first():
       flash("No puedes eliminar este producto porque tiene pedidos.")
   ```

2. **Stock se reduce al crear Order**
   ```python
   for item in cart.items:
       item.product.stock -= item.quantity
   ```

3. **Stock se restaura al cancelar Order**
   ```python
   for item in order.items:
       item.product.stock += item.quantity
   ```

### Ciclo de Vida

```
[Crear en admin] → [Validar datos]
    ↓
[Guardar imagen (opcional)]
    ↓
[Guardar en BD]
    ↓
[Aparecer en /catalogo]
    ↓
[Usuarios pueden agregar al carrito]
    ↓
[Stock disminuye al comprar]
    ↓
[Se restaura al cancelar pedido]
```

---

## 🛒 Cart (Carrito)

**Tabla**: `carts`  
**Descripción**: Carrito de compras de cada usuario

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único |
| `user_id` | Integer | FK(users.id), NOT NULL, UNIQUE | Usuario propietario |
| `created_at` | DateTime | DEFAULT NOW() | Fecha de creación |

### Relación Foreign Key

```
carts.user_id → users.id (UNIQUE)
```
- Un carrito por usuario (1:1)
- ON DELETE CASCADE: Si se elimina usuario → se elimina carrito

### Relaciones

#### `user` (Relación 1:1 inversa)
```python
user = db.relationship('User', backref=db.backref('cart', uselist=False))
```
- Acceso: `cart.user` o `user.cart`
- `uselist=False`: Solo un carrito por usuario

#### `items` (Relación 1:N)
```python
items = db.backref('cart', cascade='all, delete-orphan')
```
- Acceso: `cart.items`
- Contenedor de CartItems
- ON DELETE CASCADE: Si se elimina carrito → se eliminan items

### Ciclo de Vida

```
[Usuario se registra/login]
    ↓
[Intenta agregar producto]
    ↓
[¿Tiene carrito?] → NO → [Crear carrito]
    ↓
[Agregar CartItem]
    ↓
[Usuario puede...]
├─ Continuar comprando
├─ Ver carrito
├─ Modificar cantidades
├─ Remover items
└─ Checkout
    ↓
[Checkout crea Order]
    ↓
[Vacía carrito]
```

---

## 📦 CartItem (Items del Carrito)

**Tabla**: `cart_items`  
**Descripción**: Productos individuales dentro de un carrito

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único |
| `cart_id` | Integer | FK(carts.id), NOT NULL | Carrito propietario |
| `product_id` | Integer | FK(products.id), NOT NULL | Producto en el carrito |
| `quantity` | Integer | NOT NULL, DEFAULT 1 | Cantidad del producto |

### Foreign Keys

```
cart_items.cart_id → carts.id (ON DELETE CASCADE)
cart_items.product_id → products.id (ON DELETE CASCADE)
```

### Relaciones

#### `cart` (Relación 1:N inversa)
```python
cart = db.relationship('Cart', backref=db.backref('items', cascade='all, delete-orphan'))
```
- Acceso: `item.cart` o `cart.items`

#### `product` (Relación 1:N inversa)
```python
product = db.relationship('Product')
```
- Acceso: `item.product`
- Contiene todos los datos del producto

### Métodos Python

#### `line_total() -> float`
```python
def line_total(self):
    """Calcula el subtotal del item (cantidad × precio)"""
    return (self.product.price or 0) * (self.quantity or 0)
```
- Retorna: `quantity × price`
- Uso: Cálculo de totales en carrito

### Ejemplo de Uso

```python
# Agregar producto al carrito
item = CartItem(cart_id=cart.id, product_id=product.id, quantity=2)
db.session.add(item)

# Obtener subtotal
subtotal = item.line_total()  # 2 × price

# Aumentar cantidad
item.quantity += 1
```

---

## 📋 Order (Pedidos)

**Tabla**: `orders`  
**Descripción**: Pedidos realizados por usuarios

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único del pedido |
| `user_id` | Integer | FK(users.id), NOT NULL | Usuario que realizó la compra |
| `created_at` | DateTime | DEFAULT NOW() | Fecha y hora de creación |
| `status` | String(50) | DEFAULT 'created' | Estado actual del pedido |
| `total` | Float | DEFAULT 0.0 | Monto total del pedido |

### Foreign Keys

```
orders.user_id → users.id (ON DELETE CASCADE)
```

### Estados Válidos

| Estado | Código | Descripción | Transición |
|--------|--------|-------------|-----------|
| `created` | 1️⃣ | Recién creado, sin pagar | → paid, cancelled |
| `paid` | 2️⃣ | Pagado | → shipped, cancelled |
| `shipped` | 3️⃣ | Enviado | → delivered |
| `delivered` | 4️⃣ | Entregado | (final) |
| `cancelled` | ❌ | Cancelado | (final) |

### Transiciones Permitidas

```
created ──→ paid ──────→ shipped ──→ delivered (✅)
  ↓                         
  └─→ cancelled (❌)────→ (final)
      ↓
      └─→ paid ──→ shipped ──→ delivered

paid ──→ shipped ──→ delivered (✅)
  ↓
  └─→ cancelled (❌)
```

### Relaciones

#### `user` (Relación N:1)
```python
user = db.relationship('User', backref=db.backref('orders', order_by='Order.id.desc()'))
```
- Acceso: `order.user`
- Ordenados: Por ID descendente

#### `items` (Relación 1:N)
```python
items = db.backref('order', cascade='all, delete-orphan')
```
- Acceso: `order.items`
- ON DELETE CASCADE: Si se elimina pedido → se eliminan items

### Ciclo de Vida de una Orden

```
[Usuario en /checkout]
    ↓
[Crear Order]
├─ status = 'created'
├─ total = 0.0
└─ user_id = current_user.id
    ↓
[Para cada CartItem]
├─ Crear OrderItem (copia)
├─ Reducir stock del producto
└─ Sumar al total
    ↓
[Guardar Order.total]
    ↓
[Vaciar carrito]
    ↓
[Usuario va a /payment]
    ↓
[Procesa pago]
    ↓
[Status = 'paid']
    ↓
[Admin puede cambiar estado]
├─ 'shipped' (enviado)
├─ 'delivered' (entregado)
└─ 'cancelled' (cancelado)
```

### Ejemplo de Uso

```python
# Crear orden
order = Order(user_id=user.id, status='created', total=0.0)
db.session.add(order)
db.session.flush()  # Para obtener order.id

# Agregar items
for item in cart.items:
    order_item = OrderItem(
        order_id=order.id,
        product_id=item.product_id,
        quantity=item.quantity,
        price=item.product.price
    )
    db.session.add(order_item)
    order.total += item.quantity * item.product.price

# Cambiar estado
order.status = 'paid'
db.session.commit()
```

---

## 📄 OrderItem (Items del Pedido)

**Tabla**: `order_items`  
**Descripción**: Productos individuales dentro de un pedido

### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---|---|
| `id` | Integer | PRIMARY KEY, AUTOINCREMENT | Identificador único |
| `order_id` | Integer | FK(orders.id), NOT NULL | Pedido propietario |
| `product_id` | Integer | FK(products.id), NOT NULL | Producto comprado |
| `quantity` | Integer | NOT NULL, DEFAULT 1 | Cantidad comprada |
| `price` | Float | NOT NULL | Precio unitario en momento de la compra |

### Foreign Keys

```
order_items.order_id → orders.id (ON DELETE CASCADE)
order_items.product_id → products.id (ON DELETE CASCADE)
```

### Relaciones

#### `order` (Relación N:1)
```python
order = db.relationship('Order', backref=db.backref('items', cascade='all, delete-orphan'))
```
- Acceso: `item.order` o `order.items`

#### `product` (Relación N:1)
```python
product = db.relationship('Product')
```
- Acceso: `item.product`
- Nota: Solo lectura, no se modifica

### Métodos Python

#### `line_total() -> float`
```python
def line_total(self):
    """Calcula el subtotal del item (cantidad × precio)"""
    return (self.price or 0) * (self.quantity or 0)
```
- Retorna: `quantity × price`
- Nota: Usa `price` (no `product.price`), para historicidad

### Importancia de Guardar Precio

```python
# ✅ CORRECTO: Guardar precio en momento de compra
order_item = OrderItem(
    order_id=order.id,
    product_id=product.id,
    quantity=item.quantity,
    price=item.product.price  # Precio en ese momento
)

# ❌ INCORRECTO: Usar precio actual
# Si el producto cambia de precio después:
# El pedido antiguo tendría precio nuevo (incorrecto)
```

### Ejemplo de Uso

```python
# Crear item de pedido
order_item = OrderItem(
    order_id=123,
    product_id=5,
    quantity=2,
    price=19.99
)

# Obtener subtotal
subtotal = order_item.line_total()  # 2 × 19.99 = 39.98

# Ver detalles
print(order_item.product.name)  # Nombre de la prenda
print(order_item.price)        # Precio pagado
print(order_item.quantity)     # Cantidad
```

---

## 🔗 Diagrama de Relaciones

```
┌─────────────┐
│    User     │
├─────────────┤
│ id (PK)     │────────────┐
│ username    │            │
│ email       │            │
│ password    │            │ 1:N
│ role        │            │
│ fav_cat1    │            │
│ fav_cat2    │            │
└─────────────┘            │
      │                    │
      │ 1:1                │
      └──────┐             │
             ▼             │
        ┌─────────────┐    │
        │   Cart      │    │
        ├─────────────┤    │
        │ id (PK)     │    │
        │ user_id(FK) │    │
        │ created_at  │    │
        └─────────────┘    │
             │              │
             │ 1:N          │
             ▼              │
        ┌──────────────┐    │
        │  CartItem    │    │
        ├──────────────┤    │
        │ id (PK)      │    │
        │ cart_id (FK) ├────┼──→ (Can be deleted)
        │ product_id (FK) │    │
        │ quantity     │    │
        └──────────────┘    │
             │              │
             │ FK           │
             ▼              │
        ┌─────────────┐     │
        │   Product   │     │
        ├─────────────┤     │
        │ id (PK)     │     │
        │ name        │     │
        │ brand       │     │
        │ price       │     │
        │ stock       │     │
        │ category    │     │
        │ image       │     │
        └─────────────┘     │
             ▲              │
             │              │
             │ 1:N        1:N
             │              │
        ┌──────────────┐    │
        │  OrderItem   │    │
        ├──────────────┤    │
        │ id (PK)      │    │
        │ order_id(FK) │    │
        │ product_id (FK) │    │
        │ quantity     │    │
        │ price        │    │
        └──────────────┘    │
             ▲              │
             │              │
             │ 1:N        N:1
             │              │
        ┌─────────────┐     │
        │   Order     │     │
        ├─────────────┤     │
        │ id (PK)     │     │
        │ user_id(FK) │◄────┘
        │ created_at  │
        │ status      │
        │ total       │
        └─────────────┘
```

---

## 💾 Esquema SQL Completo

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    fav_category1 VARCHAR(50),
    fav_category2 VARCHAR(50)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    brand VARCHAR(120) NOT NULL,
    price FLOAT NOT NULL,
    stock INTEGER NOT NULL,
    description TEXT,
    category VARCHAR(50),
    image_filename VARCHAR(255)
);

CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'created',
    total FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price FLOAT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

---

## 🔍 Consultas Comunes

### Obtener carrito de un usuario
```python
cart = Cart.query.filter_by(user_id=user.id).first()
# O más simple:
cart = current_user.cart
```

### Obtener productos en carrito
```python
items = cart.items
for item in items:
    print(f"{item.product.name}: {item.quantity} × ${item.product.price}")
```

### Obtener total del carrito
```python
total = sum(item.line_total() for item in cart.items)
```

### Obtener pedidos de un usuario
```python
orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
```

### Obtener items de un pedido
```python
items = order.items
for item in items:
    print(f"{item.product.name}: {item.quantity} × ${item.price}")
```

### Calcular total de pedido
```python
total = sum(item.line_total() for item in order.items)
# O más simple:
total = order.total
```

### Obtener pedidos en estado "paid"
```python
paid_orders = Order.query.filter_by(status='paid').all()
```

### Obtener productos en una categoría
```python
fiction_products = Product.query.filter_by(category='Ficción').all()
```

### Cambiar estado de pedido
```python
order.status = 'shipped'
db.session.commit()
```

### Cancelar pedido (restaurar stock)
```python
for item in order.items:
    item.product.stock += item.quantity
order.status = 'cancelled'
db.session.commit()
```

---

## 📊 Estadísticas por Consulta

### Total de ingresos
```python
total_revenue = db.session.query(func.sum(Order.total)).filter_by(status='paid').scalar()
```

### Total de pedidos
```python
total_orders = Order.query.count()
```

### Total de usuarios
```python
total_users = User.query.count()
```

### Total de productos vendidos
```python
total_sold = db.session.query(func.sum(OrderItem.quantity)).scalar()
```

### Producto más vendido
```python
most_sold = db.session.query(
    Product.name,
    func.sum(OrderItem.quantity).label('total_sold')
).join(OrderItem).group_by(Product.id).order_by('total_sold').first()
```

---

**Documento actualizado**: Noviembre 2025
