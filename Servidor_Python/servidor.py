from flask import Flask, jsonify, request
import ikpy.chain
from ikpy.chain import Chain
import numpy as np
import threading
import time
import tempfile



try:
    my_chain = ikpy.chain.Chain.from_urdf_file("niryo_ned2_UWU.urdf")
    print("✅ Robot Ned 2 cargado correctamente (Modo Seguro).")
except Exception as e:
    print(f"❌ Error al generar el robot: {e}")
    my_chain = None
app = Flask(__name__)

# Estado del robot
# Ned 2 tiene 6 ejes, pero IKPy a veces usa 7 (incluyendo base fija).
# Trabajaremos con listas dinámicas para evitar errores.
current_joints_deg = [0.0] * 6
HOME_POSE = [0.0] * 6
state_lock = threading.Lock()


# --- RUTAS ---

@app.route('/get_state', methods=['GET'])
def get_state():
    with state_lock:
        return jsonify({"joints": current_joints_deg})


# ESTA ES LA QUE TE FALTABA (La que arregla el 404)
@app.route('/set_home', methods=['POST'])
def set_home():
    global current_joints_deg, HOME_POSE
    try:
        data = request.get_json()
        received_joints = data.get("joints")

        if received_joints:
            with state_lock:
                # Actualizamos la posición actual y la Home
                current_joints_deg = received_joints
                HOME_POSE = received_joints

            print(f"📥 Sincronizado con Unity. Posición inicial: {received_joints}")
            return "OK", 200
    except Exception as e:
        print(f"Error en set_home: {e}")
        return "Error", 500




# --- AÑADE ESTA FUNCIÓN (La interpolación suave) ---
def interpolate_value(start, end, progress):
    return start + (end - start) * progress

def simulate_move(target_joints, duration_sec=2.0):
    global current_joints_deg
    
    steps = int(duration_sec / 0.05) # 20 pasos por segundo
    
    with state_lock:
        start_joints = list(current_joints_deg)
    
    # Si la lista de tamaños no coincide, forzamos la igualación
    if len(start_joints) != len(target_joints):
        start_joints = [0.0] * len(target_joints)

    for i in range(1, steps + 1):
        progress = i / float(steps)
        current_step_joints = []
        for j in range(len(target_joints)):
            # Interpolamos cada articulación
            val = interpolate_value(start_joints[j], target_joints[j], progress)
            current_step_joints.append(val)
        
        with state_lock:
            current_joints_deg = current_step_joints
        time.sleep(0.05) # Espera 50ms entre pasos

# --- MODIFICA ESTA RUTA (Para usar la función suave) ---
@app.route('/calculate_ik', methods=['POST'])
def calculate_ik():
    global current_joints_deg, my_chain
    
    if my_chain is None:
        return "Error: No hay URDF", 500

    try:
        data = request.get_json()
        x = float(data.get("x", 0.3))
        y = float(data.get("y", 0.0))
        z = float(data.get("z", 0.2))
        duration = float(data.get("duration", 0.0)) 
        print(f"🧮 IK a: [{x}, {y}, {z}] en {duration}s")
        

        # Cálculo IK (igual que antes)
        target_position = [x, y, z]
        ik_solution_rad = my_chain.inverse_kinematics(target_position)
        ik_solution_deg = np.degrees(ik_solution_rad).tolist()
        angulo_base = ik_solution_deg[1] + 180
        if angulo_base > 180:
            angulo_base -= 360
        elif angulo_base < -180:
            angulo_base += 360
        ik_solution_deg[1] = angulo_base
        final_joints = ik_solution_deg[1:7] 

        print(f"✅ Solución hallada. Iniciando movimiento suave...")

        # CAMBIO IMPORTANTE: En vez de asignar directo, lanzamos el hilo suave
        if duration < 0.1:
            with state_lock:
                current_joints_deg = final_joints
        else:
            move_thread = threading.Thread(target=simulate_move, args=(final_joints, 2.0)) # 2.0 segundos
            move_thread.start()

        return jsonify({"joints": final_joints, "status": "moving"}), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

# Rutas manuales básicas
@app.route('/home', methods=['POST'])
def move_home():
    print("🏠 Volviendo a Home (Suave)...")
    
    # Usamos la función de interpolación en un hilo aparte
    # args=(PosiciónDestino, TiempoEnSegundos)
    move_thread = threading.Thread(target=simulate_move, args=(HOME_POSE, 2.0))
    move_thread.start()
    
    return "OK", 200


@app.route('/rest', methods=['POST'])
def move_rest():
    print("💤 Moviendo a Rest (Suave)...")
    
    # Definimos una pose de descanso (Asegúrate de que tenga 6 valores para el Ned2)
    # Ejemplo: Base quieta, Hombro quieto, Codo a -90...
    rest_pose = [0.0, 90.0, 90.0, 0.0, 0.0, 0.0] 
    
    # Lanzamos la animación
    move_thread = threading.Thread(target=simulate_move, args=(rest_pose, 2.0))
    move_thread.start()
    
    return "OK", 200


if __name__ == '__main__':
    print("🚀 Servidor MAESTRO iniciado en puerto 5000")
    print("Esperando conexión de Unity...")
    app.run(host='0.0.0.0', port=5000)