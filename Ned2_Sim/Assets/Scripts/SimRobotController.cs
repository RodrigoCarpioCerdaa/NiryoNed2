using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System.Globalization;

[System.Serializable]
public class RobotState
{
    public float[] joints; // Los 6 ángulos que manda Python
}

public class SimRobotController : MonoBehaviour
{
    [Header("🔌 Conexión")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float pollInterval = 0.05f; // 20 veces por segundo

    [Header("🤖 Configuración Visual")]
    public Transform[] jointTransforms; // Arrastra tus pivotes aquí
    public Vector3[] jointAxes;         // Configura tus ejes (Z=1, etc)
    public float smoothing = 20f;       // Velocidad de suavizado

    [Header("🕵️ Cotilleo (Debug)")]
    public bool mostrarDatosEnConsola = true; // ¿Quieres ver los logs?
    public bool soloImprimirSiCambia = true;  // Para no llenar la consola si está quieto

    // Estado interno
    private RobotState currentState = null;
    private string ultimoJsonRecibido = ""; // Para comparar si ha cambiado

    void Start()
    {
        Debug.Log("🚀 SimRobotController INICIADO. Empezando a escuchar al servidor...");
        StartCoroutine(PollLoop());
    }

    // --- 1. BUCLE DE ESCUCHA INFINITO ---
    IEnumerator PollLoop()
    {
        while (true)
        {
            using (UnityWebRequest www = UnityWebRequest.Get(serverUrl + "/get_state"))
            {
                yield return www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    string json = www.downloadHandler.text;

                    // --- EL CHIVATO ---
                    if (mostrarDatosEnConsola)
                    {
                        // Si "soloSiCambia" está activo, solo imprimimos si el JSON es nuevo
                        if (!soloImprimirSiCambia || json != ultimoJsonRecibido)
                        {
                            Debug.Log($"📥 RECIBIDO DE PYTHON: {json}");
                            ultimoJsonRecibido = json;
                        }
                    }
                    // ------------------

                    currentState = JsonUtility.FromJson<RobotState>(json);
                }
                else
                {
                    // Error de conexión (silenciado para no molestar si apagas el server)
                    // Debug.LogWarning("⚠️ Esperando a Python... " + www.error);
                }
            }

            yield return new WaitForSeconds(pollInterval);
        }
    }

    // --- 2. APLICAR MOVIMIENTO ---
    void Update()
    {
        if (currentState == null || currentState.joints == null) return;

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
}