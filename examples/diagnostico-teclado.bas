' Probar flechas, F1-F12, Shift+F*, Alt, Ctrl+letra
' Para salir, pulsar ESC.
PRINT "DIAGNOSTICO TECLADO PICO"
PRINT "ESC PARA SALIR"
DO
  K$=INKEY$
  IF K$<>"" THEN
    PRINT "CODIGO: "; ASC(K$)
    IF ASC(K$)=27 THEN EXIT DO
  ENDIF
  PAUSE 10
LOOP
END
