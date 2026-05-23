# Instalação do FFmpeg para Vídeos Compatíveis com Navegadores

## Por que FFmpeg?

O sistema agora salva vídeos de alertas em formato **MP4 com codec H.264**, garantindo reprodução em todos os navegadores modernos (Chrome, Firefox, Safari, Edge).

O OpenCV nem sempre tem suporte nativo para H.264, por isso usamos o **FFmpeg** para converter os vídeos automaticamente.

## Status Atual

- ✅ **Com FFmpeg**: Vídeos em MP4 H.264 (100% compatível com navegadores)
- ⚠️ **Sem FFmpeg**: Sistema funciona mas pode usar codecs antigos (compatibilidade limitada)

## Instalação do FFmpeg

### Windows

#### Opção 1: Chocolatey (Recomendado)
```powershell
# Instalar Chocolatey (se não tiver)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Instalar FFmpeg
choco install ffmpeg -y
```

#### Opção 2: winget
```powershell
winget install "FFmpeg (Essentials Build)"
```

#### Opção 3: Download Manual
1. Baixar: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
2. Extrair para `C:\ffmpeg`
3. Adicionar `C:\ffmpeg\bin` ao PATH:
   - Pesquisar "Variáveis de Ambiente" no Windows
   - Editar "Path" nas variáveis do sistema
   - Adicionar `C:\ffmpeg\bin`
   - Reiniciar terminal

### Linux

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg -y
```

#### Fedora/RHEL
```bash
sudo dnf install ffmpeg -y
```

#### Arch Linux
```bash
sudo pacman -S ffmpeg
```

### macOS

#### Homebrew
```bash
brew install ffmpeg
```

## Verificar Instalação

Abra um terminal e execute:
```bash
ffmpeg -version
```

Você deve ver algo como:
```
ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers
...
```

## Como Funciona

### Processo Automático

1. **Detecção de Codec**: Sistema tenta usar H.264 direto no OpenCV
2. **Fallback**: Se H.264 não disponível, usa codec temporário
3. **Conversão**: FFmpeg converte automaticamente para MP4 H.264
4. **Limpeza**: Arquivo temporário é removido

### Configurações de Vídeo

Os vídeos são otimizados para web com:
- **Codec**: H.264 (libx264)
- **Profile**: Baseline (máxima compatibilidade)
- **Qualidade**: CRF 23 (bom balanço qualidade/tamanho)
- **Formato**: MP4 com faststart (streaming progressivo)
- **Pixel Format**: yuv420p (compatibilidade universal)

### Logs

O sistema imprime mensagens de status:

```
[ALERT] Video codec selected: avc1 (H.264/AVC)  ← H.264 direto (melhor)
```
ou
```
[ALERT] Temporary codec: mp4v (MPEG-4)          ← Usando fallback
[ALERT] Converting video to browser-compatible MP4...
[ALERT] Video converted to browser-compatible H.264 MP4: alerts/alert_cam1_20260522_143025.mp4
```

Se FFmpeg não estiver instalado:
```
[ALERT] FFmpeg not found. Install FFmpeg for guaranteed browser compatibility.
[ALERT] Using original video file without conversion.
```

## Solução de Problemas

### Vídeo não reproduz no navegador

1. **Verificar FFmpeg**: Execute `ffmpeg -version`
2. **Verificar logs**: Procure por mensagens `[ALERT]` no console
3. **Testar manualmente**:
   ```bash
   ffmpeg -i alerts/alert_cam1_timestamp.mp4 -c:v libx264 -profile:v baseline -pix_fmt yuv420p output.mp4
   ```

### FFmpeg não encontrado

- **Windows**: Verifique se `C:\ffmpeg\bin` está no PATH
- **Linux/Mac**: Execute `which ffmpeg` para verificar instalação
- **Reinicie** o terminal/IDE após instalação

### Conversão muito lenta

O sistema usa preset `fast` para balancear velocidade e qualidade. Se necessário, você pode alterar para `ultrafast` no código (menor qualidade mas mais rápido).

## Formatos Suportados por Navegador

| Browser | H.264/MP4 | VP8/WebM | VP9/WebM | AV1/MP4 |
|---------|-----------|----------|----------|---------|
| Chrome  | ✅        | ✅       | ✅       | ✅      |
| Firefox | ✅        | ✅       | ✅       | ✅      |
| Safari  | ✅        | ❌       | ❌       | ❌      |
| Edge    | ✅        | ✅       | ✅       | ✅      |

**H.264/MP4 é a única combinação suportada por todos os navegadores.**

## Referências

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [H.264 Web Video Encoding](https://trac.ffmpeg.org/wiki/Encode/H.264)
- [HTML5 Video Browser Support](https://caniuse.com/mpeg4)
