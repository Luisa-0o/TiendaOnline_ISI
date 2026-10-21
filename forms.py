from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User
from flask_wtf.file import FileField, FileAllowed
from wtforms import IntegerField, FloatField, TextAreaField
from wtforms.validators import NumberRange, Optional
from wtforms import StringField

class RegisterForm(FlaskForm):
    username = StringField('Nombre', validators=[DataRequired(), Length(3,80)])
    email = StringField('Correo', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(6,128)])
    password2 = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('El nombre de usuario ya existe.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('El email ya está en uso.')

class LoginForm(FlaskForm):
    email = StringField('Correo', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Ingresar')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva contraseña', validators=[DataRequired(), Length(6,128)])
    new_password2 = PasswordField('Confirmar nueva contraseña', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Cambiar contraseña')

class ProductForm(FlaskForm):
    name = StringField('Nombre de la prenda', validators=[DataRequired(), Length(max=200)])
    brand = StringField('Marca', validators=[DataRequired(), Length(max=200)])
    category = StringField('Categoría (Camisas, Pantalones, Zapatos, Accesorios...)', validators=[Optional(), Length(max=100)])
    price = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Descripción', validators=[Optional(), Length(max=2000)])
    image = FileField('Foto de la prenda (opcional)', validators=[Optional(), FileAllowed(['jpg','jpeg','png'], 'Solo imágenes')])
    submit = SubmitField('Guardar')
