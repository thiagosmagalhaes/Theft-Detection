# Gravação de Vídeo em Alertas

## Visão Geral

O sistema agora salva automaticamente um vídeo dos **últimos 20 segundos** sempre que um alerta é acionado. Isso permite revisar o que aconteceu antes do incidente.

## Como Funciona

### 1. Buffer Circular de Vídeo
Cada câmera mantém um buffer circular que armazena continuamente os últimos 20 segundos de vídeo:
- **FPS**: Detectado automaticamente da câmera (padrão: 25 fps)
- **Capacidade**: ~500 frames (20 segundos × 25 fps)
- **Armazenamento**: Frames são mantidos em memória usando `collections.deque`

### 2. Gravação Automática
Quando um alerta é acionado:
1. O sistema captura todos os frames do buffer (últimos 20 segundos)
2. Salva um **snapshot** (imagem) do frame atual
3. Salva um **vídeo MP4** com todos os frames do buffer
4. Armazena ambos os caminhos no banco de dados

### 3. Tipos de Alertas com Vídeo
Todos os alertas agora incluem vídeo:
- ✅ Atividade Criminosa Detectada
- ✅ Rosto da Lista Negra
- ✅ Furto Confirmado (Item Escondido)
- ✅ Intrusão em Área Restrita
- ✅ Suspeita de Loitering

## Estrutura de Arquivos

### Localização dos Vídeos
```
alerts/
├── alert_cam1_20260521_143025.jpg    # Snapshot do alerta
├── alert_cam1_20260521_143025.mp4    # Vídeo dos últimos 20s
├── alert_cam2_20260521_143156.jpg
└── alert_cam2_20260521_143156.mp4
```

### Formato do Arquivo
- **Imagem**: JPEG (.jpg)
- **Vídeo**: MP4 (.mp4) com codec mp4v
- **Nomenclatura**: `alert_{camera_id}_{timestamp}.{ext}`

## Banco de Dados

### Schema Atualizado
A tabela `alerts` agora inclui:
```sql
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    message TEXT,
    timestamp TEXT,
    image_path TEXT,      -- Snapshot do alerta
    video_path TEXT       -- Vídeo dos últimos 20s (NOVO)
)
```

### Migração
Para bancos de dados existentes, execute:
```bash
py migrate_video_column.py
```

## Arquitetura Técnica

### Componentes

#### 1. VideoBuffer (`backend/camera/video_buffer.py`)
- Buffer circular thread-safe
- Armazena frames com timestamps
- Configurável (FPS e duração)

#### 2. ThreadedCamera (`backend/camera/threaded_camera.py`)
- Integra VideoBuffer
- Adiciona cada frame capturado ao buffer
- Fornece método `get_buffer_frames()` para recuperar frames

#### 3. trigger_alert (`backend/alerts/notifications.py`)
- Aceita buffer de frames como parâmetro opcional
- Salva vídeo em thread separada (não-bloqueante)
- Mantém compatibilidade com código legado

#### 4. video_loop (`backend/video/video_loop.py`)
- Obtém buffer da câmera ao acionar alerta
- Passa buffer para `trigger_alert()`

### Fluxo de Execução

```
┌─────────────────┐
│ ThreadedCamera  │
│   (Captura)     │
└────────┬────────┘
         │ Cada frame
         ▼
┌─────────────────┐
│  VideoBuffer    │
│ (20s circular)  │
└────────┬────────┘
         │ Quando alerta
         ▼
┌─────────────────┐
│  trigger_alert  │
│  (Salva vídeo)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Arquivo .mp4   │
│  (Disco)        │
└─────────────────┘
```

## Desempenho

### Uso de Memória
- **Por Câmera**: ~150-300 MB (500 frames × 1280×720 × 3 bytes)
- **4 Câmeras**: ~600 MB - 1.2 GB
- Frames são descartados automaticamente (buffer circular)

### Uso de CPU
- Mínimo impacto: apenas cópia de frames já capturados
- Gravação de vídeo: thread separada (não-bloqueante)
- Codec mp4v: rápido, sem compressão complexa

### Uso de Disco
- **Vídeo**: ~5-15 MB por alerta (20 segundos)
- **Imagem**: ~100-500 KB por alerta
- **Total**: ~10-20 MB por alerta (imagem + vídeo)

## Configuração

### Ajustar Duração do Buffer
Edite `backend/camera/threaded_camera.py`:
```python
# Alterar de 20 para 30 segundos
self.video_buffer = VideoBuffer(fps=int(fps), duration_seconds=30)
```

### Ajustar FPS
O FPS é detectado automaticamente da câmera. Para forçar um valor:
```python
self.video_buffer = VideoBuffer(fps=25, duration_seconds=20)  # Forçar 25 FPS
```

### Desabilitar Vídeos (Apenas Imagens)
Edite `backend/video/video_loop.py` e remova `frame_buffer`:
```python
# Antes
trigger_alert(cam_id, name, message, frame, alert_payload_wrapper, frame_buffer)

# Depois
trigger_alert(cam_id, name, message, frame, alert_payload_wrapper)
```

## API de Alertas

### Resposta da API
```json
{
  "id": "uuid-here",
  "message": "THEFT CONFIRMED (Item Concealed)",
  "timestamp": "20260521_143025",
  "image_path": "alerts/alert_cam1_20260521_143025.jpg",
  "video_path": "alerts/alert_cam1_20260521_143025.mp4",
  "camera_id": "cam1"
}
```

### Endpoints Afetados
- `GET /api/alerts` - Lista de alertas (com video_path)
- `GET /api/stats` - Estatísticas de alertas
- WebSocket - Notificações em tempo real

## Resolução de Problemas

### Vídeos Não Estão Sendo Salvos
1. Verifique se a pasta `alerts/` existe
2. Verifique permissões de escrita
3. Verifique logs para erros de codec

### Buffer Vazio
- Aguarde ~20 segundos após iniciar o sistema
- O buffer precisa encher antes do primeiro alerta

### Vídeo Corrompido
- Verifique se OpenCV tem suporte a mp4v:
  ```python
  python -c "import cv2; print(cv2.getBuildInformation())"
  ```

### Alto Uso de Memória
- Reduza `duration_seconds` de 20 para 10-15
- Reduza resolução da câmera (atualmente 1280×720)

## Próximas Melhorias

- [ ] Compressão H.264 para vídeos menores
- [ ] Download de vídeos via dashboard
- [ ] Player de vídeo integrado no frontend
- [ ] Limpeza automática de vídeos antigos
- [ ] Configuração de duração via settings
- [ ] Pre e post-buffer configuráveis (ex: 10s antes + 10s depois)

## Compatibilidade

- ✅ Windows
- ✅ Linux
- ✅ macOS (não testado)
- ✅ Câmeras USB
- ✅ Streams RTSP
- ✅ Arquivos de vídeo

## Dependências

Nenhuma dependência adicional necessária. Usa bibliotecas já presentes:
- `cv2` (OpenCV) - Para gravação de vídeo
- `collections.deque` - Para buffer circular
- `threading` - Para gravação não-bloqueante
