# Estrutura Modular - Visão Geral

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│                   (FastAPI Application)                      │
│                                                              │
│  • Inicializa FastAPI                                       │
│  • Configura CORS e Static Files                           │
│  • Registra routers da API                                 │
│  • Inicia video_loop em thread separada                    │
│  • Gerencia WebSocket (/ws)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   config.py  │    │ database.py  │      │  API Routes  │
│              │    │              │      │   (api/)     │
│ • Settings   │    │ • init_db()  │      │              │
│ • Constants  │    │ • CRUD ops   │      │ • settings   │
│ • Thresholds │    │ • Alerts     │      │ • cameras    │
│ • Model paths│    │ • Faces      │      │ • faces      │
└──────────────┘    └──────────────┘      │ • history    │
                                          │ • stats      │
                                          └──────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   camera/    │    │  detection/  │      │face_recogn./ │
│              │    │              │      │              │
│ • Threaded   │    │ • heatmap    │      │ • FaceManager│
│   Camera     │    │ • pose       │      │ • auto_reg   │
│ • Camera     │    │   analysis   │      │              │
│   Manager    │    │              │      └──────────────┘
└──────────────┘    └──────────────┘
        │                     │
        └─────────────────────┼─────────────────────┐
                              │                     │
                              ▼                     ▼
                    ┌──────────────┐      ┌──────────────┐
                    │   video/     │      │   alerts/    │
                    │              │      │              │
                    │ • video_loop │      │ • trigger    │
                    │ • YOLO       │      │   alert      │
                    │ • Processing │      │ • Email      │
                    │              │      │ • Telegram   │
                    └──────────────┘      └──────────────┘
```

## Fluxo de Dados

### 1. Inicialização
```
main.py → init_db() → load settings → CameraManager.load_cameras()
       → start video_loop thread
```

### 2. Processamento de Vídeo (Loop Contínuo)
```
video_loop():
  ├─ CameraManager.cameras → ThreadedCamera.read()
  ├─ YOLO Pose Detection
  ├─ YOLO Object Detection
  │
  ├─ Para cada pessoa detectada:
  │   ├─ Validação (tamanho bbox, keypoints)
  │   ├─ Face Recognition (se disponível)
  │   ├─ Theft Detection (objeto + concealment)
  │   ├─ ROI Intrusion Detection
  │   ├─ Loitering Detection
  │   └─ Heatmap Update
  │
  ├─ Frame Encoding (JPEG)
  └─ Update latest_frame (para WebSocket)
```

### 3. API Request/Response
```
Cliente → FastAPI Router → Async Handler → Database/Manager
                                         → Response ← Cliente
```

### 4. WebSocket Streaming
```
Cliente ← WebSocket (/ws) ← latest_frame ← video_loop thread
```

### 5. Alert Flow
```
Detecção Suspeita → trigger_alert()
                   ├─ Salvar imagem (alerts/)
                   ├─ Insert no database
                   ├─ Update alert_payload
                   └─ send_notifications()
                       ├─ Email (SMTP)
                       └─ Telegram (API)
```

## Responsabilidades dos Módulos

### `config.py`
- Carrega variáveis de ambiente (.env)
- Define constantes globais
- Verifica dependências opcionais
- Carrega settings.json

### `database.py`
- Abstrai operações SQLite
- Fornece funções thread-safe
- Gerencia serialização de face encodings

### `models/`
- Define estruturas de dados (Pydantic)
- Valida inputs da API
- Mantém estado de tracking

### `camera/`
- **ThreadedCamera**: Captura não-bloqueante em thread separada
- **CameraManager**: Gerencia múltiplas câmeras, salva/carrega config

### `detection/`
- **heatmap**: Acumula movimentação, gera overlay
- **pose_analysis**: Analisa keypoints para comportamentos suspeitos

### `face_recognition/`
- **FaceManager**: Carrega/atualiza faces conhecidas
- **auto_register**: Registra automaticamente novas pessoas

### `api/`
- Endpoints REST organizados por feature
- Operações assíncronas (não bloqueia event loop)
- Validação de inputs com Pydantic

### `video/`
- Loop principal de processamento
- Integração de todos os detectores
- Geração de frames para streaming

### `alerts/`
- Salva evidências (imagens)
- Envia notificações (Email/Telegram)
- Fire-and-forget threads (não bloqueia)

## Padrões de Importação

### Imports Relativos (dentro do pacote backend/)
```python
from ..config import ALERT_COOLDOWN
from ..database import insert_alert
from .pose_analysis import check_bending
```

### Imports Absolutos (em main.py ou scripts externos)
```python
from backend.database import init_db
from backend.api import settings_router
from backend.video import video_loop
```

## Threading Model

```
Main Thread:
  ├─ FastAPI/Uvicorn Event Loop (async)
  └─ WebSocket handlers (async)

Background Threads (daemon=True):
  ├─ video_loop() → processamento YOLO
  ├─ ThreadedCamera.update() → captura de frames (por câmera)
  └─ send_notifications() → envio de alertas (fire-and-forget)
```

## Locks e Sincronização

- `camera_manager.lock`: Protege acesso a `cameras` dict
- `faces_lock`: Protege `known_face_encodings` (em FaceManager)
- `auto_register_lock`: Protege `pending_face_registrations`
- `lock` (video): Protege `latest_frame` e `alert_payload`
- `ThreadedCamera.lock`: Protege frame atual da câmera

## Benefícios desta Arquitetura

1. **Separação de Responsabilidades**: Cada módulo tem uma função clara
2. **Testabilidade**: Módulos podem ser testados isoladamente
3. **Manutenibilidade**: Fácil localizar e modificar funcionalidades
4. **Escalabilidade**: Adicionar features sem modificar código existente
5. **Reutilização**: Módulos podem ser importados em outros projetos
6. **Documentação**: Estrutura auto-documentada através da organização
