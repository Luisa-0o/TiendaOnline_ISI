"""Pagos simulados.

Névora Moda! NO procesa pagos reales ni guarda datos bancarios. Cada método es una
pasarela que cumple ``PaymentGateway``. Para integrar una pasarela real (o un método
nuevo) se escribe otra clase y se registra en ``build_default_registry``: OrderService
y las rutas no cambian (Open/Closed, Dependency Inversion).
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Mapping


class PaymentError(Exception):
    """El pago no pudo procesarse; mensaje apto para el cliente."""


@dataclass(frozen=True)
class PaymentRequest:
    order_id: int
    amount: float
    details: Mapping[str, str] = field(default_factory=dict, repr=False)  # solo para validar; no se persiste


@dataclass(frozen=True)
class PaymentResult:
    approved: bool
    message: str = ""


class PaymentGateway(ABC):
    code: str = ""
    label: str = ""
    requires_card: bool = False

    @abstractmethod
    def charge(self, request: PaymentRequest) -> PaymentResult:
        """Procesa el pago. Lanza PaymentError si los datos no son válidos."""


class SimulatedCardGateway(PaymentGateway):
    """Valida el formato de los datos de tarjeta y aprueba (simulación)."""
    requires_card = True

    def __init__(self, code: str, label: str, today=date.today):
        self.code, self.label, self._today = code, label, today

    def charge(self, request: PaymentRequest) -> PaymentResult:
        number = re.sub(r"[\s-]", "", request.details.get("card_number", ""))
        expiry = request.details.get("expiry_date", "").strip()
        cvv = request.details.get("cvv", "").strip()
        if not re.fullmatch(r"\d{13,19}", number):
            raise PaymentError("El número de tarjeta debe tener entre 13 y 19 dígitos.")
        if not self._expiry_is_valid(expiry):
            raise PaymentError("La fecha de expiración debe tener el formato MM/AA y no estar vencida.")
        if not re.fullmatch(r"\d{3,4}", cvv):
            raise PaymentError("El CVV debe tener 3 o 4 dígitos.")
        return PaymentResult(True, "Pago simulado aprobado.")

    def _expiry_is_valid(self, expiry: str) -> bool:
        match = re.fullmatch(r"(\d{2})\s*/\s*(\d{2})", expiry)
        if not match:
            return False
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        today = self._today()
        return 1 <= month <= 12 and (year, month) >= (today.year, today.month)


class SimulatedCashGateway(PaymentGateway):
    """Pago en punto físico (Efecty), simulado."""

    def __init__(self, code: str, label: str):
        self.code, self.label = code, label

    def charge(self, request: PaymentRequest) -> PaymentResult:
        return PaymentResult(True, "Pago en punto físico simulado aprobado.")


class PaymentGatewayRegistry:
    def __init__(self):
        self._gateways: Dict[str, PaymentGateway] = {}

    def register(self, gateway: PaymentGateway) -> None:
        self._gateways[gateway.code] = gateway

    def get(self, code: str) -> PaymentGateway:
        try:
            return self._gateways[code]
        except KeyError:
            raise PaymentError("Selecciona un método de pago válido.") from None

    def all(self) -> List[PaymentGateway]:
        return list(self._gateways.values())


def build_default_registry() -> PaymentGatewayRegistry:
    registry = PaymentGatewayRegistry()
    registry.register(SimulatedCardGateway("visa", "Visa"))
    registry.register(SimulatedCardGateway("mastercard", "MasterCard"))
    registry.register(SimulatedCashGateway("efecty", "Efecty (pago en punto físico)"))
    return registry
