Attribute VB_Name = "PDFErstellen"
' ---------------------------------------------------------------
'  Aufmassblatt: Button "PDF erstellen"
'
'  Einbau (einmalig):
'   1. Datei als .xlsm speichern (Datei > Speichern unter >
'      "Excel-Arbeitsmappe mit Makros")
'   2. Alt+F11 > Datei > Datei importieren... > PDFErstellen.bas
'   3. Auf dem Blatt: Einfuegen > Formen > Rechteck, beschriften mit
'      "PDF erstellen", Rechtsklick > Makro zuweisen > PDFErstellen
' ---------------------------------------------------------------
Option Explicit

Public Sub PDFErstellen()
    Dim ordner As String, skript As String, befehl As String
    Dim ergebnis As Long

    ordner = ThisWorkbook.Path
    If ordner = "" Then
        MsgBox "Bitte die Datei zuerst speichern.", vbExclamation
        Exit Sub
    End If

    skript = ordner & "\PDF erstellen.bat"
    If Dir(skript) = "" Then
        MsgBox "Nicht gefunden:" & vbCrLf & skript & vbCrLf & vbCrLf & _
               "Die Datei 'PDF erstellen.bat' muss im selben Ordner liegen.", _
               vbCritical
        Exit Sub
    End If

    ' Aktuellen Stand speichern, damit das Skript die neuen Werte liest
    Application.DisplayAlerts = False
    ThisWorkbook.Save
    Application.DisplayAlerts = True

    befehl = """" & skript & """ """ & ThisWorkbook.FullName & """"
    ergebnis = Shell("cmd.exe /c " & befehl, vbNormalFocus)

    If ergebnis = 0 Then
        MsgBox "Das Skript konnte nicht gestartet werden.", vbCritical
    End If
End Sub
