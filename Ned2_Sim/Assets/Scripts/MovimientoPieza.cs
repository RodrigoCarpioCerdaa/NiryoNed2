using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class MovimientoPieza : MonoBehaviour
{
    public float velocidadFisica = 0.5f;

    [Header("Dirección de la Cinta (Mundo)")]
    // IMPORTANTE: Define aquí hacia dónde va la cinta en el mundo (X, Y, Z)
    // Si tu cinta va hacia el fondo (eje azul), pon Z=1.
    // Si va hacia la derecha (eje rojo), pon X=1.
    public Vector3 direccionCinta = new Vector3(0, 0, 1); 

    private Rigidbody rb;

    void Start()
    {
        rb = GetComponent<Rigidbody>();
    }

    void FixedUpdate()
    {
        if (ConveyorEstadoGlobal.EstaFuncionando)
        {
            // --- EL CAMBIO CLAVE ESTÁ AQUÍ ---
            
            // ANTES (Mal): Usábamos transform.TransformDirection (dependía de la rotación del cubo)
            // AHORA (Bien): Usamos directamente el vector direcciónCinta (ignoramos la rotación del cubo)
            
            Vector3 velocidadFinal = direccionCinta.normalized * velocidadFisica;
            
            // Aplicamos la velocidad manteniendo la gravedad (eje Y)
            rb.velocity = new Vector3(velocidadFinal.x, rb.velocity.y, velocidadFinal.z);
        }
        else
        {
            // Frenar en seco si la cinta se para
            rb.velocity = new Vector3(0, rb.velocity.y, 0);
        }
    }
}