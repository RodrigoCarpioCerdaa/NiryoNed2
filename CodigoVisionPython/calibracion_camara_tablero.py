# Fichero: calibrar_con_portatil.py
import cv2
import numpy as np

# --- CONFIGURACIÓN ---
# Define el tamaño de tu tablero (cuenta las esquinas interiores)
# Corregido para un tablero de 8x5 cuadrados
NUMERO_ESQUINAS_ANCHO = 7
NUMERO_ESQUINAS_ALTO = 4

print("Iniciando prueba de detección de tablero...")
print("Apunta con la cámara al tablero IMPRESO EN PAPEL.")
print("Presiona 'q' para salir.")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: No se puede acceder a la cámara.")
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Buscar las esquinas del tablero
    ret_corners, corners = cv2.findChessboardCorners(gray, (NUMERO_ESQUINAS_ANCHO, NUMERO_ESQUINAS_ALTO), None)
    
    # Si se encontraron las esquinas, dibujarlas sobre la imagen
    if ret_corners:
        cv2.drawChessboardCorners(frame, (NUMERO_ESQUINAS_ANCHO, NUMERO_ESQUINAS_ALTO), corners, ret_corners)
        cv2.putText(frame, "¡TABLERO DETECTADO!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Buscando tablero...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Prueba de Deteccion de Tablero", frame)
    
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()