' PicoMite 6 / BASIC PicoCalc Linux - cotejar en PicoCalc real
' Sin tildes para el charset del hardware.
PRINT "LONGSTRING 248"
DIM INTEGER A%(64), B%(64)
LONGSTRING LOAD A%(), 4, "HOLA"
PRINT "LEN=";LLEN(A%())
LONGSTRING APPEND A%(), " Pico"
PRINT "TEXT=";LGETSTR$(A%(),1,9)
PRINT "FIND=";LINSTR(A%(),"Pico")
PRINT "BYTE=";LGETBYTE(A%(),1)
LONGSTRING COPY B%(), A%()
LONGSTRING LEFT A%(), B%(), 4
PRINT "LEFT=";LGETSTR$(A%(),1,4)
LONGSTRING MID A%(), B%(), 6, 4
PRINT "MID=";LGETSTR$(A%(),1,4)
LONGSTRING RIGHT A%(), B%(), 4
PRINT "RIGHT=";LGETSTR$(A%(),1,4)
LONGSTRING CLEAR A%()
PRINT "CLEAR=";LLEN(A%())
' JSON: reemplazar comillas BASIC con comillas dobles
J$="{""user"":{""name"":""Pico"",""v"":3}}"
LONGSTRING LOAD A%(), LEN(J$), J$
PRINT "JSON=";JSON$(A%(),"user.name")
PRINT "JSON N=";JSON$(A%(),"user.v")
PRINT "FIN"
END
