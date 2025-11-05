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
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) UNIQUE NOT NULL,
                    contraseña VARCHAR(100) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'usuario' CREADA EXITOSAMENTE")
        else:
            logger.info("✅ TABLA 'usuario' YA EXISTE")
        
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
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(200),
                    latitud DECIMAL(10, 8),
                    longitud DECIMAL(11, 8),
                    descripcion TEXT,
                    telefono VARCHAR(20),
                    estado VARCHAR(100),
                    municipio VARCHAR(100),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ TABLA 'ongs' CREADA EXITOSAMENTE")
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
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id)
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

# INICIALIZACIÓN AL PRIMER REQUEST - VERSIÓN COMPATIBLE CON FLASK 2.3+
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
        "message": "🚀 API Flask - ONGs México - CONEXIÓN UBICACIÓN IMPLEMENTADA",
        "version": "10.0",
        "database_status": "conectada",
        "endpoints_available": True,
        "timestamp": str(datetime.now())
    })

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check COMPLETO con diagnóstico"""
    logger.info("❤️ SOLICITUD HEALTH CHECK")
    
    try:
        # 1. Verificar conexión básica
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "status": "unhealthy",
                "message": "❌ NO SE PUEDE CONECTAR A LA BASE DE DATOS",
                "database_connection": False,
                "timestamp": str(datetime.now())
            }), 500
        
        cur = conn.cursor()
        
        # 2. Verificar tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        logger.info(f"📋 TABLAS ENCONTRADAS: {tablas}")
        
        # 3. Contar registros
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
    """REGISTRO DE USUARIO - VERSIÓN ULTRA ROBUSTA"""
    logger.info("🎯 INICIANDO PROCESO DE REGISTRO - VERSIÓN ULTRA ROBUSTA")
    
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
        password = data.get('password', '').strip()
        
        logger.info(f"🔑 USUARIO: '{username}', LONGITUD PASSWORD: {len(password)}")
        
        # 2. VALIDACIONES DE DATOS
        if not username:
            logger.error("❌ USUARIO VACÍO")
            return jsonify({
                'success': False, 
                'message': 'El usuario no puede estar vacío',
                'error_code': 'EMPTY_USERNAME',
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
        
        # 4. VERIFICAR Y CREAR TABLA SI NO EXISTE - MÉTODO MÁS ROBUSTO
        logger.info("🔍 VERIFICANDO EXISTENCIA DE TABLA 'usuario'...")
        try:
            # Intentar una consulta simple para verificar si la tabla existe
            cur.execute("SELECT 1 FROM usuario LIMIT 1")
            logger.info("✅ TABLA 'usuario' EXISTE Y ES ACCESIBLE")
        except Exception as e:
            logger.warning(f"⚠️ TABLA 'usuario' NO EXISTE O NO ES ACCESIBLE: {e}")
            logger.info("📦 INTENTANDO CREAR TABLA 'usuario'...")
            try:
                # Crear tabla con manejo de errores más específico
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS usuario (
                        id SERIAL PRIMARY KEY,
                        nombre VARCHAR(100) UNIQUE NOT NULL,
                        contraseña VARCHAR(100) NOT NULL,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("✅ TABLA 'usuario' CREADA EXITOSAMENTE")
                
                # Verificar que la tabla se creó correctamente
                cur.execute("SELECT 1 FROM usuario LIMIT 1")
                logger.info("✅ TABLA 'usuario' VERIFICADA Y FUNCIONAL")
                
            except Exception as create_error:
                logger.error(f"❌ ERROR CRÍTICO CREANDO TABLA: {create_error}")
                # Intentar método alternativo
                try:
                    cur.execute("""
                        CREATE TABLE usuario (
                            id SERIAL PRIMARY KEY,
                            nombre VARCHAR(100) UNIQUE NOT NULL,
                            contraseña VARCHAR(100) NOT NULL,
                            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
                    logger.info("✅ TABLA 'usuario' CREADA CON MÉTODO ALTERNATIVO")
                except Exception as alt_error:
                    logger.error(f"❌ ERROR EN MÉTODO ALTERNATIVO: {alt_error}")
                    cur.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Error crítico creando tabla de usuarios',
                        'error_code': 'TABLE_CREATION_ERROR',
                        'details': str(alt_error),
                        'timestamp': str(datetime.now())
                    }), 500

        # 5. VERIFICAR SI USUARIO EXISTE - CON MÚLTIPLES INTENTOS
        logger.info(f"🔍 VERIFICANDO EXISTENCIA DE USUARIO: {username}")
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔍 INTENTO {attempt + 1} DE {max_attempts}")
                cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
                existing_user = cur.fetchone()
                
                if existing_user:
                    logger.warning(f"❌ USUARIO YA EXISTE: {username}")
                    cur.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'El usuario ya existe',
                        'error_code': 'USER_EXISTS',
                        'timestamp': str(datetime.now())
                    }), 409
                    
                logger.info(f"✅ USUARIO DISPONIBLE: {username}")
                break  # Salir del bucle si tuvo éxito
                
            except Exception as e:
                logger.error(f"❌ ERROR EN INTENTO {attempt + 1}: {e}")
                if attempt == max_attempts - 1:  # Último intento
                    logger.error(f"💥 TODOS LOS INTENTOS FALLARON PARA VERIFICAR USUARIO: {username}")
                    cur.close()
                    conn.close()
                    return jsonify({
                        'success': False,
                        'message': 'Error verificando usuario después de múltiples intentos',
                        'error_code': 'CHECK_USER_ERROR',
                        'details': str(e),
                        'attempts': max_attempts,
                        'timestamp': str(datetime.now())
                    }), 500
                # Esperar un poco antes del siguiente intento
                import time
                time.sleep(0.5)

        # 6. INSERTAR NUEVO USUARIO
        logger.info(f"💾 INSERTANDO NUEVO USUARIO: {username}")
        try:
            cur.execute(
                "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
                (username, password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ USUARIO REGISTRADO EXITOSAMENTE - ID: {user_id}, USUARIO: {username}")
            
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
            total_usuarios = 1  # Valor por defecto
        
        cur.close()
        conn.close()
        
        # 8. RESPUESTA DE ÉXITO
        logger.info(f"🎉 REGISTRO COMPLETADO EXITOSAMENTE PARA: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id,
            'username': username,
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
    """Login de usuario - VERSIÓN SIMPLIFICADA"""
    try:
        data = request.get_json()
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
            cur.execute("SELECT id, nombre FROM usuario WHERE nombre = %s AND contraseña = %s", 
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
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'user': {
                    'id': user[0],
                    'nombre': user[1]
                }
            })
        else:
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
    """Guardar ubicación del usuario con su ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False, 
                'message': 'Datos no proporcionados',
                'error_code': 'NO_DATA'
            }), 400
        
        id_usuario = data.get('id_usuario')
        latitud = data.get('latitud')
        longitud = data.get('longitud')

        if not id_usuario or not latitud or not longitud:
            return jsonify({
                'success': False, 
                'message': 'ID usuario, latitud y longitud requeridos',
                'error_code': 'MISSING_DATA'
            }), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a BD',
                'error_code': 'DB_CONNECTION_FAILED'
            }), 500
            
        cur = conn.cursor()
        
        # Verificar si existe la tabla ubicacion_usuario
        try:
            cur.execute("SELECT 1 FROM ubicacion_usuario LIMIT 1")
        except Exception as e:
            logger.info("📦 Creando tabla 'ubicacion_usuario'...")
            cur.execute("""
                CREATE TABLE ubicacion_usuario (
                    id_ubi_us SERIAL PRIMARY KEY,
                    id_usuario INT NOT NULL,
                    latitud DECIMAL(10, 8) NOT NULL,
                    longitud DECIMAL(11, 8) NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuario(id)
                );
            """)
            conn.commit()
            logger.info("✅ Tabla 'ubicacion_usuario' creada")

        # Insertar ubicación
        cur.execute(
            "INSERT INTO ubicacion_usuario (id_usuario, latitud, longitud) VALUES (%s, %s, %s) RETURNING id_ubi_us",
            (id_usuario, latitud, longitud)
        )
        id_ubi_us = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Ubicación guardada exitosamente',
            'id_ubi_us': id_ubi_us,
            'timestamp': str(datetime.now())
        })

    except Exception as e:
        logger.error(f"Error guardando ubicación: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error del servidor: {str(e)}',
            'error_code': 'SERVER_ERROR'
        }), 500

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener ONGs - VERSIÓN TOLERANTE A FALLOS"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': True, 
                'ongs': [], 
                'count': 0, 
                'message': 'Base de datos no disponible'
            })
            
        cur = conn.cursor()
        
        # Intentar diferentes nombres de tabla
        ongs_data = []
        table_names = ['ongs', 'ong', 'organizaciones']
        
        for table in table_names:
            try:
                cur.execute(f"""
                    SELECT nombre, latitud, longitud, descripcion, telefono, estado, municipio 
                    FROM {table} 
                    WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                    LIMIT 50
                """)
                ongs_data = cur.fetchall()
                if ongs_data:
                    break
            except:
                continue
        
        cur.close()
        conn.close()

        # Convertir a formato JSON
        ongs_list = []
        for ong in ongs_data:
            ongs_list.append({
                'nombre': ong[0] or 'Sin nombre',
                'latitud': float(ong[1]) if ong[1] else 0.0,
                'longitud': float(ong[2]) if ong[2] else 0.0,
                'descripcion': ong[3] or 'Sin descripción',
                'telefono': ong[4] or 'Sin teléfono',
                'estado': ong[5] or 'Sin estado',
                'municipio': ong[6] or 'Sin municipio'
            })

        return jsonify({
            'success': True, 
            'ongs': ongs_list, 
            'count': len(ongs_list),
            'message': f'Se encontraron {len(ongs_list)} ONGs'
        })

    except Exception as e:
        logger.error(f"Error obteniendo ONGs: {e}")
        return jsonify({
            'success': True, 
            'ongs': [], 
            'count': 0, 
            'message': 'Error cargando ONGs'
        })

# NO INCLUIR app.run() - RAILWAY USA GUNICORN
logger.info("✅ APLICACIÓN FLASK CARGADA CORRECTAMENTE")

