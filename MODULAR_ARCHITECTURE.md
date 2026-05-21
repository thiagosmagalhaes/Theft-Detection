# Theft Detection System - Modular Architecture

## Nova Estrutura do Projeto

O código foi reorganizado em uma estrutura modular para melhor manutenibilidade e organização:

```
Theft-Detection/
├── main.py                      # Ponto de entrada principal
├── backend.py                   # [BACKUP] Arquivo original (renomeado para backend_old.py)
├── backend/                     # Módulo principal reorganizado
│   ├── __init__.py
│   ├── config.py                # Configurações e constantes
│   ├── database.py              # Operações de banco de dados
│   │
│   ├── models/                  # Modelos de dados Pydantic
│   │   ├── __init__.py
│   │   ├── settings.py          # SettingsModel, CameraInput
│   │   └── person_state.py      # PersonState para tracking
│   │
│   ├── camera/                  # Gerenciamento de câmeras
│   │   ├── __init__.py
│   │   ├── threaded_camera.py   # ThreadedCamera para captura não-bloqueante
│   │   └── camera_manager.py    # CameraManager para múltiplas câmeras
│   │
│   ├── detection/               # Análise de pose e detecção
│   │   ├── __init__.py
│   │   ├── heatmap.py           # Visualização de heatmap
│   │   └── pose_analysis.py     # Funções de análise de pose
│   │
│   ├── face_recognition/        # Reconhecimento facial
│   │   ├── __init__.py
│   │   ├── face_manager.py      # Gerenciamento de faces conhecidas
│   │   └── auto_register.py     # Auto-registro de novas faces
│   │
│   ├── api/                     # Endpoints da API FastAPI
│   │   ├── __init__.py
│   │   ├── settings.py          # /settings, /roi
│   │   ├── cameras.py           # /cameras
│   │   ├── faces.py             # /faces
│   │   ├── history.py           # /history
│   │   └── stats.py             # /stats
│   │
│   ├── alerts/                  # Sistema de alertas
│   │   ├── __init__.py
│   │   └── notifications.py     # Email e Telegram
│   │
│   └── video/                   # Processamento de vídeo
│       ├── __init__.py
│       └── video_loop.py        # Loop principal de processamento
│
├── alerts/                      # Imagens de alertas salvos
├── faces/                       # Imagens de faces registradas
├── dashboard/                   # Frontend Next.js
└── [outros arquivos...]
```

## Como Usar

### Executar o Sistema

**Novo método (recomendado):**
```bash
py main.py
```

**Método alternativo (uvicorn direto):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Arquivo Original

O arquivo `backend.py` original foi mantido como backup. Para reverter para a versão antiga:
1. Renomeie `backend_old.py` para `backend.py`
2. Execute com `py backend.py`

## Benefícios da Reorganização

1. **Modularidade**: Cada funcionalidade está em seu próprio módulo
2. **Manutenibilidade**: Mais fácil encontrar e modificar código específico
3. **Testabilidade**: Módulos podem ser testados independentemente
4. **Escalabilidade**: Fácil adicionar novas funcionalidades
5. **Legibilidade**: Código mais organizado e documentado

## Módulos Principais

### `config.py`
- Configurações globais
- Constantes (thresholds, caminhos de modelos)
- Verificação de dependências opcionais

### `database.py`
- Inicialização do banco SQLite
- Funções CRUD para alerts e faces
- Operações thread-safe

### `camera/`
- **ThreadedCamera**: Captura de vídeo não-bloqueante
- **CameraManager**: Gerenciamento de múltiplas câmeras

### `detection/`
- **heatmap.py**: Acumulação e visualização de heatmap
- **pose_analysis.py**: Detecção de comportamentos suspeitos

### `face_recognition/`
- **FaceManager**: Gerenciamento de faces conhecidas
- **auto_register.py**: Auto-registro de novas pessoas

### `api/`
- Endpoints REST organizados por funcionalidade
- Operações assíncronas para melhor performance

### `video/video_loop.py`
- Loop principal de processamento
- Integração YOLO para detecção
- Processamento de múltiplas câmeras

## Requisitos

Todos os requisitos permanecem os mesmos:
- Python 3.10+
- Dependências em `requirements.txt` ou `requirements_noface.txt`

## Notas Importantes

- Todas as funcionalidades do código original foram preservadas
- A API REST permanece compatível com o frontend existente
- O sistema continua suportando múltiplas câmeras
- Reconhecimento facial é opcional (graceful degradation)

## Desenvolvimento

Para adicionar novas funcionalidades:

1. Identifique o módulo apropriado
2. Adicione funções/classes no módulo
3. Exporte no `__init__.py` se necessário
4. Use imports relativos dentro do pacote `backend/`

Exemplo:
```python
from ..config import ALERT_COOLDOWN
from ..database import insert_alert
from .pose_analysis import check_bending
```
