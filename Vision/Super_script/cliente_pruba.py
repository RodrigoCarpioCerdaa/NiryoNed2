# Fichero: cliente_prueba.py
import zmq
import json

# --- 1. CONFIGURACIÓN DEL CLIENTE ---
context = zmq.Context()
# Creamos un socket de tipo SUBSCRIBER
socket = context.socket(zmq.SUB)
# Nos conectamos a la dirección del servidor. "localhost" es tu propio ordenador.
socket.connect("tcp://localhost:5555")
# Nos suscribimos a los mensajes con el "topic" (la etiqueta) "VisionData".
# Si no nos suscribimos, no recibiremos nada.
socket.subscribe("VisionData")

print("✅ Cliente de prueba iniciado. Escuchando mensajes del servidor...")
print("---------------------------------------------------------")

try:
    while True:
        # --- 2. RECIBIR Y PROCESAR DATOS ---
        # Esperamos a recibir un mensaje del servidor.
        # El mensaje viene en dos partes: el topic y los datos (payload).
        [topic, payload] = socket.recv_multipart()

        # Decodificamos el payload (que está en bytes) a una cadena de texto.
        mensaje_json = payload.decode('utf-8')
        
        # Convertimos la cadena de texto JSON a un diccionario de Python.
        datos = json.loads(mensaje_json)

        # Imprimimos los datos recibidos de una forma clara.
        if datos.get("forma") != "Ninguna":
            forma = datos.get("forma")
            color = datos.get("color")
            posicion = datos.get("posicion") # Esto serán píxeles: [cx, cy]
            
            print(f"📡 Dato Recibido: Se detectó un {forma} de color {color} en la posición de píxeles {posicion}")
        else:
            # También es útil saber cuándo no se detecta nada.
            print("... Esperando objeto ...")

except KeyboardInterrupt:
    print("\nCerrando el cliente.")
finally:
    socket.close()
    context.term()