import cv2
import numpy as np
import zmq
import json
import yaml # Para cargar la matriz de calibración

# --- 1. CONFIGURACIÓN DEL SERVIDOR Y CALIBRACIÓN ---
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")
print("✅ Servidor de visión iniciado. Esperando al cliente de Unity en el puerto 5555...")

# (El código para cargar la calibración se mantiene igual)
try:
    with open("homografia_robot.yml", 'r') as f:
        data = yaml.safe_load(f)
        HOMOGRAPHY_MATRIX = np.array(data['homografia_matrix'])
    print("✅ Matriz de calibración cargada. Se enviarán coordenadas en milímetros.")
    CALIBRADO = True
except FileNotFoundError:
    print("⚠️  ADVERTENCIA: No se encontró 'homografia_robot.yml'. Se enviarán coordenadas en píxeles.")
    CALIBRADO = False

# --- 2. CÓDIGO DE VISIÓN POR COMPUTADOR ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Error: No se pudo abrir la cámara.")
    exit()

# (Los rangos de color se mantienen igual)
rojo_bajo1 = np.array([0, 100, 80], np.uint8)
rojo_alto1 = np.array([10, 255, 255], np.uint8)
rojo_bajo2 = np.array([175, 100, 80], np.uint8)
rojo_alto2 = np.array([180, 255, 255], np.uint8)
azul_bajo = np.array([95, 100, 50], np.uint8)
azul_alto = np.array([130, 255, 255], np.uint8)
verde_bajo = np.array([35, 80, 20], np.uint8)
verde_alto = np.array([90, 255, 255], np.uint8)

print("🚀 Cámara iniciada. Buscando objetos para transmitir...")

try:
    while True:
        ret, frame = cap.read()
        if not ret: break

        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # (El resto del código de detección es igual...)
        mascara_rojo1 = cv2.inRange(hsv_frame, rojo_bajo1, rojo_alto1); mascara_rojo2 = cv2.inRange(hsv_frame, rojo_bajo2, rojo_alto2); mascara_rojo = cv2.add(mascara_rojo1, mascara_rojo2); mascara_azul = cv2.inRange(hsv_frame, azul_bajo, azul_alto); mascara_verde = cv2.inRange(hsv_frame, verde_bajo, verde_alto)
        colores = [("Rojo", mascara_rojo, (0, 0, 255)), ("Verde", mascara_verde, (0, 255, 0)), ("Azul", mascara_azul, (255, 0, 0))]
        objeto_encontrado = False

        for nombre_color, mascara, color_bgr in colores:
            mascara = cv2.erode(mascara, None, iterations=2); mascara = cv2.dilate(mascara, None, iterations=2)
            contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contorno in contornos:
                area = cv2.contourArea(contorno)
                if area > 800:
                    perimetro = cv2.arcLength(contorno, True)
                    if perimetro == 0: continue
                    circularidad = (4 * np.pi * area) / (perimetro**2)
                    nombre_forma = ""
                    if circularidad > 0.83: nombre_forma = "Circulo"
                    elif 0.7 < circularidad < 0.83: nombre_forma = "Cuadrado"
                    if nombre_forma:
                        x, y, w, h = cv2.boundingRect(contorno)
                        cx = x + w // 2; cy = y + h // 2
                        
                        posicion_final = [cx, cy]
                        if CALIBRADO:
                            pixel_coords = np.array([[[cx, cy]]], dtype=np.float32)
                            real_coords = cv2.perspectiveTransform(pixel_coords, HOMOGRAPHY_MATRIX)
                            posicion_final = [round(real_coords[0][0][0], 2), round(real_coords[0][0][1], 2)]
                        
                        datos_a_enviar = {"forma": nombre_forma, "color": nombre_color, "posicion": posicion_final, "calibrado": CALIBRADO}
                        mensaje_json = json.dumps(datos_a_enviar)
                        
                        # ===== CAMBIO IMPORTANTE AQUÍ =====
                        socket.send_multipart([b"VisionData", mensaje_json.encode('utf-8')])
                        
                        objeto_encontrado = True
                        cv2.drawContours(frame, [contorno], 0, color_bgr, 3)
                        texto = f"{nombre_forma} {nombre_color}"
                        cv2.putText(frame, texto, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2)
                        break
            if objeto_encontrado: break

        if not objeto_encontrado:
            datos_nulos = {"forma": "Ninguna", "calibrado": CALIBRADO}
            mensaje_json = json.dumps(datos_nulos)
            
            # ===== CAMBIO IMPORTANTE AQUÍ =====
            socket.send_multipart([b"VisionData", mensaje_json.encode('utf-8')])

        cv2.imshow('Servidor de Vision', frame)
        if cv2.waitKey(1) == ord('q'): break
finally:
    print("\nCerrando el servidor.")
    cap.release()
    cv2.destroyAllWindows()
    socket.close()
    context.term()