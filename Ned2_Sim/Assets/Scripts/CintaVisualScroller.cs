using UnityEngine;

public class CintaVisualScroller : MonoBehaviour
{
    // Velocidad visual del desplazamiento de la textura
    public float velocidadVisual = 0.5f;
    
    // Dirección del movimiento de la textura (X o Y)
    // Prueba (1,0) o (0,1) dependiendo de cómo esté hecha tu textura UV.
    public Vector2 direccion = new Vector2(0, 1);

    private Renderer miRenderer;
    private Vector2 offsetActual;

    void Start()
    {
        miRenderer = GetComponent<Renderer>();
    }

    void Update()
    {
        // SOLO nos movemos visualmente si el estado global es TRUE
        if (ConveyorEstadoGlobal.EstaFuncionando)
        {
            // Calculamos el nuevo desplazamiento
            offsetActual += direccion * velocidadVisual * Time.deltaTime;
            // Aplicamos el desplazamiento a la textura principal del material
            miRenderer.material.mainTextureOffset = offsetActual;
        }
    }
}