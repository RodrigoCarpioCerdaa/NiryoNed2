import cv2
import cv2.aruco as aruco
import numpy as np
import zmq
import yaml

# --- 1. CONFIGURACIÓN ---
# Tipo de diccionario ArUco (Ajusta si usas otro en Unity)
ARUCO_DICT_TYPE = aruco.DICT_6X6_250

# IDs de los marcadores que usas para calibrar (Esquinas del campo)
IDS_OBJETIVO = [25, 26, 27, 28]

# Coordenadas REALES en Unity (X, Z)
# IMPORTANTE: Usa las coordenadas GLOBALES (transform.position) de cada ArUco.
# CORREGIDO: Pasado a METROS (dividido por 1000 respecto a la versión anterior)
PUNTOS_REALES_UNITY = {
    25: [1.210, 2.530],
    26: [-1.800, 2.480],
    27: [1.210, 5.890],
    28: [-1.800, 5.890]
}

NOMBRE_FICHERO = "homografia_robot.yml"

# --- 2. CONEXIÓN ZMQ (Recibir vídeo de Unity) ---
context = zmq.Context()
socket_video = context.socket(zmq.SUB)
socket_video.connect("tcp://localhost:5556")
socket_video.setsockopt_string(zmq.SUBSCRIBE, "Video")

# --- 3. CONFIGURACIÓN DETECTOR ---
aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
parameters = aruco.DetectorParameters()
# Refinamiento Subpixel: Crucial para precisión en entornos virtuales
parameters.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Variables globales
homography_matrix = None
punto_test_click = None  # Guarda las coordenadas del último clic del usuario


def on_mouse_click(event, x, y, flags, param):
    """Captura el clic del usuario para testear coordenadas."""
    global punto_test_click
    if event == cv2.EVENT_LBUTTONDOWN:
        punto_test_click = (x, y)


def calcular_posicion_global(h_matrix, x, y):
    """Traduce un píxel (x,y) a Coordenada Global Unity usando la matriz."""
    if h_matrix is None: return None

    # Formato necesario para perspectiveTransform: Array de forma (1, 1, 2)
    punto_pixel = np.array([[[x, y]]], dtype=np.float32)
    punto_global = cv2.perspectiveTransform(punto_pixel, h_matrix)

    return punto_global[0][0]  # Devuelve [X, Z]


def calcular_error_reproyeccion(h_matrix, puntos_img, puntos_unity_reales):
    """Calcula cuánto se equivoca la matriz en píxeles (RMS)."""
    if h_matrix is None: return 0.0
    try:
        h_inv = np.linalg.inv(h_matrix)
    except np.linalg.LinAlgError:
        return 9999.0

    pts_real_np = np.array(puntos_unity_reales, dtype=np.float32).reshape(-1, 1, 2)
    pts_proyectados_img = cv2.perspectiveTransform(pts_real_np, h_inv)

    error_total = 0
    for i in range(len(puntos_img)):
        p_detectado = puntos_img[i]
        p_calculado = pts_proyectados_img[i][0]
        dist = np.linalg.norm(p_detectado - p_calculado)
        error_total += dist * dist

    return np.sqrt(error_total / len(puntos_img))


# --- INICIO DE VENTANA Y CALLBACKS ---
cv2.namedWindow("Calibrador Unity VIRTUAL")
cv2.setMouseCallback("Calibrador Unity VIRTUAL", on_mouse_click)

print(f"✅ Conectado a Unity.")
print(f"🎯 IDs objetivo: {IDS_OBJETIVO}")
print("👉 Pulsa 'c' para CALIBRAR cuando se vean los 4 marcadores.")
print("👉 Una vez calibrado, haz CLIC en la imagen para ver coordenadas globales.")
print("👉 Pulsa 's' para GUARDAR la matriz y salir.")
print("👉 Pulsa 'q' para SALIR sin guardar.")

try:
    while True:
        # --- RECEPCIÓN DE IMAGEN ---
        try:
            topic = socket_video.recv_string(flags=zmq.NOBLOCK)
            frame_bytes = socket_video.recv(flags=zmq.NOBLOCK)
            np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 1)  # Espejo vertical si es necesario
        except zmq.Again:
            continue

        # --- DETECCIÓN ARUCO ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        puntos_img_actuales = []
        puntos_unity_ordenados = []

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            ids_flatten = ids.flatten()

            # Verificar si tenemos los 4 marcadores de calibración
            if all(id_obj in ids_flatten for id_obj in IDS_OBJETIVO):
                for id_obj in IDS_OBJETIVO:
                    index = np.where(ids_flatten == id_obj)[0][0]
                    c = corners[index][0]
                    center = np.mean(c, axis=0)

                    puntos_img_actuales.append(center)
                    puntos_unity_ordenados.append(PUNTOS_REALES_UNITY[id_obj])

                estado_texto = "LISTO PARA CALIBRAR (4/4) -> Pulsa 'C'"
                color_texto = (0, 255, 0)  # Verde
            else:
                faltan = [id_o for id_o in IDS_OBJETIVO if id_o not in ids_flatten]
                estado_texto = f"Buscando IDs: {faltan}"
                color_texto = (0, 0, 255)  # Rojo
        else:
            estado_texto = "Esperando señal ArUco..."
            color_texto = (0, 0, 255)

        # --- INTERFAZ DE USUARIO ---

        # Si ya está calibrado, mostramos herramientas de diagnóstico
        if homography_matrix is not None:
            cv2.putText(frame, "MODO DIAGNOSTICO ACTIVADO", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # 1. Si el usuario ha hecho clic, calculamos y mostramos la coordenada
            if punto_test_click is not None:
                ux, uy = punto_test_click
                # Dibujar cruz donde se hizo clic
                cv2.drawMarker(frame, (ux, uy), (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

                # Calcular coordenada GLOBAL
                coord_global = calcular_posicion_global(homography_matrix, ux, uy)

                texto_coord = f"Unity Global: X={coord_global[0]:.3f}, Z={coord_global[1]:.3f}"

                # Fondo negro para el texto para que se lea bien
                cv2.rectangle(frame, (ux + 10, uy - 25), (ux + 350, uy + 5), (0, 0, 0), -1)
                cv2.putText(frame, texto_coord, (ux + 10, uy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)

        # Mostrar estado general
        cv2.putText(frame, estado_texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_texto, 2)

        cv2.imshow("Calibrador Unity VIRTUAL", frame)

        # --- CONTROL DE TECLADO ---
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('c'):
            if len(puntos_img_actuales) == 4:
                print("Calculando homografía...")
                h, status = cv2.findHomography(np.array(puntos_img_actuales),
                                               np.array(puntos_unity_ordenados))

                error = calcular_error_reproyeccion(h, puntos_img_actuales, puntos_unity_ordenados)
                print(f"--------------------------------------------------")
                print(f"📊 RESULTADO CALIBRACIÓN")
                print(f"   Error RMS: {error:.4f} píxeles")
                if error < 2.0:
                    print("   ✅ Calidad: EXCELENTE")
                else:
                    print("   ⚠️ Calidad: REVISABLE (¿Están bien las coords en el script?)")
                print(f"--------------------------------------------------")

                homography_matrix = h
            else:
                print("❌ No veo los 4 marcadores necesarios.")

        elif key == ord('s') and homography_matrix is not None:
            with open(NOMBRE_FICHERO, 'w') as f:
                yaml.dump({'homography_matrix': homography_matrix.tolist()}, f)
            print(f"💾 Archivo '{NOMBRE_FICHERO}' guardado correctamente.")
            break

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    socket_video.close()
    context.term()