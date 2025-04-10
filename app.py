from flask import Flask, render_template, request, redirect, url_for, session
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto por una clave secreta segura
mongo_uri = os.environ.get("MONGO_URI")

if not mongo_uri:
    # Usar la URI directamente (menos seguro, solo para desarrollo local)
    uri = "mongodb+srv://DbCentral:DbCentral2025@cluster0.vhltza7.mongodb.net/?appName=Cluster0"
    mongo_uri = uri

# Función para conectar a MongoDB
def connect_mongo():
    try:
        client = MongoClient(mongo_uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("Conexión exitosa a MongoDB!")
        return client
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        # Aquí puedes agregar la lógica para procesar el formulario de contacto
        return redirect(url_for('contacto'))
    return render_template('contacto.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        client = connect_mongo()
        db = client['administracion']
        security_collection = db['seguridad']
        usuario = request.form['usuario']
        password = request.form['password']
        
        # Verificar credenciales en MongoDB
        user = security_collection.find_one({
            'usuario': usuario,
            'password': password
        })
        
        if user:
            session['usuario'] = usuario
            return redirect(url_for('gestion_mongodb'))
        else:
            return render_template('login.html', error_message='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/gestion-mongodb')
def gestion_mongodb():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        client = connect_mongo()
        # Obtener lista de bases de datos
        databases = client.list_database_names()
        # Eliminar bases de datos del sistema
        system_dbs = ['admin', 'local', 'config']
        databases = [db for db in databases if db not in system_dbs]
        
        selected_db = request.args.get('database')
        collections_data = []
        
        if selected_db:
            db = client[selected_db]
            collections = db.list_collection_names()
            for index, collection_name in enumerate(collections, 1):
                collection = db[collection_name]
                count = collection.count_documents({})
                collections_data.append({
                    'index': index,
                    'name': collection_name,
                    'count': count
                })
        
        return render_template('gestionMongoDb.html',
                             databases=databases,
                             selected_db=selected_db,
                             collections_data=collections_data)
    except Exception as e:
        return render_template('gestionMongoDb.html',
                             error_message=f'Error al conectar con MongoDB: {str(e)}')

if __name__ == '__main__':
    app.run(debug=True)