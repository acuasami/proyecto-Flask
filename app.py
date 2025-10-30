from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    """Inicializar tablas"""
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
                municipio VARCHAR(100)
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

# Inicializar al inicio
init_database()

@app.route("/")
def home():
    return jsonify({
        "status": "active", 
        "message": "🚀 API Flask - ONGs México",
        "version": "3.0"
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
    """Verificar estado"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "❌ No se pudo conectar a BD"}), 500
            
        cur = conn.cursor()
        
        # Verificar tablas
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tablas = [row[0] for row in cur.fetchall()]
        
        # Contar usuarios
        total_usuarios = 0
        if 'usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "tablas": tablas,
            "total_usuarios": total_usuarios,
            "tabla_usuario_existe": 'usuario' in tablas
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro SIMPLIFICADO y ROBUSTO"""
    logger.info("=== INICIANDO REGISTRO ===")
    
    try:
        # 1. Obtener datos
        data = request.get_json()
        logger.info(f"Datos recibidos: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"Usuario: '{username}', Password: {'*' * len(password)}")
        
        # 2. Validaciones básicas
        if not username or not password:
            return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400
        
        if len(password) < 4:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 4 caracteres'}), 400
        
        # 3. Conectar a BD
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cur = conn.cursor()
        
        # 4. Verificar si usuario existe
        logger.info("Verificando si usuario existe...")
        cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'El usuario ya existe'}), 409
        
        # 5. Insertar nuevo usuario
        logger.info("Insertando nuevo usuario...")
        cur.execute(
            "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
            (username, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"✅ USUARIO CREADO - ID: {user_id}")
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id
        })
        
    except psycopg2.IntegrityError:
        logger.error("Error de integridad - usuario duplicado")
        return jsonify({'success': False, 'message': 'El usuario ya existe'}), 409
    except Exception as e:
        logger.error(f"💥 ERROR GENERAL: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Error del servidor: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login SIMPLIFICADO"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no proporcionados'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

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
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'user': {'id': user[0], 'nombre': user[1]}
            })
        else:
            return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401

    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({'success': False, 'message': 'Error del servidor'}), 500

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener ONGs"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cur = conn.cursor()
        cur.execute("SELECT nombre, latitud, longitud, descripcion, telefono, estado, municipio FROM ongs")
        ongs_data = cur.fetchall()
        cur.close()
        conn.close()

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

        return jsonify({'success': True, 'ongs': ongs_list, 'count': len(ongs_list)})

    except Exception as e:
        logger.error(f"Error obteniendo ONGs: {e}")
        return jsonify({'success': False, 'message': 'Error obteniendo ONGs'}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
