# Sistema de Reconhecimento Facial com InsightFace

## 🎯 Visão Geral

Sistema automatizado de registro e rastreamento de pessoas usando **InsightFace** (ArcFace) para reconhecimento facial de alta performance, compatível com Windows e Python 3.10+.

## ✨ Funcionalidades

### 1. **Auto-Registro de Pessoas**
- Detecta automaticamente novas pessoas que aparecem nas câmeras
- Após 3 segundos de visualização, registra a pessoa no banco de dados
- Gera nome automático (ex: `Person_1234`)
- Salva foto do rosto em `faces/`

### 2. **Rastreamento de Detecções**
- Cada vez que uma pessoa conhecida é detectada, salva:
  - Timestamp da detecção
  - Câmera que detectou
  - Foto da detecção em `faces/detections/`
  - Nível de confiança

### 3. **Histórico Completo**
- Veja quantas vezes cada pessoa foi detectada
- Histórico por pessoa ou por câmera
- Primeira e última vez que foi vista
- Estatísticas detalhadas

## 🔧 Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

**Principais bibliotecas:**
- `insightface` - Reconhecimento facial moderno e rápido
- `onnxruntime` - Runtime para modelos ONNX (InsightFace)
- `scipy` - Cálculo de similaridade

### 2. Estrutura de Pastas

O sistema criará automaticamente:
```
faces/                    # Fotos principais das pessoas
faces/detections/         # Histórico de detecções
```

## 📊 Banco de Dados

### Tabelas Criadas

**`faces`** - Pessoas registradas
- `id` - UUID único
- `name` - Nome da pessoa (auto-gerado ou manual)
- `type` - whitelist/blacklist
- `encoding` - Embedding facial (512 dimensões - InsightFace ArcFace)
- `first_seen` - Primeira vez detectada
- `last_seen` - Última vez detectada

**`person_detections`** - Histórico de detecções
- `id` - UUID da detecção
- `person_id` - Referência para a pessoa
- `timestamp` - Momento da detecção
- `camera_id` - Qual câmera detectou
- `image_path` - Foto da detecção
- `confidence` - Nível de confiança (0-1)

## 🚀 API Endpoints

### Gerenciamento de Pessoas

#### `GET /persons`
Lista todas as pessoas com estatísticas
```json
{
  "persons": [
    {
      "id": "uuid",
      "name": "Person_1234",
      "type": "whitelist",
      "first_seen": "2026-05-21T10:00:00",
      "last_seen": "2026-05-21T15:30:00",
      "detection_count": 15
    }
  ]
}
```

#### `GET /persons/{person_id}`
Detalhes de uma pessoa específica
```json
{
  "person": {
    "id": "uuid",
    "name": "Person_1234",
    "type": "whitelist"
  },
  "stats": {
    "total_detections": 15,
    "by_camera": {
      "cam1": 10,
      "cam2": 5
    },
    "first_seen": "2026-05-21T10:00:00",
    "last_seen": "2026-05-21T15:30:00"
  }
}
```

#### `GET /persons/{person_id}/detections`
Histórico de detecções de uma pessoa
```json
{
  "detections": [
    {
      "id": "uuid",
      "person_id": "uuid",
      "person_name": "Person_1234",
      "timestamp": "2026-05-21T15:30:00",
      "camera_id": "cam1",
      "image_path": "faces/detections/Person_1234_20260521_153000.jpg",
      "confidence": 0.95
    }
  ]
}
```

#### `GET /detections?camera_id=cam1&limit=100`
Todas as detecções (opcionalmente filtradas por câmera)

#### `GET /detections/stats`
Estatísticas gerais
```json
{
  "total_detections": 150,
  "detections_today": 25,
  "unique_persons": 10,
  "top_persons": [
    {"name": "Person_1234", "count": 30},
    {"name": "Person_5678", "count": 25}
  ]
}
```

## 🔍 Como Funciona

### 1. Detecção Inicial
Quando uma pessoa é detectada pela câmera:
```python
from backend.face_recognition.auto_register import auto_register_or_track_person

# Passar a imagem do rosto detectado
person_id = auto_register_or_track_person(
    face_image=cropped_face,
    cam_id="cam1",
    track_id=track_id
)
```

### 2. Fluxo de Reconhecimento

```
┌─────────────────────┐
│ Pessoa detectada    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Extrair embedding   │  ← InsightFace ArcFace (512-dim)
│ com InsightFace     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Comparar com banco  │  ← Similaridade de cosseno
│ de pessoas          │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
  Conhecida   Nova
      │         │
      │         └─► Aguardar 3s ─► Registrar
      │                            │
      ▼                            ▼
  Salvar detecção          Salvar pessoa + detecção
  em histórico             em banco de dados
```

### 3. Exemplo de Uso no Código

```python
# No loop de processamento de vídeo
for person in detected_persons:
    # Extrair região do rosto
    face_crop = frame[y1:y2, x1:x2]
    
    # Auto-registrar ou rastrear
    person_id = auto_register_or_track_person(
        face_image=face_crop,
        cam_id=camera_id,
        track_id=person.track_id
    )
    
    if person_id:
        print(f"Pessoa {person_id} detectada!")
```

## ⚙️ Configuração

### Ajustar Threshold de Similaridade

Edite `backend/face_recognition/auto_register.py`:
```python
def compare_faces(embedding1, embedding2, threshold=0.4):
    # threshold menor = mais rigoroso
    # threshold maior = mais tolerante
```

**Valores recomendados:**
- `0.3` - Muito rigoroso (pode criar duplicatas)
- `0.4` - **Padrão** (bom equilíbrio)
- `0.5` - Mais tolerante (pode juntar pessoas diferentes)

### Ajustar Tempo de Auto-Registro

Edite `backend/config.py`:
```python
AUTO_REGISTER_DELAY = 3.0  # segundos
```

## 📈 Monitoramento

### Logs do Sistema

O sistema imprime logs detalhados:
```
[AUTO-REG] Processing person - cam:cam1, track:123
[AUTO-REG] Person recognized: Person_1234 (confidence: 0.95)
[AUTO-REG] New person detected. Starting tracking...
[AUTO-REG] Time threshold met! Registering new person...
[AUTO-REG] Successfully registered new person: Person_5678
```

### Verificar Banco de Dados

```python
from backend.database import get_all_persons_with_stats

persons = get_all_persons_with_stats()
for person in persons:
    print(f"{person['name']}: {person['detection_count']} detecções")
```

## 🎨 Integração com Dashboard

### Exemplo de componente React

```typescript
// Listar pessoas
const response = await fetch('http://localhost:8000/persons');
const data = await response.json();

// Histórico de uma pessoa
const detections = await fetch(`http://localhost:8000/persons/${personId}/detections`);

// Estatísticas
const stats = await fetch('http://localhost:8000/detections/stats');
```

## 🔒 Segurança e Performance

### Performance
- **InsightFace/ArcFace**: ~50ms por face em CPU, <10ms em GPU
- **Comparação de embeddings**: <1ms por face no banco
- **Recomendado**: GPU para melhor performance em múltiplas câmeras

### Armazenamento
- Cada embedding: ~2KB (512 floats)
- Cada foto: ~50-200KB (depende da resolução)
- Histórico cresce com o tempo - considere limpeza periódica

## 🐛 Troubleshooting

### Erro: "InsightFace not installed"
```bash
pip install insightface onnxruntime
```

### Erro: "No module named scipy"
```bash
pip install scipy
```

### Python 3.14 - Conflitos de dependência
InsightFace funciona melhor com Python 3.10 ou 3.11:
```bash
# Use Python 3.10 ou 3.11
py -3.10 -m pip install -r requirements.txt
py -3.10 main.py
```

### Performance lenta
1. Use GPU se disponível
2. Reduza resolução das imagens de rosto
3. Aumente intervalo entre detecções

### Muitas pessoas duplicadas
- Reduza o `threshold` em `compare_faces()`
- Melhore a qualidade/iluminação das câmeras

### Pessoas não sendo registradas
- Verifique se `AUTO_REGISTER_DELAY` não está muito alto
- Confirme que rostos estão sendo detectados corretamente
- Verifique logs `[AUTO-REG]`

## 📝 Próximos Passos

1. **Migrar para PostgreSQL + pgvector** (para produção)
2.InsightFace (ArcFace) - Reconhecimento facial de alta performance
3. **Busca por similaridade** de rostos
4. **Alertas** para pessoas específicas
5. **Relatórios** de frequência de visitantes

---

**Desenvolvido com:**
- DeepFace (ArcFace) - Reconhecimento facial
- FastAPI - API REST
- SQLite - Banco de dados
- OpenCV - Processamento de imagem
