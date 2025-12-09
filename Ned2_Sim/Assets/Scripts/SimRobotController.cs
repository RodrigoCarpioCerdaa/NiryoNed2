using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

[System.Serializable]
public class RobotState
{
    public float[] joints;
    public bool gripper;
    // Eliminado el campo 'cinta'
}

public class SimRobotController : MonoBehaviour
{
    [Header("🔌 Conexión")]
    public string serverUrl = "http://127.0.0.1:5000";
    public float frecuencia = 0.05f;

    [Header("🤖 Robot")]
    public Transform[] jointTransforms;
    public Vector3[] jointAxes;
    public float suavizado = 20f;

    [Header("🧲 Configuración Imán PRO")]
    public Transform gripperTransform;
    public float radioIman = 2.5f;
    public LayerMask capaObjetos;
    public string filtroTag = "Pieza";

    // Estado interno
    private RobotState estadoActual = null;
    private Transform objetoEnMano = null;

    void Start() { StartCoroutine(BucleRed()); }

    IEnumerator BucleRed()
    {
        while (true)
        {
            using (UnityWebRequest www = UnityWebRequest.Get(serverUrl + "/get_state"))
            {
                yield return www.SendWebRequest();
                if (www.result == UnityWebRequest.Result.Success)
                {
                    estadoActual = JsonUtility.FromJson<RobotState>(www.downloadHandler.text);

                    // 1. Mover Robot (Se hace en Update, aquí solo guardamos datos)

                    // 2. Controlar Imán
                    ControlarIman(estadoActual.gripper);

                    // Lógica de cinta eliminada completamente
                }
            }
            yield return new WaitForSeconds(frecuencia);
        }
    }

    void ControlarIman(bool encendido)
    {
        if (gripperTransform == null) return;

        if (encendido)
        {
            // ACTIVAR: Si no tengo nada, busco algo
            if (objetoEnMano == null)
            {
                Collider[] hits = Physics.OverlapSphere(gripperTransform.position, radioIman, capaObjetos);
                foreach (Collider hit in hits)
                {
                    // ¡FILTRO DE TAG! Solo cogemos lo que sea "Pieza"
                    if (hit.CompareTag(filtroTag))
                    {
                        objetoEnMano = hit.transform;

                        // Quitamos físicas para que no pese
                        var rb = objetoEnMano.GetComponent<Rigidbody>();
                        if (rb) rb.isKinematic = true;

                        // Lo pegamos a la mano
                        objetoEnMano.SetParent(gripperTransform);
                        objetoEnMano.localPosition = Vector3.zero;

                        Debug.Log($"🧲 IMÁN: Atrapado '{objetoEnMano.name}'");
                        return; // Ya tenemos uno, dejamos de buscar
                    }
                }
            }
        }
        else
        {
            // DESACTIVAR: Soltar
            if (objetoEnMano != null)
            {
                var rb = objetoEnMano.GetComponent<Rigidbody>();
                if (rb) rb.isKinematic = false; // Devuelve gravedad

                objetoEnMano.SetParent(null); // Lo suelta en el mundo
                Debug.Log($"💨 IMÁN: Soltado '{objetoEnMano.name}'");

                objetoEnMano = null;
            }
        }
    }

    void Update()
    {
        if (estadoActual == null || estadoActual.joints == null) return;

        int count = Mathf.Min(jointTransforms.Length, estadoActual.joints.Length);
        for (int i = 0; i < count; i++)
        {
            if (jointTransforms[i] == null) continue;

            float angulo = estadoActual.joints[i];
            Quaternion rot = Quaternion.Euler(jointAxes[i] * angulo);
            jointTransforms[i].localRotation = Quaternion.Slerp(
                jointTransforms[i].localRotation, rot, Time.deltaTime * suavizado
            );
        }
    }

    void OnDrawGizmos()
    {
        if (gripperTransform != null)
        {
            Gizmos.color = new Color(0, 1, 0, 0.2f);
            Gizmos.DrawSphere(gripperTransform.position, radioIman);
        }
    }
}