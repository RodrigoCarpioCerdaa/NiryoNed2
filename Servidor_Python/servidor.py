from flask import Flask, jsonify
import threading
import time

# --- Estado Simulado del Robot ---
# Mantenemos el estado de las 6 articulaciones (en grados)
# Usamos un Lock para evitar problemas si Unity pide el estado
# justo cuando lo estamos cambiando.
robot_state = {
    "joints": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
}
state_lock = threading.Lock()

# Posición "Home" (en grados)
HOME_POSE = [0.0, 0.0, 0.0, 0.0, -90.0, 0.0]
# Posición "Descanso" (ejemplo)
REST_POSE = [0.0, 45.0, -90.0, 0.0, 0.0, 0.0]


# --- El Servidor Flask ---
app = Flask(__name__)

def simulate_move(target_joints, duration_sec=2.0):
    """
    Esta función se ejecuta en un hilo (thread) para
    simular un movimiento suave sin bloquear el servidor.
    """
    global robot_state
    steps = int(duration_sec / 0.05) # 20 pasos por segundo
    
    with state_lock:
        start_joints = list(robot_state["joints"]) # Copia del estado actual

    if steps == 0:
        with state_lock:
            robot_state["joints"] = target_joints
        return

    for i in range(1, steps + 1):
        progress = i / float(steps)
        current_step_joints = []
        for j in range(6):
            # Interpolación lineal simple (lerp)
            start = start_joints[j]
            end = target_joints[j]
            lerp_val = start + (end - start) * progress
            current_step_joints.append(lerp_val)
        
        with state_lock:
            robot_state["joints"] = current_step_joints
        
        time.sleep(0.05) # Espera 50ms

    print(f"Movimiento a {target_joints} completado.")


# --- Rutas de la API ---

@app.route('/get_state', methods=['GET'])
def get_state():
    """
    Unity llamará a esta ruta en cada fotograma.
    Devuelve el estado actual de las articulaciones.
    """
    with state_lock:
        return jsonify(robot_state)

@app.route('/home', methods=['POST'])
def move_home():
    """
    Unity llama a esta ruta para iniciar el movimiento a Home.
    """
    print("Recibida petición: Mover a Home")
    # Creamos un hilo para no bloquear la respuesta
    # El hilo ejecutará la función 'simulate_move'
    move_thread = threading.Thread(target=simulate_move, args=(HOME_POSE,))
    move_thread.start()
    return "OK: Moviendo a Home", 200

@app.route('/rest', methods=['POST'])
def move_rest():
    """
    Ruta de ejemplo para mover a otra posición
    """
    print("Recibida petición: Mover a Descanso")
    move_thread = threading.Thread(target=simulate_move, args=(REST_POSE,))
    move_thread.start()
    return "OK: Moviendo a Descanso", 200


# --- ARRANQUE DEL SERVIDOR ---
if __name__ == '__main__':
    print("Iniciando servidor de simulación del Ned 2 en http://127.0.0.1:5000")
    # Corremos en 'localhost' (127.0.0.1) porque solo Unity (en el mismo PC)
    # necesita conectarse
    app.run(host='127.0.0.1', port=5000, debug=False)