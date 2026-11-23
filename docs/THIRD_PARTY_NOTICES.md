# Third-party components and attributions

BASIC PicoCalc Emulator is an independent project.

This document records the provenance of third-party resources
used by the emulator. It does not replace their applicable
licenses or grant redistribution rights.

## 1. PicoMite / MMBasic ROM fonts

Source repository:
https://github.com/cuu/PicoMite

Verified revision:
8adc11f3ba5e2a0a496363e732995ca1b009f697

Upstream project authors:
Geoff Graham and Peter Mather.

The following source files were compared byte-for-byte after
normalizing line endings. All eight matched the specified
upstream revision.

| BASIC font | Local source | Upstream file | SHA-256 prefix |
|---|---|---|---|
| FONT 1 | 01-font1.h | font1.h | 4e77a41166c2345d |
| FONT 2 | 02-Misc_12x20_LE.h | Misc_12x20_LE.h | 4461f422085a63aa |
| FONT 3 | 03-Hom_16x24_LE.h | Hom_16x24_LE.h | c2a242a32da11641 |
| FONT 4 | 04-Fnt_10x16.h | Fnt_10x16.h | 43f1a9f972b756ff |
| FONT 5 | 05-Inconsola.h | Inconsola.h | fc0ee1e0ae01168d |
| FONT 6 | 06-ArialNumFontPlus.h | ArialNumFontPlus.h | cdbba7ec3fc0a438 |
| FONT 7 | 07-Font_8x6.h | Font_8x6.h | d0b1430ba19c35fd |
| FONT 8 | 08-smallfont.h | smallfont.h | bc19032e8df2bee6 |

The hashes above are the first 16 hexadecimal characters of
the SHA-256 hashes of the line-ending-normalized files.
They are identifiers for this audit, not complete SHA-256 values.

### Compressed representations

The emulator includes corresponding font1.rle through
font8.rle resources, containing compressed representations
of the ROM font data.

Compression does not change the copyright or licensing
status of the original glyphs.

### Additional provenance information

FONT 1 contains the upstream comment:

"Font adapted from: http://www.rinkydinkelectronics.com/r_fonts.php"

FONT 7 contains a generic NetBeans-generated comment,
which does not establish a redistribution license.

FONT 8 declares TinyFont, although its original header
contains apparently unrelated ArialNumFontPlus metadata.

These observations are inherited from the upstream files.

### Licensing status

The eight original ROM fonts are redistributed under the
general copyright and redistribution provisions of
MMBasic V6 and V7, not under this project's MIT license.

On 22 November 2026, Geoff Graham explicitly confirmed
by email that these fonts are covered by those provisions.

The original PicoMite V6.03.00 Version.h containing the
redistribution conditions and disclaimer is preserved in:

docs/licenses/PicoMite-V6.03.00-Version.h

Official upstream source:
https://github.com/UKTailwind/PicoMite

Applicable attribution and redistribution obligations
must be respected in source and binary distributions.

The original font files and their compressed derivatives
remain subject to the upstream conditions.

## 2. BASIC PicoCalc Emulator

The emulator's independently developed Python code is
maintained separately from the PicoMite firmware sources.

The independently developed code owned by the project
is distributed under the MIT License (root LICENSE file).

Third-party resources remain subject to their own
applicable licenses.

## 3. Graphical assets and PicoCalc skins

The PicoCalc interface images included in this repository
were created from photographs taken by Ariel Palazzesi.

The photographs were edited, processed and redrawn with
AI-assisted tools to produce the emulator's graphical skins.

The project author confirms the provenance of the original
photographs and authorizes redistribution of these graphical
resources as part of BASIC PicoCalc Emulator.

The images are visual representations of the PicoCalc
hardware and do not imply endorsement by ClockworkPi.

PicoCalc and ClockworkPi are names associated with their
respective owners.

## 4. Release status

Technical provenance of FONT 1 through FONT 8: VERIFIED.

Font redistribution permission: CONFIRMED by Geoff Graham.

Graphical assets provenance: CONFIRMED by project author.

Public releases must preserve applicable third-party notices
and comply with the conditions of redistributed dependencies.
