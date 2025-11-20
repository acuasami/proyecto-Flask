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
    """Conecta a PostgreSQL - VERSIÓN CORREGIDA CON TU URL"""
    try:
        logger.info("🔍 INICIANDO CONEXIÓN A BD...")
        
        # PRIMERO: Variable de entorno de Railway
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            logger.info("🔗 Usando DATABASE_URL de Railway...")
            try:
                conn = psycopg2.connect(database_url)
                logger.info("✅ CONEXIÓN EXITOSA CON DATABASE_URL")
                return conn
            except Exception as e:
                logger.error(f"❌ Error con DATABASE_URL: {e}")
        
        # SEGUNDO: Fallback con TU URL específica
        logger.info("🔗 Usando URL específica de tu base de datos...")
        try:
            conn = psycopg2.connect(
                "postgresql://postgres:KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ@switchyard.proxy.rlwy.net:13155/railway"
            )
            logger.info("✅ CONEXIÓN EXITOSA CON URL ESPECÍFICA")
            return conn
        except Exception as e:
            logger.error(f"❌ Error con URL específica: {e}")
        
        logger.error("💥 TODOS LOS MÉTODOS DE CONEXIÓN FALLARON")
        return None
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO EN get_db_connection: {e}")
        return None

def init_database():
    """Inicializar tablas EXACTAMENTE como en el esquema PDF - VERSIÓN MEJORADA CON DIAGNÓSTICO"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN DE BD - VERSIÓN DIAGNÓSTICO")
    
    try:
        logger.info("🔍 PASO 1: CONECTANDO A LA BASE DE DATOS...")
        conn = get_db_connection()
        if not conn:
            logger.error("❌ FALLO CRÍTICO: No se pudo conectar a la base de datos")
            return False
            
        cur = conn.cursor()
        logger.info("✅ Conexión a BD establecida correctamente")
        
        # Verificar qué tablas existen actualmente
        logger.info("🔍 PASO 2: VERIFICANDO TABLAS EXISTENTES...")
        try:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tablas_existentes = [row[0] for row in cur.fetchall()]
            logger.info(f"📋 Tablas existentes: {tablas_existentes}")
        except Exception as e:
            logger.error(f"❌ Error al verificar tablas existentes: {e}")
            tablas_existentes = []

        # 1. TABLA USUARIO
        logger.info("🔍 PASO 3: VERIFICANDO TABLA 'usuario'...")
        try:
            if 'usuario' not in tablas_existentes:
                logger.info("📦 Creando tabla 'usuario'...")
                cur.execute("""
                    CREATE TABLE usuario (
                        id_usuario SERIAL PRIMARY KEY,
                        correo VARCHAR(255) NOT NULL,
                        nombre_Usuario VARCHAR(100) NOT NULL,
                        contraseña VARCHAR(255) NOT NULL
                    );
                """)
                logger.info("✅ Tabla 'usuario' creada exitosamente")
            else:
                logger.info("✅ Tabla 'usuario' ya existe")
        except Exception as e:
            logger.error(f"❌ Error con tabla 'usuario': {e}")
            conn.rollback()
            return False

        # 2. TABLA MUNICIPIO
        logger.info("🔍 PASO 4: VERIFICANDO TABLA 'municipio'...")
        try:
            if 'municipio' not in tablas_existentes:
                logger.info("📦 Creando tabla 'municipio'...")
                cur.execute("""
                    CREATE TABLE municipio (
                        id_municipio SERIAL PRIMARY KEY,
                        nom_municipio VARCHAR(100) NOT NULL,
                        nom_estado VARCHAR(100) NOT NULL
                    );
                """)
                logger.info("✅ Tabla 'municipio' creada exitosamente")
                
                # Insertar municipios de ejemplo
                logger.info("📝 Insertando municipios de ejemplo...")
                municipios_ejemplo = [
                    ('Ciudad de México', 'CDMX'),
                    ('Guadalajara', 'Jalisco'),
                    ('Monterrey', 'Nuevo León')
                ]
                
                for municipio, estado in municipios_ejemplo:
                    cur.execute(
                        "INSERT INTO municipio (nom_municipio, nom_estado) VALUES (%s, %s)",
                        (municipio, estado)
                    )
                logger.info("✅ Municipios de ejemplo insertados")
            else:
                logger.info("✅ Tabla 'municipio' ya existe")
        except Exception as e:
            logger.error(f"❌ Error con tabla 'municipio': {e}")
            conn.rollback()
            return False

        # 3. TABLA ONGS
        logger.info("🔍 PASO 5: VERIFICANDO TABLA 'ongs'...")
        try:
            if 'ongs' not in tablas_existentes:
                logger.info("📦 Creando tabla 'ongs'...")
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
                logger.info("✅ Tabla 'ongs' creada exitosamente")
                
                # Insertar ONGs de ejemplo
                logger.info("📝 Insertando ONGs de ejemplo...")
                ongs_ejemplo = [
                    (1, 'Fundación Infantil Mexicana', 'Ayuda a niños', 19.4326, -99.1332),
                    (2, 'Ecología y Desarrollo', 'Protección ambiental', 20.6668, -103.3918)
                ]
                
                for id_municipio, nombre, tipo, lat, lng in ongs_ejemplo:
                    cur.execute("""
                        INSERT INTO ongs (id_municipio, nom_ong, tipo, latitud, longitud) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id_municipio, nombre, tipo, lat, lng))
                logger.info("✅ ONGs de ejemplo insertadas")
            else:
                logger.info("✅ Tabla 'ongs' ya existe")
        except Exception as e:
            logger.error(f"❌ Error con tabla 'ongs': {e}")
            conn.rollback()
            return False

        # 4. TABLA UBICACION_USUARIO
        logger.info("🔍 PASO 6: VERIFICANDO TABLA 'ubicacion_usuario'...")
        try:
            if 'ubicacion_usuario' not in tablas_existentes:
                logger.info("📦 Creando tabla 'ubicacion_usuario'...")
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
                logger.info("✅ Tabla 'ubicacion_usuario' creada exitosamente")
            else:
                logger.info("✅ Tabla 'ubicacion_usuario' ya existe")
        except Exception as e:
            logger.error(f"❌ Error con tabla 'ubicacion_usuario': {e}")
            conn.rollback()
            return False

        # 5. TABLA FECHA (opcional - puede omitirse si falla)
        logger.info("🔍 PASO 7: VERIFICANDO TABLA 'fecha'...")
        try:
            if 'fecha' not in tablas_existentes:
                logger.info("📦 Creando tabla 'fecha'...")
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
                logger.info("✅ Tabla 'fecha' creada exitosamente")
            else:
                logger.info("✅ Tabla 'fecha' ya existe")
        except Exception as e:
            logger.warning(f"⚠️ Error con tabla 'fecha' (omitible): {e}")
            # No hacemos rollback porque esta tabla es opcional

        # 6. TABLA ARISTA (opcional - puede omitirse si falla)
        logger.info("🔍 PASO 8: VERIFICANDO TABLA 'arista'...")
        try:
            if 'arista' not in tablas_existentes:
                logger.info("📦 Creando tabla 'arista'...")
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
                logger.info("✅ Tabla 'arista' creada exitosamente")
            else:
                logger.info("✅ Tabla 'arista' ya existe")
        except Exception as e:
            logger.warning(f"⚠️ Error con tabla 'arista' (omitible): {e}")
            # No hacemos rollback porque esta tabla es opcional

        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("🎉 INICIALIZACIÓN DE BD COMPLETADA EXITOSAMENTE")
        return True
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO EN INIT_DATABASE: {e}")
        logger.error(f"🔍 Stack trace completo: {traceback.format_exc()}")
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
        "version": "4.0",
        "database_status": "conectada",
        "timestamp": str(datetime.now())
    })

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check optimizado para Railway"""
    logger.info("❤️ SOLICITUD HEALTH CHECK - RAILWAY")
    
    try:
        # Verificar conexión usando TU URL específica
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "status": "unhealthy",
                "message": "❌ No se pudo conectar a la base de datos",
                "database_connection": False,
                "timestamp": str(datetime.now())
            }), 500
        
        cur = conn.cursor()
        
        # Verificar tablas esenciales
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tablas = [row[0] for row in cur.fetchall()]
        
        # Verificar tablas esenciales según esquema PDF
        tablas_esenciales = ['usuario', 'ongs', 'municipio', 'ubicacion_usuario']
        tablas_faltantes = [tabla for tabla in tablas_esenciales if tabla not in tablas]
        
        # Estadísticas básicas
        stats = {}
        for tabla in tablas_esenciales:
            if tabla in tablas:
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                stats[f'total_{tabla}'] = cur.fetchone()[0]
            else:
                stats[f'total_{tabla}'] = "no_existe"
        
        cur.close()
        conn.close()
        
        # Determinar estado
        if not tablas_faltantes:
            estado = "healthy"
            mensaje = "✅ SISTEMA OPERATIVO - ESQUEMA PDF"
        else:
            estado = "degraded"
            mensaje = f"⚠️ SISTEMA DEGRADADO - Faltan: {tablas_faltantes}"
        
        return jsonify({
            "status": estado,
            "message": mensaje,
            "database_connection": True,
            "connection_type": "DATABASE_URL (privada)",
            "tablas_esenciales": tablas_esenciales,
            "tablas_faltantes": tablas_faltantes,
            "estadisticas": stats,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"💥 ERROR EN HEALTH CHECK: {e}")
        return jsonify({
            "status": "error",
            "message": f"❌ ERROR: {str(e)}",
            "database_connection": False,
            "timestamp": str(datetime.now())
        }), 500

@app.route("/api/verificar-conexion", methods=['GET'])
def verificar_conexion():
    """Verificar específicamente la conexión a la base de datos"""
    logger.info("🔍 VERIFICANDO CONEXIÓN A BD...")
    
    resultado = {
        "timestamp": str(datetime.now()),
        "metodos_intentados": [],
        "conexion_exitosa": False,
        "url_utilizada": None,
        "error": None
    }
    
    # Método 1: DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        resultado["metodos_intentados"].append("DATABASE_URL (privada)")
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            resultado["conexion_exitosa"] = True
            resultado["url_utilizada"] = "DATABASE_URL (privada)"
            logger.info("✅ VERIFICACIÓN: Conexión exitosa con DATABASE_URL")
            return jsonify(resultado)
        except Exception as e:
            resultado["error"] = f"DATABASE_URL falló: {str(e)}"
            logger.error(f"❌ DATABASE_URL falló: {e}")
    
    # Método 2: URL específica
    resultado["metodos_intentados"].append("URL específica")
    try:
        conn = psycopg2.connect(
            "postgresql://postgres:KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ@switchyard.proxy.rlwy.net:13155/railway"
        )
        conn.close()
        resultado["conexion_exitosa"] = True
        resultado["url_utilizada"] = "URL específica"
        logger.info("✅ VERIFICACIÓN: Conexión exitosa con URL específica")
        return jsonify(resultado)
    except Exception as e:
        resultado["error"] = f"URL específica falló: {str(e)}"
        logger.error(f"❌ URL específica falló: {e}")
    
    return jsonify(resultado), 500

@app.route("/api/debug-connection", methods=['GET'])
def debug_connection():
    """Debug específico para tu base de datos"""
    try:
        # Conexión directa con TU URL
        conn = psycopg2.connect(
            "postgresql://postgres:KAGJhRklTcsevGqKEgCNPfmdDiGzsLyQ@switchyard.proxy.rlwy.net:13155/railway"
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version(), current_database(), current_user")
        db_info = cur.fetchone()
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "database_version": db_info[0],
            "database_name": db_info[1],
            "current_user": db_info[2],
            "tables": tables,
            "message": "✅ CONEXIÓN EXITOSA A TU BD"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Error de conexión: {str(e)}",
            "timestamp": str(datetime.now())
        }), 500

@app.route("/api/info-variables", methods=['GET'])
def info_variables():
    """Mostrar información sobre las variables de entorno (sin exponer contraseñas)"""
    database_url = os.environ.get('DATABASE_URL')
    
    info = {
        "timestamp": str(datetime.now()),
        "variables": {
            "DATABASE_URL_existe": bool(database_url),
            "DATABASE_URL_host": None,
        },
        "recomendacion": "Usar DATABASE_URL para evitar cargos por egreso"
    }
    
    if database_url:
        # Extraer host de forma segura
        if "@" in database_url and ":" in database_url:
            host_part = database_url.split("@")[1].split(":")[0]
            info["variables"]["DATABASE_URL_host"] = host_part
    
    return jsonify(info)

@app.route("/api/diagnostico-bd", methods=['GET'])
def diagnostico_bd():
    """Diagnóstico completo de la base de datos"""
    logger.info("🔍 INICIANDO DIAGNÓSTICO COMPLETO DE BD")
    
    diagnostico = {
        "timestamp": str(datetime.now()),
        "conexion": None,
        "tablas_existentes": [],
        "estructura_tablas": {},
        "errores": [],
        "recomendaciones": []
    }
    
    try:
        # 1. Verificar conexión
        conn = get_db_connection()
        if not conn:
            diagnostico["conexion"] = "❌ FALLIDA"
            diagnostico["errores"].append("No se pudo conectar a la base de datos")
            return jsonify(diagnostico)
        
        diagnostico["conexion"] = "✅ EXITOSA"
        cur = conn.cursor()
        
        # 2. Verificar tablas existentes
        try:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tablas = [row[0] for row in cur.fetchall()]
            diagnostico["tablas_existentes"] = tablas
        except Exception as e:
            diagnostico["errores"].append(f"Error al listar tablas: {str(e)}")
        
        # 3. Verificar estructura de tablas esenciales
        tablas_esenciales = ['usuario', 'municipio', 'ongs', 'ubicacion_usuario']
        for tabla in tablas_esenciales:
            try:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (tabla,))
                columnas = cur.fetchall()
                diagnostico["estructura_tablas"][tabla] = [
                    {"nombre": col[0], "tipo": col[1], "nulable": col[2]} 
                    for col in columnas
                ]
            except Exception as e:
                diagnostico["estructura_tablas"][tabla] = f"Error: {str(e)}"
        
        # 4. Verificar datos de ejemplo
        try:
            cur.execute("SELECT COUNT(*) FROM municipio")
            count_municipios = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ongs")
            count_ongs = cur.fetchone()[0]
            
            diagnostico["datos_ejemplo"] = {
                "municipios": count_municipios,
                "ongs": count_ongs
            }
        except Exception as e:
            diagnostico["errores"].append(f"Error contando datos: {str(e)}")
        
        cur.close()
        conn.close()
        
        # 5. Generar recomendaciones
        tablas_faltantes = [tabla for tabla in tablas_esenciales if tabla not in diagnostico["tablas_existentes"]]
        
        if tablas_faltantes:
            diagnostico["recomendaciones"].append(f"Faltan tablas: {tablas_faltantes}. Ejecuta /api/initdb")
        else:
            diagnostico["recomendaciones"].append("✅ Todas las tablas esenciales existen")
        
        if diagnostico["conexion"] == "✅ EXITOSA" and not tablas_faltantes:
            diagnostico["estado"] = "✅ SALUDABLE"
        else:
            diagnostico["estado"] = "❌ CON PROBLEMAS"
        
        return jsonify(diagnostico)
        
    except Exception as e:
        logger.error(f"💥 Error en diagnóstico BD: {e}")
        return jsonify({
            "error": f"Error en diagnóstico: {str(e)}",
            "timestamp": str(datetime.now())
        }), 500

@app.route("/api/reset-bd", methods=['POST'])
def reset_bd():
    """Eliminar y recrear todas las tablas (SOLO PARA DESARROLLO)"""
    logger.info("🔄 SOLICITUD DE RESET COMPLETO DE BD")
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "message": "❌ No se pudo conectar a la base de datos"
            }), 500
            
        cur = conn.cursor()
        
        # Eliminar tablas en orden inverso (por dependencias de FK)
        tablas = ['arista', 'fecha', 'ubicacion_usuario', 'ongs', 'municipio', 'usuario']
        
        for tabla in tablas:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
                logger.info(f"✅ Tabla {tabla} eliminada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar tabla {tabla}: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ Reset de BD completado, ahora ejecuta /api/initdb")
        
        return jsonify({
            "success": True,
            "message": "✅ Base de datos reseteada. Ahora ejecuta /api/initdb para recrear las tablas."
        })
        
    except Exception as e:
        logger.error(f"💥 Error en reset BD: {e}")
        return jsonify({
            "success": False,
            "message": f"❌ Error reseteando BD: {str(e)}"
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
