import cv2
import cv2.aruco as aruco
import numpy as np
import zmq

# --- 1. CONEXIÓN CON UNITY ---
context = zmq.Context()
socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

print("✅ Conectado a Unity. Diagnosticano ArUcos...")

# --- 2. DICCIONARIOS A PROBAR ---
DICCIONARIOS = {
    "DICT_4X4_50": aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
    "DICT_5X5_100": aruco.getPredefinedDictionary(aruco.DICT_5X5_100),
    "DICT_6X6_250": aruco.getPredefinedDictionary(aruco.DICT_6X6_250), # El que usa tu código original
    "DICT_ARUCO_ORIGINAL": aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
}

parameters = aruco.DetectorParameters()
# Hacemos el detector más flexible para probar
parameters.polygonalApproxAccuracyRate = 0.1 

try:
    while True:
        # Recibir imagen
        try:
            topic = socket_video.recv_string()
            frame_bytes = socket_video.recv()
            np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 0) # Girar si es necesario
        except:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        marker_found = False

        # Probar todos los diccionarios
        for name, dictionary in DICCIONARIOS.items():
            detector = aruco.ArucoDetector(dictionary, parameters)
            corners, ids, rejected = detector.detectMarkers(gray)
            
            if ids is not None:
                aruco.drawDetectedMarkers(frame, corners, ids)
                cv2.putText(frame, f"DETECTADO: {name}", (10, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                marker_found = True
                break # ¡Encontrado!
            
            # Si ve cuadrados pero no los lee, dibuja rojo (Usamos el 4x4 como referencia para rechazos)
            if name == "DICT_4X4_50" and len(rejected) > 0:
                aruco.drawDetectedMarkers(frame, rejected, borderColor=(0, 0, 255))

        if not marker_found:
             cv2.putText(frame, "Buscando...", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Diagnostico Unity", frame)
        if cv2.waitKey(1) == ord('q'): break

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    socket_video.close()
    context.term()