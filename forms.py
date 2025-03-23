# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, IntegerField, SubmitField, HiddenField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Regexp, EqualTo
from models import User

class PedidoForm(FlaskForm):
    tipo_formulario = HiddenField(default="pedido")  
    nombre = StringField('Nombre', [
        DataRequired(message="El nombre es obligatorio."),
        Length(max=50, message="El nombre no debe exceder 50 caracteres."),
        Regexp(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', message="El nombre solo debe contener letras y espacios.")
    ])
    direccion = StringField('Dirección', [
        DataRequired(message="La dirección es obligatoria."),
        Length(max=100, message="La dirección no debe exceder 100 caracteres."),
        Regexp(r'^[a-zA-Z0-9\s.,#-]+$', message="La dirección solo debe contener letras, números y caracteres básicos (.,#-).")
    ])
    telefono = StringField('Teléfono', [
        DataRequired(message="El teléfono es obligatorio."),
        Length(min=10, max=10, message="El teléfono debe tener exactamente 10 dígitos."),
        Regexp(r'^\d+$', message="El teléfono solo debe contener números.")
    ])
    tamano = RadioField('Tamaño Pizza', choices=[
        ('Chica', 'Chica $40'),
        ('Mediana', 'Mediana $80'),
        ('Grande', 'Grande $120')
    ], validators=[DataRequired(message="Debe seleccionar un tamaño de pizza.")])
    jamon = BooleanField('Jamón $10')
    pina = BooleanField('Piña $10')
    champinones = BooleanField('Champiñones $10')
    num_pizzas = IntegerField('Num. de Pizzas', [
        DataRequired(message="El número de pizzas es obligatorio."),
        NumberRange(min=1, max=10, message="El número de pizzas debe estar entre 1 y 10.")
    ])
    submit = SubmitField('Agregar')

class BusquedaForm(FlaskForm):
    tipo_formulario = HiddenField(default="busqueda") 
    periodo = RadioField('Período', choices=[('dia', 'Día'), ('mes', 'Mes')], validators=[DataRequired(message="Debe seleccionar un período.")])
    fecha = StringField('Fecha (YYYY-MM-DD o YYYY-MM)', [
        DataRequired(message="La fecha es obligatoria."),
        Regexp(r'^\d{4}-(?:\d{2}-)?\d{2}$', message="La fecha debe estar en formato YYYY-MM-DD o YYYY-MM.")
    ])
    submit = SubmitField('Buscar')

class LoginForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[
        DataRequired(message="El nombre de usuario es obligatorio"),
        Length(min=4, max=80, message="El nombre de usuario debe tener entre 4 y 80 caracteres")
    ])
    password = PasswordField('contraseña', validators=[
        DataRequired(message="La contraseña es obligatoria"),
        Length(min=8, message="La contraseña debe tener al menos 8 caracteres.")
    ])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[
        DataRequired(message="El nombre de usuario es obligatorio"),
        Length(min=4, max=80, message="El nombre de usuario debe tener entre 4 y 80 caracteres")
    ])
    password = PasswordField('contraseña', validators=[
        DataRequired(message="La contraseña es obligatoria"),
        Length(min=8, message="La contraseña debe tener al menos 8 caracteres..")
    ])
    confirm_password = PasswordField('Confirma la contraseña', validators=[
        DataRequired(message="Por favor confirma tu contraseña"),
        EqualTo('password', message="Las contraseñas deben coincidir")
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ese nombre de usuario ya está en uso. Elige uno diferente.')