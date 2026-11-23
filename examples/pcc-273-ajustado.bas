'--------------------------------------
' PicoCalc Commander: File Manager and
' Launcher for PicoCalc in MMBasic.
' Traducido/ampliado por A. Palazzesi
'--------------------------------------

Option explicit
On error ignore 1
If MM.VER < 6.0002 Then Error
If MM.Errno <> 0 Then
  Print "PCC necesita firmware version 6.00.02 o"
  Print "mayor para funcionar."
  Print
  Print "Presiona una tecla para continuar."
  GetKey
  CLS
  DRIVE "B:"
  CHDIR "B:/bas"
  RUN "menu.bas"
End If

'---------------------------------------
' Global variables

Const maxVisible = 21
Const maxItems = 300
Const maxDepth = 32

Dim integer curPane = 0
Dim integer altPane = 1
Dim integer paneLen(1)
Dim integer previSel(1,maxDepth)
Dim integer previOffset(1,maxDepth)
Dim string  file$(maxItems)
Dim string  fileType$(maxItems)
Dim string  curPath$(1)
Dim string  curDrive$(1)
Dim integer curDepth(1)
Dim integer totalItems = 0
Dim integer sel = 1
Dim integer offset = 1
Dim integer i, idx, invert, feasible, info = 0
Dim string  message$, inputString$, k$ = "", op$
Dim float l
Dim color_msg, color_progress

paneLen(0) = 20     : paneLen(1) = 19
curPath$(0) = "/"   : curPath$(1) = "/"
curDrive$(0) = "B:" : curDrive$(1) = "A:"
curDepth(0) = 0     : curDepth(1) = 0
previSel(0,0) = 1   : previSel(1,0) = 1
previOffset(0,0)= 1 : previOffset(1,0) = 1
color_msg = RGB(green)
color_progress = RGB(green)
'---------------------------------------
' If last exit was due to launching a
' BASIC program, then reload saved state
' to continue where we left off

If MM.PERSISTENT = 1 Then
  On error ignore 1
  Load context
  Save persistent 0
End If

'---------------------------------------
' Initial display of default panes

DrawFrame

'---------------------------------------
' Main loop: gets input and selection

Do
  GetKey
  Select Case k$

    Case "A", "B" ' select drive
      curDrive$(curPane) = UCase$(k$)+":"
      curPath$(curPane) = "/"
      sel = 1 : offset = 1
      curDepth(curPane) = 0
      LoadDir curDrive$(curPane), curPath$(curPane)
    Case Chr$(27), Chr$(8) ' dir up
      If curPath(curPane) <> "/" Then
        DirSelect ".."
        LoadDir curDrive$(curPane), curPath$(curPane)
      End If

    Case "C", "M" ' copy, move
      If fileType$(sel)="D" Then
        message$ = "Los directories no se    pueden copiar o mover."
        Dialog message$, "OK", color_msg

      Else If curDrive$(curPane)+curPath$(curPane)=curDrive$(altPane)+curPath$(altPane) Then
        message$ = "No se puede copiar o     mover un archivo sobre   si mismo."
        Dialog message$, "OK", color_msg
      Else
        feasible = TestFeasible(file$(sel), curDrive$(altPane), curPath$(altPane))
        print "feasible",feasible
        If k$="C" Then op$="copiar" Else op$="mover"
        Select Case feasible
        Case 0, 1
          ' message$ = "Quieres "+Choice(feasible, "sobreescribir:   ", op$+":           ")
          ' message$ = message$+Chr$(34)+file$(sel)+Chr$(34)+Choice(feasible," en ", " a ")
          ' message$ = message$+Chr$(34)+curDrive$(altPane)+curPath$(altPane)+Chr$(34)+"?"
          ' Dialog message$, "SN", Choice(feasible,RGB(yellow),RGB(cyan))

          dest$ = curDrive$(altPane) + curPath$(altPane)
          message$ = "Quieres "+Choice(feasible, "sobreescribir:   ", op$+":")
          message$ = PadToNextRow$(message$, 25)
          message$ = message$ + CHR$(34) + file$(sel) + CHR$(34)   ' línea 2 (solo el archivo)
          message$ = PadToNextRow$(message$, 25)
          message$ = message$ + " a " + CHR$(34) + dest$ + CHR$(34) + "?"  ' línea 3 (destino)
          Dialog message$, "SN", Choice(feasible, RGB(yellow), RGB(cyan))

          If k$="S" Then
            If op$="copiar" Then
              Progress "COPIANDO...",Choice(feasible,RGB(yellow),RGB(cyan))
              Copy file$(sel) To curDrive$(altPane)+curPath$(altpane)+file$(sel)
            Else If op$="mover" Then
              Progress "MOVIENDO...",Choice(feasible,RGB(yellow),RGB(cyan))
              On error ignore 1
              Copy file$(sel) To curDrive$(altPane)+curPath$(altpane)+file$(sel)
              If MM.Errno <> 0 Then
                DrawFrame
                message$ = "Error durante la copia.  No se pudo borrar.       (Mover es copiar+borrar)"
                Dialog message$, "OK", color_msg
              Else
                Kill file$(sel)
              End If
            End If
           End If
        Case 2
          message$ = "No hay espacio suficienteen el disco de destino.  "
          message$ = message$ + "(Mover es copiar+borrar  y se necesita espacio)"
          Dialog message$, "OK", color_msg
        End Select
      End If
      DrawFrame

    Case "O", CHR$(127) ' delete
      message$ = "Quieres borrar:          "
      message$ = message$+Chr$(34)+file$(sel)+Chr$(34)+"?"
      Dialog message$, "SN",color_msg
      If k$ = "S" or k$ = "s" Then
        Progress "BORRANDO...", color_progress
        If fileType$(sel)="D" Then
          If file$(sel)<>".." Then
            On error ignore 1
            Rmdir file$(sel)
            If MM.Errno <> 0 Then
              DrawFrame
              message$ = "No es posible borrar el  directorio. Quizas no    esta vacio."
              Dialog message$, "OK", color_msg
            End If
          Else
            DrawFrame
            message$=Chr$(34)+".."+Chr$(34)+" no fue borrado."
            Dialog message$, "OK", color_msg
          End If
        Else
          Kill file$(sel)
        End If
      End If
      DrawFrame

    Case "K" ' mkdir
      message$ = "Escribe el nombre del    directorio a crear:      "
      message$ = message$+"(en blanco para salir)"
      Dialog message$, "INPUT",RGB(cyan)
      If inputString$<>"" Then
        feasible = TestFeasible(inputString$, curDrive$(curPane), curPath$(curPane))
        If feasible = 1 Then
          message$="Ya existe un directorio o archivo llamado:        " + Chr$(34) + inputString$ + Chr$(34)
          Dialog message$, "OK", color_msg
        Else
          Progress "CREANDO...", RGB(cyan)
          Mkdir inputString$
        End If
      End If
      DrawFrame

    Case "R" 'Ren
      If fileType$(sel)="D" Then
        message$ = "No se pueden renombrar   los directorios."
        Dialog message$, "OK", RGB(white)
      Else
        message$ = "Renombrar "+Chr$(34)+file$(sel)+Chr$(34)+" a:"
        Dialog message$, "INPUT",RGB(cyan)
        If inputString$<>"" Then
          feasible = TestFeasible(inputString$, curDrive$(curPane), curPath$(curPane))
          If feasible = 1 Then
            message$="Ya existe un archivo o   directorio llamado       " + inputString$ 
            Dialog message$, "OK", color_msg
          Else
            Progress "RENOMBRANDO...", RGB(cyan)
            Rename file$(sel) As inputString$
          End If
        End If
      End If
      DrawFrame

    Case "I"
      If info=0 Then
        info =1
      Else
        info = 0 : KeysDisp
      End If

    Case "H","Y" ' help
      DisplayHelp
      DrawFrame

    Case Chr$(9), Chr$(130), Chr$(131)
      ' change pane (tab, left, right)
      DisplayList curPane, 1
      previSel(curPane, curDepth(curPane)) = sel
      previOffset(curPane, curDepth(curPane)) = offset
      sel = previSel(altPane, curDepth(altPane))
      offset = previOffset(altPane, curDepth(altPane))
      If curPane = 1 Then
        curPane = 0 : altPane = 1
      Else
        curPane = 1 : altPane = 0
      End If
      LoadDir curDrive$(curPane), curPath$(curPane)

    Case Chr$(13)  ' select (enter)
      ProcessItem

    Case Chr$(129) ' arrow down
      sel = sel + 1
      If sel > totalItems Then sel = totalItems
      If sel < offset Then offset = sel
      If sel > offset + maxVisible - 1 Then offset = sel - maxVisible + 1

    Case Chr$(128) ' arrow up
      sel = sel - 1
      If sel < 1 Then sel = 1
      If sel < offset Then offset = sel
      If sel > offset + maxVisible - 1 Then offset = sel - maxVisible + 1


    Case "Q","S" ' quit
      CLS
      Color RGB(green), 0
      Print curDrive$(curPane)+curPath$(curPane)
      Save persistent 1
      On error ignore 1
      Save context

      DRIVE "B:"
      CHDIR "B:/bas/"
      COLOR RGB(WHITE)  
      CLS
      PRINT "[F1] Menu Principal"
      PRINT "[F5] Calculadora RPN"
      PRINT "[F7] Navegador de Archivos"
      PRINT "[F8] Graficador de Funciones"
      PRINT 
      COLOR RGB(GREEN)
      END

    Case "E" ' editar
      CLS
      Color RGB(green), 0
      Print curDrive$(curPane)+curPath$(curPane)
      Save persistent 1
      On error ignore 1
      Save context

      DRIVE curDrive$(curPane)
      CHDIR curDrive$(curPane)+curPath$(curPane)

      ' --- Editar ---
      EDIT FILE file$(sel)

      CLS
      DRIVE "B:"
      CHDIR "B:/bas"
      RUN "pcc.bas"      
    End Select

  DisplayList curPane, 0
  If info=1 Then InfoDisp
Loop

'---------------------------------------
' Subs

Sub LoadDir(drive$ As string, path$ As string)
  ' Load current dir into an array
  Local d$
  Drive drive$
  Chdir path$
  totalItems = 0

  ' If Not at root, add a parent dir
  If path$ <> "/" Then
    totalItems = 1
    file$(totalItems) = ".."
    fileType$(totalItems) = "D"
  End If

  ' Load directories first:
  d$ = Dir$("*", DIR)
  Do While d$ <> ""
    totalItems = totalItems + 1
    If totalItems > maxItems Then Return
    file$(totalItems) = d$
    fileType$(totalItems) = "D"
    d$ = Dir$()
  Loop

  ' Load files:
  d$ = Dir$("*.*", FILE)
  Do While d$ <> ""
    totalItems = totalItems + 1
    If totalItems > maxItems Then Return
    file$(totalItems) = d$
    Select Case UCase$(Right$(d$,3))
      Case "BAS"
        fileType$(totalItems) = "B"
      Case "BMP"
        fileType$(totalItems) = "I"
      Case "JPG"
        fileType$(totalItems) = "J"
      Case "TXT", ".MD", "BAT"
        fileType$(totalItems) = "T"
      Case "WAV"
        fileType$(totalItems) = "W"
      Case Else
        fileType$(totalItems) = "M"
    End Select
    d$ = Dir$()
  Loop
End Sub

'---------------------------------------
Sub DisplayList(pane As integer, isAlt As integer)
  Local dispPath$, dispLine$, fileName$
  Local i, dotPos, nameLen

  ' Display path
  ItemColor "H", 1
  dispPath$ = curDrive$(pane)+curPath$(pane)
  If Len(dispPath$) > 40 Then
    dispPath$ = Left$(dispPath$,39)+"~"
  Else
    dispPath$ = dispPath$+String$(40-Len(dispPath$)," ")
  End If
  Print @(0,4) dispPath$;

  ' Display directory list
  For i = 0 To maxVisible
    idx = offset + i
    If idx > totalItems Then Exit For
    invert = 0
    If idx = sel And isAlt = 0 Then invert = 1
    ItemColor fileType$(idx), invert
    fileName$ = file$(idx)
    nameLen = Len(fileName$)
    If fileType$(idx) = "D" Then ' dirs
      If nameLen > paneLen(pane)-4 Then
        dispLine$ = Left$(fileName$,paneLen(pane)-5)+"~ <d>"
      Else
        dispLine$ = fileName$+String$(paneLen(pane)-nameLen-3," ")+"<d>"
      End If
    Else 'file names
      dotPos = Instr(1,fileName$,"\.[^\.]*$",l)
      If dotPos = 1 Then
        fileName$=Right$(fileName$,nameLen-1)+".<h>"
        nameLen = Len(fileName$)
        dotPos = Instr(1,fileName$,"\.[^\.]*$",l)
      EndIf
      Select Case dotPos
        Case 0 ' no dot in the name
          If nameLen > paneLen(pane)-4 Then
            dispLine$ = Left$(fileName$,paneLen(pane)-4)+"~   "
          Else ' name not long
            dispLine$ = fileName$+String$(paneLen(pane)-nameLen," ")
          End If
        Case is > paneLen(pane)-3
          dispLine$ = Left$(fileName$,paneLen(pane)-5)+"~ "
          dispLine$ = dispLine$ + Right$(fileName$+"   ",nameLen-dotPos+3)
          dispLine$ = Left$(dispLine$,paneLen(pane))
        Case Else ' name before dot not long
          dispLine$ = Left$(fileName$,dotPos-1)+String$(paneLen(pane)-dotPos-2," ")
          dispLine$ = dispLine$ + Right$(fileName$+"   ",nameLen-dotPos+3)
          dispLine$ = Left$(dispLine$,paneLen(pane))
      End Select
    End If
    Print @(pane*168,i*12+24) dispLine$;
  Next i
  ClearPane pane, i
  ItemColor "M", 0
End Sub

'---------------------------------------
Sub ProcessItem
  ' Process the highlighted item
  Select Case fileType$(sel)
    Case "D"
      DirSelect file$(sel)
      LoadDir curDrive$(curPane), curPath$(curPane)
    Case "B"
      CLS
      Save persistent 1
      On error ignore 1
      Save context
      Run file$(sel)
      CLS
      DRIVE "B:"
      CHDIR "B:/bas"
      RUN "pcc.bas"  
    Case "I"
      CLS
      Load image file$(sel)
      GetKey : DrawFrame
    Case "J"
      CLS
      Load jpg file$(sel)
      GetKey : DrawFrame
    Case "T"
      CLS
      ItemColor fileType$(sel), 0
      List file$(sel)
      GetKey : DrawFrame
    Case "W"
      Play wav file$(sel)
  End Select
End Sub

'---------------------------------------
Sub DirSelect(d$ As string)
  If d$=".." Then
    curDepth(curPane) = curDepth(curPane)-1
    sel = previSel(curPane, curDepth(curPane))
    offset = previOffset(curPane, curDepth(curPane))
    curPath$(curPane)=Left$(curPath$(curPane),Instr(1,curPath$(curPane),"[^/]\+/$",l)-1)
  Else
    previSel(curPane, curDepth(curPane)) = sel
    previOffset(curPane, curDepth(curPane)) = offset
    curDepth(curPane) = curDepth(curPane)+1
    sel = 1 : offset = 1
    curPath$(curPane)=curPath$(curPane)+d$+"/"
  End If

  Chdir d$
End Sub

'---------------------------------------
Sub GetKey
  Do : k$ = Inkey$
  Loop Until k$ <> ""
  k$=UCase$(k$)
End Sub

'---------------------------------------
' Devuelve s$ rellenado con espacios 
' hasta el proximo multiplo de w (25)
FUNCTION PadToNextRow$(s$, w)
  LOCAL r
  r = LEN(s$) MOD w
  IF r = 0 THEN
    PadToNextRow$ = s$
  ELSE
    PadToNextRow$ = s$ + SPACE$(w - r)
  ENDIF
END FUNCTION

'---------------------------------------
Sub ItemColor(c$ As string,i As integer)
  Local integer selCol
  Select Case c$
    Case "D" 'directory
      selCol = RGB(green)
    Case "B" 'basic program
      selCol = RGB(white) 'RGB(salmon)
    Case "M" 'misc items (non actionable)
      selCol = RGB(lightgrey)
    Case "H" 'header
      selCol = RGB(Green)
    Case "I", "P", "J" 'images
      selCol = RGB(Gold) 'RGB(cyan)
    Case "T" 'text file
      selCol = RGB(Yellow)
    Case "W" 'wav file
      selCol = RGB(blue)
  End Select
  If i=1 Then
    Color 0, selCol
  Else
    Color selCol, 0
  End If
End Sub

'---------------------------------------
Sub DrawFrame
  Local i, frColor = RGB(White)
  Local v$=Chr$(179)
  Local h1$=String$(20,196)
  Local h2$=String$(19,196)
  Local top$=h1$+Chr$(194)+h2$
  Local bot$=h1$+Chr$(193)+h2$

  CLS
  Color frColor, 0

  Print @(0,12) top$
  Print @(0,288) bot$
  For i=24 To 276 Step 12
    Print @(160,i) v$
  Next i
  If info = 0 Then KeysDisp Else InfoDisp

  Box 0,2,320,2,1,RGB(Green),RGB(Green)
  Box 0,16,320,2,1,RGB(Green),RGB(Green)

  LoadDir curDrive$(altPane), curPath$(altPane)
  previOffset(curPane, curDepth(curPane))=offset
  offset = previOffset(altPane, curDepth(altPane))
  DisplayList altPane, 1
  LoadDir curDrive$(curPane), curPath$(Curpane)
  offset = previOffset(curPane, curDepth(curPane))
  DisplayList curPane, 0
End Sub

'---------------------------------------
Sub ClearPane(pane As integer, row As integer)
  Local i,p,spaces$
  p=pane*168
  spaces$=String$(paneLen(pane)," ")

  Color RGB(lightgrey), 0

  For i=row To maxVisible
    Print @(p,i*12+24) spaces$
  Next i
End Sub

'---------------------------------------
Function TestFeasible(fileName$ As string, destDrive$ As string, destPath$ As string)
  Local integer fSize
  fSize = MM.Info(FILESIZE file$(sel))

  If destDrive$ <> "" Then
    Drive destDrive$
  End If
  If destPath$ <> "" Then
    Chdir destPath$
  End If

  If MM.Info(EXISTS FILE fileName$)<>0 Or MM.Info(EXISTS DIR fileName$) Then
    TestFeasible = 1
  Else If MM.Info(FREE SPACE) < fSize Then
    TestFeasible = 2
  Else
    TestFeasible = 0
  End If

  Drive curDrive$(curPane)
  Chdir curPath$(curPane)
End Function

'---------------------------------------
Sub Dialog(dispText$ As string, choices$ As string, selCol As integer)
  Local i
  Play tone 900,900,70
  Color selCol, 0

  RBox  32,  72,  256,  120  , 10, RGB(lightgrey), 0
  If Len(dispText$)> 125 Then
    dispText$ = Left$(dispText$, 122)+"..."
  End If
  For i=1 To Fix(Len(dispText$)/25+0.96)
    Print @(60,80+i*12) Mid$(dispText$,(i-1)*24+i,25)
  Next i
  Color RGB(white), 0
  Select Case choices$
    Case "SN"
      Print @(132,72+(i+2)*12,2) "S";
      Print "i/";
      Print @(132+36,72+(i+2)*12,2) "N";
      Print "o"
      Do : GetKey
      Loop Until k$="S" Or k$="N" Or k$="s" Or k$="n"
    Case "OK"
      Print @(156,72+(i+2)*12,2) "OK"
      GetKey
    Case "INPUT"
      Print @(72,72+(i+2)*12,2);
      Input ""; inputString$
  End Select
End Sub

'---------------------------------------
Sub Progress(dispText$ As string, selCol As integer)
  Color selCol, 0
  RBox  96,  180,  128,  24  , 10, selCol, selCol
  Print @(104,186,2) dispText$
End Sub

'---------------------------------------
Sub DisplayHelp
  Color RGB(white), 0
  RBox  32,  52,  256,  202, 10, RGB(lightgrey), 0
  Print @(48,60) Chr$(149)+"/"+Chr$(148)+"/TAB:  Selecciona panel"
  Print @(48,72) Chr$(146)+"/"+Chr$(147)+":      Selecciona elemento"
  Print @(48,84)  "A/B:      Muestra disco A:/B:"
  Print @(48,96)  "Enter:    Ejecutar/ver o"
  Print @(48,108) "          Abrir directorio"
  Print @(48,120) "Esc/Back: Directorio padre"
  Print @(48,132) "C/M:      Copia/Mueve"
  Print @(48,144) "DEL/O:    Borra"
  Print @(48,156) "K:        Crea directorio"
  Print @(48,168) "R:        Renombra"
  Print @(48,180) "I:        Muestra linea con"
  Print @(48,192) "          info del elemento"
  Print @(48,204) "S:        Salir"
  Print @(48,216) "Y/H:      Esta ayuda"
  Print @(156,238,2) "OK"  
  GetKey
End Sub

'---------------------------------------
Function FormSize$(size As integer)
  Select Case size
    Case is >= 1.0e9
      FormSize$=Str$(Cint(size/1024^3))+"GB"
    Case is >= 1.0e6
      FormSize$=Str$(Cint(size/1024^2))+"MB"
    Case is >= 1.0e3
      FormSize$=Str$(Cint(size/1024))+"KB"
    Case Else
      FormSize$=Str$(Cint(size))+"B"
  End Select
End Function

'---------------------------------------
Sub InfoDisp
  Color RGB(white), 0
  Print @(0,300) String$(40," ");
  If file$(sel) <> ".." Then
    Print @(0,300) Left$(MM.Info(modified file$(sel)),10);
  End If
  If fileType$(sel)<>"D" Then
    Print @(88,300) FormSize$(MM.Info(filesize file$(sel)));
  End If
  Color RGB(gold), 0
  Print @(168,300) curDrive$(curPane);
  Print @(192,300) FormSize$(MM.Info(free space))+" libre/"+FormSize$(MM.Info(disk size));
End Sub

'---------------------------------------
Sub KeysDisp
  Color RGB(Green), 0
  Print @(0,300) String$(40," ");
  Print @(0,300,2) "A/B";
  Print @(80,300,2) "C";
  Print @(128,300,2) "M";
  Print @(184,300,2) "O"; 'x
  'Print @(200,300,2) "K";
  Print @(240,300,2) "Y"; 'x
  Print @(280,300,2) "S"; 'x
  'Print @(0,300,1) "   :drive  opy  ove  el m dir  elp   uit";
  Print @(0,300,1) "   :disco  opia  ueve b rra  a uda  alir";
End Sub