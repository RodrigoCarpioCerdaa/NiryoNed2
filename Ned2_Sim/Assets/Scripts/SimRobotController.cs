using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System.Globalization; // Importante para que los decimales sean puntos (.) y no comas (,)

// Clase para leer el JSON que manda Python
[System.Serializable]
public class RobotState
{
    public float[] joints; // Array de ángulos
}

public class SimRobotController : MonoBehaviour
{
    [Header("🔌 Conexión")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float pollInterval = 0.1f;

    [Header("🤖 Configuración del Robot")]
    // IMPORTANTE: Arrastra aquí los "Pivotes" o "Cajas Padre" si hiciste el truco
    public Transform[] jointTransforms;
    // IMPORTANTE: Configura aquí los Ejes (X=1, Y=0, etc.)
    public Vector3[] jointAxes;

    [Header("📍 Pruebas de IK (Coordenadas)")]
    public float targetX = 0.3f;
    public float targetY = 0.0f;
    public float targetZ = 0.2f;

    // Estado interno
    private RobotState currentState = new RobotState();
    private bool isConnected = false;

    void Start()
    {
        // Al arrancar, leemos la pose visual de Unity y se la mandamos a Python
        // para que el "Home" sea la posición actual.
        StartCoroutine(InitializeServer());
    }

    // --- FASE 1: INICIALIZACIÓN (SET HOME) ---
    IEnumerator InitializeServer()
    {
        Debug.Log("🚀 Iniciando sincronización con el servidor...");

        // 1. Leer ángulos actuales de Unity
        float[] startingJoints = new float[jointTransforms.Length];
        for (int i = 0; i < jointTransforms.Length; i++)
        {
            if (jointTransforms[i] != null)
            {
                startingJoints[i] = GetAngleFromAxis(jointTransforms[i], jointAxes[i]);
            }
        }

        // 2. Preparar el JSON
        RobotState initState = new RobotState();
        initState.joints = startingJoints;
        string jsonToSend = JsonUtility.ToJson(initState);

        // 3. Enviar a Python (/set_home)
        using (UnityWebRequest www = new UnityWebRequest(serverUrl + "/set_home", "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonToSend);
            www.uploadHandler = new UploadHandlerRaw(bodyRaw);
            www.downloadHandler = new DownloadHandlerBuffer();
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("✅ Sincronización EXITOSA. Robot listo.");
                isConnected = true;
                // Arrancamos el bucle de escucha
                StartCoroutine(PollRobotState());
            }
            else
            {
                Debug.LogError("❌ Error al conectar con Python: " + www.error);
            }
        }
    }

    // --- FASE 2: BUCLE DE ESCUCHA (POLLING) ---
    IEnumerator PollRobotState()
    {
        while (isConnected)
        {
            using (UnityWebRequest www = UnityWebRequest.Get(serverUrl + "/get_state"))
            {
                yield return www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    currentState = JsonUtility.FromJson<RobotState>(www.downloadHandler.text);
                }
            }
            yield return new WaitForSeconds(pollInterval);
        }
    }

    // --- FASE 3: ACTUALIZAR VISUALES (UPDATE) ---
    void Update()
    {
        if (!isConnected || currentState == null || currentState.joints == null) return;

        int count = Mathf.Min(jointTransforms.Length, currentState.joints.Length);

        for (int i = 0; i < count; i++)
        {
            if (jointTransforms[i] != null)
            {
                // Aplicamos la rotación: Eje * Ángulo recibido
                float angle = currentState.joints[i];
                jointTransforms[i].localRotation = Quaternion.Euler(jointAxes[i] * angle);
            }
        }
    }

    // --- FASE 4: CINEMÁTICA INVERSA (MOVER A POSICIÓN) ---

    // Función para llamar desde un Botón de UI
    public void SendIKCommand()
    {
        // Usa los valores que hayas puesto en el Inspector (Header "Pruebas de IK")
        Debug.Log($"📐 Solicitando IK a: X={targetX}, Y={targetY}, Z={targetZ}");
        StartCoroutine(SendIKRequest(targetX, targetY, targetZ));
    }

    // Función para llamar desde código
    public void MoveToPosition(float x, float y, float z)
    {
        StartCoroutine(SendIKRequest(x, y, z));
    }

    IEnumerator SendIKRequest(float x, float y, float z)
    {
        // Creamos el JSON manual para asegurar formato de punto (0.5 no 0,5)
        string json = string.Format(CultureInfo.InvariantCulture,
                                    "{{\"x\":{0}, \"y\":{1}, \"z\":{2}}}", x, y, z);

        using (UnityWebRequest www = new UnityWebRequest(serverUrl + "/calculate_ik", "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(json);
            www.uploadHandler = new UploadHandlerRaw(bodyRaw);
            www.downloadHandler = new DownloadHandlerBuffer();
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("✅ Movimiento IK calculado y enviado.");
                // Python actualizará su estado interno, y nosotros lo leeremos en el próximo Poll()
            }
            else
            {
                Debug.LogError("❌ Error IK: " + www.error + " " + www.downloadHandler.text);
            }
        }
    }

    // --- BOTONES DE CONTROL MANUAL ---
    public void SendHomeCommand() { StartCoroutine(SimplePost("/home")); }
    public void SendRestCommand() { StartCoroutine(SimplePost("/rest")); }

    IEnumerator SimplePost(string endpoint)
    {
        using (UnityWebRequest www = UnityWebRequest.Post(serverUrl + endpoint, new WWWForm()))
        {
            yield return www.SendWebRequest();
        }
    }

    // --- AYUDANTES ---
    float GetAngleFromAxis(Transform t, Vector3 axis)
    {
        float angle = 0;
        if (Mathf.Abs(axis.x) > 0.5f) angle = t.localEulerAngles.x;
        else if (Mathf.Abs(axis.y) > 0.5f) angle = t.localEulerAngles.y;
        else if (Mathf.Abs(axis.z) > 0.5f) angle = t.localEulerAngles.z;

        if (angle > 180) angle -= 360;
        if (axis.x < -0.1f || axis.y < -0.1f || axis.z < -0.1f) angle = -angle;
        return angle;
    }
}