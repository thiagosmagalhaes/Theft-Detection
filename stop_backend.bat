@echo off
REM Script para parar o backend do sistema de detecção de furtos
echo Parando backend...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend parado com sucesso!
) else (
    echo Nenhum processo Python em execução
)
pause
