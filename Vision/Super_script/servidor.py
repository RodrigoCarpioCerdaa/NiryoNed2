from flask import Flask, jsonify, request
import ikpy.chain
import numpy as np
import threading
import time
import zmq
import json

# --- CONFIGURACIÓN ---
URDF_FILE = "urdf_prueba.urdf"
PUERTO_VISION = "5555"

# --- 🚧 VALLA VIRTUAL (Safety Zone) 🚧 ---
# Solo haremos caso a coordenadas que estén DENTRO de este rectángulo (en Metros).
# Basado en tus ArUcos: X entre -1.8 y 1.2 | Z entre 2.5 y 5.9
X_MIN, X_MAX = -1.8, 1.3
Z_MIN, Z_MAX = 2.4, 6.0

# --- 🔧 AJUSTE ODOMETRÍA ---
AJUSTE_ANGULO_BASE = -90.0
INVERTIR_GIRO_BASE = False

try:
    my_chain = ikpy.chain.Chain.from_urdf_file(URDF_FILE)
    my_chain.links[1].bounds = (-6.28, 6.28)
    print("✅ Robot Ned 2 cargado.")
except Exception as e:
    print(f"❌ Error URDF: {e}")
    my_chain = None

app = Flask(__name__)
current_joints_deg = [0.0] * 6
HOME_POSE = [0.0] * 6
state_lock = threading.Lock()


# --- FUNCIONES ---

def es_zona_segura(x, z):
    """ Devuelve True si la coordenada está dentro de los ArUcos """
    if X_MIN <= x <= X_MAX and Z_MIN <= z <= Z_MAX:
        return True
    return False


def interpolate_value(start, end, progress):
    return start + (end - start) * progress


def calcular_ik_raw(x, y, z):
    if my_chain is None: return [0.0] * 6
    target_position = [x, y, z]
    ik_solution_rad = my_chain.inverse_kinematics(target_position)
    ik_solution_deg = np.degrees(ik_solution_rad).tolist()

    # Corrección Base
    base = ik_solution_deg[1] + AJUSTE_ANGULO_BASE
    if INVERTIR_GIRO_BASE: base = -base

    if base > 180:
        base -= 360
    elif base < -180:
        base += 360
    ik_solution_deg[1] = base

    return ik_solution_deg[1:7]


def simulate_move(target_joints, duration_sec=2.0):
    global current_joints_deg
    steps = int(duration_sec / 0.05)
    with state_lock:
        start_joints = list(current_joints_deg)
    if len(start_joints) != len(target_joints): start_joints = [0.0] * len(target_joints)

    for i in range(1, steps + 1):
        progress = i / float(steps)
        current_step_joints = []
        for j in range(len(target_joints)):
            val = interpolate_value(start_joints[j], target_joints[j], progress)
            current_step_joints.append(val)
        with state_lock:
            current_joints_deg = current_step_joints
        time.sleep(0.05)


# --- HILO DE VISIÓN CON FILTRO DE ZONA ---
def vision_listener():
    print(f"👂 Escuchando visión en puerto {PUERTO_VISION}...")
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PUERTO_VISION}")
    socket.subscribe("VisionData")

    global current_joints_deg
    ALTURA_FIJA = 2.500

    while True:
        try:
            topic = socket.recv_string()
            json_str = socket.recv_string()
            data = json.loads(json_str)

            if data.get("objeto_encontrado") and data.get("calibrado"):

                vision_x = data["posicion"][0]/1000
                vision_z = data["posicion"][1]/1000

                # --- 🛑 FILTRO DE SEGURIDAD 🛑 ---
                if not es_zona_segura(vision_x, vision_z):
                    print(f"⛔ IGNORADO: Objeto fuera de zona ({vision_x:.2f}, {vision_z:.2f})")
                    continue  # Saltamos al siguiente ciclo sin mover el robot
                # ---------------------------------

                target_x = vision_x
                target_y = vision_z
                target_z = ALTURA_FIJA

                print(f"✅ ACEPTADO: [{target_x:.2f}, {target_y:.2f}]")
                nuevos_angulos = calcular_ik_raw(target_x, target_y, target_z)

                angulos_bonitos = [round(a, 2) for a in nuevos_angulos]
                print(f"📐 MOTORES: {angulos_bonitos}")

                with state_lock:
                    current_joints_deg = nuevos_angulos

        except zmq.Again:
            continue
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(0.1)


t_vision = threading.Thread(target=vision_listener)
t_vision.daemon = True
t_vision.start()


# --- RUTAS FLASK ---
@app.route('/get_state', methods=['GET'])
def get_state():
    with state_lock: return jsonify({"joints": current_joints_deg})


@app.route('/set_home', methods=['POST'])
def set_home():
    global current_joints_deg, HOME_POSE
    try:
        data = request.get_json()
        if data.get("joints"):
            with state_lock:
                current_joints_deg = data.get("joints")
                HOME_POSE = data.get("joints")
            return "OK", 200
    except:
        return "Error", 500


@app.route('/calculate_ik', methods=['POST'])
def calculate_ik():
    try:
        data = request.get_json()
        x, y, z = float(data.get("x", 0.3)), float(data.get("y", 0.0)), float(data.get("z", 0.2))
        final = calcular_ik_raw(x, y, z)
        threading.Thread(target=simulate_move, args=(final, 2.0)).start()
        return jsonify({"joints": final}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/home', methods=['POST'])
def move_home():
    threading.Thread(target=simulate_move, args=(HOME_POSE, 2.0)).start()
    return "OK", 200


if __name__ == '__main__':
    print("🚀 Servidor con VALLA VIRTUAL listo (Puerto 5000)")
    app.run(host='0.0.0.0', port=5000)