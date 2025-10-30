from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
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
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        raise e

def init_database():
    """Inicializar tablas si no existen"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Crear tabla de usuarios si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL,
                contraseña VARCHAR(100) NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Crear tabla de ONGs si no existe
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
        logger.info("✅ Tablas inicializadas correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando tablas: {e}")

# Inicializar tablas al iniciar la app
init_database()

# --- ENDPOINT PRINCIPAL ---
@app.route("/")
def home():
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México",
        "version": "2.1",
        "endpoints": {
            "health": "/api/health",
            "login": "/api/auth/login",
            "register": "/api/auth/register", 
            "ongs": "/api/ongs",
            "init_db": "/api/initdb",
            "debug": "/api/debug/db"
        }
    })

# --- ENDPOINT PARA INICIALIZAR BD ---
@app.route("/api/initdb", methods=['GET', 'POST'])
def init_db():
    """Forzar inicialización de tablas"""
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

# --- ENDPOINTS DE AUTENTICACIÓN MEJORADOS ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de nuevo usuario - VERSIÓN MEJORADA"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no proporcionados'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        logger.info(f"📝 Intentando registrar usuario: {username}")

        if not username or not password:
            return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400

        if len(password) < 4:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 4 caracteres'}), 400

        if len(username) < 3:
            return jsonify({'success': False, 'message': 'El usuario debe tener al menos 3 caracteres'}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si el usuario ya existe
        try:
            cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
            if cur.fetchone():
                cur.close()
                conn.close()
                logger.warning(f"❌ Usuario ya existe: {username}")
                return jsonify({
                    'success': False,
                    'message': 'El usuario ya existe'
                }), 409  # 409 Conflict
        except Exception as e:
            logger.error(f"❌ Error verificando usuario: {e}")
            # Posiblemente la tabla no existe, intentar crearla
            init_database()
            # Reintentar la verificación
            cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'El usuario ya existe'
                }), 409

        # Crear nuevo usuario
        try:
            cur.execute(
                "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
                (username, password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ Usuario registrado exitosamente: {username} (ID: {user_id})")
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'user_id': user_id
            })
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Error insertando usuario: {e}")
            return jsonify({
                'success': False,
                'message': f'Error creando usuario: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"💥 Error general en registro: {e}")
        return jsonify({
            'success': False,
            'message': 'Error del servidor en el registro'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuario - VERSIÓN MEJORADA"""
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
        cur = conn.cursor()
        
        # Verificar credenciales
        try:
            cur.execute(
                "SELECT id, nombre FROM usuario WHERE nombre = %s AND contraseña = %s", 
                (username, password)
            )
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
                return jsonify({
                    'success': False,
                    'message': 'Credenciales incorrectas'
                }), 401
                
        except Exception as e:
            logger.error(f"❌ Error en consulta de login: {e}")
            return jsonify({
                'success': False,
                'message': 'Error en la base de datos'
            }), 500

    except Exception as e:
        logger.error(f"💥 Error general en login: {e}")
        return jsonify({
            'success': False,
            'message': 'Error del servidor en el login'
        }), 500

# --- ENDPOINTS DE ONGs (mantener igual) ---
@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener todas las ONGs"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT nombre, latitud, longitud, descripcion, telefono, estado, municipio 
            FROM ongs 
            WHERE latitud IS NOT NULL AND longitud IS NOT NULL
            LIMIT 50
        """)
        ongs_data = cur.fetchall()

        cur.close()
        conn.close()

        # Convertir a JSON
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
            'count': len(ongs_list)
        })

    except Exception as e:
        logger.error(f"💥 Error obteniendo ONGs: {e}")
        # Si la tabla no existe, devolver lista vacía
        return jsonify({
            'success': True,
            'ongs': [],
            'count': 0,
            'message': 'No hay ONGs registradas aún'
        })

# --- ENDPOINT DE SALUD MEJORADO ---
@app.route("/api/health", methods=['GET'])
def health_check():
    """Verifica que la API y base de datos estén funcionando"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('usuario', 'ongs')
        """)
        tablas = cur.fetchall()
        
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        
        # Contar usuarios
        cur.execute("SELECT COUNT(*) FROM usuario")
        total_usuarios = cur.fetchone()[0]
        
        # Contar ONGs
        cur.execute("SELECT COUNT(*) FROM ongs")
        total_ongs = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "message": "✅ API y base de datos conectadas",
            "database": "PostgreSQL en Railway",
            "database_version": db_version[0] if db_version else "unknown",
            "tablas_existen": len(tablas) == 2,
            "total_usuarios": total_usuarios,
            "total_ongs": total_ongs
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "message": f"❌ Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
