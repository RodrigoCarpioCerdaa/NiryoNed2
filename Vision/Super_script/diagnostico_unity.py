import cv2
import cv2.aruco as aruco
import numpy as np
import zmq

# --- 1. CONFIGURACIÓN DE CONEXIÓN CON UNITY (Puerto 5556) ---
context = zmq.Context()
socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

print("✅ Conectado a Unity. Buscando ArUcos en el stream de vídeo...")
print("Cuadrados ROJOS: Formas detectadas (pero ID desconocido)")
print("Cuadrados VERDES: Marcador identificado correctamente")

# --- 2. CONFIGURACIÓN DE DICCIONARIOS A PROBAR ---
DICCIONARIOS = {
    "DICT_4X4_50": aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
    "DICT_5X5_100": aruco.getPredefinedDictionary(aruco.DICT_5X5_100),
    "DICT_6X6_250": aruco.getPredefinedDictionary(aruco.DICT_6X6_250), # El estándar
    "DICT_ARUCO_ORIGINAL": aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
}

# Parámetros de detección (ajustados para ser más tolerantes)
parameters = aruco.DetectorParameters()
parameters.polygonalApproxAccuracyRate = 0.05 

try:
    while True:
        # --- 3. RECIBIR IMAGEN DE UNITY ---
        try:
            topic = socket_video.recv_string(flags=zmq.NOBLOCK)
            frame_bytes = socket_video.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            continue # Esperar si no hay datos

        # Decodificar imagen
        np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None: continue

        # IMPORTANTE: Girar la imagen de Unity si sale al revés
        frame = cv2.flip(frame, 0) 

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        marker_found = False
        
        # --- 4. TU LÓGICA DE DIAGNÓSTICO ---
        # Iteramos por los diccionarios para ver cuál es el de Unity
        for name, dictionary in DICCIONARIOS.items():
            # Crear el detector con el diccionario actual
            detector = aruco.ArucoDetector(dictionary, parameters)
            
            # Detectar
            corners, ids, rejected = detector.detectMarkers(gray)
            
            # Si encontramos algo válido
            if ids is not None:
                aruco.drawDetectedMarkers(frame, corners, ids)
                marker_found = True
                
                # Mostrar qué diccionario funcionó
                cv2.putText(frame, f"EXITO: {name}", (10, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # Mostrar IDs
                for i, corner in enumerate(corners):
                    c = corner[0][0]
                    cv2.putText(frame, f"ID: {ids[i][0]}", (int(c[0]), int(c[1]) - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                break # Salimos del bucle porque ya lo encontramos
            
            # Si no encontramos ID, dibujamos los "rechazados" del primer diccionario en rojo
            if name == "DICT_4X4_50" and len(rejected) > 0:
                 aruco.drawDetectedMarkers(frame, rejected, borderColor=(0, 0, 255))

        if not marker_found:
            cv2.putText(frame, "Buscando...", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("Diagnostico Unity-Python", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    socket_video.close()
    context.term()