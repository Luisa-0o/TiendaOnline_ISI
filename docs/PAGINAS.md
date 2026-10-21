# 📄 Documentación de Páginas

Este documento describe todas las páginas de la aplicación, sus funcionalidades y datos asociados.

---

## 🏠 Página Principal (`/`)

**Acceso**: Autenticado  
**Método**: GET  
**Template**: `profile.html`

### Descripción
Muestra el perfil del usuario actual con opciones de navegación a diferentes secciones.

### Elementos
- Nombre del usuario
- Email registrado
- Botones de navegación:
  - Ir al catálogo
  - Ver mis pedidos
  - Ver carrito
  - Panel admin (si es admin)
  - Cambiar contraseña
  - Cerrar sesión

---

## 📝 Registro (`/register`)

**Acceso**: Público (redirect si ya está autenticado)  
**Método**: GET (mostrar formulario) / POST (procesar registro)  
**Template**: `register.html`

### Descripción
Permite que nuevos usuarios se registren en la plataforma.

### Campos del Formulario
- **Username**: 
  - Rango: 3-80 caracteres
  - Restricción: Debe ser único
  - Error: "El nombre de usuario ya existe."

- **Email**: 
  - Validación: Email válido
  - Restricción: Debe ser único
  - Error: "El email ya está en uso."

- **Contraseña**: 
  - Rango: Mín. 6 caracteres
  - Validación: Debe contener caracteres variados (recomendado)

- **Confirmar Contraseña**: 
  - Validación: Debe coincidir con contraseña

### Validaciones
- ✅ Username único
- ✅ Email válido y único
- ✅ Contraseñas coinciden
- ✅ Longitudes correctas

### Después del Registro
1. Usuario se crea automáticamente
2. Si es el **primer usuario** → Se marca como **admin**
3. Sistema inicia sesión automáticamente
4. Redirige a `/select-favs` (seleccionar categorías favoritas)

### Notas de Seguridad
- Las contraseñas se encriptan con `werkzeug.security`
- Validación CSRF en el formulario
- Validación de emails con `email-validator`

---

## 🔐 Login (`/login`)

**Acceso**: Público (redirect si ya está autenticado)  
**Método**: GET (mostrar formulario) / POST (procesar login)  
**Template**: `login.html`

### Descripción
Permite que usuarios registrados inicien sesión.

### Campos del Formulario
- **Email**: Email registrado (validación formato email)
- **Contraseña**: Contraseña de la cuenta

### Validaciones
- ✅ Email existe en BD
- ✅ Contraseña es correcta
- ✅ Usuario no está bloqueado

### Mensajes de Error
- "Correo o contraseña incorrectos." (genérico por seguridad)

### Después del Login
1. Sistema verifica credenciales
2. Si es correcto → Inicia sesión
3. Redirige a `/` (perfil/inicio)
4. Si es incorrecto → Muestra error y mantiene en login

### Notas de Seguridad
- Validación CSRF
- Mensaje de error genérico (no revela si email existe)
- Contraseña se verifica con `check_password_hash`

---

## 🚪 Logout (`/logout`)

**Acceso**: Autenticado  
**Método**: GET  

### Descripción
Cierra la sesión del usuario actual.

### Acciones
1. Destruye sesión de usuario
2. Muestra mensaje "Sesión cerrada."
3. Redirige a `/login`

---

## 🔑 Cambiar Contraseña (`/change-password`)

**Acceso**: Autenticado  
**Método**: GET (mostrar formulario) / POST (procesar cambio)  
**Template**: `change_password.html`

### Descripción
Permite que usuarios cambien su contraseña.

### Campos del Formulario
- **Contraseña Actual**: Contraseña actual del usuario
- **Nueva Contraseña**: Nueva contraseña (mín. 6 caracteres)
- **Confirmar Nueva Contraseña**: Confirmación de nueva contraseña

### Validaciones
- ✅ Contraseña actual es correcta
- ✅ Nueva contraseña tiene mín. 6 caracteres
- ✅ Las nuevas contraseñas coinciden

### Mensajes
- **Error**: "Contraseña actual incorrecta."
- **Éxito**: "Contraseña actualizada correctamente."

### Después del Cambio
- Contraseña se actualiza
- Sesión se mantiene activa
- Redirige a `/` (perfil)

---

## ⭐ Seleccionar Categorías Favoritas (`/select-favs`)

**Acceso**: Autenticado (solo usuarios normales)  
**Método**: GET (mostrar formulario) / POST (procesar selección)  
**Template**: `select_favs.html`

### Descripción
Los usuarios normales seleccionan 2 categorías favoritas para recibir recomendaciones personalizadas.

### Funcionamiento
1. Obtiene todas las categorías de productos existentes
2. Si usuario es admin → Redirige a `/admin`
3. Muestra checkboxes para cada categoría

### Validación
- **Restricción**: Debe seleccionar **exactamente 2 categorías**
- **Error**: "Por favor selecciona exactamente 2 categorías."

### Datos Guardados
- `fav_category1`: Primera categoría seleccionada
- `fav_category2`: Segunda categoría seleccionada

### Después de Guardar
- Mensaje: "✅ Preferencias guardadas."
- Redirige a `/catalogo`

### Uso de Favoritas
- Se usan en `/catalogo` para mostrar recomendaciones
- Filtro: `Product.category.in_([fav1, fav2])`
- Se muestran hasta 8 productos recomendados

---

## 👗 Catálogo (`/catalogo`)

**Acceso**: Autenticado  
**Método**: GET  
**Template**: `catalogo.html`

### Descripción
Muestra el catálogo completo de productos disponibles con búsqueda, filtros y recomendaciones.

### Parámetros de URL
| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `q` | string | Búsqueda por nombre o marca | `?q=camisa` |
| `category` | string | Filtro por categoría | `?category=Ficción` |

### Ejemplos de Búsqueda
- `/catalogo` → Todos los productos
- `/catalogo?q=rowling` → Busca por marca
- `/catalogo?category=Ficción` → Solo ficción
- `/catalogo?q=potter&category=Ficción` → Búsqueda + filtro

### Búsqueda en BD
```python
products_q = Product.query
if query:
    products_q = products_q.filter(
        (Product.name.ilike(f'%{query}%')) |
        (Product.brand.ilike(f'%{query}%'))
    )
if selected_category:
    products_q = products_q.filter(Product.category == selected_category)
```

### Información Mostrada por Producto
- Imagen (imagen)
- Nombre
- Marca
- Precio
- Categoría
- Descripción (truncada)
- Botón "Agregar al carrito"

### Recomendaciones Personalizadas
- Solo para usuarios normales (no admins)
- Basadas en `fav_category1` y `fav_category2`
- Muestra hasta 8 productos
- Se ordena por ID descendente (más recientes)

### Lista de Categorías
- Obtiene todas las categorías no nulas del BD
- Se ordena alfabéticamente
- Se usa para el dropdown de filtros

---

## 🛒 Ver Carrito (`/cart`)

**Acceso**: Autenticado  
**Método**: GET  
**Template**: `cart.html`

### Descripción
Muestra el carrito de compras del usuario actual.

### Lógica
1. Obtiene carrito del usuario (`current_user.cart`)
2. Si no existe → Crea uno nuevo
3. Obtiene todos los items del carrito

### Información Mostrada

#### Por cada item:
| Dato | Descripción |
|------|-------------|
| Imagen | Imagen del producto |
| Nombre | Nombre del producto |
| Marca | Marca de la prenda |
| Precio Unitario | Precio de venta |
| Cantidad | Cantidad en carrito |
| Subtotal | cantidad × precio |
| Botón Remover | Elimina item o disminuye cantidad |

#### Totales:
- **Subtotal**: Suma de todos los subtotales
- **Impuestos**: $0.00 (campo fijo)
- **Total**: Subtotal + impuestos

### Botones de Acción
- **"Continuar Comprando"** → Va a `/catalogo`
- **"Proceder al Checkout"** → Va a `/checkout`

### Casos Especiales
- Carrito vacío → Muestra mensaje y botón para ir al catálogo
- Usuario sin carrito → Se crea automáticamente

---

## ➕ Agregar al Carrito (`/cart/add/<product_id>`)

**Acceso**: Autenticado  
**Método**: GET o POST  
**Parámetros**:
- `product_id` (requerido): ID del producto
- `quantity` (opcional): Cantidad (default: 1)

### Descripción
Agrega un producto al carrito del usuario.

### Lógica
1. Obtiene producto por ID
2. Valida cantidad (debe ser > 0)
3. Valida stock disponible
4. Obtiene/crea carrito del usuario
5. Si item ya existe → Suma cantidad
6. Si no existe → Crea nuevo CartItem
7. Reduce stock disponible
8. Guarda cambios

### Validaciones
```python
if qty <= 0:
    flash('Cantidad inválida.', 'warning')
    
if product.stock < qty:
    flash('No hay suficiente stock disponible.', 'danger')
    
if existing_item and product.stock < item.quantity + qty:
    flash('No hay suficiente stock para aumentar.', 'danger')
```

### Mensajes
- ✅ Éxito: `"✅ Añadido {qty} x '{name}' al carrito."`
- ❌ Error: Cantidad inválida, stock insuficiente

### Redireccionamiento
- Después de agregar → Redirige a `/catalogo` (para continuar comprando)

---

## ❌ Remover del Carrito (`/cart/remove/<item_id>`)

**Acceso**: Autenticado  
**Método**: POST  
**Parámetro**: `item_id` (ID del item en carrito)

### Descripción
Reduce la cantidad de un producto o lo elimina completamente del carrito.

### Lógica
1. Obtiene carrito del usuario
2. Busca item por ID en el carrito
3. Si cantidad > 1 → Reduce cantidad en 1
4. Si cantidad = 1 → Elimina item del carrito
5. Guarda cambios

### Mensajes
- Si reduce: "Se eliminó una unidad de '{name}'."
- Si elimina: "'{name}' fue eliminado del carrito."

### Redireccionamiento
- Siempre redirige a `/cart` (ver carrito)

---

## 💳 Checkout (`/checkout`)

**Acceso**: Autenticado  
**Método**: GET o POST  

### Descripción
Procesa la creación de un pedido desde el carrito.

### Validaciones Iniciales
```python
if not cart or len(cart.items) == 0:
    flash('El carrito está vacío.', 'warning')
    return redirect(url_for('catalogo'))

for item in cart.items:
    if item.product.stock < item.quantity:
        flash(f'No hay suficiente stock para "{item.product.name}".', 'danger')
        return redirect(url_for('view_cart'))
```

### Proceso de Checkout
1. Valida que carrito no esté vacío
2. Valida stock para cada item
3. Crea nueva Order:
   - `status = 'created'`
   - `total = 0.0`
4. Para cada CartItem:
   - Reduce stock del producto
   - Crea OrderItem (copia del CartItem)
   - Suma cantidad × precio al total
   - Elimina CartItem del carrito
5. Guarda total en Order
6. Commit a BD

### Datos Guardados en Order
```
id: ID auto-generado
user_id: ID del usuario actual
created_at: Timestamp actual
status: 'created'
total: Suma de (cantidad × precio)
```

### Mensajes
- ✅ Éxito: "✅ Pedido creado correctamente."
- ❌ Error: "Ocurrió un error creando el pedido."

### Redireccionamiento
- Éxito → `/payment` (ir a pagar)
- Error → `/cart` (volver al carrito)

### Manejo de Errores
- SQLAlchemy exceptions son capturadas
- BD hace rollback si hay error
- Log de error en servidor

---

## 💰 Pago (`/payment`)

**Acceso**: Autenticado  
**Método**: GET (mostrar formulario) / POST (procesar pago)  
**Template**: `payment.html`

### Descripción
Página para procesar el pago de un pedido.

### Lógica
1. Obtiene el último pedido del usuario en estado `'created'`
2. Si GET → Muestra formulario de pago
3. Si POST → Procesa pago

### Campos del Formulario
- **Método de Pago**: Tarjeta de Crédito
- **Número de Tarjeta**: 16 dígitos
- **Fecha de Vencimiento**: MM/AA
- **CVV**: 3 dígitos

### Validaciones
- Tarjeta con formato válido
- CVV de 3-4 dígitos
- Fecha de vencimiento futura

### Procesamiento (Simulado)
```python
if order:
    order.status = 'paid'
    db.session.commit()
```

### Mensajes
- ✅ Éxito: "✅ Pago procesado correctamente. ¡Gracias por tu compra!"

### Redireccionamiento
- Éxito → `/catalogo` (volver al catálogo)

### Notas
- El pago es **simulado** (no integra pasarela real)
- No guarda datos de tarjeta
- Solo cambia estado a 'paid'

---

## 📋 Ver Pedidos (`/orders`)

**Acceso**: Autenticado  
**Método**: GET  
**Template**: `orders.html`

### Descripción
Muestra el historial de todos los pedidos del usuario actual.

### Información Mostrada
| Columna | Descripción |
|---------|-------------|
| ID Pedido | Número del pedido |
| Fecha | Fecha de creación |
| Estado | Estado actual (badge con color) |
| Total | Monto total del pedido |
| Acciones | Botón "Ver detalle" |

### Colores de Estado
- **created** → Gris (Recién creado)
- **paid** → Verde (Pagado)
- **shipped** → Celeste (Enviado)
- **delivered** → Azul (Entregado)
- **cancelled** → Rojo (Cancelado)

### Ordenamiento
- Los pedidos se ordenan por ID descendente (más recientes primero)

### Interacción
- Click en "Ver detalle" → `/orders/<order_id>`

---

## 📄 Detalle de Pedido (`/orders/<order_id>`)

**Acceso**: Autenticado (solo propietario del pedido)  
**Método**: GET  
**Template**: `order_detail.html`

### Validación de Acceso
```python
if order.user_id != current_user.id:
    flash('Acceso denegado.', 'danger')
    return redirect(url_for('view_orders'))
```

### Descripción
Muestra todos los detalles de un pedido específico.

### Información Mostrada

#### Encabezado
- Número de pedido
- Fecha de creación (formateada)
- Estado con badge
- Total

#### Tabla de Productos
| Columna | Descripción |
|---------|-------------|
| Producto | Nombre + Marca |
| Cantidad | Cantidad comprada |
| Precio Unitario | Precio en momento de compra |
| Subtotal | cantidad × precio |

#### Resumen
- Subtotal total
- Impuestos: $0.00
- Total: Monto final

#### Botones de Acción
- **"Ver Factura"** → `/invoice/<order_id>` (abre factura imprimible)
- **"Cancelar Pedido"** → POST `/orders/<order_id>/cancel` (si es posible)
- **"Volver"** → `/orders` (lista de pedidos)

---

## ❌ Cancelar Pedido (`/orders/<order_id>/cancel`)

**Acceso**: Autenticado (solo propietario)  
**Método**: POST  

### Validaciones
```python
if order.user_id != current_user.id:
    flash('Acceso no permitido.', 'danger')

if order.status not in ['created', 'paid']:
    flash(f'No puedes cancelar un pedido en estado "{order.status}".', 'warning')
```

### Estados Permitidos para Cancelación
- `'created'` → Pedido recién creado
- `'paid'` → Pagado pero no enviado

### Proceso de Cancelación
1. Restaura stock para cada item:
   ```python
   for item in order.items:
       item.product.stock += item.quantity
   ```
2. Cambia estado a `'cancelled'`
3. Guarda en BD

### Mensaje
- ✅ Éxito: "✅ Pedido cancelado correctamente. El stock ha sido restaurado."
- ❌ Error: Acceso denegado o estado no permitido

### Redireccionamiento
- Después de cancelar → `/orders/<order_id>` (detalle del pedido)

---

## 📥 Ver Factura (`/invoice/<order_id>`)

**Acceso**: Autenticado (usuario propietario o admin)  
**Método**: GET  
**Template**: `invoice.html`

### Validación de Acceso
```python
if order.user_id != current_user.id and not current_user.is_admin:
    flash('Acceso restringido.', 'danger')
    return redirect(url_for('view_orders'))
```

### Descripción
Muestra la factura del pedido con opción de imprimir/descargar.

### Información de la Factura

#### Encabezado
- "📋 FACTURA DE COMPRA"
- Número de factura (#ID)
- Fecha de generación

#### Información del Pedido
- Número de pedido
- Fecha y hora
- Estado (con color)

#### Información del Cliente
- Nombre de usuario
- Email
- ID de cliente

#### Detalles de Productos
| Columna | Formato |
|---------|---------|
| Producto | Nombre + Marca |
| Cantidad | Número entero |
| Precio Unitario | $XX.XX |
| Subtotal | $XX.XX |

#### Resumen de Totales
- Subtotal: $XX.XX
- Impuestos: $0.00
- **Total**: $XX.XX (destacado)

#### Información de Pago
- Método de pago: Tarjeta de Crédito
- Estado del pago: Estado actual
- Fecha de procesamiento

#### Pie de Página
- Mensaje de agradecimiento
- Aviso sobre guardar comprobante
- Timestamp de generación (día/mes/año hora:minuto:segundo)

### Botones de Acción
- **"🖨️ Imprimir Factura"** → Abre diálogo de impresión
- **"💳 Continuar con el Pago"** → Redirige a `/payment` (si no está pagado)

### Estilos de Impresión
- `@media print` oculta botones y navbar
- Elimina sombra de tarjeta
- Agrega borde simple para impresión limpia

### Datos Variables
- `order`: Objeto Order de la BD
- `now`: datetime.now() para timestamp

---

## 🛠️ Panel Admin (`/admin`)

**Acceso**: Admin solamente  
**Método**: GET  
**Template**: `admin.html`

### Validación de Acceso
```python
@login_required
@admin_required
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)
```

### Descripción
Dashboard principal del administrador.

### Información Mostrada
- Total de usuarios
- Total de productos
- Total de pedidos
- Total de ingresos (si aplica)

### Opciones de Navegación
- 👗 **Gestión de Productos** → `/admin/products`
- 👥 **Gestión de Usuarios** → `/admin/users`
- 📦 **Gestión de Pedidos** → `/admin/orders`

---

## 👗 Gestión de Productos (`/admin/products`)

**Acceso**: Admin solamente  
**Método**: GET  
**Template**: `admin_products.html`

### Descripción
Tabla de todos los productos en el sistema.

### Información por Producto
| Columna | Descripción |
|---------|-------------|
| ID | Identificador |
| Imagen | Imagen del producto |
| Nombre | Nombre del producto |
| Marca | Marca de la prenda |
| Categoría | Categoría asignada |
| Precio | Precio de venta |
| Stock | Cantidad disponible |
| Acciones | Editar, Eliminar |

### Botones de Acción
- **"➕ Crear Producto"** → `/admin/products/create`
- **"✏️ Editar"** → `/admin/products/edit/<id>`
- **"🗑️ Eliminar"** → POST `/admin/products/delete/<id>`

### Ordenamiento
- Los productos se ordenan por ID descendente (más recientes primero)

---

### Crear Producto (`/admin/products/create`)

**Acceso**: Admin solamente  
**Método**: GET (formulario) / POST (crear)  
**Template**: `edit_product.html` (reutilizado con action="Crear")

### Campos del Formulario
| Campo | Tipo | Validación |
|-------|------|-----------|
| Nombre | String | Requerido, máx 200 |
| Marca | String | Requerido, máx 200 |
| Categoría | String | Opcional, máx 100 |
| Precio | Float | Requerido, ≥ 0 |
| Stock | Integer | Requerido, ≥ 0 |
| Descripción | Text | Opcional, máx 2000 |
| Imagen | File | Opcional, jpg/jpeg/png |

### Procesamiento
1. Valida todos los campos
2. Si hay imagen:
   - Valida que sea imagen (jpg/jpeg/png)
   - Genera nombre seguro: `secure_filename()`
   - Crea carpeta `static/uploads/` si no existe
   - Guarda archivo
3. Crea nuevo Product en BD
4. Guarda cambios

### Ruta de Archivos
- Destino: `static/uploads/{filename}`
- Acceso web: `static/uploads/{image_filename}`

### Mensaje de Éxito
- "✅ Producto creado correctamente."

### Redireccionamiento
- Éxito → `/admin/products` (lista de productos)

---

### Editar Producto (`/admin/products/edit/<product_id>`)

**Acceso**: Admin solamente  
**Método**: GET (formulario) / POST (guardar)  
**Template**: `edit_product.html` (con action="Editar")

### Lógica
1. Obtiene producto por ID (404 si no existe)
2. Si GET → Llena formulario con datos actuales
3. Si POST → Actualiza campos

### Campos Editables
- Nombre, Marca, Categoría, Precio, Stock, Descripción
- Imagen (puede cambiarla)

### Actualización de Imagen
- Si sube nueva imagen:
  - Valida formato
  - Guarda nuevo archivo
  - Actualiza `image_filename`
- Si no sube → Mantiene imagen anterior

### Campos No Editables
- ID
- Fecha de creación (si la hubiera)

### Mensaje de Éxito
- "✅ Producto actualizado."

### Redireccionamiento
- Éxito → `/admin/products` (lista de productos)

---

### Eliminar Producto (`/admin/products/delete/<product_id>`)

**Acceso**: Admin solamente  
**Método**: POST  

### Validación
```python
existing_orders = OrderItem.query.filter_by(product_id=product.id).first()
if existing_orders:
    flash("⚠️ No puedes eliminar este producto porque tiene pedidos registrados.", "warning")
    return redirect(url_for('admin_products'))
```

### Lógica
1. Obtiene producto por ID
2. Verifica si tiene pedidos asociados
3. Si tiene pedidos → No permite eliminar
4. Si no tiene → Elimina de BD

### Mensajes
- ❌ Con pedidos: "⚠️ No puedes eliminar este producto porque tiene pedidos registrados."
- ✅ Sin pedidos: "✅ Producto eliminado correctamente."

### Redireccionamiento
- Siempre → `/admin/products`

---

## 👥 Gestión de Usuarios (`/admin/users`)

**Acceso**: Admin solamente  
**Método**: GET  
**Template**: `admin_users.html`

### Descripción
Tabla de todos los usuarios del sistema.

### Información por Usuario
| Columna | Descripción |
|---------|-------------|
| ID | Identificador |
| Username | Nombre de usuario |
| Email | Correo electrónico |
| Rol | 'user' o 'admin' |
| Acciones | Editar, Eliminar |

### Botones de Acción
- **"➕ Agregar Usuario"** → `/admin/users/add`
- **"✏️ Editar"** → `/admin/users/edit/<id>`
- **"🗑️ Eliminar"** → POST `/admin/users/delete/<id>`

---

### Agregar Usuario (`/admin/users/add`)

**Acceso**: Admin solamente  
**Método**: GET (formulario) / POST (crear)  
**Template**: `add_user.html`

### Campos del Formulario
- **Username**: Nombre único
- **Email**: Email único
- **Contraseña**: Contraseña inicial
- **Rol**: 'user' o 'admin'

### Procesamiento
1. Valida que username y email sean únicos
2. Crea nuevo User
3. Encripta contraseña con `set_password()`
4. Asigna rol especificado
5. Guarda en BD

### Mensaje
- "✅ Usuario agregado correctamente."

### Redireccionamiento
- Éxito → `/admin/users`

---

### Editar Usuario (`/admin/users/edit/<user_id>`)

**Acceso**: Admin solamente  
**Método**: GET (formulario) / POST (guardar)  
**Template**: `edit_user.html`

### Campos Editables
- Username
- Email
- Rol (user/admin)

### Campos No Editables
- ID
- Contraseña (cambiar en otra ruta)

### Validación
- Username debe seguir siendo único (salvo el actual)
- Email debe seguir siendo único (salvo el actual)

### Mensaje
- "✅ Usuario actualizado correctamente."

### Redireccionamiento
- Éxito → `/admin/users`

---

### Eliminar Usuario (`/admin/users/delete/<user_id>`)

**Acceso**: Admin solamente  
**Método**: POST  

### Validación
```python
if current_user.id == user.id:
    flash("❌ No puedes eliminarte a ti mismo.", "danger")
    return redirect(url_for('admin_users'))
```

### Lógica
1. Obtiene usuario por ID
2. Verifica que no sea el admin actual
3. Si es el mismo → No permite eliminar
4. Si es otro → Elimina de BD

### Mensajes
- ❌ Es el mismo: "❌ No puedes eliminarte a ti mismo."
- ✅ Es otro: "🗑️ Usuario eliminado correctamente."

### Cascada de Eliminación
- Se eliminan sus carritos
- Se eliminan sus pedidos
- Se eliminan sus OrderItems (BD maneja cascada)

### Redireccionamiento
- Siempre → `/admin/users`

---

## 📦 Gestión de Pedidos (`/admin/orders`)

**Acceso**: Admin solamente  
**Método**: GET  
**Template**: `admin_orders.html`

### Descripción
Tabla de todos los pedidos de usuarios normales (no admins).

### Lógica de Filtrado
```python
non_admin_users = User.query.filter_by(role='user').all()
user_ids = [user.id for user in non_admin_users]
orders = Order.query.filter(Order.user_id.in_(user_ids)).order_by(Order.id.desc()).all()
```

### Información por Pedido
| Columna | Descripción |
|---------|-------------|
| ID Pedido | Número del pedido |
| Cliente | Nombre de usuario |
| Fecha | Fecha de creación |
| Estado | Estado actual (badge) |
| Total | Monto total |
| Acciones | Ver, Cambiar estado |

### Ordenamiento
- Descendente por ID (más recientes primero)

### Botones de Acción
- **"👁️ Ver"** → `/admin/orders/<order_id>`
- **"✏️ Cambiar Estado"** → Formulario inline

---

### Ver Detalle de Pedido (`/admin/orders/<order_id>`)

**Acceso**: Admin solamente  
**Método**: GET  
**Template**: `order_detail.html`

### Validación
```python
if order.user.is_admin:
    flash('No puedes ver pedidos de admins.', 'danger')
    return redirect(url_for('admin_orders'))
```

### Información Mostrada
- Datos del cliente
- Productos del pedido (tabla)
- Total y estado
- Botón para cambiar estado

---

### Actualizar Estado de Pedido (`/admin/orders/<order_id>/status`)

**Acceso**: Admin solamente  
**Método**: POST  
**Parámetro**: `status` (nuevo estado)

### Estados Válidos
- `'created'`: Recién creado
- `'paid'`: Pagado
- `'shipped'`: Enviado
- `'delivered'`: Entregado
- `'cancelled'`: Cancelado

### Validaciones
```python
valid_statuses = ['created', 'paid', 'shipped', 'delivered', 'cancelled']
if new_status not in valid_statuses:
    flash(f'Estado inválido.', 'danger')
```

### Proceso
1. Obtiene pedido por ID
2. Valida que sea de usuario no-admin
3. Valida que estado sea válido
4. Actualiza `order.status`
5. Guarda en BD

### Mensaje
- ✅ "✅ Estado del pedido actualizado a '{new_status}'."

### Redireccionamiento
- Éxito → `/admin/orders/<order_id>` (detalle)
- Error → Mismo formulario con mensaje

---

## 🧪 Prueba de Conexión (`/test-db`)

**Acceso**: Público  
**Método**: GET  

### Descripción
Prueba la conexión a la base de datos.

### Respuesta
- ✅ Éxito: "✅ Conexión exitosa a la base de datos"
- ❌ Error: "❌ Error al conectar a la base de datos"

### Uso
- Útil para debugging y troubleshooting
- No está disponible en producción (debería removerse)

---

## 📊 Resumen de Rutas

| Sección | Ruta | Método | Autenticado | Rol |
|---------|------|--------|-------------|-----|
| **Autenticación** |
| | `/register` | GET, POST | No | - |
| | `/login` | GET, POST | No | - |
| | `/logout` | GET | Sí | user, admin |
| | `/change-password` | GET, POST | Sí | user, admin |
| **Catálogo** |
| | `/catalogo` | GET | Sí | user, admin |
| | `/select-favs` | GET, POST | Sí | user |
| **Carrito** |
| | `/cart` | GET | Sí | user, admin |
| | `/cart/add/<id>` | GET, POST | Sí | user, admin |
| | `/cart/remove/<id>` | POST | Sí | user, admin |
| **Compra** |
| | `/checkout` | GET, POST | Sí | user, admin |
| | `/payment` | GET, POST | Sí | user, admin |
| **Pedidos** |
| | `/orders` | GET | Sí | user, admin |
| | `/orders/<id>` | GET | Sí | user, admin |
| | `/orders/<id>/cancel` | POST | Sí | user, admin |
| | `/invoice/<id>` | GET | Sí | user, admin |
| **Admin** |
| | `/admin` | GET | Sí | admin |
| | `/admin/products` | GET | Sí | admin |
| | `/admin/products/create` | GET, POST | Sí | admin |
| | `/admin/products/edit/<id>` | GET, POST | Sí | admin |
| | `/admin/products/delete/<id>` | POST | Sí | admin |
| | `/admin/users` | GET | Sí | admin |
| | `/admin/users/add` | GET, POST | Sí | admin |
| | `/admin/users/edit/<id>` | GET, POST | Sí | admin |
| | `/admin/users/delete/<id>` | POST | Sí | admin |
| | `/admin/orders` | GET | Sí | admin |
| | `/admin/orders/<id>` | GET | Sí | admin |
| | `/admin/orders/<id>/status` | POST | Sí | admin |

---

**Documento actualizado**: Noviembre 2025
