@echo off
setlocal
rem ---------------------------------------------------------------
rem  Aufmassblatt: Excel-Eingabe  ->  ausgefuelltes PDF
rem  Einfach doppelklicken. Liest Aufmassblatt.xlsx im selben Ordner.
rem ---------------------------------------------------------------
cd /d "%~dp0"

set PY=
for %%P in (py.exe) do if not "%%~$PATH:P"=="" set PY=py -3
if "%PY%"=="" for %%P in (python.exe) do if not "%%~$PATH:P"=="" set PY=python

if "%PY%"=="" (
  echo.
  echo FEHLER: Python wurde nicht gefunden.
  echo Bitte Python von https://www.python.org/downloads/ installieren
  echo und dabei "Add Python to PATH" ankreuzen.
  echo.
  pause
  exit /b 1
)

%PY% -c "import openpyxl, pymupdf" 2>nul
if errorlevel 1 (
  echo Installiere einmalig die benoetigten Bibliotheken...
  %PY% -m pip install --quiet --upgrade openpyxl pymupdf
  if errorlevel 1 (
    echo FEHLER: Installation fehlgeschlagen.
    pause
    exit /b 1
  )
)

%PY% aufmass_pdf.py %*
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)

echo.
echo Fertig. Das PDF liegt in diesem Ordner.
pause
