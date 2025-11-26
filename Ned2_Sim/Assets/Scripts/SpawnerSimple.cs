using UnityEngine;

public class SpawnerSimple : MonoBehaviour
{
    [Header("Prefabs")]
    public GameObject prefabRojo;
    public GameObject prefabVerde;

    [Header("Configuración de Aleatoriedad")]
    // Ajusta esto en el Inspector. 
    // Ej: 0.1 significa que puede variar 10cm a la izq y 10cm a la derecha.
    public float anchoVariacion = 0.1f; 

    void Start()
    {
        ConveyorEstadoGlobal.Reiniciar();
    }

    // Función pública para el botón Rojo
    public void SpawnearRojo()
    {
        GenerarPieza(prefabRojo, "Roja");
    }

    // Función pública para el botón Verde
    public void SpawnearVerde()
    {
        GenerarPieza(prefabVerde, "Verde");
    }

    // Lógica interna para calcular la posición y rotación
    void GenerarPieza(GameObject prefab, string nombre)
    {
        if (prefab != null)
        {
            // 1. CALCULAR POSICIÓN ALEATORIA (Ancho)
            // Cogemos la posición del Spawner
            Vector3 posicionFinal = transform.position;
            
            // Calculamos un número al azar entre -ancho y +ancho
            float variacion = Random.Range(-anchoVariacion, anchoVariacion);
            
            // Aplicamos la variación al Eje X (asumiendo que la cinta va en Z)
            // Si tu cinta va en X, cambia esto por: posicionFinal.z += variacion;
            posicionFinal.z += variacion;

            // 2. CALCULAR ROTACIÓN ALEATORIA
            // Giramos solo en el eje Y (vertical) entre 0 y 360 grados
            Quaternion rotacionFinal = Quaternion.Euler(0, Random.Range(0, 360), 0);

            // 3. CREAR LA PIEZA
            Instantiate(prefab, posicionFinal, rotacionFinal);
            
            Debug.Log($"📦 Pieza {nombre} generada. Variación: {variacion:F2}");
        }
    }
}