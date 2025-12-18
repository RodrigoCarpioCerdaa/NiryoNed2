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
socket_datos = context.socket(zmq.PUB)
socket_datos.bind("tcp://*:5555")

socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

print("✅ Servidor de Visión iniciado.")

# --- 2. CONFIGURACIÓN ZONA DE TRABAJO (TUS PUNTOS) ---
# Ordenamos los puntos para formar un polígono cerrado (BL -> TL -> TR -> BR)
# BL: Abajo-Izq (26), TL: Arriba-Izq (28), TR: Arriba-Der (27), BR: Abajo-Der (25)
ZONA_TRABAJO = np.array([
    [-1800, 2480], # ID 26
    [-1800, 5890], # ID 28
    [1210, 5890],  # ID 27
    [1210, 2530]   # ID 25
], dtype=np.float32)

print(f"🛡️ Zona de trabajo restringida activa: {len(ZONA_TRABAJO)} puntos.")

# --- 3. CONFIGURACIÓN ARUCO ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# --- 4. CARGAR CALIBRACIÓN ---
try:
    with open("homografia_robot.yml", 'r') as f:
        data = yaml.safe_load(f)
        HOMOGRAPHY_MATRIX = np.array(data['homography_matrix'])
    CALIBRADO = True
    print("✅ Calibración cargada.")
except FileNotFoundError:
    CALIBRADO = False
    HOMOGRAPHY_MATRIX = None
    print("⚠️ ERROR: Se requiere calibración para validar la zona.")

# --- 5. FUNCIONES AUXILIARES ---
def calcular_angulo(esquina_sup_izq, esquina_sup_der):
    delta_x = esquina_sup_der[0] - esquina_sup_izq[0]
    delta_y = esquina_sup_der[1] - esquina_sup_izq[1]
    angulo_rad = math.atan2(delta_y, delta_x)
    return math.degrees(angulo_rad)

def esta_en_zona(x, y):
    """Devuelve True si la coordenada real (x,y) está dentro del polígono"""
    punto = (x, y)
    # measureDist=False devuelve: +1 (dentro), -1 (fuera), 0 (borde)
    resultado = cv2.pointPolygonTest(ZONA_TRABAJO, punto, False)
    return resultado >= 0

# --- VARIABLES DE ESTADO ---
ultimo_id_enviado = None 

# --- 6. BUCLE PRINCIPAL ---
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
        
        frame = cv2.flip(frame, 1) 
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, _ = detector.detectMarkers(gray)
        
        pieza_valida_en_escena = False 

        DICCIONARIO_PIEZAS = { 1: "Verde", 2: "Rojo" }

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)

            for i, marker_id in enumerate(ids):
                id_actual = int(marker_id[0])

                if id_actual in DICCIONARIO_PIEZAS:
                    
                    # 1. Calcular Datos Físicos
                    c = corners[i][0]
                    cx = (c[0][0] + c[1][0] + c[2][0] + c[3][0]) / 4
                    cy = (c[0][1] + c[1][1] + c[2][1] + c[3][1]) / 4
                    angulo = calcular_angulo(c[0], c[1])

                    # Necesitamos coordenadas reales OBLIGATORIAMENTE para comprobar la zona
                    if CALIBRADO:
                        pixel_coords = np.array([[[float(cx), float(cy)]]], dtype=np.float32)
                        real_coords = cv2.perspectiveTransform(pixel_coords, HOMOGRAPHY_MATRIX)
                        rx = float(real_coords[0][0][0])
                        ry = float(real_coords[0][0][1])
                        posicion_final = [round(rx, 2), round(ry, 2)]
                        
                        # --- 2. VERIFICACIÓN DE ZONA ---
                        dentro_zona = esta_en_zona(rx, ry)
                    else:
                        # Si no hay calibración, no podemos saber si está en la zona real
                        dentro_zona = False 
                        posicion_final = [0, 0]

                    color_pieza = DICCIONARIO_PIEZAS[id_actual]

                    # --- 3. LÓGICA DE ENVÍO ---
                    if dentro_zona:
                        pieza_valida_en_escena = True
                        
                        estado_vis = "EN ZONA (OK)"
                        color_texto = (0, 255, 0) # Verde

                        # Solo enviar si es NUEVA pieza
                        if id_actual != ultimo_id_enviado:
                            datos = {
                                "objeto_encontrado": True,
                                "id_aruco": id_actual,
                                "forma": "Cubo" if id_actual == 2 else "Cilindro",
                                "color": color_pieza,
                                "posicion": posicion_final,
                                "angulo": float(round(angulo, 2)),
                                "calibrado": CALIBRADO
                            }
                            print(datos)
                            socket_datos.send_multipart([b"VisionData", json.dumps(datos).encode('utf-8')])
                            print(f"🚀 ENVIADO: {color_pieza} en {posicion_final}")
                            ultimo_id_enviado = id_actual
                    else:
                        estado_vis = "FUERA DE ZONA"
                        color_texto = (0, 0, 255) # Rojo
                        # NOTA: Si está fuera, NO actualizamos ultimo_id_enviado, 
                        # así que si la empujas dentro, se enviará instantáneamente.

                    # Visualización
                    cv2.putText(frame, f"{estado_vis}", (int(cx), int(cy) - 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_texto, 2)
                    cv2.putText(frame, f"Pos: {posicion_final}", (int(cx)-60, int(cy)-15), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_texto, 2)
                    
                    if dentro_zona: break # Si encontramos una válida, dejamos de buscar

        # Reset si no hay piezas VÁLIDAS (dentro de la zona)
        if not pieza_valida_en_escena:
            if ultimo_id_enviado is not None:
                # Enviamos señal de vacío una vez
                socket_datos.send_multipart([b"VisionData", json.dumps({"objeto_encontrado": False}).encode('utf-8')])
            ultimo_id_enviado = None

        cv2.imshow('Vision ArUco + Zona', frame)
        if cv2.waitKey(1) == ord('q'): break

except KeyboardInterrupt:
    print("\nDeteniendo...")
finally:
    cv2.destroyAllWindows()
    socket_datos.close()
    socket_video.close()
    context.term()