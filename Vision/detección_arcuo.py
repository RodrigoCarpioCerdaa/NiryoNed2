import cv2
import cv2.aruco as aruco
import numpy as np

# --- CONFIGURACIÓN DE DICCIONARIOS A PROBAR ---
# Vamos a probar los diccionarios más comunes que existen en internet
DICCIONARIOS = {
    "DICT_4X4_50": aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
    "DICT_5X5_100": aruco.getPredefinedDictionary(aruco.DICT_5X5_100),
    "DICT_6X6_250": aruco.getPredefinedDictionary(aruco.DICT_6X6_250),
    "DICT_ARUCO_ORIGINAL": aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
}

# Parámetros de detección (ajustados para ser más tolerantes)
parameters = aruco.DetectorParameters()
parameters.polygonalApproxAccuracyRate = 0.05 # Más tolerancia a formas no perfectas

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error al abrir la cámara")
    exit()

print("Buscando ArUcos en múltiples diccionarios...")
print("Cuadrados ROJOS: Formas cuadradas detectadas (pero ID desconocido)")
print("Cuadrados VERDES: Marcador identificado correctamente")

while True:
    ret, frame = cap.read()
    if not ret: break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    marker_found = False
    detected_dict_name = ""
    
    # Iteramos por los diccionarios para ver cuál es el de tu papel
    for name, dictionary in DICCIONARIOS.items():
        # Crear el detector con el diccionario actual
        detector = aruco.ArucoDetector(dictionary, parameters)
        
        # Detectar
        corners, ids, rejected = detector.detectMarkers(gray)
        
        # Si encontramos algo válido, dejamos de buscar en otros diccionarios
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            marker_found = True
            detected_dict_name = name
            
            # Mostrar qué diccionario funcionó
            cv2.putText(frame, f"DETECTADO: {name}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Mostrar IDs
            for i, corner in enumerate(corners):
                c = corner[0][0]
                cv2.putText(frame, f"ID: {ids[i][0]}", (int(c[0]), int(c[1]) - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            break # Salimos del bucle for porque ya lo encontramos
        
        # Si no encontramos ID, dibujamos los "rechazados" en rojo (solo para el primer diccionario para no ensuciar)
        if name == "DICT_4X4_50" and len(rejected) > 0:
             aruco.drawDetectedMarkers(frame, rejected, borderColor=(0, 0, 255))

    if not marker_found:
        cv2.putText(frame, "Buscando...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Diagnostico ArUco", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()