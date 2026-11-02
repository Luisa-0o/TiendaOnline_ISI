"""Política de entrega: municipios permitidos y validación de datos de envío.

Única fuente de verdad de la regla «solo se entrega en Medellín, Bello y Envigado».
La usan el formulario (errores junto a cada campo) y OrderService, que vuelve a
validar: ninguna petición manual puede crear un pedido con un municipio no permitido.
"""
import re
from dataclasses import dataclass
from typing import Dict, Sequence

_PHONE_RE = re.compile(r"^3\d{9}$")   # celular colombiano: 10 dígitos que empiezan por 3
_POSTAL_RE = re.compile(r"^\d{6}$")


@dataclass(frozen=True)
class ShippingData:
    recipient_name: str = ""
    phone: str = ""
    municipality: str = ""
    address: str = ""
    neighborhood: str = ""
    postal_code: str = ""
    address_notes: str = ""

    def normalized(self) -> "ShippingData":
        digits = re.sub(r"\D", "", self.phone or "")
        if len(digits) == 12 and digits.startswith("57"):
            digits = digits[2:]
        return ShippingData(
            recipient_name=" ".join((self.recipient_name or "").split()),
            phone=digits,
            municipality=(self.municipality or "").strip(),
            address=" ".join((self.address or "").split()),
            neighborhood=" ".join((self.neighborhood or "").split()),
            postal_code=(self.postal_code or "").strip(),
            address_notes=(self.address_notes or "").strip(),
        )


class DeliveryPolicy:
    def __init__(self, municipalities: Sequence[str]):
        self._municipalities = tuple(municipalities)

    @property
    def municipalities(self) -> Sequence[str]:
        return self._municipalities

    def is_allowed(self, municipality: str) -> bool:
        return municipality in self._municipalities  # coincidencia exacta: viene de la lista

    def validate(self, data: ShippingData) -> Dict[str, str]:
        """Devuelve {campo: mensaje}; vacío significa válido."""
        d = data.normalized()
        errors: Dict[str, str] = {}
        if not (3 <= len(d.recipient_name) <= 120):
            errors["recipient_name"] = "Escribe el nombre completo de quien recibe (mínimo 3 letras)."
        if not _PHONE_RE.match(d.phone):
            errors["phone"] = "Escribe un celular colombiano de 10 dígitos que empiece por 3, por ejemplo 3001234567."
        if not d.municipality:
            errors["municipality"] = "Selecciona el municipio de entrega."
        elif not self.is_allowed(d.municipality):
            errors["municipality"] = ("Solo entregamos en " + self._join(self._municipalities)
                                      + ". Elige uno de esos municipios.")
        if not (5 <= len(d.address) <= 200):
            errors["address"] = "Escribe la dirección completa (calle, número y detalles), mínimo 5 caracteres."
        if not (2 <= len(d.neighborhood) <= 100):
            errors["neighborhood"] = "Escribe el barrio o sector."
        if d.postal_code and not _POSTAL_RE.match(d.postal_code):
            errors["postal_code"] = "El código postal debe tener 6 dígitos. Si no lo conoces, déjalo vacío."
        if len(d.address_notes) > 300:
            errors["address_notes"] = "La información adicional no puede superar los 300 caracteres."
        return errors

    @staticmethod
    def _join(items: Sequence[str]) -> str:
        items = list(items)
        return items[0] if len(items) <= 1 else ", ".join(items[:-1]) + " y " + items[-1]
