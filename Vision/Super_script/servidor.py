from flask import Flask, jsonify, request
import ikpy.chain
import numpy as np
import threading
import time
import zmq
import json

# --- CONFIGURACIÓN ---
URDF_FILE = "niryo_ned2_UWU.urdf"
PUERTO_VISION = "5555"

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


def calcular_ik_interno(x, y, z):
    """ Función interna para calcular ángulos sin pasar por Flask """
    global current_joints_deg

    with state_lock:
        snapshot = list(current_joints_deg)

    num_links = len(my_chain.links)
    padding = num_links - 1 - len(snapshot)
    seed = [0] + snapshot + ([0] * max(0, padding))
    if len(seed) != num_links: seed = [0] * num_links

    # initial_position ayuda a la continuidad del movimiento
    ik_rad = my_chain.inverse_kinematics([x, y, z], initial_position=np.radians(seed))
    ik_deg = np.degrees(ik_rad).tolist()

    # Corrección de ángulo visual (-180 a 180)
    base = ik_deg[1] + 180
    if base > 180:
        base -= 360
    elif base < -180:
        base += 360
    ik_deg[1] = base

    return ik_deg[1:7]


# --- 🧵 HILO DE ESCUCHA (CEREBRO VISIÓN -> ROBOT) ---
def vision_listener():
    print(f"👂 Iniciando escucha directa de Visión en puerto {PUERTO_VISION}...")
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PUERTO_VISION}")
    socket.subscribe("VisionData")

    global current_joints_deg

    # Altura constante (Z del robot)
    ALTURA_RECOGIDA = 0.20

    while True:
        try:
            # 1. Recibir datos
            topic = socket.recv_string()
            json_str = socket.recv_string()
            data = json.loads(json_str)

            # Solo procesamos si hay objeto y está calibrado
            if data.get("objeto_encontrado") and data.get("calibrado"):
                # --- ASIGNACIÓN DIRECTA (RAW) ---
                # "Quiero que se mueva a la posición X que le pasa el código y a la Z"

                raw_x = data["posicion"][0]
                raw_z = data["posicion"][1]

                # Mapeo directo:
                # Vision X -> Robot X
                # Vision Z -> Robot Y (el otro eje del plano)
                # Constante -> Robot Z (Altura)

                target_x = raw_x
                target_y = raw_z
                target_z = ALTURA_RECOGIDA

                print(
                    f"👁️ Directo: Recibido[{raw_x:.3f}, {raw_z:.3f}] -> Robot IK X:{target_x:.3f} Y:{target_y:.3f} Z:{target_z:.3f}")

                # --- D. CALCULAR Y MOVER ---
                nuevos_angulos = calcular_ik_interno(target_x, target_y, target_z)

                with state_lock:
                    current_joints_deg = nuevos_angulos

        except Exception as e:
            print(f"⚠️ Error en listener: {e}")
            time.sleep(0.1)


# Arrancamos el hilo
t = threading.Thread(target=vision_listener)
t.daemon = True
t.start()


# --- RUTAS FLASK ---
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


if __name__ == '__main__':
    print("🚀 Servidor AUTÓNOMO (DIRECTO) Listo (Puerto 5000)")
    app.run(host='0.0.0.0', port=5000)