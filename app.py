from flask import Flask, render_template, request, redirect, url_for, session, abort
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
import os, re

app = Flask(__name__)
app.secret_key = "12345"

# Conexión a MongoDB (Docker: mongodb://localhost:27017)
client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
db = client['united_bank_of_MONEY']
coleccion = db['transacciones']

@app.route('/')
def index():
    return redirect(url_for('login'))

USUARIOS = {
    "admin": {
        "password": "admin123",
        "rol": "admin"
    },
    "operador": {
        "password": "oper123",
        "rol": "operador"
    }
}
def requiere_rol(rol):

    def decorador(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            if 'rol' not in session:
                return redirect('/login')

            if session['rol'] != rol:
                abort(403)

            return func(*args, **kwargs)

        return wrapper

    return decorador

@app.route('/login', methods=['GET', 'POST'])
def login():

    error = ""

    if request.method == 'POST':

        usuario = request.form['usuario']
        password = request.form['password']

        if usuario in USUARIOS and \
           USUARIOS[usuario]["password"] == password:

            session['usuario'] = usuario
            session['rol'] = USUARIOS[usuario]['rol']

            if session['rol'] == 'admin':
                return redirect('/admin')

            return redirect('/operador')

        error = "Usuario o contraseña incorrectos"

    return render_template('login.html', error=error)

def validar_texto(texto):

    patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]{2,50}$'

    return re.match(patron, texto)

# === ROL OPERADOR (formulario) ===
@app.route('/operador', methods=['GET', 'POST'])
@requiere_rol('operador')
def operador():

    mensaje = ""

    if request.method == 'POST':

        id_cliente = request.form['id'].strip()
        nombre = request.form['nombre'].strip()
        apellido = request.form['apellido'].strip()
        tipo = request.form['tipo'].strip()
        valor = request.form['valor'].strip()

        # Validar nombre
        if not validar_texto(nombre):
            mensaje = "Nombre inválido."
            return render_template('operador.html', mensaje=mensaje)

        # Validar apellido
        if not validar_texto(apellido):
            mensaje = "Apellido inválido."
            return render_template('operador.html', mensaje=mensaje)

        # Validar tipo
        tipos_validos = ['pago', 'crédito']

        if tipo not in tipos_validos:
            mensaje = "Tipo de transacción inválido."
            return render_template('operador.html', mensaje=mensaje)

        # Validar valor
        try:
            valor = float(valor)

            if valor <= 0:
                mensaje = "El valor debe ser mayor que cero."
                return render_template('operador.html', mensaje=mensaje)

        except ValueError:
            mensaje = "Valor inválido."
            return render_template('operador.html', mensaje=mensaje)

        # Si todo es válido se guarda
        datos = {
            "id": id_cliente,
            "nombre": nombre,
            "apellido": apellido,
            "tipo": tipo,
            "valor": valor,
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        coleccion.insert_one(datos)

        mensaje = "✅ Transacción guardada correctamente."

    return render_template('operador.html', mensaje=mensaje)

# === ROL ADMIN (consulta, modifica, elimina - todo inseguro) ===
@app.route('/admin', methods=['GET', 'POST'])
@requiere_rol('admin')
def admin():
  id_buscar = request.args.get('id', '').strip()
  if id_buscar and not id_buscar.isdigit():
    return "ID inválido"
  
  registros = []

  if id_buscar:
      registros = list(coleccion.find({"id": id_buscar}))
  else:
      registros = list(coleccion.find())  # Muestra todos si no hay filtro
  return render_template('admin.html', registros=registros, busqueda=id_buscar)

@app.route('/eliminar/<id_cliente>', methods=['POST'])
@requiere_rol('admin')
def eliminar(id_cliente):

  coleccion.delete_one({"id": id_cliente})
  return redirect(url_for('admin'))

@app.route('/editar/<id_cliente>', methods=['GET', 'POST'])
@requiere_rol('admin')
def editar(id_cliente):

    if request.method == 'POST':

        nombre = request.form['nombre'].strip()
        apellido = request.form['apellido'].strip()
        tipo = request.form['tipo'].strip()

        try:
            valor = float(request.form['valor'])

            if valor <= 0:
                return "Valor inválido"

        except ValueError:
            return "Valor inválido"

        if not validar_texto(nombre):
            return "Nombre inválido"

        if not validar_texto(apellido):
            return "Apellido inválido"

        if tipo not in ['pago', 'crédito']:
            return "Tipo inválido"

        nuevos_datos = {
            "nombre": nombre,
            "apellido": apellido,
            "tipo": tipo,
            "valor": valor
        }

        coleccion.update_one(
            {"id": id_cliente},
            {"$set": nuevos_datos}
        )

        return redirect(url_for('admin'))

    registro = coleccion.find_one({"id": id_cliente})

    return render_template('editar.html', registro=registro)


if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=5000)



