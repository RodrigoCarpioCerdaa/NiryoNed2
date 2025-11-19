from flask import Flask, jsonify, request
import ikpy.chain
import numpy as np
import threading
import time

# --- CONFIGURACIÓN ---
# NOMBRE DEL ARCHIVO URDF (¡Tiene que estar en la misma carpeta!)
URDF_FILE = "niryo_ned2_UwU.urdf" 

# Cargamos la cadena cinemática del robot
# active_links_mask le dice qué articulaciones se mueven (True) y cuáles son fijas (False)
# Para un brazo de 6 ejes suele ser [False, True, True, True, True, True, True, False...]
# Dejamos que ikpy lo intente adivinar primero, o lo ajustamos luego.
try:
    my_chain = ikpy.chain.Chain.from_urdf_file(URDF_FILE)
    print(f"✅ Robot cargado desde {URDF_FILE}")
    print("Links activos:", my_chain.links)
except Exception as e:
    print(f"❌ ERROR: No encuentro el archivo {URDF_FILE}. Asegúrate de ponerlo en la carpeta.")
    print(f"Error detalle: {e}")
    my_chain = None

app = Flask(__name__)

# Estado actual del robot (Ángulos en grados)
current_joints_deg = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
state_lock = threading.Lock()

@app.route('/get_state', methods=['GET'])
def get_state():
    with state_lock:
        # Devolvemos solo los primeros 6 ángulos (o los necesarios para Unity)
        # Unity espera array de floats
        return jsonify({"joints": current_joints_deg})

@app.route('/calculate_ik', methods=['POST'])
def calculate_ik():
    global current_joints_deg
    
    if my_chain is None:
        return "Error: No hay URDF cargado", 500

    try:
        data = request.get_json()
        x = float(data.get("x", 0.3))
        y = float(data.get("y", 0.0))
        z = float(data.get("z", 0.2))
        
        print(f"🎯 Calculando IK para ir a: [{x}, {y}, {z}]")

        # --- LA MAGIA DE LA CINEMÁTICA INVERSA ---
        # Target: Posición X, Y, Z. 
        # orientation_mode=None deja que el robot elija la orientación más fácil
        target_position = [x, y, z]
        
        # Calculamos (devuelve radianes)
        ik_solution_rad = my_chain.inverse_kinematics(target_position)
        
        # Convertimos a Grados
        ik_solution_deg = np.degrees(ik_solution_rad).tolist()
        
        # ikpy suele devolver una lista que incluye la "Base" estática al principio.
        # Normalmente los motores son el índice 1, 2, 3, 4, 5, 6.
        # Recortamos para quedarnos con los 6 motores.
        # (Ajusta este recorte si ves que te sobra o falta alguno)
        final_joints = ik_solution_deg[1:7] 

        print(f"📐 Solución hallada (Grados): {final_joints}")

        with state_lock:
            current_joints_deg = final_joints

        return jsonify({"joints": final_joints, "status": "moved"}), 200

    except Exception as e:
        print(f"Error calculando IK: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🤖 Servidor IK listo en puerto 5000")
    app.run(host='0.0.0.0', port=5000)