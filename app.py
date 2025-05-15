from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import zipfile
import os
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto por una clave secreta segura

# Versión de la aplicación
VERSION_APP = "Versión 1.3 del Mayo 15 del 2025"
#
CREATOR_APP = "Nombre del creador/ruta github"

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
    return render_template('index.html', version=VERSION_APP,creador=CREATOR_APP)
@app.route('/about')
def about():
    return render_template('about.html', version=VERSION_APP,creador=CREATOR_APP)

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        # Aquí puedes agregar la lógica para procesar el formulario de contacto
        return redirect(url_for('contacto'))
    return render_template('contacto.html', version=VERSION_APP,creador=CREATOR_APP)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Primero verificar la conectividad con MongoDB
        client = connect_mongo()
        if not client:
            return render_template('login.html', error_message='Error de conexión con la base de datos. Por favor, intente más tarde.', version=VERSION_APP,creador=CREATOR_APP)
        
        try:
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
                return redirect(url_for('gestion_proyecto'))
            else:
                return render_template('login.html', error_message='Usuario o contraseña incorrectos', version=VERSION_APP,creador=CREATOR_APP)
        except Exception as e:
            return render_template('login.html', error_message=f'Error al validar credenciales: {str(e)}', version=VERSION_APP,creador=CREATOR_APP)
        finally:
            client.close()
    
    return render_template('login.html', version=VERSION_APP,creador=CREATOR_APP)

@app.route('/gestion_proyecto', methods=['GET', 'POST'])
def gestion_proyecto():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        client = connect_mongo()
        # Obtener lista de bases de datos
        databases = client.list_database_names()
        # Eliminar bases de datos del sistema
        system_dbs = ['admin', 'local', 'config']
        databases = [db for db in databases if db not in system_dbs]
        
        selected_db = request.form.get('database') if request.method == 'POST' else request.args.get('database')
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
        
        return render_template('gestion/index.html',
                            databases=databases,
                            selected_db=selected_db,
                            collections_data=collections_data,
                            version=VERSION_APP,
                            creador=CREATOR_APP,
                            usuario=session['usuario'])
    except Exception as e:
        return render_template('gestion/index.html',
                            error_message=f'Error al conectar con MongoDB: {str(e)}',
                            version=VERSION_APP,
                            creador=CREATOR_APP,
                            usuario=session['usuario'])

@app.route('/logout')
def logout():
    # Limpiar todas las variables de sesión
    session.clear()
    # Redirigir al index principal
    return redirect(url_for('index'))

@app.route('/listar-usuarios')
def listar_usuarios():
    try:
        client = connect_mongo()
        if not client:
            return jsonify({'error': 'Error de conexión con la base de datos'}), 500
        
        db = client['administracion']
        security_collection = db['seguridad']
        
        # Obtener todos los usuarios, excluyendo la contraseña por seguridad
        #usuarios = list(security_collection.find({}, {'password': 0}))

        usuarios = list(security_collection.find())
        
        # Convertir ObjectId a string para serialización JSON
        for usuario in usuarios:
            usuario['_id'] = str(usuario['_id'])
        
        return jsonify(usuarios)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()

@app.route('/crear-coleccion-form/<database>')
def crear_coleccion_form(database):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('gestion/crear_coleccion.html', 
                         database=database,
                         usuario=session['usuario'],
                         version=VERSION_APP,
                         creador=CREATOR_APP)

@app.route('/crear-coleccion', methods=['POST'])
def crear_coleccion():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        database = request.form.get('database')
        collection_name = request.form.get('collection_name')
        zip_file = request.files.get('zip_file')
        
        if not all([database, collection_name, zip_file]):
            return render_template('gestion/crear_coleccion.html',
                                error_message='Todos los campos son requeridos',
                                database=database,
                                usuario=session['usuario'],
                                version=VERSION_APP,
                                creador=CREATOR_APP)
        
        # Conectar a MongoDB
        client = connect_mongo()
        if not client:
            return render_template('gestion/crear_coleccion.html',
                                error_message='Error de conexión con MongoDB',
                                database=database,
                                usuario=session['usuario'],
                                version=VERSION_APP,
                                creador=CREATOR_APP)
        
        # Crear la colección
        db = client[database]
        collection = db[collection_name]
        
        # Procesar el archivo ZIP
        with zipfile.ZipFile(zip_file) as zip_ref:
            # Crear un directorio temporal para extraer los archivos
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Extraer los archivos
            zip_ref.extractall(temp_dir)
            
            # Procesar cada archivo JSON
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            try:
                                json_data = json.load(f)
                                # Si el JSON es una lista, insertar cada elemento
                                if isinstance(json_data, list):
                                    collection.insert_many(json_data)
                                else:
                                    collection.insert_one(json_data)
                            except json.JSONDecodeError:
                                print(f"Error al procesar el archivo {file}")
                            except Exception as e:
                                print(f"Error al insertar datos del archivo {file}: {str(e)}")
            
            # Limpiar el directorio temporal
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(temp_dir)
        
        return redirect(url_for('gestion_proyecto', database=database))
        
    except Exception as e:
        return render_template('gestion/crear_coleccion.html',
                            error_message=f'Error al crear la colección: {str(e)}',
                            database=database,
                            usuario=session['usuario'],
                            version=VERSION_APP,
                            creador=CREATOR_APP)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == '__main__':
    app.run(debug=True)