PRINT "TECLADO Y PAUSA"
PRINT "Presione una tecla para terminar"
DO
  K$=INKEY$
  PAUSE 30
LOOP UNTIL K$<>""
PRINT "Tecla leida. Codigo: "; ASC(K$)
END
