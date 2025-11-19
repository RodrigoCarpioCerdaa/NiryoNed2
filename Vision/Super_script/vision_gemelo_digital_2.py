# Fichero: vision_gemelo_digital.py

import cv2
import cv2.aruco as aruco
import numpy as np
import zmq
import json
import yaml
import math

# --- 1. CONFIGURACIÓN RED ---
context = zmq.Context()

# Socket para ENVIAR datos (JSON) a Unity - Puerto 5555
socket_datos = context.socket(zmq.PUB)
socket_datos.bind("tcp://*:5555")

# Socket para RECIBIR vídeo de Unity - Puerto 5556
socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

print("✅ Servidor de Visión iniciado.")
print("📡 Esperando vídeo de Unity en puerto 5556...")
print("📤 Enviando datos JSON en puerto 5555...")

# --- 2. CONFIGURACIÓN ARUCO ---
# Asegúrate de que en Unity usas marcadores de este diccionario (6x6_250)
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# --- 3. CARGAR CALIBRACIÓN (SI EXISTE) ---
try:
    with open("homografia_robot.yml", 'r') as f:
        data = yaml.safe_load(f)
        HOMOGRAPHY_MATRIX = np.array(data['homography_matrix'])
    CALIBRADO = True
    print("✅ Matriz de calibración cargada: Enviando milímetros.")
except FileNotFoundError:
    CALIBRADO = False
    HOMOGRAPHY_MATRIX = None
    print("⚠️  No se encontró 'homografia_robot.yml': Enviando píxeles.")

# --- 4. FUNCIÓN AUXILIAR: CALCULAR ÁNGULO ---
def calcular_angulo(esquina_sup_izq, esquina_sup_der):
    """Calcula la rotación del marcador en grados"""
    delta_x = esquina_sup_der[0] - esquina_sup_izq[0]
    delta_y = esquina_sup_der[1] - esquina_sup_izq[1]
    angulo_rad = math.atan2(delta_y, delta_x)
    return math.degrees(angulo_rad)

# --- 5. BUCLE PRINCIPAL ---
try:
    while True:
        # --- A. RECIBIR IMAGEN ---
        try:
            topic = socket_video.recv_string(flags=zmq.NOBLOCK)
            frame_bytes = socket_video.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            continue # Si no hay vídeo, esperamos

        # Decodificar imagen
        np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None: continue
        
        # Girar imagen (Unity suele enviarla invertida verticalmente)
        frame = cv2.flip(frame, 0) 
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # --- B. DETECCIÓN ---
        corners, ids, _ = detector.detectMarkers(gray)
        
        objeto_encontrado = False

        if ids is not None:
            # Procesamos el primer marcador encontrado como la "pieza"
            for i, marker_id in enumerate(ids):
                # 1. Calcular Centro
                c = corners[i][0]
                cx = (c[0][0] + c[1][0] + c[2][0] + c[3][0]) / 4
                cy = (c[0][1] + c[1][1] + c[2][1] + c[3][1]) / 4
                
                # 2. Calcular Ángulo
                angulo = calcular_angulo(c[0], c[1])

                # 3. Aplicar Homografía (si existe)
                # Convertimos a float estándar de Python para evitar errores de JSON
                pos_x = float(cx)
                pos_y = float(cy)
                
                if CALIBRADO:
                    pixel_coords = np.array([[[pos_x, pos_y]]], dtype=np.float32)
                    real_coords = cv2.perspectiveTransform(pixel_coords, HOMOGRAPHY_MATRIX)
                    
                    # Extracción y conversión explícita a float
                    rx = float(real_coords[0][0][0])
                    ry = float(real_coords[0][0][1])
                    
                    posicion_final = [round(rx, 2), round(ry, 2)]
                else:
                    posicion_final = [int(pos_x), int(pos_y)]
                
                # 4. Preparar JSON (Tipos corregidos)
                datos = {
                    "objeto_encontrado": True,
                    "id_aruco": int(marker_id[0]),      # Convertir numpy.int a int
                    "posicion": posicion_final,          # Lista de floats estándar
                    "angulo": float(round(angulo, 2)),   # Convertir a float estándar
                    "calibrado": CALIBRADO
                }
                
                # 5. Enviar
                mensaje_json = json.dumps(datos)
                socket_datos.send_multipart([b"VisionData", mensaje_json.encode('utf-8')])
                objeto_encontrado = True
                
                # Dibujar para visualización
                aruco.drawDetectedMarkers(frame, corners, ids)
                texto = f"ID:{marker_id[0]} Ang:{angulo:.1f}"
                cv2.putText(frame, texto, (int(cx), int(cy) - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                break # Solo enviamos una pieza por fotograma

        # Si no se encuentra nada, avisar a Unity
        if not objeto_encontrado:
             datos_nulos = {"objeto_encontrado": False}
             socket_datos.send_multipart([b"VisionData", json.dumps(datos_nulos).encode('utf-8')])

        cv2.imshow('Vision ArUco (Gemelo Digital)', frame)
        if cv2.waitKey(1) == ord('q'): break

except KeyboardInterrupt:
    print("\nDeteniendo por teclado...")
finally:
    cv2.destroyAllWindows()
    socket_datos.close()
    socket_video.close()
    context.term()
    print("Cerrado correctamente.")