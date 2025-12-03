using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Text;
using System.Globalization;

[System.Serializable]
public class RobotState
{
    public float[] joints;
}

public class SimRobotController : MonoBehaviour
{
    [Header("🔌 Conexión")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float pollInterval = 0.05f;

    [Header("🤖 Configuración del Robot")]
    // IMPORTANTE: Recuerda configurar aquí los Pivotes y los Ejes en el Inspector
    // Base(Y=1), Hombro(Z=1), Codo(Z=1), Antebrazo(X=1), Muñeca(Z=1), Mano(X=1)
    public Transform[] jointTransforms;
    public Vector3[] jointAxes;

    [Header("📍 Control Tiempo Real")]
    public Transform targetGhost;
    public bool followTarget = false;
    public float smoothing = 10f;

    private RobotState currentState = new RobotState();
    private bool isConnected = false;
    private float lastIKRequestTime = 0;

    void Start()
    {
        StartCoroutine(InitializeServer());
    }

    // --- 1. CONEXIÓN INICIAL ---
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

    // --- 2. BUCLE DE LECTURA ---
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

    // --- 3. MOVIMIENTO VISUAL ---
    void Update()
    {
        if (!isConnected) return;

        // Mover articulaciones
        if (currentState != null && currentState.joints != null)
        {
            int count = Mathf.Min(jointTransforms.Length, currentState.joints.Length);
            for (int i = 0; i < count; i++)
            {
                if (jointTransforms[i] != null)
                {
                    float targetAngle = currentState.joints[i];
                    Quaternion targetRot = Quaternion.Euler(jointAxes[i] * targetAngle);

                    jointTransforms[i].localRotation = Quaternion.Slerp(
                        jointTransforms[i].localRotation,
                        targetRot,
                        Time.deltaTime * smoothing
                    );
                }
            }
        }

        // Tracking manual con la bola fantasma (si está activado)
        if (followTarget && targetGhost != null)
        {
            if (Time.time - lastIKRequestTime > 0.05f)
            {
                lastIKRequestTime = Time.time;
                // Envío con duración 0.0 para respuesta rápida
                StartCoroutine(SendIKRequest(targetGhost.localPosition.x,
                                             targetGhost.localPosition.y,
                                             targetGhost.localPosition.z,
                                             0.0f));
            }
        }
    }

    // --- 4. NUEVA FUNCIÓN PÚBLICA (Para el script de Visión) ---
    // Esta es la que llama RobotController.cs
    public void MoveToPosition(float x, float y, float z)
    {
        // Desactivamos el "Follow Target" manual para que no interfiera
        followTarget = false;

        // Enviamos la orden con una duración suave (ej. 0.5s o 1.0s) para que no sea un teletransporte
        StartCoroutine(SendIKRequest(x, y, z, 0.5f));
    }

    // --- 5. ENVÍO AL SERVIDOR ---
    IEnumerator SendIKRequest(float x, float y, float z, float duration)
    {
        // TRADUCTOR DE EJES (Unity -> Robot)
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
        }
    }

    // --- UTILIDADES ---
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