using UnityEngine;

public class RobotTester : MonoBehaviour
{
    [Header(" Configuración del Robot")]
    [Tooltip("Arrastra aquí los 6 pivotes/links del robot")]
    public Transform[] jointTransforms;

    [Tooltip("Define aquí el eje de giro de cada uno (X=1, Y=1, o Z=1)")]
    public Vector3[] jointAxes;

    [Header(" Control Manual (Mueve estos sliders)")]
    [Range(-180, 180)] public float anguloJ1;
    [Range(-180, 180)] public float anguloJ2;
    [Range(-180, 180)] public float anguloJ3;
    [Range(-180, 180)] public float anguloJ4;
    [Range(-180, 180)] public float anguloJ5;
    [Range(-180, 180)] public float anguloJ6;

    // Array interno para procesar el bucle rápido
    private float[] angulos;

    void Update()
    {
        // Agrupamos los sliders en un array para procesarlos
        angulos = new float[] { anguloJ1, anguloJ2, anguloJ3, anguloJ4, anguloJ5, anguloJ6 };

        // Seguridad: Evitar errores si te faltan objetos
        int count = Mathf.Min(jointTransforms.Length, jointAxes.Length, angulos.Length);

        for (int i = 0; i < count; i++)
        {
            if (jointTransforms[i] != null)
            {
                // Multiplicamos el Eje (Vector3) por el Ángulo (float)
                // Ejemplo: (0,0,1) * 45 = (0,0,45) -> Rota 45º en Z
                jointTransforms[i].localRotation = Quaternion.Euler(jointAxes[i] * angulos[i]);
            }
        }
    }
}