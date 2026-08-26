@echo off
REM Atalho de duplo clique para Compact-Vhdx.ps1.
REM O proprio script pede elevacao (UAC) se precisar.
setlocal

echo Iniciando Compact-Vhdx.ps1 ...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Compact-Vhdx.ps1" %*
set RC=%ERRORLEVEL%

echo.
if not "%RC%"=="0" (
  echo O script terminou com codigo %RC%.
  echo Veja o log em: %~dp0compact-log.txt
) else (
  echo Uma janela com privilegio de administrador deve ter aberto.
  echo Se nao abriu, confira o log: %~dp0compact-log.txt
)
echo.
pause
