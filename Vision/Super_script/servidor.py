from flask import Flask, jsonify, request
import ikpy.chain
import numpy as np
import threading
import time
import zmq  # <--- NUEVO: Para hablar con Visión
import json

# --- CONFIGURACIÓN ---
URDF_FILE = "niryo_ned2_UWU.urdf"
PUERTO_VISION = "5555"  # Puerto donde publica detector_piezas.py

try:
    my_chain = ikpy.chain.Chain.from_urdf_file(URDF_FILE)
    # Hack de límites para permitir giro libre
    my_chain.links[1].bounds = (-6.28, 6.28)
    print(f"✅ Robot cargado. Modo Autónomo preparado.")
except Exception as e:
    print(f"❌ Error crítico URDF: {e}")
    my_chain = None

app = Flask(__name__)

current_joints_deg = [0.0] * 6
state_lock = threading.Lock()


# --- FUNCIONES MATEMÁTICAS ---
def interpolate_value(start, end, progress):
    return start + (end - start) * progress


def simulate_move(target_joints, duration_sec=2.0):
    global current_joints_deg
    steps = int(duration_sec / 0.05)
    with state_lock:
        start_joints = list(current_joints_deg)

    if len(start_joints) != len(target_joints): start_joints = [0.0] * 6

    for i in range(1, steps + 1):
        progress = i / float(steps)
        current = []
        for j in range(6):
            current.append(interpolate_value(start_joints[j], target_joints[j], progress))
        with state_lock:
            current_joints_deg = current
        time.sleep(0.05)


def calcular_ik_interno(x, y, z):
    """ Función interna para calcular ángulos sin pasar por Flask """
    global current_joints_deg

    # 1. Seeding
    with state_lock:
        snapshot = list(current_joints_deg)

    num_links = len(my_chain.links)
    padding = num_links - 1 - len(snapshot)
    seed = [0] + snapshot + ([0] * max(0, padding))
    if len(seed) != num_links: seed = [0] * num_links

    # 2. Cálculo
    ik_rad = my_chain.inverse_kinematics([x, y, z], initial_position=np.radians(seed))
    ik_deg = np.degrees(ik_rad).tolist()

    # 3. Corrección 180
    base = ik_deg[1] + 180
    if base > 180:
        base -= 360
    elif base < -180:
        base += 360
    ik_deg[1] = base

    return ik_deg[1:7]


# --- 🧵 HILO DE ESCUCHA (EL CEREBRO AUTÓNOMO) ---
# --- 🧵 HILO DE ESCUCHA (CON CHIVATO ACTIVADO) ---
def vision_listener():
    print(f"👂 Iniciando escucha directa de Visión en puerto {PUERTO_VISION}...")
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PUERTO_VISION}")
    socket.subscribe("VisionData")

    global current_joints_deg

    while True:
        try:
            # 1. Recibir datos (Esto sigue igual para mantener el ritmo)
            topic = socket.recv_string()
            json_str = socket.recv_string()
            data = json.loads(json_str)

            # --- 🛑 ZONA DE PRUEBA (IGNORAMOS DATOS REALES) 🛑 ---
            # Aunque la cámara diga X=3000, nosotros forzamos una buena.

            # Simulamos que la pieza está 30cm delante y centrada
            unity_x = 0.0  # 0.0 metros (Centro izquierda/derecha)
            unity_z = 0.3  # 0.3 metros (30cm hacia el fondo)
            unity_y = 0.20  # 0.2 metros (Altura)

            print(f"🧪 [TEST] Forzando movimiento a: X={unity_x}, Z={unity_z}")

            # 2. TRADUCCIÓN DE EJES (Igual que antes)
            target_x = unity_z  # 0.3
            target_y = -unity_x  # 0.0
            target_z = unity_y  # 0.2

            print(f"   🤖 IK Objetivo: X={target_x:.2f}, Y={target_y:.2f}, Z={target_z:.2f}")

            # 3. CALCULAR Y MOVER
            nuevos_angulos = calcular_ik_interno(target_x, target_y, target_z)

            with state_lock:
                current_joints_deg = nuevos_angulos

            # Pequeña pausa para no saturar la consola en el test
            time.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Error en listener: {e}")
            time.sleep(0.1)

# Arrancamos el hilo de escucha en segundo plano
t = threading.Thread(target=vision_listener)
t.daemon = True  # Se cierra si cierras el programa
t.start()


# --- RUTAS FLASK (Para que Unity pueda leer el estado) ---

@app.route('/get_state', methods=['GET'])
def get_state():
    with state_lock:
        return jsonify({"joints": current_joints_deg})


@app.route('/set_home', methods=['POST'])
def set_home():
    global current_joints_deg
    try:
        data = request.get_json()
        if data.get("joints"):
            with state_lock:
                current_joints_deg = data.get("joints")
            return "OK", 200
    except:
        return "Error", 500


# Mantenemos calculate_ik por si quieres usar el botón manual alguna vez
@app.route('/calculate_ik', methods=['POST'])
def calculate_ik():
    try:
        d = request.get_json()
        res = calcular_ik_interno(d.get("x"), d.get("y"), d.get("z"))
        with state_lock:
            current_joints_deg = res
        return jsonify({"joints": res}), 200
    except:
        return "Error", 500


if __name__ == '__main__':
    print("🚀 Servidor AUTÓNOMO Listo (Puerto 5000)")
    app.run(host='0.0.0.0', port=5000)