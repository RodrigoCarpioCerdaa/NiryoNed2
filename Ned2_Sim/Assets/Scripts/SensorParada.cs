using UnityEngine;

public class SensorParada : MonoBehaviour
{
    // Esta función se ejecuta automáticamente cuando algo entra en el Trigger
    private void OnTriggerEnter(Collider other)
    {
        // Verificamos si lo que ha entrado es un "Producto" (usando el Tag que creamos antes)
        if (other.CompareTag("Producto"))
        {
            Debug.Log("🛑 Sensor activado: Parando la cinta.");
            
            // APAGAMOS EL INTERRUPTOR GLOBAL
            ConveyorEstadoGlobal.EstaFuncionando = false;
            
            // Opcional: Aquí podrías avisar al RobotController de que ya puede empezar a moverse.
            // FindObjectOfType<RobotController>().PiezaListaParaRecoger = true;
        }
    }
}