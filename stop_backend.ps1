# Script para parar o backend do sistema de detecção de furtos
# Uso: .\stop_backend.ps1

Write-Host "Parando backend..." -ForegroundColor Yellow

try {
    $processes = Get-Process python -ErrorAction SilentlyContinue
    
    if ($processes) {
        $processes | Stop-Process -Force
        Write-Host "✅ Backend parado com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ Nenhum processo Python em execução" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Erro ao parar backend: $_" -ForegroundColor Red
    exit 1
}
