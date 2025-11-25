using UnityEngine;

public class TargetMover : MonoBehaviour
{
    // Creamos un "Enum" para que salga la lista desplegable en el Inspector
    public enum MoveMode
    {
        Manual_Teclado,  // Tú controlas con WASD
        Automatico_Bucle // La bola se mueve sola
    }

    [Header("Configuración Principal")]
    [Tooltip("Elige aquí si quieres moverla tú o que se mueva sola")]
    public MoveMode modoDeMovimiento = MoveMode.Manual_Teclado;

    public float velocidad = 3.0f;

    [Header("Solo para Modo Automático")]
    [Tooltip("Distancia máxima que se alejará del centro")]
    public float distanciaAuto = 1.5f;

    [Tooltip("Eje en el que se moverá (X=1,0,0 | Y=0,1,0 | Z=0,0,1)")]
    public Vector3 direccionAuto = Vector3.right; // Por defecto se mueve en X

    // Variable privada para recordar dónde empezó
    private Vector3 startPos;

    void Start()
    {
        startPos = transform.position;
    }

    void Update()
    {
        // Aquí está la magia: el script decide qué hacer según lo que elegiste
        switch (modoDeMovimiento)
        {
            case MoveMode.Manual_Teclado:
                MoverConTeclado();
                break;

            case MoveMode.Automatico_Bucle:
                MoverAutomatico();
                break;
        }
    }

    // --- LÓGICA MANUAL ---
    void MoverConTeclado()
    {
        // Flechas o WASD para moverse por el suelo
        float x = Input.GetAxis("Horizontal"); // A - D
        float z = Input.GetAxis("Vertical");   // W - S

        // Extra: Teclas Q y E para subir y bajar altura (Eje Y)
        float y = 0;
        if (Input.GetKey(KeyCode.E)) y = 1; // Subir
        if (Input.GetKey(KeyCode.Q)) y = -1; // Bajar

        Vector3 movimiento = new Vector3(x, y, z);

        // Movemos la bola respecto al mundo
        transform.Translate(movimiento * velocidad * Time.deltaTime, Space.World);
    }

    // --- LÓGICA AUTOMÁTICA ---
    void MoverAutomatico()
    {
        // Calcula un valor que va y viene (PingPong)
        float offset = Mathf.PingPong(Time.time * velocidad, distanciaAuto * 2) - distanciaAuto;

        // Aplica la posición basándose en el punto inicial
        transform.position = startPos + (direccionAuto.normalized * offset);
    }
}