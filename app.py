from flask import Flask, jsonify, request, g
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback
import sys
from datetime import datetime

# Configurar logging
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

# Configuración Railway
DB_CONFIG = {
    'host': 'tramway.proxy.rlwy.net',
    'port': 31631,
    'database': 'railway',
    'user': 'postgres',
    'password': 'KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ'
}

def get_db_connection():
    """Conecta a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ CONEXIÓN BD EXITOSA")
        return conn
    except Exception as e:
        logger.error(f"❌ ERROR CONEXIÓN BD: {e}")
        return None

def init_database():
    """Inicializar TODAS las tablas según el diagrama"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN COMPLETA DE BD")
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # 1. Crear tabla Municipio (debe ir primero por las FK)
        logger.info("📦 CREANDO TABLA 'municipio'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS municipio (
                id_municipio SERIAL PRIMARY KEY,
                nom_municipio VARCHAR(100) NOT NULL,
                nom_estado VARCHAR(100) NOT NULL
            );
        """)
        
        # 2. Crear tabla Usuario (actualizada según diagrama)
        logger.info("📦 CREANDO TABLA 'usuario'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id_usuario SERIAL PRIMARY KEY,
                correo VARCHAR(100) UNIQUE NOT NULL,
                nombre_Usuario VARCHAR(100) UNIQUE NOT NULL,
                contraseña VARCHAR(100) NOT NULL
            );
        """)
        
        # 3. Crear tabla ONGs (actualizada según diagrama)
        logger.info("📦 CREANDO TABLA 'ongs'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ongs (
                id_ong SERIAL PRIMARY KEY,
                id_municipio INTEGER REFERENCES municipio(id_municipio),
                nom_ong VARCHAR(200) NOT NULL,
                tipo VARCHAR(100),
                latitud DECIMAL(10, 8),
                longitud DECIMAL(11, 8)
            );
        """)
        
        # 4. Crear tabla Ubicacion_Usuario
        logger.info("📦 CREANDO TABLA 'ubicacion_usuario'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ubicacion_usuario (
                id_ubi_us SERIAL PRIMARY KEY,
                id_usuario INTEGER REFERENCES usuario(id_usuario),
                latitud DECIMAL(10, 8),
                longitud DECIMAL(11, 8),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 5. Crear tabla Fecha (estadísticas de delitos)
        logger.info("📦 CREANDO TABLA 'fecha'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fecha (
                id_fecha SERIAL PRIMARY KEY,
                id_municipio INTEGER REFERENCES municipio(id_municipio),
                fecha DATE,
                robos INTEGER DEFAULT 0,
                secuestros INTEGER DEFAULT 0,
                grado VARCHAR(50)
            );
        """)
        
        # 6. Crear tabla Arista (relación usuario-ONG)
        logger.info("📦 CREANDO TABLA 'arista'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arista (
                id_grafo SERIAL PRIMARY KEY,
                id_ubi_us INTEGER REFERENCES ubicacion_usuario(id_ubi_us),
                id_ong INTEGER REFERENCES ongs(id_ong),
                distancia NUMERIC(10, 2),
                fecha DATE DEFAULT CURRENT_DATE
            );
        """)
        
        # Insertar datos de ejemplo en municipio
        logger.info("📝 INSERTANDO DATOS DE EJEMPLO EN MUNICIPIO...")
        cur.execute("""
            INSERT INTO municipio (nom_municipio, nom_estado) VALUES 
            ('Ciudad de México', 'Ciudad de México'),
            ('Guadalajara', 'Jalisco'),
            ('Monterrey', 'Nuevo León')
            ON CONFLICT DO NOTHING;
        """)
        
        # Insertar ONGs de ejemplo
        logger.info("📝 INSERTANDO ONGS DE EJEMPLO...")
        cur.execute("""
            INSERT INTO ongs (id_municipio, nom_ong, tipo, latitud, longitud) VALUES 
            (1, 'Fundación Infantil Mexicana', 'Infantil', 19.4326, -99.1332),
            (2, 'Ecología y Desarrollo', 'Medio Ambiente', 20.6668, -103.3918),
            (3, 'Ayuda Humanitaria Norte', 'Emergencias', 25.6866, -100.3161)
            ON CONFLICT DO NOTHING;
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 INICIALIZACIÓN COMPLETA DE BD EXITOSA")
        return True
        
    except Exception as e:
        logger.error(f"💥 ERROR EN INIT_DATABASE: {e}")
        logger.error(traceback.format_exc())
        return False

@app.before_request
def initialize_on_first_request():
    """Inicialización al primer request"""
    if not hasattr(g, 'db_initialized'):
        logger.info("🚀 INICIANDO APLICACIÓN FLASK - PRIMER REQUEST")
        init_database()
        g.db_initialized = True

@app.route("/")
def home():
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México - ESTRUCTURA COMPLETA",
        "version": "10.0",
        "timestamp": str(datetime.now())
    })

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check completo"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "status": "unhealthy",
                "message": "❌ NO SE PUEDE CONECTAR A LA BASE DE DATOS",
                "database_connection": False
            }), 500
        
        cur = conn.cursor()
        
        # Verificar todas las tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        
        # Contar registros en cada tabla
        stats = {}
        for tabla in ['usuario', 'ongs', 'municipio', 'ubicacion_usuario', 'fecha', 'arista']:
            if tabla in tablas:
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                stats[tabla] = cur.fetchone()[0]
            else:
                stats[tabla] = "tabla_no_existe"
        
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
            "message": f"❌ ERROR: {str(e)}"
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """REGISTRO DE USUARIO - VERSIÓN MEJORADA"""
    logger.info("🎯 INICIANDO REGISTRO DE USUARIO")
    
    try:
        if not request.is_json:
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json'
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS RECIBIDOS: {data}")
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'No se recibieron datos JSON'
            }), 400
        
        # Obtener datos según el diagrama
        nombre_usuario = data.get('username', '').strip()
        correo = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        # Validaciones
        if not nombre_usuario or not password or not correo:
            return jsonify({
                'success': False, 
                'message': 'Usuario, email y contraseña son obligatorios'
            }), 400

        if len(password) < 4:
            return jsonify({
                'success': False, 
                'message': 'La contraseña debe tener al menos 4 caracteres'
            }), 400

        # Conexión a BD
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cur = conn.cursor()
        
        try:
            # Verificar si usuario ya existe
            cur.execute("SELECT id_usuario FROM usuario WHERE nombre_Usuario = %s OR correo = %s", 
                       (nombre_usuario, correo))
            existing_user = cur.fetchone()
            
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': 'El usuario o email ya existen'
                }), 409
            
            # Insertar nuevo usuario según estructura del diagrama
            cur.execute(
                "INSERT INTO usuario (nombre_Usuario, correo, contraseña) VALUES (%s, %s, %s) RETURNING id_usuario", 
                (nombre_usuario, correo, password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ USUARIO REGISTRADO - ID: {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'user_id': user_id,
                'username': nombre_usuario,
                'timestamp': str(datetime.now())
            })
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ ERROR EN REGISTRO: {e}")
            return jsonify({
                'success': False,
                'message': f'Error en el registro: {str(e)}'
            }), 500
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO EN REGISTRO: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error del servidor: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuario - VERSIÓN MEJORADA"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False, 
                'message': 'Datos no proporcionados'
            }), 400
        
        nombre_usuario = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not nombre_usuario or not password:
            return jsonify({
                'success': False, 
                'message': 'Usuario y contraseña requeridos'
            }), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a BD'
            }), 500
            
        cur = conn.cursor()
        
        # Buscar usuario por nombre_usuario según diagrama
        cur.execute("""
            SELECT id_usuario, nombre_Usuario, correo 
            FROM usuario 
            WHERE nombre_Usuario = %s AND contraseña = %s
        """, (nombre_usuario, password))
        
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
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
            return jsonify({
                'success': False, 
                'message': 'Credenciales incorrectas'
            }), 401

    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error del servidor en login'
        }), 500

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener ONGs con información completa según diagrama"""
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
        
        # Consulta mejorada con JOIN según diagrama
        cur.execute("""
            SELECT 
                o.id_ong,
                o.nom_ong,
                o.tipo,
                o.latitud,
                o.longitud,
                m.nom_municipio,
                m.nom_estado
            FROM ongs o
            LEFT JOIN municipio m ON o.id_municipio = m.id_municipio
            WHERE o.latitud IS NOT NULL AND o.longitud IS NOT NULL
        """)
        
        ongs_data = cur.fetchall()
        cur.close()
        conn.close()

        # Convertir a formato JSON
        ongs_list = []
        for ong in ongs_data:
            ongs_list.append({
                'id': ong[0],
                'nombre': ong[1] or 'Sin nombre',
                'tipo': ong[2] or 'Sin tipo',
                'latitud': float(ong[3]) if ong[3] else 0.0,
                'longitud': float(ong[4]) if ong[4] else 0.0,
                'municipio': ong[5] or 'Sin municipio',
                'estado': ong[6] or 'Sin estado'
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

# Nuevos endpoints según el diagrama
@app.route("/api/municipios", methods=['GET'])
def get_municipios():
    """Obtener lista de municipios"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'})
            
        cur = conn.cursor()
        cur.execute("SELECT id_municipio, nom_municipio, nom_estado FROM municipio")
        municipios = cur.fetchall()
        
        result = []
        for m in municipios:
            result.append({
                'id': m[0],
                'municipio': m[1],
                'estado': m[2]
            })
            
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'municipios': result})
        
    except Exception as e:
        logger.error(f"Error obteniendo municipios: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route("/api/ubicacion-usuario", methods=['POST'])
def guardar_ubicacion_usuario():
    """Guardar ubicación del usuario según diagrama"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no proporcionados'})
        
        id_usuario = data.get('id_usuario')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not id_usuario or not latitud or not longitud:
            return jsonify({'success': False, 'message': 'Datos incompletos'})
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'})
            
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ubicacion_usuario (id_usuario, latitud, longitud) 
            VALUES (%s, %s, %s) RETURNING id_ubi_us
        """, (id_usuario, latitud, longitud))
        
        ubicacion_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Ubicación guardada',
            'id_ubicacion': ubicacion_id
        })
        
    except Exception as e:
        logger.error(f"Error guardando ubicación: {e}")
        return jsonify({'success': False, 'message': str(e)})

logger.info("✅ APLICACIÓN FLASK CARGADA CON ESTRUCTURA COMPLETA")
