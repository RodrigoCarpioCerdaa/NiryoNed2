using System.Collections.Generic;

[System.Serializable]
public class VisionData
{
    // Estas variables TIENEN que llamarse igual que en mi Python
    public bool objeto_encontrado;
    public string forma;
    public string color;
    public List<float> posicion; 
    public bool calibrado;
}
