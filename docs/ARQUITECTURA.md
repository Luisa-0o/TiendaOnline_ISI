# Arquitectura y principios SOLID

## Capas
- `blueprints/` – HTTP: lee la petición, llama a un servicio, renderiza. Sin reglas de negocio.
- `services/` – reglas de negocio, **sin imports de Flask** (se prueban sin servidor).
- `models.py` – persistencia (SQLAlchemy). `forms.py` – validación de entrada (WTForms).
- `services/factory.py` – raíz de composición: único lugar donde se instancian y conectan los servicios.

## SOLID con ejemplos concretos
| Principio | Evidencia |
|---|---|
| **S** (responsabilidad única) | `DeliveryPolicy` solo decide qué municipios se atienden; `ImageService` solo guarda imágenes; `OrderService` solo crea/cancela pedidos; `CatalogService` solo consulta el catálogo; `RecommendationService` solo recomienda; `ReportService` solo estadísticas del panel. |
| **O** (abierto/cerrado) | Nuevo medio de pago = nueva subclase de `PaymentGateway` registrada en `PaymentGatewayRegistry`, sin tocar `OrderService`. Nuevo filtro de catálogo = nueva clase con `apply(stmt)` añadida en `build_filters`. Nuevos municipios = `DELIVERY_MUNICIPALITIES` en la configuración. |
| **L** (sustitución de Liskov) | `CookieCartStore` (invitado) y `DatabaseCartStore` (usuario) implementan `CartStore` y son intercambiables en `CartService`; `tests/test_solid.py` ejecuta el mismo escenario con ambos. |
| **I** (segregación de interfaces) | `OrderService` depende solo del Protocol `CheckoutCart` (líneas y total), no de todo el carrito. Los filtros exponen únicamente `apply`. |
| **D** (inversión de dependencias) | Los servicios reciben sesión, almacenes y pasarelas por constructor; `factory.py` los compone. Las pruebas inyectan sustitutos sin parchear módulos. |

## Seguridad en capas
El municipio se valida en el formulario (lista cerrada en el desplegable), de nuevo en `ShippingForm` en el servidor y por última vez en `OrderService.place_order`. Precios y existencias se releen de la base de datos al crear el pedido; el stock se descuenta con `UPDATE ... WHERE stock >= cantidad` dentro de una sola transacción.
