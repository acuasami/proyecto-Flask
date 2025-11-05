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

def get_db_connection():
    """Conecta a PostgreSQL con manejo robusto de errores"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ CONEXIÓN BD EXITOSA")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"❌ ERROR OPERACIONAL BD: {e}")
        return None
    except psycopg2.InterfaceError as e:
        logger.error(f"❌ ERROR INTERFAZ BD: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ ERROR INESPERADO BD: {e}")
        logger.error(traceback.format_exc())
        return None

def init_database():
    """Inicializar tablas con verificación paso a paso"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN DE BASE DE DATOS")
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ NO SE PUDO CONECTAR PARA INICIALIZAR BD")
            return False
            
        cur = conn.cursor()
        
        # Verificar si existe la tabla usuario
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLAS...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuario'
            );
        """)
        usuario_existe = cur.fetchone()[0]
        
        if not usuario_existe:
            logger.info("📦 CREANDO TABLA 'usuario'...")
            cur.execute("""
                CREATE TABLE usuario (
                    id_usuario SERIAL PRIMARY KEY,
                    nombre_usuario VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    contraseña VARCHAR(100) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'usuario' CREADA EXITOSAMENTE")
        else:
            logger.info("✅ TABLA 'usuario' YA EXISTE")
            # Verificar la estructura de la tabla
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'usuario' 
                ORDER BY ordinal_position;
            """)
            columnas = cur.fetchall()
            logger.info(f"📊 COLUMNAS DE USUARIO: {columnas}")
        
        # Verificar tabla ongs
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ongs'
            );
        """)
        ongs_existe = cur.fetchone()[0]
        
        if not ongs_existe:
            logger.info("📦 CREANDO TABLA 'ongs'...")
            cur.execute("""
                CREATE TABLE ongs (
                    id_ong SERIAL PRIMARY KEY,
                    nom_ong VARCHAR(200),
                    latitud DECIMAL(10, 8),
                    longitud DECIMAL(11, 8),
                    tipo TEXT,
                    telefono VARCHAR(20),
                    estado VARCHAR(100),
                    municipio VARCHAR(100),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'ongs' CREADA EXITOSAMENTE")
            
            # Insertar datos de ejemplo
            logger.info("📝 INSERTANDO DATOS DE EJEMPLO EN ONGs...")
            ongs_ejemplo = [
                ("Fundación Infantil Mexicana", 19.4326, -99.1332, "Ayuda a niños", "55-1234-5678", "CDMX", "Ciudad de México"),
                ("Ecología y Desarrollo", 20.6668, -103.3918, "Protección ambiental", "33-9876-5432", "Jalisco", "Guadalajara"),
                ("Cruz Roja Mexicana", 19.4326, -99.1332, "Ayuda humanitaria", "55-1111-2222", "CDMX", "Ciudad de México")
            ]
            
            for ong in ongs_ejemplo:
                cur.execute("""
                    INSERT INTO ongs (nom_ong, latitud, longitud, tipo, telefono, estado, municipio) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ong)
            
            conn.commit()
            logger.info("✅ DATOS DE EJEMPLO INSERTADOS")
        else:
            logger.info("✅ TABLA 'ongs' YA EXISTE")

        # Verificar tabla ubicacion_usuario
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ubicacion_usuario'
            );
        """)
        ubicacion_existe = cur.fetchone()[0]
        
        if not ubicacion_existe:
            logger.info("📦 CREANDO TABLA 'ubicacion_usuario'...")
            cur.execute("""
                CREATE TABLE ubicacion_usuario (
                    id_ubi_us SERIAL PRIMARY KEY,
                    id_usuario INT NOT NULL,
                    latitud DECIMAL(10, 8) NOT NULL,
                    longitud DECIMAL(11, 8) NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'ubicacion_usuario' CREADA EXITOSAMENTE")
        else:
            logger.info("✅ TABLA 'ubicacion_usuario' YA EXISTE")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 INICIALIZACIÓN DE BD COMPLETADA")
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
        "message": "🚀 API Flask - ONGs México - REGISTRO CORREGIDO",
        "version": "11.0",
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
            
            # Verificar estructura de usuario
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'usuario'
            """)
            columnas_usuario = cur.fetchall()
            stats['columnas_usuario'] = str(columnas_usuario)
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
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "message": "✅ SISTEMA OPERATIVO",
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
            "message": "✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE",
            "details": "Tablas 'usuario', 'ongs' y 'ubicacion_usuario' verificadas/creadas",
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
    """REGISTRO DE USUARIO - VERSIÓN COMPLETAMENTE CORREGIDA"""
    logger.info("🎯 INICIANDO PROCESO DE REGISTRO - VERSIÓN CORREGIDA")
    
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
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"🔑 USUARIO: '{username}', EMAIL: '{email}', LONGITUD PASSWORD: {len(password)}")
        
        # 2. VALIDACIONES DE DATOS
        if not username:
            logger.error("❌ USUARIO VACÍO")
            return jsonify({
                'success': False, 
                'message': 'El usuario no puede estar vacío',
                'error_code': 'EMPTY_USERNAME',
                'timestamp': str(datetime.now())
            }), 400

        if not email:
            logger.error("❌ EMAIL VACÍO")
            return jsonify({
                'success': False, 
                'message': 'El email no puede estar vacío',
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
        
        # 4. VERIFICAR Y CREAR TABLA SI NO EXISTE
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'usuario'...")
        try:
            # Verificar estructura de la tabla
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'usuario'
                ORDER BY ordinal_position;
            """)
            columnas = cur.fetchall()
            logger.info(f"📊 ESTRUCTURA DE TABLA USUARIO: {columnas}")
            
            # Intentar una consulta simple para verificar si la tabla funciona
            cur.execute("SELECT 1 FROM usuario LIMIT 1")
            logger.info("✅ TABLA 'usuario' EXISTE Y ES ACCESIBLE")
            
        except Exception as e:
            logger.warning(f"⚠️ TABLA 'usuario' NO EXISTE O NO ES ACCESIBLE: {e}")
            logger.info("📦 INTENTANDO CREAR TABLA 'usuario'...")
            try:
                # Crear tabla con la estructura correcta según el diagrama
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS usuario (
                        id_usuario SERIAL PRIMARY KEY,
                        nombre_usuario VARCHAR(100) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        contraseña VARCHAR(100) NOT NULL,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("✅ TABLA 'usuario' CREADA EXITOSAMENTE")
                
            except Exception as create_error:
                logger.error(f"❌ ERROR CRÍTICO CREANDO TABLA: {create_error}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Error crítico creando tabla de usuarios',
                    'error_code': 'TABLE_CREATION_ERROR',
                    'details': str(create_error),
                    'timestamp': str(datetime.now())
                }), 500

        # 5. VERIFICAR SI USUARIO O EMAIL EXISTEN - CONSULTA CORREGIDA
        logger.info(f"🔍 VERIFICANDO EXISTENCIA DE USUARIO: {username} Y EMAIL: {email}")
        try:
            # Consulta adaptativa - probar diferentes nombres de columnas
            consultas = [
                "SELECT id_usuario FROM usuario WHERE nombre_usuario = %s OR email = %s",
                "SELECT id FROM usuario WHERE nombre_usuario = %s OR email = %s", 
                "SELECT id_usuario FROM usuario WHERE username = %s OR email = %s",
                "SELECT id FROM usuario WHERE username = %s OR email = %s"
            ]
            
            existing_user = None
            columna_id = None
            
            for consulta in consultas:
                try:
                    logger.info(f"🔍 PROBANDO CONSULTA: {consulta}")
                    cur.execute(consulta, (username, email))
                    existing_user = cur.fetchone()
                    if existing_user:
                        columna_id = 'id_usuario' if 'id_usuario' in consulta else 'id'
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Consulta falló: {consulta} - {e}")
                    continue
            
            if existing_user:
                logger.warning(f"❌ USUARIO O EMAIL YA EXISTEN: {username}, {email}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'El usuario o email ya existen',
                    'error_code': 'USER_EXISTS',
                    'timestamp': str(datetime.now())
                }), 409
                
            logger.info(f"✅ USUARIO Y EMAIL DISPONIBLES: {username}, {email}")
                
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

        # 6. INSERTAR NUEVO USUARIO - CONSULTA ADAPTATIVA
        logger.info(f"💾 INSERTANDO NUEVO USUARIO: {username}, {email}")
        try:
            # Intentar diferentes formatos de INSERT
            inserciones = [
                "INSERT INTO usuario (nombre_usuario, email, contraseña) VALUES (%s, %s, %s) RETURNING id_usuario",
                "INSERT INTO usuario (nombre_usuario, email, contraseña) VALUES (%s, %s, %s) RETURNING id",
                "INSERT INTO usuario (username, email, password) VALUES (%s, %s, %s) RETURNING id_usuario",
                "INSERT INTO usuario (username, email, password) VALUES (%s, %s, %s) RETURNING id"
            ]
            
            user_id = None
            for insercion in inserciones:
                try:
                    logger.info(f"💾 INTENTANDO INSERTAR CON: {insercion}")
                    cur.execute(insercion, (username, email, password))
                    result = cur.fetchone()
                    if result:
                        user_id = result[0]
                        conn.commit()
                        logger.info(f"✅ USUARIO INSERTADO CON ÉXITO - ID: {user_id}")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Inserción falló: {insercion} - {e}")
                    conn.rollback()
                    continue
            
            if not user_id:
                raise Exception("Todas las inserciones fallaron")
            
            logger.info(f"✅ USUARIO REGISTRADO EXITOSAMENTE - ID: {user_id}, USUARIO: {username}, EMAIL: {email}")
            
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

        # 7. VERIFICAR INSERCIÓN Y OBTENER ESTADÍSTICAS
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
        
        # 8. RESPUESTA DE ÉXITO
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
    """Login de usuario - VERSIÓN CORREGIDA"""
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
            # Consulta adaptativa para login
            consultas = [
                "SELECT id_usuario, nombre_usuario, email FROM usuario WHERE nombre_usuario = %s AND contraseña = %s",
                "SELECT id_usuario, nombre_usuario, email FROM usuario WHERE username = %s AND password = %s",
                "SELECT id, nombre_usuario, email FROM usuario WHERE nombre_usuario = %s AND contraseña = %s",
                "SELECT id, username, email FROM usuario WHERE username = %s AND password = %s"
            ]
            
            user = None
            for consulta in consultas:
                try:
                    logger.info(f"🔍 PROBANDO LOGIN CON: {consulta}")
                    cur.execute(consulta, (username, password))
                    user = cur.fetchone()
                    if user:
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Consulta login falló: {consulta} - {e}")
                    continue
                    
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
    """Guardar ubicación del usuario con su ID - VERSIÓN MEJORADA"""
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
        
        # Verificar y crear tabla si no existe
        try:
            cur.execute("SELECT 1 FROM ubicacion_usuario LIMIT 1")
            logger.info("✅ TABLA 'ubicacion_usuario' EXISTE Y ES ACCESIBLE")
        except Exception as e:
            logger.warning(f"⚠️ TABLA 'ubicacion_usuario' NO EXISTE: {e}")
            logger.info("📦 CREANDO TABLA 'ubicacion_usuario'...")
            try:
                cur.execute("""
                    CREATE TABLE ubicacion_usuario (
                        id_ubi_us SERIAL PRIMARY KEY,
                        id_usuario INT NOT NULL,
                        latitud DECIMAL(10, 8) NOT NULL,
                        longitud DECIMAL(11, 8) NOT NULL,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                logger.info("✅ TABLA 'ubicacion_usuario' CREADA EXITOSAMENTE")
            except Exception as create_error:
                logger.error(f"❌ ERROR CREANDO TABLA: {create_error}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Error creando tabla de ubicaciones',
                    'error_code': 'TABLE_CREATION_ERROR'
                }), 500

        # Verificar que el usuario exista
        logger.info(f"🔍 VERIFICANDO EXISTENCIA DE USUARIO ID: {id_usuario}")
        try:
            consultas_usuario = [
                "SELECT id_usuario FROM usuario WHERE id_usuario = %s",
                "SELECT id FROM usuario WHERE id = %s"
            ]
            
            usuario_existe = None
            for consulta in consultas_usuario:
                try:
                    cur.execute(consulta, (id_usuario,))
                    usuario_existe = cur.fetchone()
                    if usuario_existe:
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Consulta usuario falló: {consulta} - {e}")
                    continue
            
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

        # Insertar ubicación
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

        # Obtener estadísticas
        logger.info("📊 OBTENIENDO ESTADÍSTICAS...")
        try:
            cur.execute("SELECT COUNT(*) FROM ubicacion_usuario WHERE id_usuario = %s", (id_usuario,))
            total_ubicaciones_usuario = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM ubicacion_usuario")
            total_ubicaciones = cur.fetchone()[0]
            
            logger.info(f"📊 Estadísticas - Usuario: {total_ubicaciones_usuario}, Total: {total_ubicaciones}")
        except Exception as e:
            logger.warning(f"⚠️ ERROR OBTENIENDO ESTADÍSTICAS: {e}")
            total_ubicaciones_usuario = 1
            total_ubicaciones = 1
        
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
            'estadisticas': {
                'total_ubicaciones_usuario': total_ubicaciones_usuario,
                'total_ubicaciones': total_ubicaciones
            },
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
    """Obtener ONGs - VERSIÓN MEJORADA"""
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
                },
                {
                    'nom_ong': 'Ecología y Desarrollo',
                    'latitud': 20.6668,
                    'longitud': -103.3918,
                    'tipo': 'Protección del medio ambiente',
                    'telefono': '33-9876-5432',
                    'estado': 'Jalisco',
                    'municipio': 'Guadalajara'
                }
            ]
            return jsonify({
                'success': True, 
                'ongs': ongs_ejemplo, 
                'count': len(ongs_ejemplo),
                'message': 'ONGs de ejemplo (sin conexión a BD)'
            })
            
        cur = conn.cursor()
        
        # Intentar obtener ONGs de la base de datos
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

# NO INCLUIR app.run() - RAILWAY USA GUNICORN
logger.info("✅ APLICACIÓN FLASK CARGADA CORRECTAMENTE")

if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(host='0.0.0.0', port=5000, debug=True)
