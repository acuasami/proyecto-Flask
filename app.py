from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        logger.info("✅ Conexión a BD exitosa")
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        return None

def init_database():
    """Inicializar tablas si no existen"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # Crear tabla usuario si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL,
                contraseña VARCHAR(100) NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Crear tabla ongs si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ongs (
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
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ Tablas inicializadas/verificadas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en init_database: {e}")
        return False

# Inicializar BD al inicio
init_database()

@app.route("/")
def home():
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México",
        "version": "5.0",
        "database": "conectada",
        "endpoints": {
            "health": "/api/health",
            "initdb": "/api/initdb", 
            "register": "/api/auth/register",
            "login": "/api/auth/login",
            "ongs": "/api/ongs"
        }
    })

@app.route("/api/initdb", methods=['GET'])
def init_db():
    """Forzar inicialización de BD"""
    success = init_database()
    if success:
        return jsonify({"success": True, "message": "✅ BD inicializada"})
    else:
        return jsonify({"success": False, "message": "❌ Error inicializando BD"}), 500

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check completo"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "❌ No se pudo conectar a BD"}), 500
            
        cur = conn.cursor()
        
        # Verificar tablas existentes
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tablas = [row[0] for row in cur.fetchall()]
        
        # Contar usuarios
        total_usuarios = 0
        if 'usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cur.fetchone()[0]
        
        # Contar ONGs
        total_ongs = 0
        if 'ongs' in tablas:
            cur.execute("SELECT COUNT(*) FROM ongs")
            total_ongs = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "message": "✅ API y BD funcionando",
            "tablas": tablas,
            "total_usuarios": total_usuarios,
            "total_ongs": total_ongs,
            "tabla_usuario_existe": 'usuario' in tablas,
            "tabla_ongs_existe": 'ongs' in tablas
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de usuario - VERSIÓN ROBUSTA"""
    logger.info("🎯 INICIANDO PROCESO DE REGISTRO")
    
    try:
        # 1. Obtener y validar datos
        data = request.get_json()
        logger.info(f"📨 Datos recibidos: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"👤 Usuario: '{username}', Longitud password: {len(password)}")
        
        # Validaciones
        if not username:
            return jsonify({'success': False, 'message': 'Usuario requerido'}), 400
        if not password:
            return jsonify({'success': False, 'message': 'Contraseña requerida'}), 400
        if len(password) < 4:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 4 caracteres'}), 400
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'El usuario debe tener al menos 3 caracteres'}), 400

        # 2. Conectar a BD
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cur = conn.cursor()
        
        # 3. Verificar si usuario existe
        logger.info(f"🔍 Verificando existencia de usuario: {username}")
        cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
        existing_user = cur.fetchone()
        
        if existing_user:
            logger.warning(f"❌ Usuario ya existe: {username}")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'El usuario ya existe'}), 409
        
        # 4. Insertar nuevo usuario
        logger.info(f"💾 Insertando nuevo usuario: {username}")
        cur.execute(
            "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
            (username, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"✅ USUARIO REGISTRADO EXITOSAMENTE - ID: {user_id}")
        
        # 5. Verificar inserción
        cur.execute("SELECT COUNT(*) FROM usuario")
        total_usuarios = cur.fetchone()[0]
        logger.info(f"📊 Total de usuarios en BD: {total_usuarios}")
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id,
            'total_usuarios': total_usuarios
        })
        
    except psycopg2.IntegrityError:
        logger.error("❌ Error de integridad - usuario duplicado")
        return jsonify({'success': False, 'message': 'El usuario ya existe'}), 409
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO EN REGISTRO: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Error del servidor: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuario"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no proporcionados'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        logger.info(f"🔐 Intentando login para: {username}")

        if not username or not password:
            return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a BD'}), 500
            
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM usuario WHERE nombre = %s AND contraseña = %s", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            logger.info(f"✅ Login exitoso para: {username}")
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'user': {
                    'id': user[0],
                    'nombre': user[1]
                }
            })
        else:
            logger.warning(f"❌ Credenciales incorrectas para: {username}")
            return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401

    except Exception as e:
        logger.error(f"💥 Error en login: {e}")
        return jsonify({'success': False, 'message': 'Error del servidor'}), 500

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener todas las ONGs"""
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
                    logger.info(f"✅ Tabla encontrada: {table}")
                    break
            except Exception as e:
                logger.warning(f"Tabla {table} no encontrada: {e}")
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

        logger.info(f"📊 Se enviaron {len(ongs_list)} ONGs")
        
        return jsonify({
            'success': True, 
            'ongs': ongs_list, 
            'count': len(ongs_list),
            'message': f'Se encontraron {len(ongs_list)} ONGs'
        })

    except Exception as e:
        logger.error(f"💥 Error obteniendo ONGs: {e}")
        return jsonify({
            'success': True, 
            'ongs': [], 
            'count': 0, 
            'message': 'Error cargando ONGs'
        })

@app.route("/api/debug/db", methods=['GET'])
def debug_db():
    """Diagnóstico de la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a BD"}), 500
            
        cur = conn.cursor()
        
        # Ver tablas existentes
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        
        # Contar registros en cada tabla
        counts = {}
        for tabla in tablas:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                counts[tabla] = cur.fetchone()[0]
            except:
                counts[tabla] = "error"
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "tablas": tablas,
            "conteos": counts,
            "total_tablas": len(tablas)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NO incluyas app.run() - Railway usa Gunicorn
