using System.Collections;
using UnityEngine;
using UnityEngine.Networking; // Para peticiones web

// Esta clase DEBE coincidir con el JSON que envía Python
// Python envía: {"joints": [0.0, ...]}
[System.Serializable]
public class RobotState
{
    public float[] joints;
}

public class SimRobotController : MonoBehaviour
{
    [Header("Configuración del Servidor")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float pollInterval = 0.05f; // Preguntar al servidor 20 veces/seg

    [Header("Articulaciones del Robot (Cuerpo)")]
    // Arrastra aquí los 6 GameObjects de tus articulaciones
    public Transform[] jointTransforms;

    [Header("Ejes de Rotación")]
    // Define el eje de rotación local para CADA articulación
    public Vector3[] jointAxes;

    // --- Estado Interno ---
    private RobotState currentState = new RobotState { joints = new float[6] };
    private bool stateUpdated = false;

    void Start()
    {
        // Inicia el bucle de "polling" para preguntar al servidor
        StartCoroutine(PollRobotState());
    }

    void Update()
    {
        // Si no hay 6 articulaciones o 6 ejes, no hagas nada
        if (jointTransforms.Length != 6 || jointAxes.Length != 6) return;

        // Si hemos recibido un estado nuevo, aplicamos los ángulos
        if (stateUpdated)
        {
            for (int i = 0; i < 6; i++)
            {
                if (jointTransforms[i] != null)
                {
                    // ¡Esta es la magia!
                    // Aplicamos la rotación desde el estado recibido
                    // sobre el eje que hemos definido
                    jointTransforms[i].localRotation = Quaternion.Euler(jointAxes[i] * currentState.joints[i]);
                }
            }
            stateUpdated = false; // Marcamos como aplicado
        }
    }

    // --- BUCLE DE POLLING ---

    IEnumerator PollRobotState()
    {
        while (true)
        {
            // Hacemos una petición GET a /get_state
            using (UnityWebRequest www = UnityWebRequest.Get(serverUrl + "/get_state"))
            {
                yield return www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    // Deserializamos el JSON
                    string jsonResponse = www.downloadHandler.text;
                    currentState = JsonUtility.FromJson<RobotState>(jsonResponse);
                    stateUpdated = true; // Marcamos que hay un estado nuevo
                }
                else
                {
                    Debug.LogWarning("Error al conectar con el servidor: " + www.error);
                }
            }

            // Esperamos el intervalo definido antes de volver a preguntar
            yield return new WaitForSeconds(pollInterval);
        }
    }

    // --- FUNCIONES DE COMANDO (Para Botones UI) ---

    public void SendHomeCommand()
    {
        Debug.Log("Enviando comando 'Home'...");
        StartCoroutine(PostRequest(serverUrl + "/home"));
    }

    public void SendRestCommand()
    {
        Debug.Log("Enviando comando 'Rest'...");
        StartCoroutine(PostRequest(serverUrl + "/rest"));
    }

    // Corutina genérica para enviar comandos POST
    IEnumerator PostRequest(string url)
    {
        using (UnityWebRequest www = UnityWebRequest.Post(url, new WWWForm()))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("Servidor respondió: " + www.downloadHandler.text);
            }
            else
            {
                Debug.LogWarning("Error al enviar comando: " + www.error);
            }
        }
    }
}