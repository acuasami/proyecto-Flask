from flask import Flask, jsonify, request, g
from flask_cors import CORS
import psycopg2
import os
import logging
import traceback
import sys
from datetime import datetime
import math

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
    """Inicializar tablas"""
    logger.info("🔄 INICIANDO INICIALIZACIÓN DE BD")
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ FALLO CRÍTICO: No se pudo conectar a la base de datos")
            return False
            
        cur = conn.cursor()
        
        # Verificar tablas existentes
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

        # 2. TABLA MUNICIPIO
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

        # 3. TABLA ONGS
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

        # 4. TABLA UBICACION_USUARIO
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
    """Endpoint raíz - ACTUALIZADO CON RUTAS PARA MIGRANTES"""
    return jsonify({
        "message": "🚀 Servidor de Rutas para Migrantes - ONG Finder",
        "version": "2.0",
        "endpoints": {
            "calcular_ruta": "POST /calcular-ruta",
            "health": "GET /health", 
            "info": "GET /",
            "mapa": "GET /mapa?lat=xx.xx&lon=xx.xx&id_usuario=xx",
            "ongs": "GET /api/ongs",
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login"
        },
        "usage": {
            "calcular_ruta": "Envía JSON con {lat: xx.xx, lon: xx.xx}",
            "response": "Devuelve HTML del mapa interactivo con rutas"
        }
    })

@app.route("/api/health", methods=['GET'])
def health_check():
    """Health check optimizado para Railway"""
    logger.info("❤️ SOLICITUD HEALTH CHECK")
    
    try:
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
        
        # Verificar tablas esenciales
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
            mensaje = "✅ SISTEMA OPERATIVO - RUTAS PARA MIGRANTES"
        else:
            estado = "degraded"
            mensaje = f"⚠️ SISTEMA DEGRADADO - Faltan: {tablas_faltantes}"
        
        return jsonify({
            "status": estado,
            "message": mensaje,
            "database_connection": True,
            "connection_type": "DATABASE_URL",
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

@app.route('/calcular-ruta', methods=['POST'])
def calcular_ruta():
    """🆕 CALCULAR RUTA A ONGs CERCANAS - NUEVO ENDPOINT"""
    try:
        logger.info("🗺️ SOLICITUD DE CÁLCULO DE RUTA RECIBIDA")
        
        if not request.is_json:
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS RUTA RECIBIDOS: {data}")
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'No se recibieron datos JSON',
                'error_code': 'NO_DATA'
            }), 400
        
        lat = data.get('lat')
        lon = data.get('lon')

        if lat is None or lon is None:
            return jsonify({
                'success': False, 
                'message': 'Latitud y longitud requeridos',
                'error_code': 'MISSING_COORDINATES'
            }), 400

        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError) as e:
            logger.error(f"❌ ERROR EN TIPOS DE DATOS: {e}")
            return jsonify({
                'success': False, 
                'message': 'Latitud y longitud deben ser números',
                'error_code': 'INVALID_COORDINATES'
            }), 400

        # Obtener ONGs de la base de datos
        conn = get_db_connection()
        ongs_list = []
        
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT o.id_ong, o.nom_ong, o.tipo, o.latitud, o.longitud, 
                           m.nom_municipio, m.nom_estado
                    FROM ongs o
                    LEFT JOIN municipio m ON o.id_municipio = m.id_municipio
                    WHERE o.latitud IS NOT NULL AND o.longitud IS NOT NULL
                    LIMIT 50
                """)
                ongs_data = cur.fetchall()
                
                for ong in ongs_data:
                    ong_lat = float(ong[3]) if ong[3] else 0.0
                    ong_lon = float(ong[4]) if ong[4] else 0.0
                    
                    # Calcular distancia (fórmula haversine simplificada)
                    distancia = calcular_distancia(lat, lon, ong_lat, ong_lon)
                    
                    ongs_list.append({
                        'id': ong[0],
                        'nombre': ong[1],
                        'tipo': ong[2],
                        'lat': ong_lat,
                        'lon': ong_lon,
                        'municipio': ong[5],
                        'estado': ong[6],
                        'distancia_km': round(distancia, 2)
                    })
                    
                # Ordenar por distancia
                ongs_list.sort(key=lambda x: x['distancia_km'])
                    
            except Exception as e:
                logger.error(f"Error obteniendo ONGs para ruta: {e}")
            finally:
                cur.close()
                conn.close()
        
        # Generar HTML del mapa con rutas
        html_content = generar_mapa_con_rutas(lat, lon, ongs_list[:10])  # Top 10 más cercanas
        return html_content
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint /calcular-ruta: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error crítico del servidor: {str(e)}',
            'error_code': 'UNHANDLED_ERROR'
        }), 500

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcular distancia entre dos puntos usando fórmula haversine"""
    # Radio de la Tierra en kilómetros
    R = 6371.0
    
    # Convertir grados a radianes
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferencia entre coordenadas
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distancia = R * c
    return distancia

def generar_mapa_con_rutas(lat_usuario, lon_usuario, ongs_list):
    """Generar HTML del mapa con rutas a ONGs cercanas"""
    
    # Generar JavaScript para los marcadores y rutas
    marcadores_js = ""
    rutas_js = ""
    
    for i, ong in enumerate(ongs_list):
        color = get_color_by_index(i)
        marcadores_js += f"""
            // Marcador de {ong['nombre']}
            var marker{i} = L.marker([{ong['lat']}, {ong['lon']}])
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px">
                        <h4>🏥 ${ong['nombre']}</h4>
                        <p><strong>Tipo:</strong> ${ong['tipo']}</p>
                        <p><strong>Ubicación:</strong> ${ong['municipio']}, ${ong['estado']}</p>
                        <p><strong>Distancia:</strong> ${ong['distancia_km']} km</p>
                        <button onclick="calcularRutaEspecifica({ong['lat']}, {ong['lon']})" 
                                style="background: {color}; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                            🗺️ Ver Ruta
                        </button>
                    </div>
                `);
        """
        
        rutas_js += f"""
            // Ruta a {ong['nombre']}
            var polyline{i} = L.polyline(
                [[{lat_usuario}, {lon_usuario}], [{ong['lat']}, {ong['lon']}]],
                {{
                    color: '{color}',
                    weight: 4,
                    opacity: 0.7,
                    dashArray: '10, 10'
                }}
            ).addTo(map);
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🗺️ Rutas a ONGs Cercanas</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
            #map {{ height: 100vh; width: 100%; }}
            .info {{ 
                position: absolute; 
                top: 10px; 
                left: 10px; 
                background: white; 
                padding: 15px; 
                border-radius: 8px;
                z-index: 1000;
                max-width: 350px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }}
            .ruta-item {{ 
                margin: 5px 0; 
                padding: 8px; 
                border-left: 4px solid #007bff;
                background: #f8f9fa;
            }}
            .user-marker {{ color: #007bff; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="info">
            <h3 class="user-marker">📍 Tu Ubicación</h3>
            <p><strong>Coordenadas:</strong> {lat_usuario:.6f}, {lon_usuario:.6f}</p>
            <p><strong>ONGs cercanas encontradas:</strong> {len(ongs_list)}</p>
            
            <div style="max-height: 200px; overflow-y: auto; margin-top: 10px;">
                <h4>🗺️ Rutas Disponibles:</h4>
                {"".join([f'''
                <div class="ruta-item">
                    <strong>{ong["nombre"]}</strong><br>
                    <small>📍 {ong["distancia_km"]} km - {ong["tipo"]}</small>
                </div>
                ''' for ong in ongs_list])}
            </div>
            
            <p><small>💡 Las rutas se muestran como líneas rectas de referencia</small></p>
        </div>
        <div id="map"></div>
        
        <script>
            // Inicializar mapa
            var map = L.map('map').setView([{lat_usuario}, {lon_usuario}], 12);
            
            // Capa de tiles
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }}).addTo(map);
            
            // Marcador del usuario
            var userIcon = L.divIcon({{
                className: 'user-marker',
                html: '📍<div style="font-size: 12px; margin-top: 5px;">Tú</div>',
                iconSize: [30, 40],
                iconAnchor: [15, 40]
            }});
            
            L.marker([{lat_usuario}, {lon_usuario}], {{icon: userIcon}})
                .addTo(map)
                .bindPopup('<b>📍 Tu Ubicación</b><br>Coordenadas: {lat_usuario:.6f}, {lon_usuario:.6f}')
                .openPopup();
            
            // Marcadores de ONGs
            {marcadores_js}
            
            // Rutas a ONGs
            {rutas_js}
            
            // Función para calcular ruta específica
            function calcularRutaEspecifica(latOng, lonOng) {{
                // Limpiar rutas anteriores
                map.eachLayer(function(layer) {{
                    if (layer instanceof L.Polyline) {{
                        map.removeLayer(layer);
                    }}
                }});
                
                // Dibujar ruta específica
                var rutaEspecifica = L.polyline(
                    [[{lat_usuario}, {lon_usuario}], [latOng, lonOng]],
                    {{
                        color: '#dc3545',
                        weight: 6,
                        opacity: 0.9
                    }}
                ).addTo(map);
                
                // Ajustar vista para mostrar la ruta completa
                map.fitBounds(rutaEspecifica.getBounds());
                
                alert('🗺️ Ruta calculada a la ONG seleccionada');
            }}
            
            console.log('✅ Mapa de rutas cargado correctamente');
        </script>
    </body>
    </html>
    """

def get_color_by_index(index):
    """Obtener color único para cada ruta"""
    colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', 
              '#e83e8c', '#fd7e14', '#20c997', '#6610f2', '#d63384']
    return colors[index % len(colors)]

@app.route('/api/auth/register', methods=['POST'])
def register():
    """REGISTRO DE USUARIO"""
    logger.info("🎯 INICIANDO PROCESO DE REGISTRO")
    
    try:
        if not request.is_json:
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            }), 400
        
        data = request.get_json()
        logger.info(f"📨 DATOS RECIBIDOS: {data}")
        
        if not data:
            return jsonify({
                'success': False, 
                'message': 'No se recibieron datos JSON',
                'error_code': 'NO_DATA'
            }), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        # Validaciones
        if not username or not email or not password:
            return jsonify({
                'success': False, 
                'message': 'Todos los campos son requeridos',
                'error_code': 'MISSING_FIELDS'
            }), 400

        if len(password) < 4:
            return jsonify({
                'success': False, 
                'message': 'La contraseña debe tener al menos 4 caracteres',
                'error_code': 'SHORT_PASSWORD'
            }), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False, 
                'message': 'Error de conexión a la base de datos',
                'error_code': 'DB_CONNECTION_FAILED'
            }), 500
            
        cur = conn.cursor()
        
        # Verificar si usuario o correo existen
        try:
            cur.execute("SELECT id_usuario FROM usuario WHERE nombre_Usuario = %s OR correo = %s", (username, email))
            existing_user = cur.fetchone()
            
            if existing_user:
                logger.warning(f"❌ USUARIO O CORREO YA EXISTEN: {username}, {email}")
                cur.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'El usuario o correo ya existen',
                    'error_code': 'USER_EXISTS'
                }), 409
        except Exception as e:
            logger.error(f"❌ ERROR VERIFICANDO USUARIO: {e}")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Error verificando usuario',
                'error_code': 'CHECK_USER_ERROR'
            }), 500

        # Insertar nuevo usuario
        try:
            cur.execute(
                "INSERT INTO usuario (nombre_Usuario, correo, contraseña) VALUES (%s, %s, %s) RETURNING id_usuario", 
                (username, email, password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ USUARIO REGISTRADO EXITOSAMENTE - ID: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ ERROR INSERTANDO USUARIO: {e}")
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Error insertando usuario: {str(e)}',
                'error_code': 'INSERT_ERROR'
            }), 500

        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user_id': user_id,
            'username': username,
            'email': email,
            'timestamp': str(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"💥 ERROR CRÍTICO NO MANEJADO EN REGISTRO: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error crítico del servidor: {str(e)}',
            'error_code': 'UNHANDLED_ERROR'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuario"""
    try:
        logger.info("🔐 SOLICITUD DE LOGIN RECIBIDA")
        
        if not request.is_json:
            return jsonify({
                'success': False, 
                'message': 'Content-Type debe ser application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            }), 400
        
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

@app.route("/api/ongs", methods=['GET'])
def get_ongs():
    """Obtener ONGs"""
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
            console.log('🗺️ Inicializando mapa...');
            
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
            
            console.log('✅ Mapa cargado correctamente');
            
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    </html>
    """
