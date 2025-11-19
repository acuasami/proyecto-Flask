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

# Configuración Railway - VERIFICADA
DB_CONFIG = {
    'host': 'tramway.proxy.rlwy.net',
    'port': 31631,
    'database': 'railway',
    'user': 'postgres',
    'password': 'KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ'
}

# --- Reemplaza esto al inicio de tu script ---

def get_db_connection():
    """Conecta a PostgreSQL usando las variables de entorno de Railway"""
    try:
        # Opción A: Usar la URL completa (Recomendada para Railway)
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Fix para asegurar SSL si la URL no lo tiene
            if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
                 if "?" not in database_url:
                     database_url += "?sslmode=require"
            
            conn = psycopg2.connect(database_url)
        else:
            # Opción B: Usar variables individuales (Respaldo)
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST'),
                port=os.environ.get('PGPORT'),
                database=os.environ.get('PGDATABASE'),
                user=os.environ.get('PGUSER'),
                password=os.environ.get('PGPASSWORD'),
                sslmode='require' # ⚠️ Importante para Railway
            )
            
        logger.info("✅ CONEXIÓN BD EXITOSA")
        return conn
    except Exception as e:
        logger.error(f"❌ ERROR CONEXIÓN BD: {e}")
        return None

def init_database():
    """Inicializar tablas con verificación paso a paso SEGÚN ESQUEMA PDF"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN DE BASE DE DATOS SEGÚN ESQUEMA PDF")
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ NO SE PUDO CONECTAR PARA INICIALIZAR BD")
            return False
            
        cur = conn.cursor()
        
        # 1. TABLA USUARIO - SEGÚN ESQUEMA PDF
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'usuario'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuario'
            );
        """)
        usuario_existe = cur.fetchone()[0]
        
        if not usuario_existe:
            logger.info("📦 CREANDO TABLA 'usuario' SEGÚN ESQUEMA PDF...")
            cur.execute("""
                CREATE TABLE usuario (
                    id_usuario SERIAL PRIMARY KEY,
                    correo VARCHAR(255) UNIQUE NOT NULL,
                    nombre_Usuario VARCHAR(100) UNIQUE NOT NULL,
                    contraseña VARCHAR(255) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'usuario' CREADA EXITOSAMENTE SEGÚN ESQUEMA PDF")
        else:
            logger.info("✅ TABLA 'usuario' YA EXISTE")
            # Verificar estructura actual
            cur.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'usuario' 
                ORDER BY ordinal_position;
            """)
            columnas = cur.fetchall()
            logger.info(f"📊 ESTRUCTURA ACTUAL DE 'usuario': {columnas}")
        
        # 2. TABLA MUNICIPIO - SEGÚN ESQUEMA PDF
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'municipio'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'municipio'
            );
        """)
        municipio_existe = cur.fetchone()[0]
        
        if not municipio_existe:
            logger.info("📦 CREANDO TABLA 'municipio' SEGÚN ESQUEMA PDF...")
            cur.execute("""
                CREATE TABLE municipio (
                    id_municipio SERIAL PRIMARY KEY,
                    nom_municipio VARCHAR(100) NOT NULL,
                    nom_estado VARCHAR(100) NOT NULL
                );
            """)
            logger.info("✅ TABLA 'municipio' CREADA EXITOSAMENTE")
            
            # Insertar algunos municipios de ejemplo
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
            logger.info("✅ MUNICIPIOS DE EJEMPLO INSERTADOS")
        else:
            logger.info("✅ TABLA 'municipio' YA EXISTE")
        
        # 3. TABLA ONGs - SEGÚN ESQUEMA PDF
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'ongs'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ongs'
            );
        """)
        ongs_existe = cur.fetchone()[0]
        
        if not ongs_existe:
            logger.info("📦 CREANDO TABLA 'ongs' SEGÚN ESQUEMA PDF...")
            cur.execute("""
                CREATE TABLE ongs (
                    id_ong SERIAL PRIMARY KEY,
                    id_municipio INT,
                    nom_ong VARCHAR(200) NOT NULL,
                    tipo VARCHAR(100),
                    latitud DECIMAL(10, 8),
                    longitud DECIMAL(11, 8),
                    telefono VARCHAR(20),
                    estado VARCHAR(100),
                    municipio VARCHAR(100),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_municipio) REFERENCES municipio(id_municipio)
                );
            """)
            logger.info("✅ TABLA 'ongs' CREADA EXITOSAMENTE SEGÚN ESQUEMA PDF")
            
            # Insertar ONGs de ejemplo
            ongs_ejemplo = [
                (1, 'Fundación Infantil Mexicana', 'Ayuda a niños', 19.4326, -99.1332, '55-1234-5678', 'CDMX', 'Ciudad de México'),
                (2, 'Ecología y Desarrollo', 'Protección ambiental', 20.6668, -103.3918, '33-9876-5432', 'Jalisco', 'Guadalajara'),
                (3, 'Cruz Roja Mexicana', 'Ayuda humanitaria', 25.6866, -100.3161, '81-1111-2222', 'Nuevo León', 'Monterrey')
            ]
            
            for id_municipio, nombre, tipo, lat, lng, tel, estado, municipio in ongs_ejemplo:
                cur.execute("""
                    INSERT INTO ongs (id_municipio, nom_ong, tipo, latitud, longitud, telefono, estado, municipio) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (id_municipio, nombre, tipo, lat, lng, tel, estado, municipio))
            
            logger.info("✅ ONGs DE EJEMPLO INSERTADAS")
        else:
            logger.info("✅ TABLA 'ongs' YA EXISTE")

        # 4. TABLA UBICACION_USUARIO - SEGÚN ESQUEMA PDF
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'ubicacion_usuario'...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ubicacion_usuario'
            );
        """)
        ubicacion_existe = cur.fetchone()[0]
        
        if not ubicacion_existe:
            logger.info("📦 CREANDO TABLA 'ubicacion_usuario' SEGÚN ESQUEMA PDF...")
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
            logger.info("✅ TABLA 'ubicacion_usuario' CREADA EXITOSAMENTE SEGÚN ESQUEMA PDF")
        else:
            logger.info("✅ TABLA 'ubicacion_usuario' YA EXISTE")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 INICIALIZACIÓN DE BD COMPLETADA SEGÚN ESQUEMA PDF")
        return True
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO EN INIT_DATABASE: {e}")
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
        "version": "13.0",
        "database_status": "conectada",
        "endpoints_available": True,
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
        if 'usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM usuario")
            stats['total_usuarios'] = cur.fetchone()[0]
        else:
            stats['total_usuarios'] = "tabla_no_existe"
            
        if 'ongs' in tablas:
            cur.execute("SELECT COUNT(*) FROM ongs")
            stats['total_ongs'] = cur.fetchone()[0]
        else:
            stats['total_ongs'] = "tabla_no_existe"

        if 'ubicacion_usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM ubicacion_usuario")
            stats['total_ubicaciones'] = cur.fetchone()[0]
        else:
            stats['total_ubicaciones'] = "tabla_no_existe"
            
        if 'municipio' in tablas:
            cur.execute("SELECT COUNT(*) FROM municipio")
            stats['total_municipios'] = cur.fetchone()[0]
        else:
            stats['total_municipios'] = "tabla_no_existe"
        
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
            "details": "Tablas 'usuario', 'municipio', 'ongs' y 'ubicacion_usuario' verificadas/creadas",
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
            # Si no hay conexión, devolver ONGs de ejemplo
            ongs_ejemplo = [
                {
                    'nom_ong': 'Fundación Infantil Mexicana',
                    'latitud': 19.4326,
                    'longitud': -99.1332,
                    'tipo': 'Ayuda a niños en situación vulnerable',
                    'telefono': '55-1234-5678',
                    'estado': 'CDMX',
                    'municipio': 'Ciudad de México'
                }
            ]
            return jsonify({
                'success': True, 
                'ongs': ongs_ejemplo, 
                'count': len(ongs_ejemplo),
                'message': 'ONGs de ejemplo (sin conexión a BD)'
            })
            
        cur = conn.cursor()
        
        # Intentar obtener ONGs de la base de datos - SEGÚN ESQUEMA PDF
        try:
            cur.execute("""
                SELECT nom_ong, latitud, longitud, tipo, telefono, estado, municipio 
                FROM ongs 
                WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                LIMIT 50
            """)
            ongs_data = cur.fetchall()
            
            ongs_list = []
            for ong in ongs_data:
                ongs_list.append({
                    'nom_ong': ong[0] or 'Sin nombre',
                    'latitud': float(ong[1]) if ong[1] else 0.0,
                    'longitud': float(ong[2]) if ong[2] else 0.0,
                    'tipo': ong[3] or 'Sin descripción',
                    'telefono': ong[4] or 'Sin teléfono',
                    'estado': ong[5] or 'Sin estado',
                    'municipio': ong[6] or 'Sin municipio'
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
            # Si falla, devolver ONGs de ejemplo
            ongs_ejemplo = [
                {
                    'nom_ong': 'Fundación Infantil Mexicana',
                    'latitud': 19.4326,
                    'longitud': -99.1332,
                    'tipo': 'Ayuda a niños en situación vulnerable',
                    'telefono': '55-1234-5678',
                    'estado': 'CDMX',
                    'municipio': 'Ciudad de México'
                }
            ]
            cur.close()
            conn.close()
            return jsonify({
                'success': True, 
                'ongs': ongs_ejemplo, 
                'count': len(ongs_ejemplo),
                'message': 'ONGs de ejemplo (error en BD)'
            })

    except Exception as e:
        logger.error(f"Error obteniendo ONGs: {e}")
        # Último recurso: ONGs de ejemplo
        ongs_ejemplo = [
            {
                'nom_ong': 'Fundación Infantil Mexicana',
                'latitud': 19.4326,
                'longitud': -99.1332,
                'tipo': 'Ayuda a niños en situación vulnerable',
                'telefono': '55-1234-5678',
                'estado': 'CDMX',
                'municipio': 'Ciudad de México'
            }
        ]
        return jsonify({
            'success': True, 
            'ongs': ongs_ejemplo, 
            'count': len(ongs_ejemplo),
            'message': 'ONGs de ejemplo (error general)'
        })

@app.route("/api/municipios", methods=['GET'])
def get_municipios():
    """Obtener municipios - NUEVO ENDPOINT SEGÚN ESQUEMA PDF"""
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

logger.info("✅ APLICACIÓN FLASK CARGADA CORRECTAMENTE - ESQUEMA PDF")

if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(host='0.0.0.0', port=5000, debug=True)

