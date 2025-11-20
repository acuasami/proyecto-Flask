from flask import Flask, jsonify, request, g
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback
import sys
from datetime import datetime

# Configurar logging DETALLADO
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Conecta a PostgreSQL usando las variables de entorno de Railway"""
    try:
        # PRIORIDAD 1: Usar DATABASE_URL de Railway (RECOMENDADO)
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            logger.info("🔗 Usando DATABASE_URL de variables de entorno")
            # Convertir postgres:// a postgresql:// y agregar SSL
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            # Asegurar parámetros SSL
            if "sslmode" not in database_url:
                separator = "?" if "?" not in database_url else "&"
                database_url += f"{separator}sslmode=require"
            
            conn = psycopg2.connect(database_url)
            logger.info("✅ CONEXIÓN EXITOSA CON DATABASE_URL")
            return conn
        
        # PRIORIDAD 2: Usar variables individuales de Railway
        logger.info("🔗 Usando variables individuales de Railway")
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST', 'tramway.proxy.rlwy.net'),
            port=os.environ.get('PGPORT', '31631'),
            database=os.environ.get('PGDATABASE', 'railway'),
            user=os.environ.get('PGUSER', 'postgres'),
            password=os.environ.get('PGPASSWORD', 'KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ'),
            sslmode='require'
        )
        logger.info("✅ CONEXIÓN EXITOSA CON VARIABLES INDIVIDUALES")
        return conn
        
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN CONEXIÓN BD: {e}")
        logger.error(f"🔍 DATABASE_URL: {os.environ.get('DATABASE_URL', 'No configurada')}")
        logger.error(f"🔍 PGHOST: {os.environ.get('PGHOST', 'No configurado')}")
        return None

def init_database():
    """Inicializar tablas EXACTAMENTE como en el esquema PDF"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN DE BD SEGÚN ESQUEMA PDF")
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ NO SE PUDO CONECTAR PARA INICIALIZAR BD")
            return False
            
        cur = conn.cursor()
        
        # 1. TABLA USUARIO - EXACTA AL PDF
        logger.info("🔍 VERIFICANDO TABLA 'usuario'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuario'
            );
        """)
        usuario_existe = cur.fetchone()[0]
        
        if not usuario_existe:
            logger.info("📦 CREANDO TABLA 'usuario' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE usuario (
                    id_usuario SERIAL PRIMARY KEY,
                    correo VARCHAR(255) NOT NULL,
                    nombre_Usuario VARCHAR(100) NOT NULL,
                    contraseña VARCHAR(255) NOT NULL
                );
            """)
            logger.info("✅ TABLA 'usuario' CREADA")
        else:
            logger.info("✅ TABLA 'usuario' YA EXISTE")

        # 2. TABLA MUNICIPIO - EXACTA AL PDF
        logger.info("🔍 VERIFICANDO TABLA 'municipio'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'municipio'
            );
        """)
        municipio_existe = cur.fetchone()[0]
        
        if not municipio_existe:
            logger.info("📦 CREANDO TABLA 'municipio' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE municipio (
                    id_municipio SERIAL PRIMARY KEY,
                    nom_municipio VARCHAR(100) NOT NULL,
                    nom_estado VARCHAR(100) NOT NULL
                );
            """)
            logger.info("✅ TABLA 'municipio' CREADA")
            
            # Insertar municipios de ejemplo
            municipios_ejemplo = [
                ('Ciudad de México', 'CDMX'),
                ('Guadalajara', 'Jalisco'),
                ('Monterrey', 'Nuevo León'),
                ('Puebla', 'Puebla'),
                ('Cancún', 'Quintana Roo')
            ]
            
            for municipio, estado in municipios_ejemplo:
                cur.execute(
                    "INSERT INTO municipio (nom_municipio, nom_estado) VALUES (%s, %s)",
                    (municipio, estado)
                )
            logger.info("✅ MUNICIPIOS INSERTADOS")

        # 3. TABLA ONGS - EXACTA AL PDF (SIN columnas extras)
        logger.info("🔍 VERIFICANDO TABLA 'ongs'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ongs'
            );
        """)
        ongs_existe = cur.fetchone()[0]
        
        if not ongs_existe:
            logger.info("📦 CREANDO TABLA 'ongs' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE ongs (
                    id_ong SERIAL PRIMARY KEY,
                    id_municipio INT,
                    nom_ong VARCHAR(200) NOT NULL,
                    tipo VARCHAR(100),
                    latitud DECIMAL(10, 8),
                    longitud DECIMAL(11, 8),
                    FOREIGN KEY (id_municipio) REFERENCES municipio(id_municipio)
                );
            """)
            logger.info("✅ TABLA 'ongs' CREADA SEGÚN PDF")
            
            # Insertar ONGs de ejemplo
            ongs_ejemplo = [
                (1, 'Fundación Infantil Mexicana', 'Ayuda a niños', 19.4326, -99.1332),
                (2, 'Ecología y Desarrollo', 'Protección ambiental', 20.6668, -103.3918),
                (3, 'Cruz Roja Mexicana', 'Ayuda humanitaria', 25.6866, -100.3161),
                (4, 'Alimentos para Todos', 'Ayuda alimentaria', 19.0414, -98.2063),
                (5, 'Salvemos los Animales', 'Protección animal', 21.1619, -86.8515)
            ]
            
            for id_municipio, nombre, tipo, lat, lng in ongs_ejemplo:
                cur.execute("""
                    INSERT INTO ongs (id_municipio, nom_ong, tipo, latitud, longitud) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_municipio, nombre, tipo, lat, lng))
            
            logger.info("✅ ONGs DE EJEMPLO INSERTADAS")

        # 4. TABLA UBICACION_USUARIO - EXACTA AL PDF
        logger.info("🔍 VERIFICANDO TABLA 'ubicacion_usuario'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ubicacion_usuario'
            );
        """)
        ubicacion_existe = cur.fetchone()[0]
        
        if not ubicacion_existe:
            logger.info("📦 CREANDO TABLA 'ubicacion_usuario' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE ubicacion_usuario (
                    id_ubi_us SERIAL PRIMARY KEY,
                    id_usuario INT NOT NULL,
                    latitud DECIMAL(10, 8) NOT NULL,
                    longitud DECIMAL(11, 8) NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
                );
            """)
            logger.info("✅ TABLA 'ubicacion_usuario' CREADA")

        # 5. TABLA FECHA - NUEVA SEGÚN PDF
        logger.info("🔍 VERIFICANDO TABLA 'fecha'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'fecha'
            );
        """)
        fecha_existe = cur.fetchone()[0]
        
        if not fecha_existe:
            logger.info("📦 CREANDO TABLA 'fecha' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE fecha (
                    id_fecha SERIAL PRIMARY KEY,
                    id_municipio INT NOT NULL,
                    fecha DATE NOT NULL,
                    robos INT,
                    secuestros INT,
                    grado VARCHAR(50),
                    FOREIGN KEY (id_municipio) REFERENCES municipio(id_municipio)
                );
            """)
            logger.info("✅ TABLA 'fecha' CREADA")

        # 6. TABLA ARISTA - NUEVA SEGÚN PDF
        logger.info("🔍 VERIFICANDO TABLA 'arista'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'arista'
            );
        """)
        arista_existe = cur.fetchone()[0]
        
        if not arista_existe:
            logger.info("📦 CREANDO TABLA 'arista' SEGÚN PDF...")
            cur.execute("""
                CREATE TABLE arista (
                    id_grafo SERIAL PRIMARY KEY,
                    id_ubi_us INT NOT NULL,
                    id_ong INT NOT NULL,
                    distancia NUMERIC(10, 2),
                    fecha DATE NOT NULL,
                    FOREIGN KEY (id_ubi_us) REFERENCES ubicacion_usuario(id_ubi_us),
                    FOREIGN KEY (id_ong) REFERENCES ongs(id_ong)
                );
            """)
            logger.info("✅ TABLA 'arista' CREADA")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 ESQUEMA COMPLETO SEGÚN PDF CREADO")
        return True
        
    except Exception as e:
        logger.error(f"💥 ERROR EN INIT_DATABASE: {e}")
        logger.error(traceback.format_exc())
        return False

# INICIALIZACIÓN AL PRIMER REQUEST
@app.before_request
def initialize_on_first_request():
    """Inicialización que se ejecuta una vez en el primer request"""
    if not hasattr(g, 'db_initialized'):
        logger.info("🚀 INICIANDO APLICACIÓN FLASK - PRIMER REQUEST")
        init_database()
        g.db_initialized = True

@app.route("/")
def home():
    """Endpoint raíz"""
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México - ESQUEMA PDF IMPLEMENTADO",
        "version": "2.0",
        "database_status": "conectada",
        "timestamp": str(datetime.now())
    })

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check COMPLETO con diagnóstico"""
    logger.info("❤️ SOLICITUD HEALTH CHECK")
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "status": "unhealthy",
                "message": "❌ NO SE PUEDE CONECTAR A LA BASE DE DATOS",
                "database_connection": False,
                "timestamp": str(datetime.now())
            }), 500
        
        cur = conn.cursor()
        
        # Verificar tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        logger.info(f"📋 TABLAS ENCONTRADAS: {tablas}")
        
        # Contar registros
        stats = {}
        for tabla in ['usuario', 'ongs', 'ubicacion_usuario', 'municipio', 'fecha', 'arista']:
            if tabla in tablas:
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                stats[f'total_{tabla}'] = cur.fetchone()[0]
            else:
                stats[f'total_{tabla}'] = "tabla_no_existe"
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "message": "✅ SISTEMA OPERATIVO - ESQUEMA PDF",
            "database_connection": True,
            "tablas": tablas,
            "estadisticas": stats,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"💥 ERROR EN HEALTH CHECK: {e}")
        return jsonify({
            "status": "error",
            "message": f"❌ ERROR: {str(e)}",
            "timestamp": str(datetime.now())
        }), 500

@app.route("/api/initdb", methods=['GET', 'POST'])
def init_db():
    """Forzar inicialización de BD con respuesta detallada"""
    logger.info("🔄 SOLICITUD DE INICIALIZACIÓN DE BD")
    
    success = init_database()
    
    if success:
        return jsonify({
            "success": True,
            "message": "✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE SEGÚN ESQUEMA PDF",
            "details": "Todas las tablas del PDF verificadas/creadas",
            "timestamp": str(datetime.now())
        })
    else:
        return jsonify({
            "success": False,
            "message": "❌ ERROR INICIALIZANDO BASE DE DATOS",
            "details": "Revisar logs para más información",
            "timestamp": str(datetime.now())
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """REGISTRO DE USUARIO - CORREGIDO SEGÚN ESQUEMA PDF"""
    logger.info("🎯 INICIANDO PROCESO DE REGISTRO - ESQUEMA PDF")
    
    try:
        # 1. OBTENER Y VALIDAR DATOS DE ENTRADA
        if not request.is_json:
            logger.error("❌ CONTENT-TYPE NO ES APPLICATION/JSON")
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE',
                'timestamp': str(datetime.now())
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS RECIBIDOS: {data}")
        
        if not data:
            logger.error("❌ NO SE RECIBIERON DATOS JSON")
            return jsonify({
                'success': False, 
                'message': 'No se recibieron datos JSON',
                'error_code': 'NO_DATA',
                'timestamp': str(datetime.now())
            }), 400
        
        # SEGÚN ESQUEMA PDF: nombre_Usuario, correo, contraseña
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"🔑 USUARIO: '{username}', CORREO: '{email}', LONGITUD CONTRASEÑA: {len(password)}")
        
        # 2. VALIDACIONES DE DATOS
        if not username:
            logger.error("❌ NOMBRE_USUARIO VACÍO")
            return jsonify({
                'success': False, 
                'message': 'El nombre de usuario no puede estar vacío',
                'error_code': 'EMPTY_USERNAME',
                'timestamp': str(datetime.now())
            }), 400

        if not email:
            logger.error("❌ CORREO VACÍO")
            return jsonify({
                'success': False, 
                'message': 'El correo no puede estar vacío',
                'error_code': 'EMPTY_EMAIL',
                'timestamp': str(datetime.now())
            }), 400
            
        if not password:
            logger.error("❌ CONTRASEÑA VACÍA")
            return jsonify({
                'success': False, 
                'message': 'La contraseña no puede estar vacía',
                'error_code': 'EMPTY_PASSWORD',
                'timestamp': str(datetime.now())
            }), 400

        if len(password) < 4:
            logger.error("❌ CONTRASEÑA DEMASIADO CORTA")
            return jsonify({
                'success': False, 
                'message': 'La contraseña debe tener al menos 4 caracteres',
                'error_code': 'SHORT_PASSWORD',
                'timestamp': str(datetime.now())
            }), 400

        # 3. CONEXIÓN A BASE DE DATOS
        logger.info("🔌 CONECTANDO A BASE DE DATOS...")
        conn = get_db_connection()
        if not conn:
            logger.error("❌ FALLA CRÍTICA DE CONEXIÓN A BD")
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a la base de datos',
                'error_code': 'DB_CONNECTION_FAILED',
                'timestamp': str(datetime.now())
            }), 500
            
        cur = conn.cursor()
        
        # 4. VERIFICAR SI USUARIO O CORREO EXISTEN - SEGÚN ESQUEMA PDF
        logger.info(f"🔍 VERIFICANDO EXISTENCIA DE USUARIO: {username} Y CORREO: {email}")
        try:
            # SEGÚN ESQUEMA PDF: nombre_Usuario, correo
            cur.execute("SELECT id_usuario FROM usuario WHERE nombre_Usuario = %s OR correo = %s", (username, email))
            existing_user = cur.fetchone()
            
            if existing_user:
                logger.warning(f"❌ USUARIO O CORREO YA EXISTEN: {username}, {email}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'El usuario o correo ya existen',
                    'error_code': 'USER_EXISTS',
                    'timestamp': str(datetime.now())
                }), 409
                
            logger.info(f"✅ USUARIO Y CORREO DISPONIBLES: {username}, {email}")
                
        except Exception as e:
            logger.error(f"❌ ERROR VERIFICANDO USUARIO: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Error verificando usuario',
                'error_code': 'CHECK_USER_ERROR',
                'details': str(e),
                'timestamp': str(datetime.now())
            }), 500

        # 5. INSERTAR NUEVO USUARIO - SEGÚN ESQUEMA PDF
        logger.info(f"💾 INSERTANDO NUEVO USUARIO: {username}, {email}")
        try:
            # SEGÚN ESQUEMA PDF: nombre_Usuario, correo, contraseña
            cur.execute(
                "INSERT INTO usuario (nombre_Usuario, correo, contraseña) VALUES (%s, %s, %s) RETURNING id_usuario", 
                (username, email, password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ USUARIO REGISTRADO EXITOSAMENTE - ID: {user_id}, USUARIO: {username}, CORREO: {email}")
            
        except Exception as e:
            logger.error(f"❌ ERROR INSERTANDO USUARIO: {e}")
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Error insertando usuario: {str(e)}',
                'error_code': 'INSERT_ERROR',
                'timestamp': str(datetime.now())
            }), 500

        # 6. VERIFICAR INSERCIÓN Y OBTENER ESTADÍSTICAS
        logger.info("🔍 VERIFICANDO INSERCIÓN...")
        try:
            cur.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cur.fetchone()[0]
            logger.info(f"📊 TOTAL USUARIOS EN BD: {total_usuarios}")
        except Exception as e:
            logger.warning(f"⚠️ ERROR CONTANDO USUARIOS: {e}")
            total_usuarios = 1
        
        cur.close()
        conn.close()
        
        # 7. RESPUESTA DE ÉXITO
        logger.info(f"🎉 REGISTRO COMPLETADO EXITOSAMENTE PARA: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id,
            'username': username,
            'email': email,
            'total_usuarios': total_usuarios,
            'timestamp': str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO NO MANEJADO EN REGISTRO: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Error crítico del servidor: {str(e)}',
            'error_code': 'UNHANDLED_ERROR',
            'timestamp': str(datetime.now())
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuario - CORREGIDO SEGÚN ESQUEMA PDF"""
    try:
        logger.info("🔐 SOLICITUD DE LOGIN RECIBIDA")
        
        if not request.is_json:
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS LOGIN RECIBIDOS: {data}")
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'Datos no proporcionados',
                'error_code': 'NO_DATA'
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({
                'success': False, 
                'message': 'Usuario y contraseña requeridos',
                'error_code': 'MISSING_CREDENTIALS'
            }), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a BD',
                'error_code': 'DB_CONNECTION_FAILED'
            }), 500
            
        cur = conn.cursor()
        
        try:
            # SEGÚN ESQUEMA PDF: nombre_Usuario, contraseña
            cur.execute("SELECT id_usuario, nombre_Usuario, correo FROM usuario WHERE nombre_Usuario = %s AND contraseña = %s", 
                       (username, password))
            user = cur.fetchone()
        except Exception as e:
            logger.error(f"Error en consulta login: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Error en consulta de login',
                'error_code': 'QUERY_ERROR'
            }), 500
        
        cur.close()
        conn.close()

        if user:
            logger.info(f"✅ LOGIN EXITOSO PARA USUARIO: {username}")
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'user': {
                    'id': user[0],
                    'nombre': user[1],
                    'email': user[2]
                }
            })
        else:
            logger.warning(f"❌ CREDENCIALES INCORRECTAS PARA: {username}")
            return jsonify({
                'success': False, 
                'message': 'Credenciales incorrectas',
                'error_code': 'INVALID_CREDENTIALS'
            }), 401

    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error del servidor en login',
            'error_code': 'LOGIN_ERROR'
        }), 500

@app.route('/api/ubicacion-usuario', methods=['POST'])
def guardar_ubicacion_usuario():
    """Guardar ubicación del usuario - CORREGIDO SEGÚN ESQUEMA PDF"""
    try:
        logger.info("📍 SOLICITUD DE GUARDAR UBICACIÓN RECIBIDA")
        
        if not request.is_json:
            logger.error("❌ CONTENT-TYPE NO ES APPLICATION/JSON")
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS UBICACIÓN RECIBIDOS: {data}")
        
        if not data:
            logger.error("❌ NO SE RECIBIERON DATOS JSON")
            return jsonify({
                'success': False, 
                'message': 'No se recibieron datos JSON',
                'error_code': 'NO_DATA'
            }), 400
        
        id_usuario = data.get('id_usuario')
        latitud = data.get('latitud')
        longitud = data.get('longitud')

        if id_usuario is None or latitud is None or longitud is None:
            logger.error("❌ DATOS INCOMPLETOS")
            return jsonify({
                'success': False, 
                'message': 'ID usuario, latitud y longitud requeridos',
                'error_code': 'MISSING_DATA'
            }), 400

        try:
            id_usuario = int(id_usuario)
            latitud = float(latitud)
            longitud = float(longitud)
        except (ValueError, TypeError) as e:
            logger.error(f"❌ ERROR EN TIPOS DE DATOS: {e}")
            return jsonify({
                'success': False, 
                'message': 'ID usuario debe ser entero, latitud y longitud deben ser números',
                'error_code': 'INVALID_DATA_TYPES'
            }), 400

        conn = get_db_connection()
        if not conn:
            logger.error("❌ FALLA CRÍTICA DE CONEXIÓN A BD")
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a la base de datos',
                'error_code': 'DB_CONNECTION_FAILED'
            }), 500
            
        cur = conn.cursor()
        
        # Verificar que el usuario exista - SEGÚN ESQUEMA PDF: id_usuario
        logger.info(f"🔍 VERIFICANDO EXISTENCIA DE USUARIO ID: {id_usuario}")
        try:
            cur.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,))
            usuario_existe = cur.fetchone()
            
            if not usuario_existe:
                logger.error(f"❌ USUARIO NO ENCONTRADO: {id_usuario}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'Usuario con ID {id_usuario} no encontrado',
                    'error_code': 'USER_NOT_FOUND'
                }), 404
        except Exception as e:
            logger.error(f"❌ ERROR VERIFICANDO USUARIO: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Error verificando usuario',
                'error_code': 'USER_VERIFICATION_ERROR'
            }), 500

        # Insertar ubicación - SEGÚN ESQUEMA PDF: id_usuario, latitud, longitud
        logger.info(f"💾 INSERTANDO UBICACIÓN - Usuario: {id_usuario}, Lat: {latitud}, Lng: {longitud}")
        try:
            cur.execute(
                "INSERT INTO ubicacion_usuario (id_usuario, latitud, longitud) VALUES (%s, %s, %s) RETURNING id_ubi_us",
                (id_usuario, latitud, longitud)
            )
            id_ubi_us = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ UBICACIÓN GUARDADA EXITOSAMENTE - ID Ubicación: {id_ubi_us}")
            
        except Exception as e:
            logger.error(f"❌ ERROR INSERTANDO UBICACIÓN: {e}")
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Error insertando ubicación: {str(e)}',
                'error_code': 'INSERT_ERROR'
            }), 500

        cur.close()
        conn.close()
        
        logger.info(f"🎉 UBICACIÓN GUARDADA EXITOSAMENTE PARA USUARIO: {id_usuario}")
        
        return jsonify({
            'success': True,
            'message': 'Ubicación guardada exitosamente',
            'id_ubi_us': id_ubi_us,
            'id_usuario': id_usuario,
            'latitud': latitud,
            'longitud': longitud,
            'timestamp': str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO NO MANEJADO EN GUARDAR UBICACIÓN: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Error crítico del servidor: {str(e)}',
            'error_code': 'UNHANDLED_ERROR',
            'timestamp': str(datetime.now())
        }), 500

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener ONGs - CORREGIDO SEGÚN ESQUEMA PDF"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': True, 
                'ongs': obtener_ongs_ejemplo(),
                'message': 'ONGs de ejemplo (sin conexión a BD)'
            })
            
        cur = conn.cursor()
        
        try:
            # ✅ CORREGIDO: JOIN con municipio según esquema PDF
            cur.execute("""
                SELECT o.nom_ong, o.tipo, o.latitud, o.longitud, 
                       m.nom_municipio, m.nom_estado
                FROM ongs o
                LEFT JOIN municipio m ON o.id_municipio = m.id_municipio
                WHERE o.latitud IS NOT NULL AND o.longitud IS NOT NULL
                LIMIT 50
            """)
            ongs_data = cur.fetchall()
            
            ongs_list = []
            for ong in ongs_data:
                ongs_list.append({
                    'nom_ong': ong[0] or 'Sin nombre',
                    'tipo': ong[1] or 'Sin descripción',
                    'latitud': float(ong[2]) if ong[2] else 0.0,
                    'longitud': float(ong[3]) if ong[3] else 0.0,
                    'municipio': ong[4] or 'Sin municipio',
                    'estado': ong[5] or 'Sin estado'
                })

            cur.close()
            conn.close()

            return jsonify({
                'success': True, 
                'ongs': ongs_list, 
                'count': len(ongs_list),
                'message': f'Se encontraron {len(ongs_list)} ONGs'
            })

        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo ONGs de BD: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': True, 
                'ongs': obtener_ongs_ejemplo(),
                'message': 'ONGs de ejemplo (error en consulta)'
            })

    except Exception as e:
        logger.error(f"Error obteniendo ONGs: {e}")
        return jsonify({
            'success': True, 
            'ongs': obtener_ongs_ejemplo(),
            'message': 'ONGs de ejemplo (error general)'
        })

def obtener_ongs_ejemplo():
    """ONGs de ejemplo cuando falla la BD"""
    return [
        {
            'nom_ong': 'Fundación Infantil Mexicana',
            'tipo': 'Ayuda a niños en situación vulnerable',
            'latitud': 19.4326,
            'longitud': -99.1332,
            'municipio': 'Ciudad de México',
            'estado': 'CDMX'
        }
    ]

@app.route("/api/municipios", methods=['GET'])
def get_municipios():
    """Obtener municipios - CORREGIDO SEGÚN ESQUEMA PDF"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos',
                'municipios': []
            }), 500
            
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT id_municipio, nom_municipio, nom_estado FROM municipio ORDER BY nom_estado, nom_municipio")
            municipios_data = cur.fetchall()
            
            municipios_list = []
            for municipio in municipios_data:
                municipios_list.append({
                    'id_municipio': municipio[0],
                    'nom_municipio': municipio[1],
                    'nom_estado': municipio[2]
                })

            cur.close()
            conn.close()

            return jsonify({
                'success': True, 
                'municipios': municipios_list, 
                'count': len(municipios_list),
                'message': f'Se encontraron {len(municipios_list)} municipios'
            })

        except Exception as e:
            logger.error(f"Error obteniendo municipios: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Error obteniendo municipios',
                'municipios': []
            }), 500

    except Exception as e:
        logger.error(f"Error en endpoint municipios: {e}")
        return jsonify({
            'success': False,
            'message': 'Error del servidor',
            'municipios': []
        }), 500

@app.route("/mapa")
def mostrar_mapa():
    """Endpoint para mapa interactivo con Folium"""
    try:
        lat = request.args.get('lat', default=19.4326, type=float)
        lon = request.args.get('lon', default=-99.1332, type=float)
        id_usuario = request.args.get('id_usuario', default=-1, type=int)
        
        logger.info(f"🗺️ Solicitando mapa - Usuario: {id_usuario}, Ubicación: ({lat}, {lon})")
        
        # Obtener ONGs de la base de datos
        conn = get_db_connection()
        ongs_list = []
        
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT o.nom_ong, o.tipo, o.latitud, o.longitud, 
                           m.nom_municipio, m.nom_estado
                    FROM ongs o
                    LEFT JOIN municipio m ON o.id_municipio = m.id_municipio
                    WHERE o.latitud IS NOT NULL AND o.longitud IS NOT NULL
                    LIMIT 20
                """)
                ongs_data = cur.fetchall()
                
                for ong in ongs_data:
                    ongs_list.append({
                        'nombre': ong[0],
                        'tipo': ong[1],
                        'lat': float(ong[2]),
                        'lon': float(ong[3]),
                        'municipio': ong[4],
                        'estado': ong[5]
                    })
                    
            except Exception as e:
                logger.error(f"Error obteniendo ONGs para mapa: {e}")
            finally:
                cur.close()
                conn.close()
        
        # Generar HTML del mapa
        html_content = generar_mapa_html(lat, lon, ongs_list, id_usuario)
        return html_content
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint /mapa: {e}")
        return f"Error cargando mapa: {str(e)}", 500

def generar_mapa_html(lat_usuario, lon_usuario, ongs_list, id_usuario):
    """Generar HTML del mapa con usuario y ONGs"""
    
    ongs_html = ""
    for ong in ongs_list:
        ongs_html += f"""
        <div class="ong-marker">
            <h4>🏥 {ong['nombre']}</h4>
            <p><strong>Tipo:</strong> {ong['tipo']}</p>
            <p><strong>Ubicación:</strong> {ong['municipio']}, {ong['estado']}</p>
            <p><strong>Coordenadas:</strong> {ong['lat']:.4f}, {ong['lon']:.4f}</p>
        </div>
        """
    
    # Generar JavaScript para los marcadores de ONGs
    marcadores_js = ""
    for i, ong in enumerate(ongs_list):
        marcadores_js += f"""
            L.marker([{ong['lat']}, {ong['lon']}])
                .addTo(map)
                .bindPopup('<b>🏥 {ong['nombre']}</b><br>{ong['tipo']}<br>{ong['municipio']}, {ong['estado']}');
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mapa de ONGs - Usuario {id_usuario}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; }}
            #map {{ height: 100vh; width: 100%; }}
            .info {{ 
                position: absolute; 
                top: 10px; 
                left: 10px; 
                background: white; 
                padding: 15px; 
                border-radius: 8px;
                z-index: 1000;
                max-width: 300px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif;
            }}
            .user-marker {{ color: #007bff; font-weight: bold; }}
            .ong-marker {{ color: #28a745; }}
        </style>
    </head>
    <body>
        <div class="info">
            <h3 class="user-marker">📍 Tu Ubicación</h3>
            <p><strong>Lat:</strong> {lat_usuario:.6f}</p>
            <p><strong>Lon:</strong> {lon_usuario:.6f}</p>
            <p><strong>Usuario ID:</strong> {id_usuario}</p>
            <p><strong>ONGs cercanas:</strong> {len(ongs_list)}</p>
        </div>
        <div id="map"></div>
        
        <script>
            // Inicializar mapa centrado en el usuario
            var map = L.map('map').setView([{lat_usuario}, {lon_usuario}], 13);
            
            // Capa de tiles de OpenStreetMap
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }}).addTo(map);
            
            // Marcador del usuario (azul)
            var userIcon = L.divIcon({{
                className: 'user-marker',
                html: '📍<div style="font-size: 12px; margin-top: 5px;">Tú</div>',
                iconSize: [30, 40],
                iconAnchor: [15, 40]
            }});
            
            L.marker([{lat_usuario}, {lon_usuario}], {{icon: userIcon}})
                .addTo(map)
                .bindPopup('<b class="user-marker">📍 Tu Ubicación</b><br>Usuario ID: {id_usuario}<br>Coordenadas: {lat_usuario:.6f}, {lon_usuario:.6f}')
                .openPopup();
            
            // Marcadores de ONGs (verdes)
            {marcadores_js}
            
            // Ajustar vista para incluir todos los marcadores
            var group = new L.featureGroup([L.marker([{lat_usuario}, {lon_usuario}])]);
            map.fitBounds(group.getBounds().pad(0.1));
            
        </script>
    </body>
    </html>
    """

logger.info("✅ APLICACIÓN FLASK CARGADA CORRECTAMENTE - ESQUEMA PDF COMPLETO")

if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(host='0.0.0.0', port=5000, debug=True)
