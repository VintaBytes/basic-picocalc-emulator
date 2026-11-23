"""Genera una copia corregida de Landmine sin modificar el archivo original.

Uso:
    python -m tools.corregir_landmine /ruta/landmine.bas /ruta/landmine_corregido.bas

Se conservan los numeros de linea y el encabezado GPLv3 del autor.
"""
from pathlib import Path
import argparse

CAMBIOS = {
    125: ("Chr$(33+TankOrientation))", "Chr$(33+TankOrientation)"),
    145: ("Select Case Map(Side,x,y))", "Select Case Map(Side,x,y)"),
    212: ("Chr$(40))", "Chr$(40)"),
    246: ("i <> MapHeight-1", "y <> MapHeight-1"),
    254: ("y <> MapWidth-1", "x <> MapWidth-1"),
    311: ("Chr$(33+TankOrientation))", "Chr$(33+TankOrientation)"),
    356: ("Map(Side,TankX+1,1)=8", "Map(Side,TankX+1,TankY)=8"),
    425: ("Chr$(33))", "Chr$(33)"),
    429: ("Chr$(42))", "Chr$(42)"),
    451: ("Map(OtherSide,ShotX,Shot)=11", "Map(OtherSide,ShotX,ShotY)=11"),
    480: ("Chr$(32))", "Chr$(32)"),
    484: ("Chr$(33+TankOrientation))", "Chr$(33+TankOrientation)"),
    488: ("Chr$(44))", "Chr$(44)"),
    490: ("If ShotX<>TankX Or ShotY<>TankY) Then",
          "If ShotX<>TankX Or ShotY<>TankY Then"),
    491: ("Chr$(33))", "Chr$(33)"),
    515: ("GuysLeft>NumberOfGuys/2", "GuysLeft>NumberOfPeople/2"),
    518: ("GuysLeft>NumberOfGuys/4", "GuysLeft>NumberOfPeople/4"),
}


def corregir(origen: Path, destino: Path) -> int:
    if origen.resolve() == destino.resolve():
        raise ValueError("Origen y destino deben ser archivos diferentes")
    if destino.exists():
        raise FileExistsError(f"Ya existe: {destino}")
    source = origen.read_bytes()
    # El archivo original usa ASCII/CRLF. No cambiar encoding ni finales.
    text = source.decode("latin-1")
    lines = text.splitlines(keepends=True)
    if len(lines) != 561:
        raise ValueError(f"Landmine no coincide con la version auditada: {len(lines)} lineas")
    for line_number, (old, new) in CAMBIOS.items():
        line = lines[line_number - 1]
        if line.count(old) != 1:
            raise ValueError(f"Linea {line_number}: contenido inesperado; no se modifica nada")
        lines[line_number - 1] = line.replace(old, new, 1)
    updated = "".join(lines).encode("latin-1")
    destino.write_bytes(updated)
    return len(CAMBIOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origen", type=Path)
    parser.add_argument("destino", type=Path)
    args = parser.parse_args()
    print(f"Landmine: {corregir(args.origen, args.destino)} lineas corregidas: {args.destino}")


if __name__ == "__main__":
    main()
