# Melhorias Baseadas no Ultralytics YOLO26 Solutions

Este documento descreve as melhorias implementadas no sistema de detecção de roubo baseadas nas melhores práticas do Ultralytics YOLO26 Solutions.

## 🚀 Melhorias Implementadas

### 1. **Tracker Configurável** (botsort/bytetrack)

O sistema agora usa trackers profissionais do Ultralytics para melhor rastreamento de pessoas e objetos:

```python
# Configuração em .env
TRACKER_TYPE=botsort.yaml    # ou bytetrack.yaml
TRACKER_CONF=0.5             # Confidence threshold (0.1-1.0)
TRACKER_IOU=0.5              # IoU threshold for NMS (0.1-1.0)
```

**Benefícios:**
- Rastreamento mais consistente de pessoas em movimento
- Menos perda de IDs em oclusões temporárias
- Melhor performance em cenas com múltiplos objetos

### 2. **Rastreamento de Objetos em Zonas**

Implementação inspirada em "Track Objects in Zone" do Ultralytics Solutions:

- ✅ Rastreamento persistente de objetos que entram/saem das zonas
- ✅ Destaque vermelho quando objetos são removidos das áreas monitoradas
- ✅ Estado mantém-se até que objeto retorne à zona
- ✅ Resistente a oclusões temporárias (30 frames de tolerância)

**Como funciona:**
1. Objeto é detectado dentro da zona → marcado como "armed"
2. Objeto sai da zona → fica **vermelho** com label "FORA DA ZONA"
3. Objeto retorna à zona → volta ao estado normal

### 3. **Visualizações Melhoradas** (SolutionAnnotator pattern)

Seguindo o padrão `SolutionAnnotator` do Ultralytics:

**Labels com Background:**
```python
# Labels agora têm fundo colorido para melhor legibilidade
cv2.rectangle(frame, ..., color, -1)  # Fundo preenchido
cv2.putText(frame, label, ..., (255, 255, 255), 1)  # Texto branco
```

**Zonas ROI Semitransparentes:**
- Preenchimento com 15% de opacidade
- Bordas mais grossas (3px)
- Labels grandes e visíveis

**Antes:** Labels simples difíceis de ler
**Depois:** Labels com fundo colorido, texto branco, sempre legível

### 4. **Filtragem de Detecções de Baixa Confiança**

```python
# Filtra detecções < 25% de confiança para resultados mais limpos
detections = [d for d in detections if d.confidence >= 0.25]
```

### 5. **Documentação de Código Melhorada**

Todas as funções agora seguem o padrão Ultralytics com docstrings completas:

```python
def update_zone_object_states(cam_data, detections, monitored_object_rois):
    """Track objects that left merchandise zones and keep them red until they return.
    
    Implements zone-based object tracking following Ultralytics Solutions pattern.
    Similar to 'Track Objects in Zone' but with removal detection logic.
    
    Args:
        cam_data: Camera data dictionary with persistent state
        detections: List of ObjectDetection instances
        monitored_object_rois: List of ROI polygons to monitor
        
    Returns:
        set: Indices of detections that should be highlighted as removed
    """
```

## 🎯 Configuração Recomendada

### Para Ambientes Internos (Lojas)
```env
TRACKER_TYPE=botsort.yaml
TRACKER_CONF=0.5
TRACKER_IOU=0.5
OBJECT_DETECTION_CONFIDENCE=0.25
```

### Para Ambientes com Muita Movimentação
```env
TRACKER_TYPE=bytetrack.yaml  # Mais rápido
TRACKER_CONF=0.6             # Mais seletivo
TRACKER_IOU=0.4
```

### Para Máxima Precisão (Hardware potente)
```env
TRACKER_TYPE=botsort.yaml
TRACKER_CONF=0.4             # Detecta mais objetos
TRACKER_IOU=0.6              # Mais rigoroso no matching
OBJECT_DETECTION_INTERVAL=1  # Detecção a cada frame
```

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Tracker** | Padrão YOLO | Configurável (botsort/bytetrack) |
| **Labels** | Texto simples | Background colorido + texto branco |
| **Zonas** | Linhas finas | Semitransparente + bordas grossas |
| **Objeto removido** | ❌ Não detectava | ✅ Vermelho até retornar |
| **Confiança** | Fixa | Configurável via .env |
| **Documentação** | Básica | Completa com padrão Ultralytics |

## 🔧 Debugging

O sistema agora mostra logs detalhados no console:

```
✓ Using GENERIC object detection model
[ZONE DEBUG] Cam bba548ef...: 2 monitored zones active
[ZONE] Object class 39 entered zone (armed)
[ZONE] ⚠️ Object class 39 REMOVED from zone (flagging RED)
[ZONE] Object class 39 RETURNED to zone (cleared removed state)
```

## 📚 Referências

- [Ultralytics Solutions](https://docs.ultralytics.com/guides/solutions/)
- [Track Objects in Zone](https://docs.ultralytics.com/guides/trackzone/)
- [Object Counting in Regions](https://docs.ultralytics.com/guides/region-counting/)
- [SolutionAnnotator](https://docs.ultralytics.com/reference/solutions/solutions/#ultralytics.solutions.solutions.SolutionAnnotator)

## 🎨 Cores das Zonas

```python
zone_colours = {
    "merchandise": (0, 200, 255),   # Laranja/Âmbar - área de produtos
    "forbidden":   (0, 0, 220),     # Vermelho - área proibida
    "entry":       (80, 200, 80),   # Verde - entrada/balcão
}
```

## ✨ Próximas Melhorias Sugeridas

1. **Speed Estimation**: Calcular velocidade de objetos removidos
2. **Analytics**: Gráficos de objetos removidos por hora/dia
3. **Distance Calculation**: Distância entre pessoa e objeto
4. **Heatmaps de Remoção**: Visualizar áreas com mais remoções
5. **Queue Management**: Contagem de pessoas em filas

---

**Versão:** 1.0
**Data:** 2026-05-23
**Base:** Ultralytics YOLO26 Solutions
