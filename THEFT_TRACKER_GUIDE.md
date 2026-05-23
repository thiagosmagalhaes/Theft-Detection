# Sistema Avançado de Detecção de Furto - TheftBehaviorTracker

## 📋 Visão Geral

O **TheftBehaviorTracker** é um sistema avançado de detecção de comportamento suspeito de furto que usa **pontuação de risco progressiva** ao invés de detecção binária simples. Este sistema reduz drasticamente os falsos alarmes ao acumular evidências ao longo do tempo.

## 🎯 Diferença do Sistema Anterior

### Sistema Anterior (Binário)
```python
# Detecção simples: Pegou objeto + Escondeu = Alarme imediato
if holding_object and concealed:
    TRIGGER_ALERT()  # ❌ Muitos falsos positivos!
```

### Sistema Novo (Risk Score)
```python
# Acumula evidências ao longo do tempo
tracker.update(...)
# Pegar item na prateleira: +0.15
# Objeto na mão: +0.10
# Levar ao bolso: +0.55
# Objeto desaparecer: +0.90
# Total: 1.70 → ALERT! ✅ Alta confiança
```

## 🔢 Sistema de Pontuação

### Pesos de Risco (RISK_WEIGHTS)

| Comportamento | Peso | Descrição |
|--------------|------|-----------|
| `merchandise_pickup` | 0.15 | Pegou item na prateleira (normal sozinho) |
| `object_in_hand` | 0.10 | Segurando objeto detectado |
| `hand_to_concealment_holding` | 0.55 | Levou mão+objeto para zona de ocultação |
| `object_vanished_at_body` | 0.90 | Objeto sumiu junto ao corpo (**forte**!) |
| `ankle_conceal_bending` | 0.70 | Agachou e levou mão ao tornozelo |
| `scanning_environment` | 0.25 | Olhando muito para os lados |
| `facing_away_hands_at_body` | 0.30 | De costas com mãos no corpo |
| `prolonged_concealment_dwell` | 0.20 | Mão parada tempo demais numa zona |
| `tag_removal` | 0.65 | Movimento repetitivo (tirar etiqueta) |
| `loitering` | 0.35 | Tempo demais na mesma área |

### Níveis de Risco

| Nível | Faixa | Ação Recomendada |
|-------|-------|------------------|
| **LOW** | 0.0 - 0.4 | Comportamento normal, nenhuma ação |
| **MEDIUM** | 0.4 - 0.8 | Atenção, monitorar |
| **HIGH** | 0.8 - 1.2 | Suspeito, alertar segurança |
| **ALERT** | ≥ 1.2 | Alerta de furto! Ação imediata |

## 🎨 Zonas de Ocultação

O sistema detecta 6 zonas específicas onde objetos podem ser escondidos:

| Zona | Descrição | Função |
|------|-----------|--------|
| `BAG` | Dentro de bolsa/mochila | `hand_in_bag_zone()` |
| `POCKET` | Bolso da calça/jaqueta | `hand_in_pocket_zone()` |
| `WAISTBAND` | Cintura (por dentro da calça) | `hand_in_waistband_zone()` |
| `CHEST` | Peito/por baixo da blusa | `hand_in_chest_zone()` |
| `ARMPIT` | Axila/dentro do casaco | `hand_in_armpit_zone()` |
| `ANKLE` | Meia/bota (agachado) | `hand_in_ankle_zone()` |

### Características Importantes

✅ **Escala Corporal**: Todos os limiares são proporcionais ao tamanho da pessoa na imagem
- Pessoa perto da câmera = corpo grande = limiares maiores
- Pessoa longe = corpo pequeno = limiares menores
- **Resultado**: Detecção consistente independente da distância!

✅ **Normalização automática**: A função `body_scale()` calcula a escala baseada na distância ombro-quadril

## 📊 Como Usar

### 1. Inicialização Básica

```python
from backend.detection import TheftBehaviorTracker

# Criar tracker (configurar uma vez)
tracker = TheftBehaviorTracker(
    fps=15,                    # FPS do vídeo/câmera
    decay_per_frame=0.98,      # Risco decai 2% por frame sem novos sinais
    alert_threshold=1.2,        # >= 1.2 = ALERT
    risk_cap=2.5,               # Risco máximo possível
    conf_thr=0.3                # Confiança mínima de keypoints
)
```

### 2. Loop Principal (por frame)

```python
# Para cada frame do vídeo
for frame in video:
    # 1. Detectar pessoas com YOLO Pose (COM tracking!)
    pose_results = pose_model.track(frame, persist=True, classes=[0])
    
    # 2. Detectar objetos com YOLO
    obj_results = obj_model(frame)
    
    # 3. Separar objetos em categorias
    object_boxes = []  # Produtos gerais
    bag_boxes = []     # Bolsas/mochilas (classes 24, 26, 28 do COCO)
    
    for box, cls in zip(obj_results.boxes, obj_results.classes):
        if cls in [24, 26, 28]:  # backpack, handbag, suitcase
            bag_boxes.append(box.xyxy)
        else:
            object_boxes.append(box.xyxy)
    
    # 4. Processar cada pessoa detectada
    if pose_results[0].boxes.id is not None:
        track_ids = pose_results[0].boxes.id.cpu().numpy().astype(int)
        keypoints = pose_results[0].keypoints.data.cpu().numpy()
        
        for tid, kpts in zip(track_ids, keypoints):
            # Atualizar tracker
            result = tracker.update(
                track_id=tid,
                keypoints=kpts,              # (17, 3) - COCO keypoints
                object_boxes=object_boxes,   # Lista de [x1, y1, x2, y2]
                bag_boxes=bag_boxes,         # Lista de [x1, y1, x2, y2]
                roi_polys=[shelf_roi]        # Lista de polígonos [(x,y), ...]
            )
            
            # Processar resultado
            if result["alert"]:
                print(f"🚨 ALERTA! Pessoa {tid} - Risco: {result['risk']:.2f}")
                for event in result["events"]:
                    print(f"  → {event['desc']}")
                
                # Disparar alerta no sistema
                trigger_alert(...)
    
    # 5. Limpar pessoas que sumiram (1x por frame)
    tracker.cleanup()
```

### 3. Estrutura do Resultado

```python
result = {
    "track_id": 42,              # ID da pessoa rastreada
    "risk": 1.35,                # Pontuação de risco atual
    "level": "ALERT",            # Nível: LOW, MEDIUM, HIGH, ALERT
    "alert": True,               # True se >= alert_threshold
    "events": [                  # Eventos que ocorreram neste frame
        {
            "type": "merchandise_pickup",
            "hand": "LEFT",
            "desc": "Pegou item em área de mercadoria"
        },
        {
            "type": "hand_to_concealment_holding",
            "hand": "LEFT",
            "zone": "POCKET",
            "desc": "Levou objeto à zona de ocultação: bolso"
        },
        {
            "type": "object_vanished_at_body",
            "hand": "LEFT",
            "zone": "POCKET",
            "desc": "Objeto desapareceu da mão junto ao corpo (bolso) — ocultação provável"
        }
    ]
}
```

## 🔄 Integração com Código Existente

### Refatoração do `video_loop.py`

**ANTES** (sistema binário):
```python
# Código antigo em process_theft_detection()
if p_state.holding_object and not current_holding:
    if check_concealment(kpts, hand_to_check):
        trigger_alert(...)  # Alerta imediato
```

**DEPOIS** (sistema de risk score):
```python
# No início do video_loop(), criar tracker global
behavior_tracker = TheftBehaviorTracker(fps=15)

# No loop principal, por pessoa:
result = behavior_tracker.update(
    track_id=track_id,
    keypoints=kpts,
    object_boxes=detected_objects,
    bag_boxes=bag_boxes,
    roi_polys=[cam_roi]
)

# Disparar alerta apenas se nível alto
if result["level"] in ("HIGH", "ALERT"):
    # Desenhar informações visuais
    draw_risk_overlay(frame, result, box)
    
    # Alerta se >= threshold
    if result["alert"]:
        trigger_alert(
            cam_id, 
            cam_name, 
            f"THEFT RISK: {result['risk']:.2f} - {', '.join([e['type'] for e in result['events']])}",
            frame
        )

# Limpar tracker (1x por frame, fora do loop de pessoas)
behavior_tracker.cleanup()
```

## 🎨 Visualização Recomendada

```python
def draw_risk_overlay(frame, result, box):
    """Desenha informações de risco sobre a pessoa."""
    # Cores por nível
    colors = {
        "LOW": (0, 255, 0),       # Verde
        "MEDIUM": (0, 165, 255),   # Laranja
        "HIGH": (0, 100, 255),     # Vermelho-laranja
        "ALERT": (0, 0, 255)       # Vermelho
    }
    color = colors[result["level"]]
    
    # Borda
    thickness = 3 if result["level"] in ("HIGH", "ALERT") else 2
    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
    
    # Texto de risco
    cv2.putText(
        frame, 
        f"ID:{result['track_id']} Risk:{result['risk']:.2f} [{result['level']}]",
        (box[0], box[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
    )
    
    # Eventos recentes
    y = box[1] - 35
    for event in result["events"][:2]:  # Últimos 2 eventos
        cv2.putText(frame, event["desc"][:50], (box[0], y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        y -= 20
```

## 🧪 Testes

Execute o teste standalone:
```bash
python test_theft_tracker.py
```

Este teste demonstra:
- ✅ Inicialização do tracker
- ✅ Processamento frame-a-frame
- ✅ Detecção de múltiplas zonas de ocultação
- ✅ Sistema de pontuação progressiva
- ✅ Visualização de risco em tempo real

## 🔧 Configuração Avançada

### Ajustar Sensibilidade

```python
# Mais conservador (menos alarmes)
tracker = TheftBehaviorTracker(
    fps=15,
    decay_per_frame=0.95,      # Risco decai mais rápido
    alert_threshold=1.5,        # Threshold mais alto
    risk_cap=2.0
)

# Mais sensível (mais alarmes)
tracker = TheftBehaviorTracker(
    fps=15,
    decay_per_frame=0.99,      # Risco decai mais devagar
    alert_threshold=0.9,        # Threshold mais baixo
    risk_cap=3.0
)
```

### Modificar Pesos

```python
from backend.detection import RISK_WEIGHTS

# Aumentar peso de "objeto desapareceu"
RISK_WEIGHTS["object_vanished_at_body"] = 1.2

# Reduzir peso de "olhar para os lados"
RISK_WEIGHTS["scanning_environment"] = 0.15
```

## 📝 Notas Importantes

1. **SEMPRE use `model.track()` com `persist=True`**: O tracker precisa de IDs estáveis!
   ```python
   pose_results = model.track(frame, persist=True)  # ✅ Correto
   pose_results = model(frame)  # ❌ Errado - sem tracking!
   ```

2. **Chame `cleanup()` uma vez por frame**: Remove pessoas que sumiram
   ```python
   for person in persons:
       tracker.update(...)
   tracker.cleanup()  # Depois do loop
   ```

3. **Keypoints no formato COCO-17**: Shape (17, 3) - [x, y, confidence]

4. **ROI como lista de polígonos**: `[ [(x1,y1), (x2,y2), ...] ]`

## 🚀 Vantagens do Sistema

✅ **Redução drástica de falsos positivos**: Exige sequência de ações suspeitas
✅ **Independente de distância**: Escala corporal automática
✅ **Múltiplas zonas de ocultação**: 6 zonas diferentes detectadas
✅ **Tracking temporal**: Histórico de comportamento
✅ **Comportamentos avançados**: Scanning, loitering, tag removal
✅ **Score progressivo**: Alertas baseados em evidência acumulada
✅ **Configurável**: Pesos e thresholds ajustáveis

## 📚 Referências

- **Arquivo principal**: `backend/detection/pose_analysis.py`
- **Teste standalone**: `test_theft_tracker.py`
- **Exports**: `backend/detection/__init__.py`
- **Documentação de keypoints COCO**: https://github.com/ultralytics/ultralytics

---

**Desenvolvido para máxima precisão e mínimos falsos alarmes! 🎯**
