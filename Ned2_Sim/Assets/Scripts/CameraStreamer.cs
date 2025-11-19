using UnityEngine;
using NetMQ;
using NetMQ.Sockets;
using System.Threading;
using System; // Necesario para TimeSpan

public class CameraStreamer : MonoBehaviour
{
    public Camera camaraSimulada; 
    public int resolucionAncho = 640;
    public int resolucionAlto = 480;

    private PublisherSocket pubSocket;
    private Thread streamThread;
    private volatile bool isRunning; // 'volatile' asegura que el hilo lo lea bien
    private byte[] currentImageJpg;
    private bool newImageReady = false;

    void Start()
    {
        AsyncIO.ForceDotNet.Force();
        
        RenderTexture rt = new RenderTexture(resolucionAncho, resolucionAlto, 24);
        camaraSimulada.targetTexture = rt;

        isRunning = true;
        streamThread = new Thread(NetworkLoop);
        streamThread.Start();
    }

    void Update()
    {
        if (camaraSimulada.targetTexture != null)
        {
            RenderTexture.active = camaraSimulada.targetTexture;
            Texture2D image = new Texture2D(resolucionAncho, resolucionAlto, TextureFormat.RGB24, false);
            image.ReadPixels(new Rect(0, 0, resolucionAncho, resolucionAlto), 0, 0);
            image.Apply();
            
            currentImageJpg = image.EncodeToJPG(100); 
            newImageReady = true;
            Debug.Log("📸 Foto tomada. Tamaño: " + currentImageJpg.Length + " bytes"); // <--- NUEVO
            Destroy(image);
        }
    }

    void NetworkLoop()
    {
        try 
        {
            using (pubSocket = new PublisherSocket())
            {
                pubSocket.Options.SendHighWatermark = 1; // Evita acumular mensajes si nadie escucha
                pubSocket.Bind("tcp://*:5556"); 
                
                while (isRunning)
                {
                    if (newImageReady && currentImageJpg != null)
                    {
                        // --- CAMBIO CLAVE: TrySendFrame ---
                        // Intentamos enviar durante máximo 50ms. Si no se puede, pasamos.
                        // Esto evita que el hilo se quede congelado intentando enviar.
                        bool exito = pubSocket.TrySendFrame("Video", true); // SendMore
                        if (exito) 
                        {
                            pubSocket.TrySendFrame(currentImageJpg); // SendFrame
                        }
                        
                        newImageReady = false;
                    }
                    Thread.Sleep(30); 
                }
            }
        }
        catch (Exception e)
        {
            // Si hay error al cerrar, solo lo mostramos en consola pero no bloqueamos
            Debug.LogWarning("Hilo de red cerrado: " + e.Message);
        }
    }

    // --- LA PARTE MÁS IMPORTANTE: EL CIERRE SEGURO ---
    void OnDestroy()
    {
        isRunning = false;
        
        // Si el hilo existe, le damos 200ms para que se cierre por las buenas
        if (streamThread != null) 
        {
            if(!streamThread.Join(200)) 
            {
                // Si en 200ms no se ha cerrado, forzamos la salida (Abort es brusco pero necesario a veces)
                // En versiones modernas de .NET Abort no se usa, así que confiamos en NetMQConfig.Cleanup
                Debug.LogWarning("El hilo de red tardó en cerrar, forzando limpieza...");
            }
        }

        // Limpiamos NetMQ con 'false' para que no espere a mensajes pendientes
        NetMQConfig.Cleanup(false);
    }
}