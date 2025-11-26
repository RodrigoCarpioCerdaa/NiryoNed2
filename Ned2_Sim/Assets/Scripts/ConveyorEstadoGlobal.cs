using UnityEngine;

// Este script no necesita estar en ningún objeto. 
// Es solo un contenedor para una variable global.
public static class ConveyorEstadoGlobal
{
    // Esta es la variable que todos mirarán.
    // true = todo se mueve. false = todo se para.
    public static bool EstaFuncionando = true;

    // Método útil para reiniciar el sistema si lo necesitas luego
    public static void Reiniciar()
    {
        EstaFuncionando = true;
    }
}