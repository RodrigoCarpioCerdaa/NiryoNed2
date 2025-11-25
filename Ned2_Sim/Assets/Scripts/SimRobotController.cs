using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System.Globalization; // Para que los decimales sean puntos (.)

// Clase para leer el JSON que manda Python
[System.Serializable]
public class RobotState
{
    public float[] joints; // Array de ángulos recibidos
}

public class SimRobotController : MonoBehaviour
{
    [Header("🔌 Conexión")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float pollInterval = 0.05f; // Frecuencia de lectura (20 veces/seg)

    [Header("🤖 Configuración del Robot")]
    // ¡Arrastra aquí tus Pivotes corregidos!
    public Transform[] jointTransforms;
    // ¡Pon aquí la configuración Z=1, X=1, etc.!
    public Vector3[] jointAxes;

    [Header("📍 Control Tiempo Real")]
    public Transform targetGhost;     // Arrastra aquí tu bola roja "Objetivo"
    public bool followTarget = false; // ¡ACTIVA ESTO PARA QUE TE SIGA!
    public float smoothing = 10f;     // Velocidad de suavizado visual

    // Estado interno
    private RobotState currentState = new RobotState();
    private bool isConnected = false;
    private float lastIKRequestTime = 0;

    // --- ARRANQUE ---
    void Start()
    {
        StartCoroutine(InitializeServer());
    }

    // FASE 1: LEER POSICIÓN INICIAL Y ENVIAR A PYTHON
    IEnumerator InitializeServer()
    {
        Debug.Log("🚀 Iniciando sincronización...");

        float[] startingJoints = new float[jointTransforms.Length];
        for (int i = 0; i < jointTransforms.Length; i++)
        {
            if (jointTransforms[i] != null)
                startingJoints[i] = GetAngleFromAxis(jointTransforms[i], jointAxes[i]);
        }

        RobotState initState = new RobotState();
        initState.joints = startingJoints;
        string jsonToSend = JsonUtility.ToJson(initState);

        using (UnityWebRequest www = new UnityWebRequest(serverUrl + "/set_home", "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonToSend);
            www.uploadHandler = new UploadHandlerRaw(bodyRaw);
            www.downloadHandler = new DownloadHandlerBuffer();
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("✅ Sincronización EXITOSA.");
                isConnected = true;
                StartCoroutine(PollRobotState());
            }
            else
            {
                Debug.LogError("❌ Error conexión Python: " + www.error);
            }
        }
    }

    // FASE 2: BUCLE DE ESCUCHA CONSTANTE
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

    // FASE 3: ACTUALIZACIÓN (VISUAL Y LÓGICA)
    void Update()
    {
        if (!isConnected) return;

        // A) MOVIMIENTO VISUAL SUAVE (INTERPOLACIÓN)
        if (currentState != null && currentState.joints != null)
        {
            int count = Mathf.Min(jointTransforms.Length, currentState.joints.Length);
            for (int i = 0; i < count; i++)
            {
                if (jointTransforms[i] != null)
                {
                    float targetAngle = currentState.joints[i];
                    // Calculamos la rotación objetivo
                    Quaternion targetRot = Quaternion.Euler(jointAxes[i] * targetAngle);

                    // Usamos Lerp para que vaya suavemente de donde está a donde debe ir
                    jointTransforms[i].localRotation = Quaternion.Lerp(
                        jointTransforms[i].localRotation,
                        targetRot,
                        Time.deltaTime * smoothing
                    );
                }
            }
        }

        // B) LÓGICA DE SEGUIMIENTO (TRACKING)
        if (followTarget && targetGhost != null)
        {
            // Limitamos los envíos a 10 veces por segundo (cada 0.1s) para no saturar
            if (Time.time - lastIKRequestTime > 0.1f)
            {
                lastIKRequestTime = Time.time;
                // Enviamos duración 0.0 para que Python calcule instantáneo
                StartCoroutine(SendIKRequest(targetGhost.localPosition.x,
                                             targetGhost.localPosition.y,
                                             targetGhost.localPosition.z,
                                             0.0f));
            }
        }
    }

    // FASE 4: ENVÍO DE COMANDOS IK
    public void SendIKCommand()
    {
        // Botón manual: Mueve despacio (2 segundos)
        if (targetGhost != null)
            StartCoroutine(SendIKRequest(targetGhost.localPosition.x, targetGhost.localPosition.y, targetGhost.localPosition.z, 2.0f));
    }

    IEnumerator SendIKRequest(float x, float y, float z, float duration)
    {
        // --- TRADUCCIÓN DE EJES (UNITY -> ROBOT) ---
        // Unity Z (Fondo)  -> Robot X (Adelante)
        // Unity -X (Lado)  -> Robot Y (Lado)
        // Unity Y (Altura) -> Robot Z (Altura)

        float robotX = z;
        float robotY = -x;
        float robotZ = y;

        string json = string.Format(CultureInfo.InvariantCulture,
            "{{\"x\":{0}, \"y\":{1}, \"z\":{2}, \"duration\":{3}}}",
            robotX, robotY, robotZ, duration);

        using (UnityWebRequest www = new UnityWebRequest(serverUrl + "/calculate_ik", "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(json);
            www.uploadHandler = new UploadHandlerRaw(bodyRaw);
            www.downloadHandler = new DownloadHandlerBuffer();
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            // No imprimimos log aquí para no llenar la consola en modo seguimiento
        }
    }

    // --- UTILIDADES ---
    public void ToggleTracking(bool status) { followTarget = status; }
    public void SendHomeCommand() { StartCoroutine(SimplePost("/home")); }
    public void SendRestCommand() { StartCoroutine(SimplePost("/rest")); }

    IEnumerator SimplePost(string endpoint)
    {
        using (UnityWebRequest www = UnityWebRequest.Post(serverUrl + endpoint, new WWWForm()))
        {
            yield return www.SendWebRequest();
        }
    }

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