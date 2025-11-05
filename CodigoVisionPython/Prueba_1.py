import cv2
import numpy as np

# Iniciar la captura de video desde la camara web
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: No se pudo abrir la cámara.")
    exit()

# === RANGOS DE COLOR AJUSTADOS ===
# Rojo
rojo_bajo1 = np.array([0, 100, 80], np.uint8)
rojo_alto1 = np.array([10, 255, 255], np.uint8)
rojo_bajo2 = np.array([175, 100, 80], np.uint8)
rojo_alto2 = np.array([180, 255, 255], np.uint8)

# Azul
azul_bajo = np.array([95, 100, 50], np.uint8)
azul_alto = np.array([130, 255, 255], np.uint8)

# Verde (Más flexible para capturar diferentes tonos)
verde_bajo = np.array([35, 80, 20], np.uint8)
verde_alto = np.array([90, 255, 255], np.uint8)


while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo recibir el fotograma. Saliendo...")
        break

    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Crear máscaras de color
    mascara_rojo1 = cv2.inRange(hsv_frame, rojo_bajo1, rojo_alto1)
    mascara_rojo2 = cv2.inRange(hsv_frame, rojo_bajo2, rojo_alto2)
    mascara_rojo = cv2.add(mascara_rojo1, mascara_rojo2)
    mascara_azul = cv2.inRange(hsv_frame, azul_bajo, azul_alto)
    mascara_verde = cv2.inRange(hsv_frame, verde_bajo, verde_alto)

    colores = [("Rojo", mascara_rojo, (0, 0, 255)),
               ("Verde", mascara_verde, (0, 255, 0)),
               ("Azul", mascara_azul, (255, 0, 0))]

    for nombre_color, mascara, color_bgr in colores:
        mascara = cv2.erode(mascara, None, iterations=2)
        mascara = cv2.dilate(mascara, None, iterations=2)

        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contorno in contornos:
            area = cv2.contourArea(contorno)
            if area > 800:
                perimetro = cv2.arcLength(contorno, True)
                
                if perimetro == 0:
                    continue

                # Lógica de detección de formas por circularidad
                circularidad = (4 * np.pi * area) / (perimetro**2)
                
                nombre_forma = ""
                
                if circularidad > 0.83:
                    nombre_forma = "Circulo"
                elif 0.7 < circularidad < 0.83:
                    nombre_forma = "Cuadrado"

                if nombre_forma:
                    x, y, w, h = cv2.boundingRect(contorno)
                    cv2.drawContours(frame, [contorno], 0, color_bgr, 3)
                    texto = f"{nombre_forma} {nombre_color}"
                    cv2.putText(frame, texto, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2)

    cv2.imshow('Camara Original', frame)
    
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()