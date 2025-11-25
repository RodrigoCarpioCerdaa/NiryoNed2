import cv2
import cv2.aruco as aruco
import numpy as np
import zmq
import yaml

# --- 1. CONFIGURACIÓN (¡EDITA ESTO CON TUS DATOS DE UNITY!) ---

# Diccionario: Asegúrate de que los ArUcos 25-28 sean de este tipo (6x6_250)
ARUCO_DICT_TYPE = aruco.DICT_6X6_250 

# IDs de las esquinas
IDS_OBJETIVO = [25, 26, 27, 28]

# Coordenadas REALES en Unity (Metros) -> [X, Z]
# Mira el "Transform Position" de cada ArUco en Unity y ponlo aquí.
# IMPORTANTE: Unity usa metros. Si quieres trabajar en mm, multiplica por 1000 aquí.
PUNTOS_REALES_UNITY = {
    25: [1210.0, 2530.0],   
    26: [-1800.0, 2480.0],  
    27: [1210.0, 5890.0],   
    28: [-1800.0, 5890.0]   
}

NOMBRE_FICHERO = "homografia_robot.yml"

# --- 2. CONEXIÓN CON UNITY ---
context = zmq.Context()
socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556") 
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

# Detector
aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

print(f"✅ Conectado a Unity.")
print(f"🔍 Buscando IDs de calibración: {IDS_OBJETIVO}")
print("👉 Pulsa 'c' cuando se detecten los 4 para CALIBRAR.")
print("👉 Pulsa 'q' para SALIR.")

homography_matrix = None

try:
    while True:
        # Recibir imagen
        try:
            topic = socket_video.recv_string(flags=zmq.NOBLOCK)
            frame_bytes = socket_video.recv(flags=zmq.NOBLOCK)
            np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 1) # Girar imagen verticalmente
        except zmq.Again:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        # Lista para guardar qué IDs hemos encontrado en este frame
        ids_encontrados = []

        if ids is not None:
            # Dibujar TODOS los marcadores encontrados
            aruco.drawDetectedMarkers(frame, corners, ids)
            
            ids_flatten = ids.flatten()
            
            # Filtrar y mostrar info solo de los de calibración
            for id_obj in IDS_OBJETIVO:
                if id_obj in ids_flatten:
                    ids_encontrados.append(id_obj)
                    
                    # Buscar índice
                    index = np.where(ids_flatten == id_obj)[0][0]
                    c = corners[index][0]
                    
                    # Mostrar que este es de calibración
                    coord_real = PUNTOS_REALES_UNITY[id_obj]
                    cv2.putText(frame, f"CALIB {id_obj} {coord_real}", (int(c[0][0]), int(c[0][1]) - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Estado en pantalla
        num = len(ids_encontrados)
        color = (0, 0, 255) if num < 4 else (0, 255, 0)
        texto = f"Detectados para calibrar: {num}/4"
        if num == 4: texto += " (LISTO: Pulsa 'c')"
        
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("Calibrador Unity", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            if len(ids_encontrados) < 4:
                print(f"❌ Error: Solo veo {ids_encontrados}. Necesito los 4 a la vez.")
            else:
                # Recopilar puntos
                puntos_img = []
                puntos_obj = []
                
                for id_obj in IDS_OBJETIVO:
                    index = np.where(ids.flatten() == id_obj)[0][0]
                    c = corners[index][0]
                    
                    # Centro del marcador
                    center_x = np.mean(c[:, 0])
                    center_y = np.mean(c[:, 1])
                    
                    puntos_img.append([center_x, center_y])
                    puntos_obj.append(PUNTOS_REALES_UNITY[id_obj])

                # Calcular y guardar
                h, status = cv2.findHomography(np.array(puntos_img), np.array(puntos_obj))
                
                if h is not None:
                    print("\n✅ ¡CALIBRACIÓN EXITOSA!")
                    print("Matriz generada:")
                    print(h)
                    with open(NOMBRE_FICHERO, 'w') as f:
                        yaml.dump({'homography_matrix': h.tolist()}, f)
                    print(f"✅ Archivo '{NOMBRE_FICHERO}' guardado. Ya puedes usar el gemelo digital.")
                    break
                else:
                    print("❌ Fallo matemático.")

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    socket_video.close()
    context.term()