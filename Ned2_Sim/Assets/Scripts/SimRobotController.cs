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

    // Estado interno
    private RobotState currentState = null;

    void Start()
    {
        Debug.Log("🚀 SimRobotController INICIADO. Empezando a escuchar al servidor...");
        // Arrancamos el bucle infinito inmediatamente. Sin esperas.
        StartCoroutine(PollLoop());
    }

    // --- 1. BUCLE DE ESCUCHA INFINITO ---
    IEnumerator PollLoop()
    {
        while (true)
        {
            // Preguntamos al servidor: ¿Cómo debo estar?
            using (UnityWebRequest www = UnityWebRequest.Get(serverUrl + "/get_state"))
            {
                yield return www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    // ¡Dato recibido! Lo guardamos
                    string json = www.downloadHandler.text;
                    currentState = JsonUtility.FromJson<RobotState>(json);
                }
                else
                {
                    // Si falla, no paramos. Solo avisamos y seguimos intentando.
                    // (Comenta esta línea si te molesta el spam de errores cuando cierras Python)
                    // Debug.LogWarning("⚠️ Esperando a Python... " + www.error);
                }
            }

            // Esperamos un poquito antes de preguntar otra vez
            yield return new WaitForSeconds(pollInterval);
        }
    }

    // --- 2. APLICAR MOVIMIENTO ---
    void Update()
    {
        // Si aún no hemos recibido datos válidos, no hacemos nada
        if (currentState == null || currentState.joints == null) return;

        // Seguridad: Asegurarnos de que tenemos los objetos asignados
        int count = Mathf.Min(jointTransforms.Length, currentState.joints.Length);

        for (int i = 0; i < count; i++)
        {
            if (jointTransforms[i] != null)
            {
                // Leemos el ángulo que manda Python
                float targetAngle = currentState.joints[i];

                // Calculamos la rotación en el eje que tú configuraste
                Quaternion targetRot = Quaternion.Euler(jointAxes[i] * targetAngle);

                // Aplicamos Slerp para que se mueva suavemente
                jointTransforms[i].localRotation = Quaternion.Slerp(
                    jointTransforms[i].localRotation,
                    targetRot,
                    Time.deltaTime * smoothing
                );
            }
        }
    }
}