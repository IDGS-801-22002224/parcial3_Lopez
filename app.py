# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from models import db, Venta, User
from datetime import datetime
import logging
import json
from config import DevelopmentConfig
from forms import PedidoForm, BusquedaForm, LoginForm, RegisterForm
from wtforms.validators import ValidationError

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
csrf = CSRFProtect()
db.init_app(app)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.' 
login_manager.login_message_category = 'info'  

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Crear tablas y usuario de prueba
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='testuser').first():
        user = User(username='testuser')
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PEDIDOS_FILE = "pedidos.txt"

PRECIOS_TAMANOS = {
    'Chica': 40.0,
    'Mediana': 80.0,
    'Grande': 120.0
}

def leer_pedidos():
    try:
        with open(PEDIDOS_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def escribir_pedidos(pedidos):
    with open(PEDIDOS_FILE, 'w') as file:
        json.dump(pedidos, file)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Inicio de sesión exitoso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña no válidos', 'error')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('¡Registro exitoso! Por favor, inicia sesión..', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Se ha cerrado la sesión.', 'success')
    return redirect(url_for('login'))

@app.route("/", methods=['GET', 'POST'])
@login_required
def index():
    form = PedidoForm()
    busqueda_form = BusquedaForm()

    # Inicializar pedidos_mostrados desde la sesión o el archivo
    pedidos_file = leer_pedidos()
    if 'pedidos_mostrados' not in session:
        session['pedidos_mostrados'] = pedidos_file
    pedidos_mostrados = session['pedidos_mostrados']

    # Limpiar session['cliente'] si no hay pedidos (es decir, al iniciar o despues de terminar)
    if not pedidos_mostrados:
        session['cliente'] = {}

    # Rellenar el formulario con los datos del cliente solo si hay pedidos y session['cliente'] tiene datos
    if pedidos_mostrados and 'cliente' in session and session['cliente']:
        form.nombre.data = session['cliente'].get('nombre')
        form.direccion.data = session['cliente'].get('direccion')
        form.telefono.data = session['cliente'].get('telefono')

    print(f"Pedidos mostrados antes de procesar: {pedidos_mostrados}")  # Depuracion

    if request.method == 'POST':
        print("Formulario recibido")  # Mensaje de depuracion
        print(f"Datos recibidos: {request.form}")  # Depuracion de los datos enviados
        if 'tipo_formulario' in request.form:
            print(f"Tipo de formulario recibido: {request.form['tipo_formulario']}")  # Depuracion
            if request.form['tipo_formulario'] == 'pedido':
                print("Procesando formulario de pedido")
                if form.validate_on_submit():
                    print("Formulario de pedido válido")  # Mensaje de depuracion
                    tamano = form.tamano.data
                    precio_tamano = PRECIOS_TAMANOS.get(tamano)
                    if precio_tamano is None:
                        flash('Tamaño de pizza inválido.', 'error')
                        return redirect(url_for('index'))

                    # Verificar que todos los pedidos en pedidos_mostrados tengan el mismo nombre
                    if pedidos_mostrados:
                        primer_nombre = pedidos_mostrados[0]['nombre']
                        if primer_nombre != form.nombre.data:
                            flash('No se puede agregar un pedido con un nombre diferente. Por favor, termine o elimine los pedidos actuales antes de agregar uno nuevo.', 'error')
                            return redirect(url_for('index'))

                    ingredientes_seleccionados = []
                    precio_ingredientes = 0
                    if form.jamon.data:
                        ingredientes_seleccionados.append('Jamón')
                        precio_ingredientes += 10
                    if form.pina.data:
                        ingredientes_seleccionados.append('Piña')
                        precio_ingredientes += 10
                    if form.champinones.data:
                        ingredientes_seleccionados.append('Champiñones')
                        precio_ingredientes += 10
                    ingredientes = ', '.join(ingredientes_seleccionados) if ingredientes_seleccionados else 'Ninguno'
                    num_pizzas = form.num_pizzas.data
                    subtotal = (precio_tamano + precio_ingredientes) * num_pizzas

                    # Crear el nuevo pedido
                    pedido = {
                        'id': len(pedidos_file) + 1,
                        'nombre': form.nombre.data,
                        'direccion': form.direccion.data,
                        'telefono': form.telefono.data,
                        'tamano': tamano,
                        'ingredientes': ingredientes,
                        'num_pizzas': num_pizzas,
                        'subtotal': subtotal
                    }
                    print(f"Nuevo pedido: {pedido}")  # Depuracion

                    # Agregar el pedido a ambas listas
                    pedidos_file.append(pedido)
                    pedidos_mostrados.append(pedido)

                    # Sincronizar ambas listas
                    session['pedidos_mostrados'] = pedidos_mostrados
                    escribir_pedidos(pedidos_file)

                    # Guardar los datos del cliente en la sesión para mantenerlos en el formulario
                    session['cliente'] = {
                        'nombre': form.nombre.data,
                        'direccion': form.direccion.data,
                        'telefono': form.telefono.data
                    }

                    print(f"Pedidos mostrados después de agregar: {pedidos_mostrados}")  # Depuracion

                    flash('Pizza agregada exitosamente', 'success')
                    return redirect(url_for('index'))
                else:
                    print(f"Errores de validación: {form.errors}")  # Depuracion de errores
                    for field, errors in form.errors.items():
                        for error in errors:
                            flash(f'Error en {getattr(form, field).label.text}: {error}', 'error')
            elif request.form['tipo_formulario'] == 'busqueda':
                print("Procesando formulario de búsqueda")
                if busqueda_form.validate_on_submit():
                    fecha_input = busqueda_form.fecha.data
                    print(f"Buscando ventas - Fecha: {fecha_input}")  # Depuracion

                    try:
                        # Validar el formato de la fecha ingresada (debe ser YYYY-MM-DD o YYYY-MM)
                        if not (len(fecha_input) == 7 and fecha_input[4] == '-' or len(fecha_input) == 10 and fecha_input[4] == '-' and fecha_input[7] == '-'):
                            flash('Ingrese la fecha en formato YYYY-MM-DD o YYYY-MM.', 'error')
                            return redirect(url_for('index'))

                        # Obtener todas las ventas de la base de datos
                        ventas = Venta.query.all()
                        print(f"Ventas totales en BD: {len(ventas)}")  # Depuracion
                        ventas_filtradas = {}

                        for venta in ventas:
                            fecha_venta = venta.fecha_compra
                            print(f"Venta: {venta.nombre}, Fecha: {fecha_venta}, Total: {venta.total}")  # Depuracion

                            # Comparar por mes (YYYY-MM) o por día (YYYY-MM-DD)
                            if len(fecha_input) == 7:  # Formato YYYY-MM
                                fecha_venta_str = fecha_venta.strftime('%Y-%m')
                            else:  # Formato YYYY-MM-DD
                                fecha_venta_str = fecha_venta.strftime('%Y-%m-%d')

                            if fecha_venta_str == fecha_input:
                                ventas_filtradas[venta.nombre] = ventas_filtradas.get(venta.nombre, 0) + venta.total

                        print(f"Ventas filtradas: {ventas_filtradas}")  # Depuracion
                        if not ventas_filtradas:
                            flash(f'No se encontraron ventas para {fecha_input}.', 'info')

                        return render_template(
                            "index.html",
                            form=form,
                            busqueda_form=busqueda_form,
                            pedidos_mostrados=pedidos_mostrados,
                            ventas_por_cliente=ventas_filtradas,
                            ventas_totales=sum(ventas_filtradas.values()),
                            mostrar_ventas=True
                        )
                    except Exception as e:
                        print(f"Error al buscar ventas: {e}")  # Depuracion
                        flash(f'Error al buscar ventas: {e}', 'error')
                        return redirect(url_for('index'))
                else:
                    print(f"Errores de validación en busqueda_form: {busqueda_form.errors}")
                    for field, errors in busqueda_form.errors.items():
                        for error in errors:
                            flash(f'Error en {getattr(busqueda_form, field).label.text}: {error}', 'error')

    ventas_totales = sum(pedido['subtotal'] for pedido in pedidos_mostrados) if pedidos_mostrados else 0
    return render_template("index.html", form=form, busqueda_form=busqueda_form, pedidos_mostrados=pedidos_mostrados, ventas_por_cliente={}, ventas_totales=ventas_totales, mostrar_ventas=False)

@app.route('/quitar/<int:pedido_id>', methods=['GET'])
@login_required
def quitar(pedido_id):
    pedidos_mostrados = session.get('pedidos_mostrados', [])
    pedidos_file = leer_pedidos()

    # Buscar y eliminar el pedido de pedidos_mostrados y pedidos_file
    pedido_a_eliminar = next((p for p in pedidos_mostrados if p['id'] == pedido_id), None)
    if pedido_a_eliminar:
        pedidos_mostrados = [p for p in pedidos_mostrados if p['id'] != pedido_id]
        pedidos_file = [p for p in pedidos_file if p['id'] != pedido_id]
        session['pedidos_mostrados'] = pedidos_mostrados
        escribir_pedidos(pedidos_file)
        flash(f'Pedido {pedido_id} eliminado de la tabla.', 'success')
    else:
        flash(f'Pedido {pedido_id} no encontrado en la tabla.', 'error')
    return redirect(url_for('index'))

@app.route('/terminar', methods=['GET', 'POST'])
@login_required
def terminar():
    form = PedidoForm()
    pedidos_file = leer_pedidos()
    pedidos_mostrados = session.get('pedidos_mostrados', [])

    if request.method == 'POST':
        print("Intentando terminar pedido")  # Depuracion
        print(f"Conexión a DB: {db.engine.url}")  # Depuración de la URI de la base de datos
        if pedidos_mostrados:
            total = sum(pedido['subtotal'] for pedido in pedidos_mostrados)
            print(f"Total calculado: ${total}")  # Depuracion
            if total > 0:
                try:
                    # Verificar que todos los pedidos en pedidos_mostrados tengan el mismo nombre
                    nombres = {pedido['nombre'] for pedido in pedidos_mostrados}
                    if len(nombres) > 1:
                        flash('Los pedidos contienen nombres diferentes. Por favor, asegúrese de que todos los pedidos sean del mismo cliente antes de terminar.', 'error')
                        return redirect(url_for('index'))

                    # Obtener el nombre del cliente desde los pedidos
                    nombre_cliente = pedidos_mostrados[0]['nombre']
                    print(f"Nombre del cliente para la venta: {nombre_cliente}")  # Depuracion

                    # Guardar la venta en la base de datos
                    venta = Venta(
                        nombre=nombre_cliente,
                        total=total
                    )
                    db.session.add(venta)
                    db.session.commit()
                    print(f"Venta insertada en BD: {venta}")  # Depuracion

                    # Mostrar nombre y total en el recuadro gris
                    ventas_por_cliente = {nombre_cliente: total}
                    ventas_totales = total
                    print(f"Datos para recuadro gris: {ventas_por_cliente}")  # Depuracion

                    # Limpiar la tabla visible y el archivo pedidos.txt
                    session['pedidos_mostrados'] = []
                    escribir_pedidos([])  # Vaciar el archivo pedidos.txt
                    print("Archivo pedidos.txt vaciado")  # Depuracion

                    # Limpiar los datos del cliente en la sesión para que el formulario aparezca vacío
                    session['cliente'] = {}

                    flash(f'Pedido terminado. Total a pagar: ${total}', 'success')
                    
                    return render_template("index.html", form=form, busqueda_form=BusquedaForm(), pedidos_mostrados=session['pedidos_mostrados'], ventas_por_cliente=ventas_por_cliente, ventas_totales=ventas_totales, mostrar_ventas=False)
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al insertar en BD: {e}")  # Depuracion
                    flash(f'Error al terminar el pedido: {e}', 'error')
            else:
                flash('El total del pedido es 0. No se puede terminar.', 'error')
        else:
            flash('No hay pedidos para terminar.', 'error')
        return redirect(url_for('index'))

    elif request.method == 'GET' and pedidos_mostrados:
        if 'cliente' in session and session['cliente']:
            form.nombre.data = session['cliente'].get('nombre')
            form.direccion.data = session['cliente'].get('direccion')
            form.telefono.data = session['cliente'].get('telefono')
        return render_template('index.html', form=form, busqueda_form=BusquedaForm(), pedidos_mostrados=pedidos_mostrados, ventas_por_cliente={}, ventas_totales=sum(pedido['subtotal'] for pedido in pedidos_mostrados), mostrar_ventas=False)

    flash('No hay pedidos para terminar.', 'error')
    return redirect(url_for('index'))

if __name__ == "__main__":
    csrf.init_app(app)
    with app.app_context():
        print(f"Creando tablas en: {db.engine.url}")
        db.create_all()
    app.run(debug=True)