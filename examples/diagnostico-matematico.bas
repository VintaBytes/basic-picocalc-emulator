' BASIC PicoCalc Linux - prueba diferencial con PicoCalc fisica
' Anotar firmware y contrastar cada resultado impreso.
PRINT "EXP(0)="; EXP(0)
PRINT "EXP(1)="; EXP(1)
PRINT "ASIN(1)="; ASIN(1)
PRINT "ACOS(0)="; ACOS(0)
PRINT "ATAN2(1,0)="; ATAN2(1,0)
PRINT "ATAN2(0,-1)="; ATAN2(0,-1)
PRINT "CINT(2.5)="; CINT(2.5)
PRINT "CINT(-2.5)="; CINT(-2.5)
PRINT "FIX(-2.9)="; FIX(-2.9)
PRINT "HEX$(255,4)="; HEX$(255,4)
PRINT "BIN$(10,8)="; BIN$(10,8)
PRINT "OCT$(9,4)="; OCT$(9,4)
OPTION ANGLE DEGREES
PRINT "ASIN(1) DEG="; ASIN(1)
PRINT "ATAN2(1,1) DEG="; ATAN2(1,1)
OPTION ANGLE RADIANS
PRINT "FIN PRUEBA"
END
