from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback

# Configurar logging más detallado
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- Configuración Railway ---
DB_CONFIG = {
    'host': 'tramway.proxy.rlwy.net',
    'port': 31631,
    'database': 'railway',
    'user': 'postgres',
    'password': 'KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ'
}

def get_db_connection():
    """Conecta a PostgreSQL en Railway"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Conexión a BD exitosa")
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        logger.error(traceback.format_exc())
        raise e

def init_database():
    """Inicializar tablas si no existen"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si la tabla usuario existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuario'
            );
        """)
        tabla_existe = cur.fetchone()[0]
        
        if not tabla_existe:
            logger.info("📦 Creando tabla 'usuario'...")
            cur.execute("""
                CREATE TABLE usuario (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) UNIQUE NOT NULL,
                    contraseña VARCHAR(100) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            logger.info("✅ Tabla 'usuario' creada exitosamente")
        else:
            logger.info("✅ Tabla 'usuario' ya existe")
        
        # Verificar tabla ongs
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ongs'
            );
        """)
        tabla_ongs_existe = cur.fetchone()[0]
        
        if not tabla_ongs_existe:
            logger.info("📦 Creando tabla 'ongs'...")
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
            conn.commit()
            logger.info("✅ Tabla 'ongs' creada exitosamente")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {e}")
        logger.error(traceback.format_exc())
        raise e

# Inicializar al inicio
try:
    init_database()
except Exception as e:
    logger.error(f"Error en inicialización: {e}")

# --- ENDPOINTS ---
@app.route("/")
def home():
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México",
        "version": "2.2",
        "endpoints": {
            "health": "/api/health",
            "login": "/api/auth/login",
            "register": "/api/auth/register", 
            "ongs": "/api/ongs",
            "init_db": "/api/initdb",
            "debug": "/api/debug/db"
        }
    })

@app.route("/api/initdb", methods=['GET'])
def init_db_endpoint():
    """Forzar inicialización de BD"""
    try:
        init_database()
        return jsonify({
            "success": True,
            "message": "✅ Base de datos inicializada correctamente"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"❌ Error: {str(e)}"
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de usuario - CON MEJOR LOGGING"""
    try:
        logger.info("📝 Iniciando proceso de registro...")
        
        data = request.get_json()
        if not data:
            logger.error("❌ No se recibieron datos JSON")
            return jsonify({'success': False, 'message': 'Datos no proporcionados'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        logger.info(f"📝 Datos recibidos - Usuario: '{username}', Password: {'*' * len(password)}")

        if not username:
            logger.error("❌ Usuario vacío")
            return jsonify({'success': False, 'message': 'Usuario requerido'}), 400
            
        if not password:
            logger.error("❌ Password vacío")
            return jsonify({'success': False, 'message': 'Contraseña requerida'}), 400

        if len(password) < 4:
            logger.error("❌ Password demasiado corto")
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 4 caracteres'}), 400

        # Conectar a BD
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si usuario existe
        logger.info(f"🔍 Verificando si usuario existe: {username}")
        cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
        existing_user = cur.fetchone()
        
        if existing_user:
            logger.warning(f"❌ Usuario ya existe: {username}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'El usuario ya existe'
            }), 409

        # Crear nuevo usuario
        logger.info(f"👤 Creando nuevo usuario: {username}")
        cur.execute(
            "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
            (username, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"✅ Usuario creado exitosamente - ID: {user_id}")
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id
        })
        
    except psycopg2.IntegrityError as e:
        logger.error(f"❌ Error de integridad BD: {e}")
        return jsonify({
            'success': False,
            'message': 'El usuario ya existe'
        }), 409
    except psycopg2.Error as e:
        logger.error(f"❌ Error de PostgreSQL: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error de base de datos: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error del servidor: {str(e)}'
        }), 500

@app.route("/api/health", methods=['GET'])
def health_check():
    """Verificar estado del sistema"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tablas = [row[0] for row in cur.fetchall()]
        
        # Contar usuarios
        if 'usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cur.fetchone()[0]
        else:
            total_usuarios = 0
            
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "message": "✅ API funcionando",
            "tablas": tablas,
            "total_usuarios": total_usuarios,
            "tabla_usuario_existe": 'usuario' in tablas
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "message": f"❌ Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
