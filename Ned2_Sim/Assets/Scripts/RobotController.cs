using UnityEngine;
using NetMQ;
using NetMQ.Sockets;
using System.Threading;

public class RobotController : MonoBehaviour
{
    private Thread clientThread;
    private bool isRunning;

    void Start()
    {
        AsyncIO.ForceDotNet.Force();
        isRunning = true;
        clientThread = new Thread(NetMQClient);
        clientThread.Start();
        Debug.Log("Cliente ZMQ iniciado. Esperando datos...");
    }

    private void NetMQClient()
    {
        using (var subSocket = new SubscriberSocket())
        {
            subSocket.Connect("tcp://localhost:5555");
            subSocket.Subscribe("VisionData");
            
            while (isRunning)
            {
                // --- CORRECCIÓN DEL ERROR AQUÍ ---
                // En lugar de intentar leer todo a la vez, leemos paso a paso.
                
                string topic;
                // 1. Intentamos recibir la primera parte (la etiqueta "VisionData")
                if (subSocket.TryReceiveFrameString(out topic))
                {
                    // 2. Si recibimos la etiqueta, leemos inmediatamente la segunda parte (el JSON)
                    string payload;
                    if (subSocket.TryReceiveFrameString(out payload))
                    {
                        // Enviamos el JSON al hilo principal de Unity
                        UnityMainThreadDispatcher.Instance().Enqueue(() => {
                            ProcesarDatos(payload);
                        });
                    }
                }
                // Pequeña pausa para no saturar la CPU si no hay mensajes
                Thread.Sleep(10);
            }
        }
    }

    void ProcesarDatos(string json)
    {
        try
        {
            VisionData datos = JsonUtility.FromJson<VisionData>(json);

            if (datos.objeto_encontrado)
            {
                // Mostramos solo el color y la forma para verificar
                Debug.Log($"Recibido: {datos.forma} {datos.color}");

                if (datos.calibrado)
                {
                    // Aquí tenemos las coordenadas reales
                    float x = datos.posicion[0];
                    float y = datos.posicion[1];
                    Debug.Log($"<color=green>MOVER ROBOT A:</color> X={x}, Y={y} mm");
                    
                    // AQUÍ IRÁ TU CÓDIGO DE MOVIMIENTO REAL
                }
                else
                {
                    Debug.Log($"<color=yellow>Datos en Píxeles:</color> [{datos.posicion[0]}, {datos.posicion[1]}] (Falta calibrar)");
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError("Error leyendo JSON: " + e.Message);
        }
    }

    void OnDestroy()
    {
        isRunning = false;
        if (clientThread != null) clientThread.Join();
        NetMQConfig.Cleanup();
    }
}