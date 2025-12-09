from flask import Flask, jsonify, request
import ikpy.chain
import numpy as np
import threading
import time
import zmq
import json
import math

# --- CONFIGURACIÓN ---
URDF_FILE = "urdf_prueba.urdf"
PUERTO_VISION = "5555"

# --- 🚧 VALLA VIRTUAL (Safety Zone) 🚧 ---
X_MIN, X_MAX = -1.8, 1.3
Z_MIN, Z_MAX = 2.4, 6.0

# --- 🏗️ ALTURAS ---
ALTURA_VIAJE = 3.0
ALTURA_COGER = 2.8

# Zona de Entrega
DROP_ZONE_X = -2.8
DROP_ZONE_Z = 3.0

# --- 🧠 PARÁMETROS DE PACIENCIA (ESTABILIDAD) ---
UMBRAL_MOVIMIENTO = 0.005  # 5mm de margen (para ignorar ruido de cámara)
FRAMES_PARA_CONFIRMAR = 30  # Cuantos frames debe estar "quieto" antes de atacar

# --- 🔧 AJUSTE ODOMETRÍA ---
AJUSTE_ANGULO_BASE = -90.0
INVERTIR_GIRO_BASE = False
AJUSTE_MUÑECA_PITCH = 90.0

try:
    my_chain = ikpy.chain.Chain.from_urdf_file(URDF_FILE)
    my_chain.links[1].bounds = (-6.28, 6.28)
    print("✅ Robot Ned 2 cargado.")
except Exception as e:
    print(f"❌ Error URDF: {e}")
    my_chain = None

app = Flask(__name__)

# --- ESTADO DEL ROBOT ---
current_joints_deg = [0.0] * 6
HOME_POSE = [0.0] * 6
gripper_encendido = False
robot_ocupado = False
state_lock = threading.Lock()

# Variables para la estabilidad
ultima_pos = (0, 0)
contador_estabilidad = 0


# --- FUNCIONES ---

def es_zona_segura(x, z):
    if X_MIN <= x <= X_MAX and Z_MIN <= z <= Z_MAX: return True
    return False


def interpolate_value(start, end, progress):
    return start + (end - start) * progress


def calcular_ik_raw(x, y, z):
    if my_chain is None: return [0.0] * 6
    target_position = [x, y, z]
    ik_solution_rad = my_chain.inverse_kinematics(target_position)
    ik_solution_deg = np.degrees(ik_solution_rad).tolist()

    base = ik_solution_deg[1] + AJUSTE_ANGULO_BASE
    if INVERTIR_GIRO_BASE: base = -base

    if base > 180:
        base -= 360
    elif base < -180:
        base += 360
    ik_solution_deg[1] = base

    ik_solution_deg[5] += AJUSTE_MUÑECA_PITCH
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


# --- 🤖 RUTINA PICK & PLACE ---
def rutina_coger_y_dejar(x_obj, z_obj):
    global robot_ocupado, gripper_encendido

    robot_ocupado = True
    print(f"🚨 OBJETIVO FIJADO Y QUIETO EN [{x_obj:.2f}, {z_obj:.2f}] -> ATACANDO")

    # Secuencia rápida
    print("1️⃣ Aproximando...")
    simulate_move(calcular_ik_raw(x_obj, z_obj, ALTURA_VIAJE), 2.0)

    print("2️⃣ Bajando...")
    simulate_move(calcular_ik_raw(x_obj, z_obj, ALTURA_COGER), 1.5)

    print("3️⃣ 🧲 IMÁN ON")
    with state_lock: gripper_encendido = True
    time.sleep(0.8)

    print("4️⃣ Subiendo...")
    simulate_move(calcular_ik_raw(x_obj, z_obj, ALTURA_VIAJE), 1.5)

    print(f"5️⃣ Entregando...")
    simulate_move(calcular_ik_raw(DROP_ZONE_X, DROP_ZONE_Z, ALTURA_VIAJE), 3.0)

    print("6️⃣ 💨 SOLTANDO")
    with state_lock: gripper_encendido = False
    time.sleep(0.8)

    print("7️⃣ Home...")
    simulate_move(HOME_POSE, 2.0)

    robot_ocupado = False
    print("✅ Esperando nueva pieza...")


# --- HILO DE VISIÓN INTELIGENTE ---
def vision_listener():
    print(f"👂 Escuchando visión en puerto {PUERTO_VISION}...")
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{PUERTO_VISION}")
    socket.subscribe("VisionData")

    global current_joints_deg, ultima_pos, contador_estabilidad

    while True:
        try:
            if robot_ocupado:
                try:
                    socket.recv_string(flags=zmq.NOBLOCK); socket.recv_string(flags=zmq.NOBLOCK)
                except:
                    pass
                time.sleep(0.1)
                continue

            topic = socket.recv_string()
            json_str = socket.recv_string()
            data = json.loads(json_str)

            if data.get("objeto_encontrado") and data.get("calibrado"):

                # Coordenadas actuales
                vx = data["posicion"][0] / 1000
                vz = data["posicion"][1] / 1000

                vision_id = data.get("id", -1)
                vision_color = str(data.get("color", "unknown")).lower()

                if not es_zona_segura(vx, vz): continue

                # --- 1. PRIMERO SIEMPRE SEGUIMOS (TRACKING) ---
                # El robot siempre mirará a la pieza, se mueva o no.
                target_z_robot = ALTURA_VIAJE
                nuevos_angulos = calcular_ik_raw(vx, vz, target_z_robot)
                with state_lock:
                    current_joints_deg = nuevos_angulos

                # --- 2. ¿ES EL ELEGIDO (VERDE)? ---
                if vision_id == 1 or "verd" in vision_color or "green" in vision_color:
                    threading.Thread(target=rutina_coger_y_dejar, args=(vx, vz)).start()
                    time.sleep(3.0)
                    continue

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
    with state_lock:
        return jsonify({"joints": current_joints_deg, "gripper": gripper_encendido})


@app.route('/set_home', methods=['POST'])
def set_home():
    global current_joints_deg, HOME_POSE
    try:
        d = request.get_json()
        if d.get("joints"):
            with state_lock: current_joints_deg = d.get("joints"); HOME_POSE = d.get("joints")
            return "OK", 200
    except:
        return "Error", 500


@app.route('/calculate_ik', methods=['POST'])
def calculate_ik():
    try:
        d = request.get_json()
        x, y, z = float(d.get("x", 0.3)), float(d.get("y", 0.0)), float(d.get("z", 0.2))
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
    print("🚀 Servidor 'DEPREDADOR PACIENTE' listo (Puerto 5000)")
    app.run(host='0.0.0.0', port=5000)