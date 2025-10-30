from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
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

@app.route("/")
def home():
    return jsonify({"status": "active", "message": "🚀 API DIAGNÓSTICO"})

@app.route("/api/debug/db-test", methods=['GET'])
def debug_db_test():
    """Prueba completa de conexión y tablas"""
    try:
        logger.info("🔍 Iniciando prueba de base de datos...")
        
        # 1. Conectar
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Conexión exitosa")
        
        cur = conn.cursor()
        
        # 2. Verificar tablas existentes
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        logger.info(f"📋 Tablas encontradas: {tablas}")
        
        # 3. Verificar estructura de tabla 'usuario' si existe
        if 'usuario' in tablas:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'usuario'
                ORDER BY ordinal_position
            """)
            columnas = cur.fetchall()
            logger.info(f"📝 Columnas de 'usuario': {columnas}")
            
            # Contar usuarios existentes
            cur.execute("SELECT COUNT(*) FROM usuario")
            count = cur.fetchone()[0]
            logger.info(f"👥 Usuarios en BD: {count}")
        
        # 4. Intentar crear tabla si no existe
        if 'usuario' not in tablas:
            logger.info("📦 Creando tabla 'usuario'...")
            cur.execute("""
                CREATE TABLE usuario (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) UNIQUE NOT NULL,
                    contraseña VARCHAR(100) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("✅ Tabla 'usuario' creada")
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "tablas": tablas,
            "tabla_usuario_existe": 'usuario' in tablas,
            "total_usuarios": count if 'usuario' in tablas else 0
        })
        
    except Exception as e:
        logger.error(f"❌ Error en debug_db_test: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro con diagnóstico completo"""
    logger.info("🎯 INICIANDO REGISTRO - DIAGNÓSTICO")
    
    try:
        # 1. Obtener datos
        data = request.get_json()
        logger.info(f"📨 Datos recibidos: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"🔑 Usuario: '{username}', Password length: {len(password)}")
        
        # 2. Validaciones
        if not username:
            return jsonify({'success': False, 'message': 'Username required'}), 400
        if not password:
            return jsonify({'success': False, 'message': 'Password required'}), 400
        if len(password) < 4:
            return jsonify({'success': False, 'message': 'Password too short'}), 400
        
        # 3. Conectar a BD
        logger.info("🔌 Conectando a BD...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logger.info("✅ Conexión BD exitosa")
        
        # 4. Verificar si usuario existe
        logger.info(f"🔍 Verificando usuario: {username}")
        cur.execute("SELECT id FROM usuario WHERE nombre = %s", (username,))
        existing = cur.fetchone()
        
        if existing:
            logger.warning(f"❌ Usuario ya existe: {username}")
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'User exists'}), 409
        
        # 5. Insertar usuario
        logger.info("💾 Insertando usuario...")
        cur.execute(
            "INSERT INTO usuario (nombre, contraseña) VALUES (%s, %s) RETURNING id", 
            (username, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"✅ USUARIO INSERTADO - ID: {user_id}")
        
        # 6. Verificar que se insertó
        cur.execute("SELECT COUNT(*) FROM usuario")
        total = cur.fetchone()[0]
        logger.info(f"📊 Total usuarios después de insertar: {total}")
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'User registered',
            'user_id': user_id,
            'total_users': total
        })
        
    except psycopg2.IntegrityError as e:
        logger.error(f"❌ Error de integridad: {e}")
        return jsonify({'success': False, 'message': 'User exists'}), 409
    except psycopg2.Error as e:
        logger.error(f"❌ Error PostgreSQL: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Database error: {str(e)}',
            'error_type': 'postgresql_error'
        }), 500
    except Exception as e:
        logger.error(f"💥 Error general: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': f'Server error: {str(e)}',
            'error_type': 'general_error'
        }), 500

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check simplificado"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tablas = [row[0] for row in cur.fetchall()]
        
        total_usuarios = 0
        if 'usuario' in tablas:
            cur.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "tablas": tablas,
            "total_usuarios": total_usuarios
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
