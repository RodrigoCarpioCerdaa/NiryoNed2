import cv2
import cv2.aruco as aruco
import numpy as np
import zmq
import json
import yaml
import math # IMPORTANTE: Necesario para calcular el ángulo

# --- 1. CONFIGURACIÓN RED ---
context = zmq.Context()
socket_datos = context.socket(zmq.PUB)
socket_datos.bind("tcp://*:5555")

socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

print("✅ Modo 'Pick & Place con Orientación' activado.")

# --- 2. CONFIGURACIÓN ARUCO ---
# Usamos el diccionario para las piezas (asegúrate de que sea el correcto)
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Intentar cargar calibración
try:
    with open("homografia_robot.yml", 'r') as f:
        data = yaml.safe_load(f)
        HOMOGRAPHY_MATRIX = np.array(data['homography_matrix'])
    CALIBRADO = True
except:
    CALIBRADO = False
    HOMOGRAPHY_MATRIX = None

def calcular_angulo(esquina_sup_izq, esquina_sup_der):
    """Calcula el ángulo de rotación del ArUco en grados"""
    # Diferencias de coordenadas
    delta_x = esquina_sup_der[0] - esquina_sup_izq[0]
    delta_y = esquina_sup_der[1] - esquina_sup_izq[1]
    
    # Arcotangente para obtener el ángulo en radianes
    angulo_rad = math.atan2(delta_y, delta_x)
    
    # Convertir a grados
    angulo_deg = math.degrees(angulo_rad)
    
    return angulo_deg

try:
    while True:
        try:
            topic = socket_video.recv_string(flags=zmq.NOBLOCK)
            frame_bytes = socket_video.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            continue

        np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None: continue
        
        frame = cv2.flip(frame, 0) 
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # --- DETECCIÓN ---
        corners, ids, _ = detector.detectMarkers(gray)
        
        objeto_encontrado = False

        if ids is not None:
            # Iteramos sobre los marcadores encontrados (asumimos que son piezas)
            # Si usas ArUcos para calibrar en la mesa, tendrás que filtrar por ID
            # para no confundir una pieza con una esquina de la mesa.
            
            for i, marker_id in enumerate(ids):
                # --- 1. CALCULAR POSICIÓN (CENTRO) ---
                c = corners[i][0]
                cx = (c[0][0] + c[1][0] + c[2][0] + c[3][0]) / 4
                cy = (c[0][1] + c[1][1] + c[2][1] + c[3][1]) / 4
                
                # --- 2. CALCULAR ÁNGULO (ORIENTACIÓN) ---
                # Usamos la esquina 0 (Sup. Izq) y la 1 (Sup. Der)
                angulo = calcular_angulo(c[0], c[1])

                # --- 3. APLICAR HOMOGRAFÍA ---
                posicion_final = [cx, cy]
                if CALIBRADO:
                    pixel_coords = np.array([[[cx, cy]]], dtype=np.float32)
                    real_coords = cv2.perspectiveTransform(pixel_coords, HOMOGRAPHY_MATRIX)
                    posicion_final = [round(real_coords[0][0][0], 2), round(real_coords[0][0][1], 2)]
                
                # --- 4. ENVIAR DATOS ---
                datos = {
                    "objeto_encontrado": True,
                    "id_aruco": int(marker_id[0]), # Enviamos el ID por si hay piezas distintas
                    "posicion": posicion_final,     # [X, Y] (mm o pixels)
                    "angulo": round(angulo, 2),     # Ángulo en grados
                    "calibrado": CALIBRADO
                }
                
                socket_datos.send_multipart([b"VisionData", json.dumps(datos).encode('utf-8')])
                objeto_encontrado = True
                
                # DIBUJAR
                aruco.drawDetectedMarkers(frame, corners, ids)
                # Escribir posición y ángulo en pantalla
                texto = f"ID:{marker_id[0]} Ang:{angulo:.1f}"
                cv2.putText(frame, texto, (int(cx), int(cy) - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                break # Solo enviamos la primera pieza que vemos

        if not objeto_encontrado:
             datos_nulos = {"objeto_encontrado": False}
             socket_datos.send_multipart([b"VisionData", json.dumps(datos_nulos).encode('utf-8')])

        cv2.imshow('Vision ArUco', frame)
        if cv2.waitKey(1) == ord('q'): break

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    socket_datos.close()
    socket_video.close()
    context.term()