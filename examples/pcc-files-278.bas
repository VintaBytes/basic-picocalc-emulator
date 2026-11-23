' Ensayo de operaciones de archivos MMBasic 6.00.03
' SOLO USAR EN DIRECTORIO DE PRUEBAS. BORRA test_278.tmp.
' Esta rutina presupone que test_278.tmp existe y contiene datos descartables.
PRINT "Prueba de archivos 0.2.78"
RENAME "test_278.tmp" AS "test_278_renamed.tmp"
COPY "test_278_renamed.tmp" TO "test_278_copy.tmp"
KILL "test_278_renamed.tmp"
MKDIR "test_278_dir"
RMDIR "test_278_dir"
PRINT "Operaciones terminadas"
END
