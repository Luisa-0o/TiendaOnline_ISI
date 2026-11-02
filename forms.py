"""Formularios (Flask-WTF). Las reglas de entrega viven en services.delivery."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from sqlalchemy import func, select
from wtforms import (FloatField, IntegerField, PasswordField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from extensions import db
from models import ROLES, User
from services.delivery import ShippingData
from services.factory import get_account_service, get_delivery_policy
from services.products import parse_sizes


class RegisterForm(FlaskForm):
    username = StringField("Nombre de usuario", validators=[DataRequired(), Length(3, 80)])
    email = StringField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(6, 128)])
    password2 = PasswordField("Confirmar contraseña", validators=[DataRequired(), EqualTo("password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Crear cuenta")

    def validate_username(self, field):
        taken = db.session.scalar(select(func.count()).select_from(User)
                                  .where(func.lower(User.username) == field.data.strip().lower()))
        if taken:
            raise ValidationError("El nombre de usuario ya existe.")

    def validate_email(self, field):
        if get_account_service().find_by_email(field.data):
            raise ValidationError("Ese correo ya está registrado.")


class LoginForm(FlaskForm):
    email = StringField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Iniciar sesión")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Contraseña actual", validators=[DataRequired()])
    new_password = PasswordField("Nueva contraseña", validators=[DataRequired(), Length(6, 128)])
    new_password2 = PasswordField("Confirmar nueva contraseña", validators=[DataRequired(), EqualTo("new_password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Cambiar contraseña")


class ShippingForm(FlaskForm):
    recipient_name = StringField("Nombre de quien recibe", render_kw={"autocomplete": "name"})
    phone = StringField("Número de celular", render_kw={"autocomplete": "tel", "inputmode": "tel"})
    municipality = SelectField("Municipio", choices=[], validate_choice=False)
    address = StringField("Dirección completa", render_kw={"autocomplete": "street-address"})
    neighborhood = StringField("Barrio o sector")
    postal_code = StringField("Código postal (opcional)", render_kw={"inputmode": "numeric", "autocomplete": "postal-code"})
    address_notes = TextAreaField("Información adicional de la dirección (opcional)", render_kw={"rows": 2})
    submit = SubmitField("Continuar al pago")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = get_delivery_policy()
        self.municipality.choices = [("", "Selecciona un municipio")] + [(m, m) for m in self.policy.municipalities]

    def to_shipping_data(self) -> ShippingData:
        return ShippingData(
            recipient_name=self.recipient_name.data or "", phone=self.phone.data or "",
            municipality=self.municipality.data or "", address=self.address.data or "",
            neighborhood=self.neighborhood.data or "", postal_code=self.postal_code.data or "",
            address_notes=self.address_notes.data or "")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        for name, message in self.policy.validate(self.to_shipping_data()).items():
            getattr(self, name).errors = list(getattr(self, name).errors) + [message]
            ok = False
        return ok

    def fill_from(self, data: ShippingData) -> None:
        self.recipient_name.data, self.phone.data = data.recipient_name, data.phone
        self.municipality.data, self.address.data = data.municipality, data.address
        self.neighborhood.data, self.postal_code.data = data.neighborhood, data.postal_code
        self.address_notes.data = data.address_notes


class PaymentForm(FlaskForm):
    payment_method = SelectField("Método de pago", choices=[], validate_choice=False)
    card_number = StringField("Número de tarjeta", render_kw={"autocomplete": "off", "inputmode": "numeric"})
    expiry_date = StringField("Vence (MM/AA)", render_kw={"autocomplete": "off", "placeholder": "MM/AA"})
    cvv = PasswordField("CVV", render_kw={"autocomplete": "off", "inputmode": "numeric"})
    submit = SubmitField("Pagar ahora")

    def __init__(self, gateways, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment_method.choices = [("", "Selecciona un método")] + [(g.code, g.label) for g in gateways.all()]

    def validate_payment_method(self, field):
        if not field.data:
            raise ValidationError("Selecciona un método de pago.")

    def details(self) -> dict:
        return {"card_number": self.card_number.data or "", "expiry_date": self.expiry_date.data or "",
                "cvv": self.cvv.data or ""}


class FavoritesForm(FlaskForm):
    submit = SubmitField("Guardar preferencias")


class ProductForm(FlaskForm):
    name = StringField("Nombre de la prenda", validators=[DataRequired(), Length(max=120)])
    brand = StringField("Marca", validators=[DataRequired(), Length(max=120)])
    category = StringField("Categoría (Camisas, Pantalones, Zapatos...)", validators=[Optional(), Length(max=50)])
    garment_type = StringField("Tipo de prenda (Camiseta, Jean, Blusa...)", validators=[Optional(), Length(max=80)])
    price = FloatField("Precio (COP)", validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField("Existencias", validators=[Optional(), NumberRange(min=0)])
    sizes = StringField("Tallas y existencias (opcional)", validators=[Optional(), Length(max=300)],
                        description="Formato TALLA:CANTIDAD separado por comas, por ejemplo S:10, M:15, L:8. "
                                    "Si completas las tallas, las existencias totales se calculan solas.")
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=2000)])
    image = FileField("Foto de la prenda (JPG, PNG o WEBP)", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes JPG, PNG o WEBP.")])
    submit = SubmitField("Guardar")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        # Reglas que cruzan campos (Optional() corta los validate_<campo> con valores vacíos).
        self.parsed_sizes = []
        if (self.sizes.data or "").strip():
            try:
                self.parsed_sizes = parse_sizes(self.sizes.data)
            except ValueError as exc:
                self.sizes.errors = list(self.sizes.errors) + [str(exc)]
                ok = False
        if not self.parsed_sizes and self.stock.data is None:
            self.stock.errors = list(self.stock.errors) + ["Indica las existencias, o define las tallas con su cantidad."]
            ok = False
        return ok


class AdminUserForm(FlaskForm):
    username = StringField("Nombre de usuario", validators=[DataRequired(), Length(3, 80)])
    email = StringField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[Optional(), Length(6, 128)])
    role = SelectField("Rol", choices=[(r, "Administrador" if r == "admin" else "Cliente") for r in ROLES],
                       validators=[DataRequired()])
    submit = SubmitField("Guardar")

    def __init__(self, *args, require_password=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_password = require_password

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if self.require_password and not self.password.data:
            self.password.errors = list(self.password.errors) + ["La contraseña es obligatoria."]
            ok = False
        return ok


class OrderStatusForm(FlaskForm):
    status = SelectField("Estado", validators=[DataRequired()], validate_choice=False)
    submit = SubmitField("Actualizar estado")


class EmptyForm(FlaskForm):
    """Sin campos: solo aporta el token CSRF a acciones POST (eliminar, cancelar...)."""
