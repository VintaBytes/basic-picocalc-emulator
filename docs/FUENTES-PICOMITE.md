# Fuentes bitmap ROM de PicoMite (FONT 1–8)

El emulador incluye las ocho fuentes bitmap utilizadas en el perfil de
compatibilidad PicoCalc. **No requiere descargar ni instalar las fuentes
durante su uso.**

Los archivos se encuentran en:

- `src/basic_cde/devices/font_data/01-font1.h` a
  `08-smallfont.h`: cabeceras originales que conservan sus comentarios.
- `src/basic_cde/devices/font_data/font1.rle` a
  `font8.rle`: representaciones comprimidas de las mismas tablas de bits.

`scripts/instalar_fuentes.py` es una herramienta opcional de desarrollo:
permite importar cabeceras existentes o descargarlas desde una **revisión fija**
del repositorio público de PicoMite. El emulador no depende de ese script,
ni de una carpeta externa, para ejecutar programas BASIC.

## Dimensiones y caracteres

| FONT | Celda | Formato | Repertorio |
| --- | --- | --- | --- |
| 1 | 8×12 | bytes | 32–255 |
| 2 | 12×20 | bytes | 32–126 |
| 3 | 16×24 | bytes | 32–126 |
| 4 | 10×16 | bytes | 32–255 |
| 5 | 24×32 | palabras little-endian | 32–126 |
| 6 | 32×50 | bytes | 48–58 |
| 7 | 6×8 | bytes | 32–127 |
| 8 | 4×6 | palabras little-endian | 32–127 |

La fuente 6 contiene solo once glifos y no es una tipografía de texto
general. Los caracteres ausentes se muestran como celdas vacías;
no se sustituyen por símbolos inventados.

Las fuentes se cargan en la consola, `TEXT`, `PRINT` y otros modos de
representación de caracteres. Su apariencia y su comportamiento fuera de
los casos probados todavía pueden diferir del firmware instalado en una
PicoCalc real.

## Procedencia, integridad y licencias

Origen público: https://github.com/cuu/PicoMite

Revisión de procedencia auditada:
`8adc11f3ba5e2a0a496363e732995ca1b009f697`

La comparación de los ocho archivos originales y sus hashes de referencia,
las particularidades conocidas de sus cabeceras y las condiciones de
redistribución están en
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y
[docs/licenses/](licenses/).

Geoff Graham confirmó por correo el 22 de noviembre de 2026 que las ocho
fuentes están cubiertas por las condiciones de redistribución de MMBasic
V6/V7. **No forman parte de la licencia MIT del código independiente**.

La presencia de estos datos bitmap no implica que el proyecto incluya ni
ejecute el intérprete de firmware PicoMite.
