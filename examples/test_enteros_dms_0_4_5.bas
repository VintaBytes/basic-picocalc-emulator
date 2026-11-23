' RPN 0.4.5 - Suite de enteros, DMS y validacion
' El archivo incorpora las rutinas de la misma version.
OPTION BASE 1
CONST T_REAL=1,T_CPLX=2,T_VEC=3,T_MAT=4,T_POLI=5
CONST MAX_PILA=100
DIM pila_t%(MAX_PILA)
DIM pila_a(MAX_PILA)
DIM pila_b(MAX_PILA)
DIM ayuda$(60)
DIM menu$(10)
DIM submenuTrig$(12)
DIM submenuLog$(10)
DIM submenuInt$(10)
DIM submenuConst$(10)
DIM submenuConv$(6)
DIM submenuConf$(11)
DRG$="D"
FORMATO$="NORM"
DECIM=6
aciertos=0
fallos=0
pila_iniciar
PRINT "RPN 0.4.5 - INTEGRALES Y DMS"
PRINT "------------------------------"

pila_apilar 97
op_primo
evaluar "PRIMO 97",tope=1 AND pila_a(1)=1,"1",STR$(pila_a(1))
pila_limpiar

pila_apilar 91
op_primo
evaluar "PRIMO 91",tope=1 AND pila_a(1)=0,"0",STR$(pila_a(1))
pila_limpiar

pila_apilar 2
op_primo
evaluar "PRIMO 2",tope=1 AND pila_a(1)=1,"1",STR$(pila_a(1))
pila_limpiar

pila_apilar 1
op_primo
evaluar "PRIMO 1",tope=1 AND pila_a(1)=0,"0",STR$(pila_a(1))
pila_limpiar

pila_apilar 99991
op_primo
evaluar "PRIMO 99991",tope=1 AND pila_a(1)=1,"1",STR$(pila_a(1))
pila_limpiar

pila_apilar 54
pila_apilar 24
op_mcd
evaluar "MCD 54,24",tope=1 AND pila_a(1)=6,"6",STR$(pila_a(1))
pila_limpiar

pila_apilar -54
pila_apilar 24
op_mcd
evaluar "MCD -54,24",tope=1 AND pila_a(1)=6,"6",STR$(pila_a(1))
pila_limpiar

pila_apilar 0
pila_apilar 7
op_mcd
evaluar "MCD 0,7",tope=1 AND pila_a(1)=7,"7",STR$(pila_a(1))
pila_limpiar

pila_apilar 0
pila_apilar 0
op_mcd
evaluar "MCD 0,0",tope=1 AND pila_a(1)=0,"0",STR$(pila_a(1))
pila_limpiar

pila_apilar 21
pila_apilar 6
op_mcm
evaluar "MCM 21,6",tope=1 AND pila_a(1)=42,"42",STR$(pila_a(1))
pila_limpiar

pila_apilar -21
pila_apilar 6
op_mcm
evaluar "MCM -21,6",tope=1 AND pila_a(1)=42,"42",STR$(pila_a(1))
pila_limpiar

pila_apilar 0
pila_apilar 42
op_mcm
evaluar "MCM 0,42",tope=1 AND pila_a(1)=0,"0",STR$(pila_a(1))
pila_limpiar

pila_apilar 12.5
op_d2dms
evaluar "DEG 12.5 -> DMS",tope=1 AND pila_a(1)=123000,"123000",STR$(pila_a(1))
pila_limpiar

pila_apilar -12.5
op_d2dms
evaluar "DEG -12.5 -> DMS",tope=1 AND pila_a(1)=-123000,"-123000",STR$(pila_a(1))
pila_limpiar

pila_apilar 12.999999
op_d2dms
evaluar "DEG acarreo",tope=1 AND pila_a(1)=130000,"130000",STR$(pila_a(1))
pila_limpiar

pila_apilar 123045
op_dms2d
evaluar "DMS 123045 -> DEG",tope=1 AND ABS(pila_a(1)-12.5125)<1E-9,"12.5125",STR$(pila_a(1))
pila_limpiar

pila_apilar -123045
op_dms2d
evaluar "DMS -123045",tope=1 AND ABS(pila_a(1)+12.5125)<1E-9,"-12.5125",STR$(pila_a(1))
pila_limpiar

pila_apilar 123000
op_dms2d
evaluar "DMS 123000",tope=1 AND ABS(pila_a(1)-12.5)<1E-9,"12.5",STR$(pila_a(1))
pila_limpiar

evaluar "VALIDO 12.5",es_numero("12.5")=1,"1",STR$(es_numero("12.5"))
evaluar "VALIDO -2",es_numero("-2")=1,"1",STR$(es_numero("-2"))
evaluar "INVALIDO -",es_numero("-")=0,"0",STR$(es_numero("-"))
evaluar "INVALIDO 1..2",es_numero("1..2")=0,"0",STR$(es_numero("1..2"))
evaluar "INVALIDO 12A",es_numero("12A")=0,"0",STR$(es_numero("12A"))
evaluar "VALIDO 1E-3",es_numero("1E-3")=1,"1",STR$(es_numero("1E-3"))

PRINT "------------------------------"
PRINT "OK: ";aciertos;"  FAIL: ";fallos
END

SUB evaluar(nombre$,bien,esperado$,obtenido$)
  IF bien THEN
    PRINT "OK  ";nombre$
    aciertos=aciertos+1
  ELSE
    PRINT "FAIL ";nombre$
    PRINT " ESP ";esperado$
    PRINT " OBT ";obtenido$
    fallos=fallos+1
  END IF
END SUB

SUB parse_i(s$, re, im, ok%)
  LOCAL t$, n, ch$, i%
  ok% = 0 : re = 0 : im = 0

  IF s$ = "" THEN EXIT SUB

  ' quitar espacios
  t$ = LTRIM$(RTRIM$(s$))

  ' reemplazar '_' por '-' (tu convención)
  FOR i% = 1 TO LEN(t$)
    ch$ = MID$(t$, i%, 1)
    IF ch$ = "_" THEN
      MID$(t$, i%, 1) = "-"
    END IF
  NEXT i%

  ' debe terminar en i/I
  n = LEN(t$)
  IF n = 0 THEN EXIT SUB
  ch$ = MID$(t$, n, 1)
  IF ch$ <> "i" AND ch$ <> "I" THEN EXIT SUB

  ' quitar la i final
  t$ = LEFT$(t$, n - 1)
  t$ = LTRIM$(RTRIM$(t$))

  ' casos: "", "+", "-", número
  IF t$ = "" OR t$ = "+" THEN
    im = 1 : re = 0 : ok% = 1 : EXIT SUB
  END IF
  IF t$ = "-" THEN
    im = -1 : re = 0 : ok% = 1 : EXIT SUB
  END IF

  ' intentar convertir el coeficiente
  im = VAL(t$)
  re = 0
  ok% = 1
END SUB

'--------------------------------------
FUNCTION menu_navegar$(menuGrupo)
  LOCAL menuSel, menuTotal, menuPag, menuNumPag, menuInicio
  LOCAL menuFilas, menuFila, menuIndice, menuY, menuH, menuW
  LOCAL menuX, menuRowY, menuMax, tecla$, menuTitulo$, rotulo$
  LOCAL menuLista$(16), menuSalida$, menuBg, menuInk
  LOCAL menuBarra, menuSelBg, menuBlanco, menuRedibuja
  LOCAL menuShort$, menuKey, menuN
  LOCAL menuFull, menuPrev, menuRowBg, menuValue, menuDrawRow

  menuBg=RGB(221,233,229)
  menuInk=RGB(8,12,14)
  menuBarra=RGB(30,57,72)
  menuSelBg=RGB(196,211,208)
  menuBlanco=RGB(255,255,255)
  menuSel=1
  menuRedibuja=1
  menuFull=1
  ' Region fija que cubre los menus de hasta 8 opciones.
  ' Se reserva una sola vez, y siempre se libera al salir.
  BLIT READ #1,8,98,180,199

  DO
    menuTotal=0
    SELECT CASE menuGrupo
      CASE 1
        menuTitulo$="TRIG"
        menuTotal=totalTrig
        FOR menuN=1 TO menuTotal
          menuLista$(menuN)=submenuTrig$(menuN)
        NEXT menuN
      CASE 2
        menuTitulo$="MATH"
        menuTotal=totalLog
        FOR menuN=1 TO menuTotal
          menuLista$(menuN)=submenuLog$(menuN)
        NEXT menuN
      CASE 3
        menuTitulo$="NUM"
        menuTotal=totalInt+totalConv
        FOR menuN=1 TO totalInt
          menuLista$(menuN)=submenuInt$(menuN)
        NEXT menuN
        FOR menuN=1 TO totalConv
          menuLista$(totalInt+menuN)=submenuConv$(menuN)
        NEXT menuN
      CASE 4
        menuTitulo$="CONST"
        menuTotal=totalConst
        FOR menuN=1 TO menuTotal
          menuLista$(menuN)=submenuConst$(menuN)
        NEXT menuN
      CASE 5
        menuTitulo$="SET"
        menuTotal=totalConf+1
        FOR menuN=1 TO totalConf
          menuLista$(menuN)=submenuConf$(menuN)
        NEXT menuN
        menuLista$(menuTotal)="AYUDA"
    END SELECT

    IF menuSel<1 THEN menuSel=1
    IF menuSel>menuTotal THEN menuSel=menuTotal
    menuPag=INT((menuSel-1)/8)
    menuNumPag=INT((menuTotal+7)/8)
    menuInicio=menuPag*8
    menuFilas=menuTotal-menuInicio
    IF menuFilas>8 THEN menuFilas=8

    IF menuRedibuja=1 THEN
      IF menuFull=1 THEN
        ' Recuperar fondo sin reconstruir la pila.
        BLIT WRITE #1,8,98
        menuMax=0
        FOR menuN=1 TO menuFilas
          IF LEN(menuLista$(menuInicio+menuN))>menuMax THEN
            menuMax=LEN(menuLista$(menuInicio+menuN))
          END IF
        NEXT menuN
        menuW=49+menuMax*10
        IF menuW<115 THEN menuW=115
        menuH=31+menuFilas*21
        menuX=8
        menuY=297-menuH
        BOX menuX,menuY,menuW,menuH,1,menuBarra,menuBg
        BOX menuX+1,menuY+1,menuW-2,22,0,menuBarra,menuBarra
        rotulo$=menuTitulo$
        IF menuNumPag>1 THEN
          rotulo$=rotulo$+" "+STR$(menuPag+1)+"/"+STR$(menuNumPag)
        END IF
        TEXT menuX+9,menuY+5,rotulo$,"LT",1,1,menuBlanco,menuBarra
        FOR menuDrawRow=1 TO menuFilas
          menuIndice=menuInicio+menuDrawRow
          menuRowY=menuY+26+(menuDrawRow-1)*21
          menuRowBg=menuBg
          IF menuIndice=menuSel THEN menuRowBg=menuSelBg
          BOX menuX+3,menuRowY-1,menuW-6,20,0,menuRowBg,menuRowBg
          BOX menuX+8,menuRowY+2,19,17,0,menuBarra,menuBarra
          menuShort$=CHR$(48+menuDrawRow)
          TEXT menuX+17,menuRowY+4,menuShort$,"CT",1,1,menuBlanco,menuBarra
          TEXT menuX+35,menuRowY+1,menuLista$(menuIndice),"LT",4,1,menuInk,menuRowBg
        NEXT menuDrawRow
      ELSE
        ' Mismo grupo y pagina: repintar SOLO seleccion previa y nueva.
        FOR menuN=1 TO 2
          IF menuN=1 THEN
            menuIndice=menuPrev
          ELSE
            menuIndice=menuSel
          END IF
          menuDrawRow=menuIndice-menuInicio
          IF menuDrawRow>=1 AND menuDrawRow<=menuFilas THEN
            menuRowY=menuY+26+(menuDrawRow-1)*21
            menuRowBg=menuBg
            IF menuIndice=menuSel THEN menuRowBg=menuSelBg
            BOX menuX+3,menuRowY-1,menuW-6,20,0,menuRowBg,menuRowBg
            BOX menuX+8,menuRowY+2,19,17,0,menuBarra,menuBarra
            menuShort$=CHR$(48+menuDrawRow)
            TEXT menuX+17,menuRowY+4,menuShort$,"CT",1,1,menuBlanco,menuBarra
            TEXT menuX+35,menuRowY+1,menuLista$(menuIndice),"LT",4,1,menuInk,menuRowBg
          END IF
        NEXT menuN
      END IF
      menuRedibuja=0
    END IF

    tecla$=INKEY$
    IF tecla$<>"" THEN
      menuKey=ASC(tecla$)
      SELECT CASE menuKey
        CASE 27,8,127
          menu_navegar$=""
          BLIT WRITE #1,8,98
          BLIT CLOSE #1
          EXIT FUNCTION
        CASE 145,146,147,148,149
          menuGrupo=menuKey-144
          menuSel=1
          menuFull=1
          menuRedibuja=1
        CASE 128
          IF menuSel>1 THEN
            menuPrev=menuSel
            menuSel=menuSel-1
            menuFull=0
            IF INT((menuSel-1)/8)<>menuPag THEN menuFull=1
            menuRedibuja=1
          END IF
        CASE 129
          IF menuSel<menuTotal THEN
            menuPrev=menuSel
            menuSel=menuSel+1
            menuFull=0
            IF INT((menuSel-1)/8)<>menuPag THEN menuFull=1
            menuRedibuja=1
          END IF
        CASE 130
          ' Otra categoria, como en SCI.
          menuGrupo=menuGrupo-1
          IF menuGrupo<1 THEN menuGrupo=5
          menuSel=1
          menuFull=1
          menuRedibuja=1
        CASE 131
          menuGrupo=menuGrupo+1
          IF menuGrupo>5 THEN menuGrupo=1
          menuSel=1
          menuFull=1
          menuRedibuja=1
        CASE 13,10
          menu_navegar$=TRIM$(menuLista$(menuSel))
          BLIT WRITE #1,8,98
          BLIT CLOSE #1
          EXIT FUNCTION
        CASE 49,50,51,52,53,54,55,56
          menuN=menuKey-48
          IF menuN<=menuFilas THEN
            menu_navegar$=TRIM$(menuLista$(menuInicio+menuN))
            BLIT WRITE #1,8,98
            BLIT CLOSE #1
            EXIT FUNCTION
          END IF
      END SELECT
    ELSE
      PAUSE 1
    END IF
  LOOP
END FUNCTION


'---------------------------------------------
' Mostrar pantalla (HP-style)
'---------------------------------------------
SUB pila_mostrar()
  ' RPN 0.1.0: nueva presentacion, sin tocar los datos de pila.
  LOCAL bg, tinta, barra, claro, sel, borde, acento
  LOCAL i, idx, fila, etiqueta$, cadena$, modotxt$, fmt$
  bg=RGB(221,233,229)
  tinta=RGB(8,12,14)
  barra=RGB(30,57,72)
  claro=RGB(255,255,255)
  sel=RGB(196,211,208)
  borde=RGB(168,183,180)
  acento=RGB(12,78,102)

  CLS bg
  BOX 0,0,320,32,0,barra,barra
  TEXT 8,8,"PicoCalc RPN","LT",4,1,claro,barra

  SELECT CASE DRG$
    CASE "D": modotxt$="DEG"
    CASE "R": modotxt$="RAD"
    CASE "G": modotxt$="GRA"
  END SELECT
  SELECT CASE FORMATO$
    CASE "NORM": fmt$="NORM"
    CASE "FIX": fmt$="FIX"+STR$(DECIM)
    CASE "SCI": fmt$="SCI"+STR$(DECIM)
    CASE "ENG": fmt$="ENG"
  END SELECT
  TEXT 312,10,modotxt$+" "+fmt$,"RT",1,1,RGB(203,234,219),barra

  ' Ocho niveles: etiquetas X/Y/Z/T y superiores 5..8.
  FOR i=8 TO 1 STEP -1
    idx=tope-(i-1)
    fila=43+(8-i)*24
    SELECT CASE i
      CASE 8: etiqueta$="8:"
      CASE 7: etiqueta$="7:"
      CASE 6: etiqueta$="6:"
      CASE 5: etiqueta$="5:"
      CASE 4: etiqueta$="T:"
      CASE 3: etiqueta$="Z:"
      CASE 2: etiqueta$="Y:"
      CASE 1: etiqueta$="X:"
    END SELECT
    IF i=1 THEN
      BOX 6,fila-2,308,23,0,sel,sel
      TEXT 12,fila,etiqueta$,"LT",2,1,acento,sel
    ELSE
      TEXT 12,fila,etiqueta$,"LT",2,1,tinta,bg
    END IF
    IF idx>=1 THEN
      cadena$=formatear_item$(idx)
      ' Ajustar visualmente sin tocar ningun registro de la pila.
      IF LEN(cadena$)>22 THEN
        IF pila_t%(idx)=T_CPLX THEN
          cadena$=formatear_compacto$(pila_a(idx),pila_b(idx),5)
          IF LEN(cadena$)>22 THEN
            cadena$=formatear_compacto$(pila_a(idx),pila_b(idx),3)
          END IF
        ELSEIF pila_t%(idx)=T_REAL THEN
          cadena$=FORMAT$(pila_a(idx),"%.12g")
        END IF
        IF LEN(cadena$)>22 THEN cadena$=LEFT$(cadena$,19)+"..."
      END IF
      IF i=1 THEN
        TEXT 308,fila,cadena$,"RT",2,1,acento,sel
      ELSE
        TEXT 308,fila,cadena$,"RT",2,1,tinta,bg
      END IF
    END IF
  NEXT i

  LINE 8,240,312,240,1,borde
  ' Barra inferior: acciones operativas reales, no F2-F5 ficticias.
  BOX 0,297,320,23,0,barra,barra
  LINE 64,297,64,319,1,borde
  LINE 128,297,128,319,1,borde
  LINE 192,297,192,319,1,borde
  LINE 256,297,256,319,1,borde
  TEXT 32,302,"TRIG","CT",1,1,claro,barra
  TEXT 96,302,"MATH","CT",1,1,claro,barra
  TEXT 160,302,"NUM","CT",1,1,claro,barra
  TEXT 224,302,"CONST","CT",1,1,claro,barra
  TEXT 288,302,"SET","CT",1,1,claro,barra
  mostrar_entrada
END SUB

'--------------------------------------
SUB mostrar_entrada()
  LOCAL bg, tinta, borde, cadena$
  bg=RGB(221,233,229)
  tinta=RGB(8,12,14)
  borde=RGB(168,183,180)
  ' Limpiar unicamente el editor; no borrar pila ni cabecera.
  BOX 8,248,304,34,0,bg,bg
  cadena$="> "+entrada$
  IF LEN(cadena$)>24 THEN cadena$=RIGHT$(cadena$,24)
  TEXT 308,251,cadena$,"RT",2,1,tinta,bg
END SUB

'--------------------------------------
FUNCTION formatear_item$(i)
  LOCAL t%, s$
  IF i<1 OR i>tope THEN
    formatear_item$ = ""
    EXIT FUNCTION
  END IF
  t% = pila_t%(i)
  SELECT CASE t%
    CASE T_REAL
      formatear_item$ = formatear_numero$(pila_a(i))
    CASE T_CPLX
      s$=formatear_numero$(pila_a(i))
      IF pila_b(i)>=0 THEN
        s$=s$+"+"
      END IF
      s$=s$+formatear_numero$(pila_b(i))+"i"
      formatear_item$=s$
    CASE T_VEC
      formatear_item$ = "<vec>"
    CASE T_MAT
      formatear_item$ = "[mat]"
    CASE T_POLI
      formatear_item$ = "{poly}"
    CASE ELSE
      formatear_item$ = formatear_numero$(pila_a(i))
  END SELECT
END FUNCTION


' Dos componentes compactados para caber en el registro visible.
' La cadena larga sigue accesible mediante formatear_item$.
FUNCTION formatear_compacto$(re, im, dig)
  LOCAL f$, a$, b$, prec$
  prec$=LTRIM$(STR$(dig))
  f$="%."+prec$+"g"
  a$=FORMAT$(re,f$)
  b$=FORMAT$(ABS(im),f$)
  IF im>=0 THEN
    formatear_compacto$=a$+"+"+b$+"i"
  ELSE
    formatear_compacto$=a$+"-"+b$+"i"
  END IF
END FUNCTION

'--------------------------------------
SUB mostrar_error(msg$)
  LOCAL k$, bg, tinta, acento
  bg=RGB(221,233,229)
  tinta=RGB(8,12,14)
  acento=RGB(12,78,102)
  BOX 8,248,304,45,0,bg,bg
  TEXT 8,252,"ERROR","LT",1,1,acento,bg
  IF LEN(msg$)>25 THEN msg$=LEFT$(msg$,22)+"..."
  TEXT 8,271,msg$,"LT",1,1,tinta,bg
  DO
    k$=INKEY$
    IF k$=CHR$(8) OR k$=CHR$(27) THEN EXIT DO
    PAUSE 20
  LOOP
  mostrar_entrada
END SUB

'--------------------------------------
' Helper de normalizacion----------
FUNCTION gtt%(i)
  IF i<1 OR i>tope THEN
    gtt%=0
  ELSE
    gtt%=pila_t%(i)
  END IF
END FUNCTION

'--------------------------------------
SUB op_suma()
  LOCAL tt1%, tt2%, re, im, x, y
  IF tope < 2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF

  tt1% = gtt%(tope)        ' X
  tt2% = gtt%(tope - 1)    ' Y

  ' ---- REAL + REAL ----
  IF tt1%=T_REAL AND tt2%=T_REAL THEN
    x = pila_a(tope)
    y = pila_a(tope-1)
    IF SGN(x)=SGN(y) AND ABS(x)>1.79E308-ABS(y) THEN
      mostrar_error("SUMA: DESBORDAMIENTO")
      EXIT SUB
    END IF
    pila_a(tope-1)=y+x
    tope=tope-1
    EXIT SUB
  END IF

  ' ---- CPLX + CPLX ----
  IF tt1%=T_CPLX AND tt2%=T_CPLX THEN
    re = pila_a(tope - 1) + pila_a(tope)
    im = pila_b(tope - 1) + pila_b(tope)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  ' ---- REAL + CPLX (Y real, X cplx) ----
  IF tt1%=T_CPLX AND tt2%=T_REAL THEN
    re = pila_a(tope) + pila_a(tope - 1)
    im = pila_b(tope)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  ' ---- CPLX + REAL (Y cplx, X real) ----
  IF tt1%=T_REAL AND tt2%=T_CPLX THEN
    re = pila_a(tope - 1) + pila_a(tope)
    im = pila_b(tope - 1)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  mostrar_error("ADD NO SOPORTADO")
END SUB


SUB op_resta()
  LOCAL tt1%, tt2%, re, im, x, y
  IF tope < 2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF

  tt1% = gtt%(tope)          ' X
  tt2% = gtt%(tope - 1)      ' Y

  ' ---- REAL - REAL ----
  IF tt1%=T_REAL AND tt2%=T_REAL THEN
    x = pila_a(tope)
    y = pila_a(tope-1)
    IF SGN(x)<>SGN(y) AND ABS(x)>1.79E308-ABS(y) THEN
      mostrar_error("RESTA: DESBORDAMIENTO")
      EXIT SUB
    END IF
    pila_a(tope-1)=y-x
    tope=tope-1
    EXIT SUB
  END IF

  ' ---- CPLX - CPLX ----
  IF tt1%=T_CPLX AND tt2%=T_CPLX THEN
    re = pila_a(tope - 1) - pila_a(tope)
    im = pila_b(tope - 1) - pila_b(tope)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  ' ---- REAL - CPLX (Y real, X cplx) ----
  IF tt1%=T_CPLX AND tt2%=T_REAL THEN
    re = pila_a(tope - 1) - pila_a(tope)
    im =        0     - pila_b(tope)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  ' ---- CPLX - REAL (Y cplx, X real) ----
  IF tt1%=T_REAL AND tt2%=T_CPLX THEN
    re = pila_a(tope - 1) - pila_a(tope)
    im = pila_b(tope - 1)
    tope = tope - 2
    ps_c re, im
    EXIT SUB
  END IF

  mostrar_error("SUB NO SOPORTADO")
END SUB

SUB op_mult()
  LOCAL tt1%, tt2%, a,b, c,d, den, x,y
  IF tope < 2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF

  tt1% = gtt%(tope)          ' X
  tt2% = gtt%(tope - 1)      ' Y

  ' ---- REAL * REAL ----
  IF tt1%=T_REAL AND tt2%=T_REAL THEN
    x = pila_a(tope)
    y = pila_a(tope-1)
    IF x<>0 AND y<>0 THEN
      IF LOG(ABS(x))+LOG(ABS(y))>709.7 THEN
        mostrar_error("MULT: DESBORDAMIENTO")
        EXIT SUB
      END IF
    END IF
    pila_a(tope-1)=y*x
    tope=tope-1
    EXIT SUB
  END IF

  ' ---- CPLX * CPLX ----
  IF tt1%=T_CPLX AND tt2%=T_CPLX THEN
    a = pila_a(tope - 1) : b = pila_b(tope - 1)
    c = pila_a(tope)     : d = pila_b(tope)
    ' (a+bi)(c+di) = (ac - bd) + (ad + bc)i
    x = a*c - b*d
    y = a*d + b*c
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  ' ---- REAL * CPLX (Y real, X cplx) ----
  IF tt1%=T_CPLX AND tt2%=T_REAL THEN
    a = pila_a(tope - 1) : b = 0
    c = pila_a(tope)     : d = pila_b(tope)
    x = a*c          ' a*Re
    y = a*d          ' a*Im
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  ' ---- CPLX * REAL (Y cplx, X real) ----
  IF tt1%=T_REAL AND tt2%=T_CPLX THEN
    a = pila_a(tope - 1) : b = pila_b(tope - 1)
    c = pila_a(tope)     : d = 0
    x = a*c          ' Re * r
    y = b*c          ' Im * r
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  mostrar_error("MUL NO SOPORTADO")
END SUB

SUB op_div()
  LOCAL tt1%, tt2%, a,b, c,d, den, x,y, r1, r2
  IF tope < 2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF

  tt1% = gtt%(tope)          ' X (divisor)
  tt2% = gtt%(tope - 1)      ' Y (dividendo)

  ' ---- REAL / REAL ----
  IF tt1%=T_REAL AND tt2%=T_REAL THEN
    r1=pila_a(tope)
    r2=pila_a(tope-1)
    IF r1=0 THEN
      mostrar_error("DIV. POR CERO")
      EXIT SUB
    END IF
    IF r2<>0 THEN
      IF LOG(ABS(r2))-LOG(ABS(r1))>709.7 THEN
        mostrar_error("DIV: DESBORDAMIENTO")
        EXIT SUB
      END IF
    END IF
    pila_a(tope-1)=r2/r1
    tope=tope-1
    EXIT SUB
  END IF

  ' ---- CPLX / CPLX ----
  IF tt1%=T_CPLX AND tt2%=T_CPLX THEN
    a = pila_a(tope - 1) : b = pila_b(tope - 1)   ' Y = a+bi
    c = pila_a(tope)     : d = pila_b(tope)       ' X = c+di
    den = c*c + d*d
    IF den = 0 THEN
      mostrar_error("DIV. POR CERO") : EXIT SUB
    END IF
    ' (a+bi)/(c+di) = ((ac+bd) + (bc-ad)i)/den
    x = (a*c + b*d) / den
    y = (b*c - a*d) / den
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  ' ---- REAL / CPLX  (Y real, X cplx) ----
  IF tt1%=T_CPLX AND tt2%=T_REAL THEN
    a = pila_a(tope - 1) : b = 0
    c = pila_a(tope)     : d = pila_b(tope)
    den = c*c + d*d
    IF den = 0 THEN
      mostrar_error("DIV. POR CERO") : EXIT SUB
    END IF
    x = (a*c + b*d) / den    ' (a*c)/den
    y = (b*c - a*d) / den    ' (-a*d)/den
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  ' ---- CPLX / REAL  (Y cplx, X real) ----
  IF tt1%=T_REAL AND tt2%=T_CPLX THEN
    c = pila_a(tope)             ' real divisor
    IF c = 0 THEN
      mostrar_error("DIV. POR CERO") : EXIT SUB
    END IF
    a = pila_a(tope - 1) : b = pila_b(tope - 1)
    x = a / c
    y = b / c
    tope = tope - 2 : ps_c x, y
    EXIT SUB
  END IF

  mostrar_error("DIV NO SOPORTADO")
END SUB



SUB op_potencia
  LOCAL x,y,z,lg
  IF tope<2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL OR pila_t%(tope-1)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  y=pila_a(tope-1)
  IF y=0 AND x<=0 THEN
    mostrar_error("DOMINIO: 0^X")
    EXIT SUB
  END IF
  IF y<0 AND x<>INT(x) THEN
    mostrar_error("POT: DOMINIO REAL")
    EXIT SUB
  END IF
  IF y<>0 THEN
    lg=x*LOG(ABS(y))
    IF lg>709.7 THEN
      mostrar_error("POT: DESBORDAMIENTO")
      EXIT SUB
    END IF
  END IF
  z=y^x
  pila_a(tope-1)=z
  pila_b(tope-1)=0
  pila_t%(tope-1)=T_REAL
  tope=tope-1
END SUB

SUB op_factorial
  ' Atajo ! y menu FACT comparten el mismo algoritmo.
  op_fact
END SUB

' SUB op_factorial
'   IF tope >= 1 THEN
'     n = pila_desapilar()
'     IF n < 0 OR n <> INT(n) THEN
'       mostrar_error("REQ. UN ENTERO > 0")
'       pila_apilar n    ' restaurar
'     ELSE
'       res = 1
'       FOR i = 1 TO n
'         res = res * i
'       NEXT i
'       pila_apilar res
'     END IF
'   ELSE
'     mostrar_error("PILA VACIA")
'   END IF
' END SUB



SUB op_inversa
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x=0 THEN
    mostrar_error("DIVISION POR CERO")
    EXIT SUB
  END IF
  IF ABS(x)<1E-308 THEN
    mostrar_error("INV: DESBORDAMIENTO")
    EXIT SUB
  END IF
  z=1/x
  pila_a(tope)=z
END SUB

SUB op_raiz
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x<0 THEN
    mostrar_error("ARG. RAIZ < 0")
    EXIT SUB
  END IF
  z=SQR(x)
  pila_a(tope)=z
END SUB


' Pila RPN -------------------------
SUB pila_iniciar()
  LOCAL ii
  tope=0
  FOR ii=1 TO MAX_PILA
    pila_t%(ii)=0
    pila_a(ii)=0
    pila_b(ii)=0
  NEXT ii
END SUB

FUNCTION pila_profundidad()
  pila_profundidad=tope
END FUNCTION

SUB pila_apilar(v)
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  tope=tope+1
  pila_t%(tope)=T_REAL
  pila_a(tope)=v
  pila_b(tope)=0
END SUB

FUNCTION pila_desapilar()
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    pila_desapilar=0
    EXIT FUNCTION
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    pila_desapilar=0
    EXIT FUNCTION
  END IF
  pila_desapilar=pila_a(tope)
  tope=tope-1
END FUNCTION

FUNCTION pila_ver(n)
  IF n<1 OR n>tope THEN
    mostrar_error("FUERA DE RANGO")
    pila_ver=0
    EXIT FUNCTION
  END IF
  IF pila_t%(tope-n+1)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    pila_ver=0
    EXIT FUNCTION
  END IF
  pila_ver=pila_a(tope-n+1)
END FUNCTION

SUB pila_borrar_tope()
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
  ELSE
    tope=tope-1
  END IF
END SUB

SUB pila_duplicar()
  IF tope<1 THEN
    mostrar_error("NADA PARA DUPLICAR")
    EXIT SUB
  END IF
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  pila_t%(tope+1)=pila_t%(tope)
  pila_a(tope+1)=pila_a(tope)
  pila_b(tope+1)=pila_b(tope)
  tope=tope+1
END SUB

SUB pila_intercambiar()
  LOCAL tt%, aa, bb
  IF tope<2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF
  tt%=pila_t%(tope)
  aa=pila_a(tope)
  bb=pila_b(tope)
  pila_t%(tope)=pila_t%(tope-1)
  pila_a(tope)=pila_a(tope-1)
  pila_b(tope)=pila_b(tope-1)
  pila_t%(tope-1)=tt%
  pila_a(tope-1)=aa
  pila_b(tope-1)=bb
END SUB

SUB pila_rotar_abajo()
  LOCAL ii,tt%,aa,bb
  IF tope<3 THEN
    mostrar_error("REQ. TRES ELEMENTOS")
    EXIT SUB
  END IF
  tt%=pila_t%(tope)
  aa=pila_a(tope)
  bb=pila_b(tope)
  FOR ii=tope TO 2 STEP -1
    pila_t%(ii)=pila_t%(ii-1)
    pila_a(ii)=pila_a(ii-1)
    pila_b(ii)=pila_b(ii-1)
  NEXT ii
  pila_t%(1)=tt%
  pila_a(1)=aa
  pila_b(1)=bb
END SUB

SUB pila_rotar_arriba()
  LOCAL ii,tt%,aa,bb
  IF tope<3 THEN
    mostrar_error("REQ. TRES ELEMENTOS")
    EXIT SUB
  END IF
  tt%=pila_t%(1)
  aa=pila_a(1)
  bb=pila_b(1)
  FOR ii=1 TO tope-1
    pila_t%(ii)=pila_t%(ii+1)
    pila_a(ii)=pila_a(ii+1)
    pila_b(ii)=pila_b(ii+1)
  NEXT ii
  pila_t%(tope)=tt%
  pila_a(tope)=aa
  pila_b(tope)=bb
END SUB

SUB pila_limpiar()
  tope=0
END SUB

SUB pila_enter()
  IF tope=0 THEN
    pila_apilar 0
  ELSE
    pila_duplicar
  END IF
END SUB

SUB ps_r(v)
  pila_apilar v
END SUB

SUB ps_c(re, im)
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  tope=tope+1
  pila_t%(tope)=T_CPLX
  pila_a(tope)=re
  pila_b(tope)=im
END SUB

SUB ps_vec(id)
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  tope=tope+1
  pila_t%(tope)=T_VEC
  pila_a(tope)=id
  pila_b(tope)=0
END SUB

SUB ps_mat(id)
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  tope=tope+1
  pila_t%(tope)=T_MAT
  pila_a(tope)=id
  pila_b(tope)=0
END SUB

SUB ps_pol(id)
  IF tope>=MAX_PILA THEN
    mostrar_error("PILA LLENA")
    EXIT SUB
  END IF
  tope=tope+1
  pila_t%(tope)=T_POLI
  pila_a(tope)=id
  pila_b(tope)=0
END SUB

'------Helpers que no tocan la pila
' ----- peek helpers -----
FUNCTION pk_t%(n)
  IF n>=1 AND n<=tope THEN
    pk_t% = pila_t%(tope - n + 1)
  ELSE
    mostrar_error("FUERA DE RANGO")
    pk_t% = 0
  END IF
END FUNCTION

FUNCTION pk_r(n)
  IF n>=1 AND n<=tope THEN
    IF pila_t%(tope - n + 1)=T_REAL THEN
      pk_r = pila_a(tope - n + 1)
    ELSE
      mostrar_error("NO ES REAL")
      pk_r = 0
    END IF
  ELSE
    mostrar_error("FUERA DE RANGO")
    pk_r = 0
  END IF
END FUNCTION

FUNCTION pk_re(n)
  IF n>=1 AND n<=tope THEN
    IF pila_t%(tope - n + 1)=T_CPLX THEN
      pk_re = pila_a(tope - n + 1)
    ELSE
      mostrar_error("NO ES CPLX")
      pk_re = 0
    END IF
  ELSE
    mostrar_error("FUERA DE RANGO")
    pk_re = 0
  END IF
END FUNCTION

FUNCTION pk_im(n)
  IF n>=1 AND n<=tope THEN
    IF pila_t%(tope - n + 1)=T_CPLX THEN
      pk_im = pila_b(tope - n + 1)
    ELSE
      mostrar_error("NO ES CPLX")
      pk_im = 0
    END IF
  ELSE
    mostrar_error("FUERA DE RANGO")
    pk_im = 0
  END IF
END FUNCTION

'-----HELPERS de consulta -------------
' ----- top helpers -----
FUNCTION top_t%()
  IF tope>=1 THEN
    top_t% = pila_t%(tope)
  ELSE
    top_t% = 0
  END IF
END FUNCTION

FUNCTION top_r()
  IF tope>=1 AND pila_t%(tope)=T_REAL THEN
    top_r = pila_a(tope)
  ELSE
    mostrar_error("TOP NO REAL")
    top_r = 0
  END IF
END FUNCTION


'--------------------------------------
SUB op_pi
  pila_apilar 3.14159265358979
  entrada$ = ""
END SUB

SUB op_e
  pila_apilar 2.71828182845905
  entrada$ = ""
END SUB

SUB op_phi
  pila_apilar 1.61803398874989
END SUB

SUB op_c
  pila_apilar 299792458
END SUB

SUB op_G
  pila_apilar 6.67430E-11
END SUB

SUB op_h
  pila_apilar 6.62607015E-34
END SUB

SUB op_qe
  pila_apilar 1.602176634E-19
END SUB
'--------------------------------------

SUB op_sin
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    SELECT CASE UCASE$(DRG$)
      CASE "D": x = x * PI / 180
      CASE "G": x = x * PI / 200
      ' CASE "R": nada, ya está en radianes
    END SELECT
    pila_apilar SIN(x)
    entrada$ = ""
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_cos
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    SELECT CASE UCASE$(DRG$)
      CASE "D": x = x * PI / 180
      CASE "G": x = x * PI / 200
    END SELECT
    pila_apilar COS(x)
    entrada$ = ""
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_tan
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    SELECT CASE UCASE$(DRG$)
      CASE "D": x = x * PI / 180
      CASE "G": x = x * PI / 200
    END SELECT
    pila_apilar TAN(x)
    entrada$ = ""
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_asin
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    IF x < -1 OR x > 1 THEN
      mostrar_error("FUERA DE RANGO")
      pila_apilar x
    ELSE
      res = ASIN(x)
      SELECT CASE UCASE$(DRG$)
        CASE "D": res = res * 180 / PI
        CASE "G": res = res * 200 / PI
      END SELECT
      pila_apilar res
    END IF
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_acos
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    IF x < -1 OR x > 1 THEN
      mostrar_error("FUERA DE RANGO")
      pila_apilar x
    ELSE
      res = ACOS(x)
      SELECT CASE UCASE$(DRG$)
        CASE "D": res = res * 180 / PI
        CASE "G": res = res * 200 / PI
      END SELECT
      pila_apilar res
    END IF
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_atan
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    res = ATN(x)
    SELECT CASE UCASE$(DRG$)
      CASE "D": res = res * 180 / PI
      CASE "G": res = res * 200 / PI
    END SELECT
    pila_apilar res
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

'--------------------------------------
SUB op_sinh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>710 THEN
    mostrar_error("SINH: DESBORDAMIENTO")
    EXIT SUB
  END IF
  IF x>20 THEN
    z=EXP(x-LOG(2))
  ELSEIF x< -20 THEN
    z=-EXP(-x-LOG(2))
  ELSE
    z=(EXP(x)-EXP(-x))/2
  END IF
  pila_a(tope)=z
END SUB

SUB op_cosh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>710 THEN
    mostrar_error("COSH: DESBORDAMIENTO")
    EXIT SUB
  END IF
  IF ABS(x)>20 THEN
    z=EXP(ABS(x)-LOG(2))
  ELSE
    z=(EXP(x)+EXP(-x))/2
  END IF
  pila_a(tope)=z
END SUB

SUB op_tanh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x>20 THEN
    z=1
  ELSEIF x< -20 THEN
    z=-1
  ELSE
    y=EXP(-2*ABS(x))
    z=(1-y)/(1+y)
    IF x<0 THEN z=-z
  END IF
  pila_a(tope)=z
END SUB

SUB op_asinh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>1E+150 THEN
    z=LOG(ABS(x))+LOG(2)
    IF x<0 THEN z=-z
  ELSEIF ABS(x)<0.000001 THEN
    z=x
  ELSE
    z=LOG(ABS(x)+SQR(x*x+1))
    IF x<0 THEN z=-z
  END IF
  pila_a(tope)=z
END SUB

SUB op_acosh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x<1 THEN
    mostrar_error("DOMINIO x>=1")
    EXIT SUB
  END IF
  IF x>1E+150 THEN
    z=LOG(x)+LOG(2)
  ELSE
    z=LOG(x+SQR((x-1)*(x+1)))
  END IF
  pila_a(tope)=z
END SUB

SUB op_atanh
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>=1 THEN
    mostrar_error("|x|<1 REQ.")
    EXIT SUB
  END IF
  z=0.5*LOG((1+x)/(1-x))
  pila_a(tope)=z
END SUB
'--------------------------------------
SUB op_d2r
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar x * PI / 180
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_r2d
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar x * 180 / PI
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_d2g
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar x * 200 / 180
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_g2d
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar x * 180 / 200
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_d2dms
  LOCAL x,sg,grados,segtotal,minutos,segundos,z
  IF tope<1 THEN
    mostrar_error("REQ. UN ELEMENTO")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>100000000 THEN
    mostrar_error("DMS: MAX 1E8 GRADOS")
    EXIT SUB
  END IF
  sg=1
  IF x<0 THEN sg=-1
  x=ABS(x)
  grados=INT(x)
  segtotal=INT((x-grados)*3600+0.5)
  IF segtotal>=3600 THEN
    grados=grados+1
    segtotal=segtotal-3600
  END IF
  minutos=INT(segtotal/60)
  segundos=segtotal-minutos*60
  z=sg*(grados*10000+minutos*100+segundos)
  pila_a(tope)=z
END SUB

SUB op_dms2d
  LOCAL x,sg,grados,minutos,segundos,z,fraccion
  IF tope<1 THEN
    mostrar_error("REQ. UN ELEMENTO")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF ABS(x)>1000000000000 THEN
    mostrar_error("DMS: FUERA DE RANGO")
    EXIT SUB
  END IF
  IF x<>INT(x) THEN
    mostrar_error("DMS: SOLO GGMMSS")
    EXIT SUB
  END IF
  sg=1
  IF x<0 THEN sg=-1
  x=ABS(x)
  grados=INT(x/10000)
  fraccion=x-grados*10000
  minutos=INT(fraccion/100)
  segundos=fraccion-minutos*100
  IF minutos>59 OR segundos>59 THEN
    mostrar_error("DMS: MIN/SEG 0..59")
    EXIT SUB
  END IF
  z=sg*(grados+minutos/60+segundos/3600)
  pila_a(tope)=z
END SUB
'--------------------------------------

'--------------------------------------
SUB op_ln
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x<=0 THEN
    mostrar_error("DOMINIO x>0")
    EXIT SUB
  END IF
  z=LOG(x)
  pila_a(tope)=z
END SUB

SUB op_log10
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x<=0 THEN
    mostrar_error("DOMINIO x>0")
    EXIT SUB
  END IF
  z=LOG(x)/LOG(10)
  pila_a(tope)=z
END SUB

SUB op_exp
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x>709.7 THEN
    mostrar_error("EXP: DESBORDAMIENTO")
    EXIT SUB
  END IF
  z=EXP(x)
  pila_a(tope)=z
END SUB

SUB op_10x
  LOCAL x, y, z
  IF tope<1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  x=pila_a(tope)
  IF x>308.2 THEN
    mostrar_error("10^X: DESBORDAMIENTO")
    EXIT SUB
  END IF
  z=10^x
  pila_a(tope)=z
END SUB
'--------------------------------------
SUB op_abs
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar ABS(x)
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_int
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar INT(x)
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_frac
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar x - INT(x)
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

' Signo (-1,0,1)
SUB op_sgn
  IF tope >= 1 THEN
    IF pila_t%(tope)<>T_REAL THEN
      mostrar_error("TIPO NO REAL")
      EXIT SUB
    END IF
    x = pila_desapilar()
    pila_apilar SGN(x)
  ELSE
    mostrar_error("REQ. UN ELEMENTO")
  END IF
END SUB

SUB op_fact
  ' Misma restriccion que el factorial directo (!) de op_factorial.
  ' La pila emplea reales de precision doble; 171! desborda.
  LOCAL n, res, i
  IF tope < 1 THEN
    mostrar_error("PILA VACIA")
    EXIT SUB
  END IF

  ' Validar ANTES de desapilar. Ante error, X queda intacto.
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  n = pila_a(tope)
  IF n < 0 OR n > 170 THEN
    mostrar_error("REQ. UN ENTERO [0; 170]")
    EXIT SUB
  END IF
  IF n <> INT(n) THEN
    mostrar_error("REQ. UN ENTERO [0; 170]")
    EXIT SUB
  END IF

  n = pila_desapilar()
  res = 1
  FOR i = 1 TO n
    res = res * i
  NEXT i
  pila_apilar res
END SUB

' Primo? (1 si, 0 no)
SUB op_primo
  LOCAL n,d,primo%
  IF tope<1 THEN
    mostrar_error("REQ. UN ELEMENTO")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  n=pila_a(tope)
  IF ABS(n)>100000000 OR n<>INT(n) THEN
    mostrar_error("PRIMO: ENTERO MAX 1E8")
    EXIT SUB
  END IF
  IF n<2 THEN
    pila_a(tope)=0
    EXIT SUB
  END IF
  IF n=2 THEN
    pila_a(tope)=1
    EXIT SUB
  END IF
  IF (n MOD 2)=0 THEN
    pila_a(tope)=0
    EXIT SUB
  END IF
  primo%=1
  FOR d=3 TO INT(SQR(n)) STEP 2
    IF (n MOD d)=0 THEN
      primo%=0
      EXIT FOR
    END IF
  NEXT d
  pila_a(tope)=primo%
END SUB

SUB op_mcd
  LOCAL a,b,t
  IF tope<2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL OR pila_t%(tope-1)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  a=pila_a(tope-1)
  b=pila_a(tope)
  IF ABS(a)>1000000000 OR ABS(b)>1000000000 THEN
    mostrar_error("MCD: MAX 1E9")
    EXIT SUB
  END IF
  IF a<>INT(a) OR b<>INT(b) THEN
    mostrar_error("MCD: SOLO ENTEROS")
    EXIT SUB
  END IF
  a=ABS(a)
  b=ABS(b)
  DO WHILE b<>0
    t=b
    b=a MOD b
    a=t
  LOOP
  pila_a(tope-1)=a
  tope=tope-1
END SUB

SUB op_mcm
  LOCAL a,b,aa,bb,t,g,resultado
  IF tope<2 THEN
    mostrar_error("REQ. DOS ELEMENTOS")
    EXIT SUB
  END IF
  IF pila_t%(tope)<>T_REAL OR pila_t%(tope-1)<>T_REAL THEN
    mostrar_error("TIPO NO REAL")
    EXIT SUB
  END IF
  a=pila_a(tope-1)
  b=pila_a(tope)
  IF ABS(a)>1000000000 OR ABS(b)>1000000000 THEN
    mostrar_error("MCM: MAX 1E9")
    EXIT SUB
  END IF
  IF a<>INT(a) OR b<>INT(b) THEN
    mostrar_error("MCM: SOLO ENTEROS")
    EXIT SUB
  END IF
  aa=ABS(a)
  bb=ABS(b)
  IF aa=0 OR bb=0 THEN
    resultado=0
  ELSE
    a=aa
    b=bb
    DO WHILE b<>0
      t=b
      b=a MOD b
      a=t
    LOOP
    g=a
    IF aa/g>9007199254740991/bb THEN
      mostrar_error("MCM: FUERA DE RANGO")
      EXIT SUB
    END IF
    resultado=(aa/g)*bb
  END IF
  pila_a(tope-1)=resultado
  tope=tope-1
END SUB
'--------------------------------------

' -------------------------------------
' es_numero(s$): devuelve 1 si s$ es un 
' numero valido, 0 si no.
' Soporta: [+|-]ddd[.ddd][E[+|-]ddd]
' -------------------------------------
FUNCTION es_numero(s$)
  LOCAL t$, i, c$, tiene_punto, en_exp, digitos, digitos_exp
  t$ = LTRIM$(RTRIM$(s$))
  IF t$ = "" THEN es_numero = 0 : EXIT FUNCTION

  i = 1
  ' signo inicial opcional
  IF MID$(t$,1,1) = "+" OR MID$(t$,1,1) = "-" THEN
    IF LEN(t$) = 1 THEN es_numero = 0 : EXIT FUNCTION
    i = 2
  END IF

  tiene_punto = 0 : en_exp = 0 : digitos = 0 : digitos_exp = 0

  DO WHILE i <= LEN(t$)
    c$ = MID$(t$, i, 1)
    IF c$ >= "0" AND c$ <= "9" THEN
      IF en_exp = 0 THEN
        digitos = digitos + 1
      ELSE
        digitos_exp = digitos_exp + 1
      END IF

    ELSEIF c$ = "." AND tiene_punto = 0 AND en_exp = 0 THEN
      tiene_punto = 1

    ELSEIF (c$ = "E" OR c$ = "e") AND en_exp = 0 THEN
      ' pasa a parte exponencial; puede tener signo a continuacion
      en_exp = 1
      ' si hay signo inmediatamente despues de E, saltarlo
      IF i < LEN(t$) THEN
        IF MID$(t$, i + 1, 1) = "+" OR MID$(t$, i + 1, 1) = "-" THEN
          i = i + 1
        END IF
      END IF
      ' no permitimos terminar en E o E+/- sin digitos
      IF i = LEN(t$) THEN es_numero = 0 : EXIT FUNCTION

    ELSE
      es_numero = 0 : EXIT FUNCTION
    END IF
    i = i + 1
  LOOP

  ' debe haber al menos un digito en la parte principal
  IF digitos = 0 THEN es_numero = 0 : EXIT FUNCTION
  ' si hubo exponente, debe tener digitos
  IF en_exp = 1 AND digitos_exp = 0 THEN es_numero = 0 : EXIT FUNCTION

  es_numero = 1
END FUNCTION


'--------------------------------------
FUNCTION formatear_numero$(valor)
  LOCAL temp$, absv, dig_int, prec, fmt$, s$
  LOCAL exp, mant, logv, frac
  LOCAL posE, mantisa$, exponente$

  ' ===== Casos triviales =====
  IF valor = 0 THEN
    formatear_numero$ = "0"
    EXIT FUNCTION
  END IF

  absv=ABS(valor)

  SELECT CASE FORMATO$

    ' =================== NORM ===================
    CASE "NORM"
      'absv = ABS(valor)

      ' digitos enteros con guardas
      ON ERROR SKIP
      logv = LOG(absv) / LOG(10)
      ON ERROR ABORT

      IF absv >= 1 THEN
        dig_int = INT(logv) + 1
      ELSE
        dig_int = 0
      END IF

      ' ≤13 digitos => fijo
      IF absv<1E-12 OR absv>=1E13 THEN
        ' Evita perder magnitudes pequenas o generar textos enormes.
        fmt$="%.12g"
      ELSE
        prec=13-dig_int
        IF prec<0 THEN prec=0
        IF prec>12 THEN prec=12
        s$=LTRIM$(STR$(prec))
        fmt$="%."+s$+"f"
      END IF
      temp$ = FORMAT$(valor, fmt$)


    CASE "FIX"
      'absv = ABS(valor)
      ON ERROR SKIP
      logv = LOG(absv) / LOG(10)
      ON ERROR ABORT

      s$ = LTRIM$(STR$(DECIM))
      ' FIX mantiene sus decimales cuando son visibles.
      ' La notacion exponencial impide representar un no-cero como 0.
      IF absv>=1E15 OR absv<10^(-DECIM) THEN
        fmt$="%."+s$+"e"
      ELSE
        fmt$="%."+s$+"f"
      END IF
      temp$ = FORMAT$(valor, fmt$)


    CASE "SCI"
      'absv = ABS(valor)
      ON ERROR SKIP
      logv = LOG(absv) / LOG(10)
      ON ERROR ABORT

      exp  = INT(logv)
      frac = logv - exp
      mant = SGN(valor) * (10 ^ frac)

      s$ = LTRIM$(STR$(DECIM))
      fmt$ = "%." + s$ + "f"
      temp$ = FORMAT$(mant, fmt$)

      ' Exponente con signo
      IF exp >= 0 THEN
        exponente$ = "E+" + LTRIM$(STR$(exp))
      ELSE
        exponente$ = "E" + LTRIM$(STR$(exp)) 
      END IF
      temp$ = temp$ + exponente$


    CASE "ENG"
      'absv = ABS(valor)
      ON ERROR SKIP
      logv = LOG(absv) / LOG(10)
      ON ERROR ABORT

      exp  = INT(logv)
      exp = 3*INT(logv/3) ' multiplo de 3 tambien para negativos
      frac = logv - exp
      mant = SGN(valor) * (10 ^ frac)

      s$ = LTRIM$(STR$(DECIM))
      fmt$ = "%." + s$ + "f"
      temp$ = FORMAT$(mant, fmt$)

      IF exp >= 0 THEN
        exponente$ = "E+" + LTRIM$(STR$(exp))
      ELSE
        exponente$ = "E" + LTRIM$(STR$(exp))
      END IF
      temp$ = temp$ + exponente$

    ' =====fallback =======
    CASE ELSE
      temp$ = STR$(valor)
  END SELECT

  ' ===== Limpieza mantisa =====
  posE = INSTR(UCASE$(temp$), "E")
  IF posE > 0 THEN
    mantisa$    = LEFT$(temp$, posE - 1)
    exponente$  = MID$(temp$,  posE)  
  ELSE
    mantisa$   = temp$
    exponente$ = ""
  END IF

  ' recorte de ceros enla mantisa
  IF INSTR(mantisa$, ".") > 0 THEN
    DO WHILE RIGHT$(mantisa$, 1) = "0"
      mantisa$ = LEFT$(mantisa$, LEN(mantisa$) - 1)
    LOOP
    IF RIGHT$(mantisa$, 1) = "." THEN
      mantisa$ = LEFT$(mantisa$, LEN(mantisa$) - 1)
    END IF
  END IF

  temp$ = mantisa$ + exponente$

  formatear_numero$ = temp$
END FUNCTION


'-------------------------------------
SUB ver_ayuda(texto$(), total)
  ' Ayuda RPN 0.3.0: 8 pantallas, sin instrucciones en el pie.
  ' La firma original se conserva para no cambiar su llamada.
  LOCAL helpPage, helpLast, helpRow, helpLine$(12)
  LOCAL helpTitle$, helpKey$, helpBg, helpInk, helpBarra
  LOCAL helpBlanco, helpAc, helpChanged, helpCount
  helpPage=1
  helpLast=8
  helpBg=RGB(221,233,229)
  helpInk=RGB(8,12,14)
  helpBarra=RGB(30,57,72)
  helpBlanco=RGB(255,255,255)
  helpAc=RGB(12,78,102)
  helpChanged=1
  DO
    IF helpChanged=1 THEN
      FOR helpRow=1 TO 12
        helpLine$(helpRow)=""
      NEXT helpRow
      helpCount=0
      SELECT CASE helpPage
        CASE 1
          helpTitle$="RPN / PILA"
          helpCount=10
          helpLine$(1)="X: tope de pila"
          helpLine$(2)="Y: segundo registro"
          helpLine$(3)="Z: tercer registro"
          helpLine$(4)="T: cuarto registro"
          helpLine$(5)="8..5: niveles superiores"
          helpLine$(6)=""
          helpLine$(7)="2 ENTER 3 +   = 5"
          helpLine$(8)="9 R           = 3"
          helpLine$(9)="La operacion toma X o Y,X."
          helpLine$(10)="El resultado queda en X."
        CASE 2
          helpTitle$="TECLADO"
          helpCount=11
          helpLine$(1)="ENTER : apilar / DUP"
          helpLine$(2)="U     : duplicar X"
          helpLine$(3)="S     : intercambiar X,Y"
          helpLine$(4)="D     : borrar X"
          helpLine$(5)="X     : limpiar pila"
          helpLine$(6)=""
          helpLine$(7)="+ - * / : operaciones"
          helpLine$(8)="R     : raiz cuadrada"
          helpLine$(9)="I     : inversa 1/X"
          helpLine$(10)="^ / ! : potencia / factorial"
          helpLine$(11)="P / E : pi / e"
        CASE 3
          helpTitle$="TRIG"
          helpCount=10
          helpLine$(1)="SIN   : seno"
          helpLine$(2)="COS   : coseno"
          helpLine$(3)="TAN   : tangente"
          helpLine$(4)="ASIN  : arco seno"
          helpLine$(5)="ACOS  : arco coseno"
          helpLine$(6)="ATAN  : arco tangente"
          helpLine$(7)=""
          helpLine$(8)="DEG : grados"
          helpLine$(9)="RAD : radianes"
          helpLine$(10)="GRA : gradianes"
        CASE 4
          helpTitle$="HIPERBOLICAS"
          helpCount=6
          helpLine$(1)="SINH  : seno hiperbolico"
          helpLine$(2)="COSH  : coseno hiperbolico"
          helpLine$(3)="TANH  : tangente hiperbolica"
          helpLine$(4)="ASINH : arco seno hiperb."
          helpLine$(5)="ACOSH : arco coseno hiperb."
          helpLine$(6)="ATANH : arco tangente hiperb."
        CASE 5
          helpTitle$="MATH"
          helpCount=8
          helpLine$(1)="LN    : logaritmo natural"
          helpLine$(2)="LOG   : logaritmo base 10"
          helpLine$(3)="EXP   : e elevado a X"
          helpLine$(4)="10^X  : 10 elevado a X"
          helpLine$(5)=""
          helpLine$(6)="R     : raiz cuadrada"
          helpLine$(7)="I     : inversa de X"
          helpLine$(8)="^     : Y elevado a X"
        CASE 6
          helpTitle$="NUM"
          helpCount=8
          helpLine$(1)="ABS   : valor absoluto"
          helpLine$(2)="INT   : parte entera"
          helpLine$(3)="FRAC  : parte fraccionaria"
          helpLine$(4)="SGN   : signo de X"
          helpLine$(5)="FACT  : factorial"
          helpLine$(6)="PRIMO : prueba de primalidad"
          helpLine$(7)="MCD   : maximo comun divisor"
          helpLine$(8)="MCM   : minimo comun multiplo"
        CASE 7
          helpTitle$="CONV / CONST"
          helpCount=11
          helpLine$(1)="D>R / R>D : DEG/RAD"
          helpLine$(2)="D>G / G>D : DEG/GRA"
          helpLine$(3)="DEG>DMS   : grados a DMS"
          helpLine$(4)="DMS>DEG   : DMS a grados"
          helpLine$(5)=""
          helpLine$(6)="PI : numero pi"
          helpLine$(7)="E  : numero de Euler"
          helpLine$(8)="PHI: numero aureo"
          helpLine$(9)="C  : velocidad de la luz"
          helpLine$(10)="G/H: gravitacion / Planck"
          helpLine$(11)="QE : carga del electron"
        CASE 8
          helpTitle$="CONFIG / MENUS"
          helpCount=10
          helpLine$(1)="F1: TRIG"
          helpLine$(2)="F2: MATH"
          helpLine$(3)="F3: NUM"
          helpLine$(4)="F4: CONST"
          helpLine$(5)="F5: SET"
          helpLine$(6)=""
          helpLine$(7)="M: DEG > RAD > GRA"
          helpLine$(8)="NORM: formato normal"
          helpLine$(9)="FIXn: decimales fijos"
          helpLine$(10)="SCIn/ENG: exponenciales"
      END SELECT
      CLS helpBg
      BOX 0,0,320,32,0,helpBarra,helpBarra
      TEXT 8,8,"AYUDA RPN","LT",4,1,helpBlanco,helpBarra
      TEXT 312,10,STR$(helpPage)+"/"+STR$(helpLast),"RT",1,1,RGB(203,234,219),helpBarra
      TEXT 10,43,helpTitle$,"LT",4,1,helpAc,helpBg
      LINE 10,65,310,65,1,RGB(168,183,180)
      FOR helpRow=1 TO helpCount
        IF helpLine$(helpRow)<>"" THEN
          TEXT 12,73+(helpRow-1)*19,helpLine$(helpRow),"LT",1,1,helpInk,helpBg
        END IF
      NEXT helpRow
      helpChanged=0
    END IF
    helpKey$=INKEY$
    IF helpKey$<>"" THEN
      SELECT CASE ASC(helpKey$)
        CASE 27,8,127,145
          EXIT DO
        CASE 130,128
          IF helpPage>1 THEN
            helpPage=helpPage-1
            helpChanged=1
          END IF
        CASE 131,129
          IF helpPage<helpLast THEN
            helpPage=helpPage+1
            helpChanged=1
          END IF
      END SELECT
    ELSE
      PAUSE 1
    END IF
  LOOP
END SUB

' Recorta/pad columnas
FUNCTION ajustar$(s$)
  IF LEN(s$) <= 40 THEN
    ajustar$ = s$
  ELSE
    ajustar$ = LEFT$(s$, 40)
  END IF
END FUNCTION

' Lee flechas y ESC de forma robusta.
FUNCTION leer_tecla_paginador$()
  LOCAL k$, k2$, k3$, t

  DO
    k$ = INKEY$
    IF k$ <> "" THEN
      SELECT CASE k$
        CASE CHR$(27), CHR$(8), CHR$(145)
          leer_tecla_paginador$ = "ESC"
          EXIT FUNCTION
        CASE CHR$(145),CHR$(128)
          leer_tecla_paginador$ = "UP"
          EXIT FUNCTION
        CASE CHR$(146),CHR$(129)  
            leer_tecla_paginador$ = "DOWN"
            EXIT FUNCTION
      END SELECT
    END IF
    PAUSE 10
  LOOP
END FUNCTION
' ================= fin paginador =================
SUB cargar_ayuda
  ayuda$(1)  = "  TRIGONOMETRIA"
  ayuda$(2)  = ""
  ayuda$(3)  = "SIN    seno"
  ayuda$(4)  = "COS    coseno"
  ayuda$(5)  = "TAN    tangente"
  ayuda$(6)  = "ASIN   arco seno"
  ayuda$(7)  = "ACOS   arco coseno"
  ayuda$(8)  = "ATAN   arco tangente"
  ayuda$(9)  = ""
  ayuda$(10)  = "  Hiperbolicas"
  ayuda$(11) = "SINH   seno"
  ayuda$(12) = "COSH   coseno"
  ayuda$(13) = "TANH   tangente"
  ayuda$(14) = "ASINH  arco seno"
  ayuda$(15) = "ACOSH  arco coseno"
  ayuda$(16) = "ATANH  arco tangente"
  ayuda$(17) = ""
  ayuda$(18) = ""


  ayuda$(19) = "  LOGARITMO/EXPONENCIAL"
  ayuda$(20) = ""
  ayuda$(21) = "LN     logaritmo natural"
  ayuda$(22) = "LOG    logaritmo base 10"
  ayuda$(23) = "EXP    e^x"
  ayuda$(24) = "10^X   potencia de 10"
  ayuda$(25) = ""
  ayuda$(26) = "  ENTEROS"
  ayuda$(27) = ""
  ayuda$(28) = "ABS   valor absoluto"
  ayuda$(29) = "INT   parte entera"
  ayuda$(30) = "FRAC  parte fraccionaria"
  ayuda$(31) = "SGN   signo (-1,0,1)"
  ayuda$(32) = "FACT  factorial (n!)"
  ayuda$(33) = "PRIMO 1=primo, 2=no primo"
  ayuda$(34) = "MCD   maximo comun divisor"
  ayuda$(35) = "MCM   minimo comun mult."
  ayuda$(36) = ""

  ayuda$(37) = "  MENU ANGULOS"
  ayuda$(38) = ""
  ayuda$(39) = "DEG>RAD grados a radianes"
  ayuda$(40) = "RAD>DEG radianes a grados"
  ayuda$(41) = "DEG>GRA grados a gradianes"
  ayuda$(42) = "GRA>DED gradianes a grados"
  ayuda$(43) = "DEG>DMS grados a DMS"
  ayuda$(44) = "DMS>DEM DMS a grados"
  ayuda$(45) = ""
  ayuda$(46) = "  MENU CONSTANTES"
  ayuda$(47) = ""
  ayuda$(48) = "PI   3.141592653589..."
  ayuda$(49) = "e    numero de Euler"
  ayuda$(50) = "PHI  numero aureo"
  ayuda$(51) = "c    velocidad de la luz"
  ayuda$(52) = "G    cte gravitatoria"
  ayuda$(53) = "h    cte de Planck"
  ayuda$(54) = "qe   carga electron"
END SUB

SUB C_MenuOp
  COLOR RGB(80,255,80),RGB(WHITE)
END SUB

SUB C_MenuOpSel
  C_MenuTitulo
  'COLOR RGB(33,33,127), RGB(180,180,255)
END SUB

SUB C_MenuTitulo
  COLOR RGB(WHITE),RGB(50,255,50)
END SUB

SUB variables_iniciar()
  CONST MAX_PILA = 100
  DIM tope
  DIM ayuda$(60)
  DIM menu$(10)
  DIM submenuTrig$(12)
  DIM submenuLog$(10)
  DIM submenuInt$(10)
  DIM submenuConst$(10)
  DIM submenuConv$(6)
  DIM submenuConf$(11)
  DRG$ = "D"
  total_ayuda = 54
  FORMATO$ = "NORM" '"FIX", "SCI", "ENG"
  DECIM = 6      ' cantidad de decimales

  ' ---- definir menu principal ----
  menu$(1) = "TRIGONOM.>"
  menu$(2) = "LOG/EXP  >"
  menu$(3) = "ENTEROS  >"
  menu$(4) = "ANGULOS  >"
  menu$(5) = "CONST.   >"
  menu$(6) = "CONFIG.  >"
  menu$(7) = "AYUDA     "
  total = 7

  ' ---- submenu trigonometria ----
  submenuTrig$(1) = "SIN"
  submenuTrig$(2) = "COS"
  submenuTrig$(3) = "TAN"
  submenuTrig$(4) = "ASIN"
  submenuTrig$(5) = "ACOS"
  submenuTrig$(6) = "ATAN"
  submenuTrig$(7) = "SINH"
  submenuTrig$(8) = "COSH"
  submenuTrig$(9) = "TANH"
  submenuTrig$(10) = "ASINH"
  submenuTrig$(11) = "ACOSH"
  submenuTrig$(12) = "ATANH"  
  totalTrig = 12

  ' ---- submenu LOG/EXP ----
  submenuLog$(1) = "LN"
  submenuLog$(2) = "LOG"
  submenuLog$(3) = "EXP"
  submenuLog$(4) = "10^X"
  totalLog = 4

  ' ---- submenu ENTEROS ----
  submenuInt$(1) = "ABS"
  submenuInt$(2) = "INT"
  submenuInt$(3) = "FRAC"
  submenuInt$(4) = "SGN"
  submenuInt$(5) = "FACT"
  submenuInt$(6) = "PRIMO"
  submenuInt$(7) = "MCD"
  submenuInt$(8) = "MCM"
  totalInt = 8

  ' ---- submenu ANGULOS ----
  submenuConv$(1) = "DEG > RAD"
  submenuConv$(2) = "RAD > DEG"
  submenuConv$(3) = "DEG > GRA"
  submenuConv$(4) = "GRA > DEG"
  submenuConv$(5) = "DEG > DMS"
  submenuConv$(6) = "DMS > DEG"
  totalConv = 6

  ' ---- submenu CONSTANTES ----
  submenuConst$(1) = "PI"
  submenuConst$(2) = "E"
  submenuConst$(3) = "PHI"
  submenuConst$(4) = "C"
  submenuConst$(5) = "G"
  submenuConst$(6) = "H"
  submenuConst$(7) = "QE"
  totalConst = 7

  ' ---- submenu CONFIG ----
  submenuConf$(1) = "DEG"
  submenuConf$(2) = "RAD"
  submenuConf$(3) = "GRA"
  submenuConf$(4) = "NORM"
  submenuConf$(5) = "FIX3"
  submenuConf$(6) = "FIX6"
  submenuConf$(7) = "FIX9"
  submenuConf$(8) = "SCI3"
  submenuConf$(9) = "SCI6"
  submenuConf$(10) = "SCI9"
  submenuConf$(11) = "ENG"
  totalConf = 11
END SUB

SUB testeo()
  LOCAL s$, y
  COLOR RGB(WHITE), RGB(BLACK)
  CLS : FONT 7,2
  IF FORMATO$="" THEN FORMATO$="NORM"
  IF DECIM=0 THEN DECIM=6
  y=0

  ' MUL
  TEXT 0,y,"Test MUL" : y=y+20
  pila_limpiar : ps_r 2 : ps_r 3 : op_mult
  s$=formatear_item$(tope) : TEXT 0,y,"RR 2*3 = " + s$ : y=y+20
  pila_limpiar : ps_r 5 : ps_c 3,2 : op_mult
  s$=formatear_item$(tope) : TEXT 0,y,"RC 5*(3+2i) = " + s$ : y=y+20
  pila_limpiar : ps_c 1,-4 : ps_r 10 : op_mult
  s$=formatear_item$(tope) : TEXT 0,y,"CR (1-4i)*10 = " + s$ : y=y+20
  pila_limpiar : ps_c 2,3 : ps_c 4,-5 : op_mult
  s$=formatear_item$(tope) : TEXT 0,y,"CC (2+3i)*(4-5i) = " + s$ : y=y+20

  ' DIV
  TEXT 0,y,"Test DIV" : y=y+20
  pila_limpiar : ps_r 8 : ps_r 2 : op_div
  s$=formatear_item$(tope) : TEXT 0,y,"RR 8/2 = " + s$ : y=y+20
  pila_limpiar : ps_r 5 : ps_c 3,2 : op_div
  s$=formatear_item$(tope) : TEXT 0,y,"RC 5/(3+2i) = " + s$ : y=y+20
  pila_limpiar : ps_c 1,-4 : ps_r 2 : op_div
  s$=formatear_item$(tope) : TEXT 0,y,"CR (1-4i)/2 = " + s$ : y=y+20
  pila_limpiar : ps_c 2,3 : ps_c 4,-5 : op_div
  s$=formatear_item$(tope) : TEXT 0,y,"CC (2+3i)/(4-5i) = " + s$
END SUB
