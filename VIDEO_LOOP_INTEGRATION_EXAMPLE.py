"""
EXEMPLO DE INTEGRAÇÃO - TheftBehaviorTracker no video_loop.py
==============================================================

Este arquivo mostra como refatorar o video_loop.py para usar o 
TheftBehaviorTracker ao invés do sistema binário antigo.

NÃO EXECUTE ESTE ARQUIVO DIRETAMENTE! 
Use-o como referência para modificar seu video_loop.py.

Principais mudanças:
1. Criar TheftBehaviorTracker global (um por câmera ou compartilhado)
2. Substituir process_theft_detection() pelo tracker.update()
3. Processar bag_boxes separadamente dos object_boxes
4. Usar result["risk"] e result["level"] para decisões
5. Desenhar overlay de risco visual
"""

# ============================================================================
# PARTE 1: IMPORTS E SETUP (adicionar no início do video_loop.py)
# ============================================================================

from backend.detection import (
    update_heatmap,
    get_heatmap_overlay,
    check_reaching,
    is_person_facing_away,
    TheftBehaviorTracker,  # NOVO!
    ZONE_LABELS,           # NOVO!
)

# ============================================================================
# PARTE 2: INICIALIZAÇÃO (adicionar no início de video_loop())
# ============================================================================

def video_loop():
    """Main video processing loop"""
    global latest_frame, alert_payload, person_states
    
    # ... código existente de carregamento de modelos ...
    
    # NOVO: Criar tracker de comportamento de furto
    # Opção 1: Um tracker compartilhado para todas as câmeras
    behavior_tracker = TheftBehaviorTracker(
        fps=15,
        decay_per_frame=0.98,
        alert_threshold=1.2,
        risk_cap=2.5,
        conf_thr=0.3
    )
    
    # Opção 2: Um tracker por câmera (mais preciso se FPS diferente)
    # behavior_trackers = {}  # {cam_id: TheftBehaviorTracker}
    
    print("✓ TheftBehaviorTracker inicializado!")
    
    # ... resto do código ...

# ============================================================================
# PARTE 3: PROCESSAMENTO DE OBJETOS (modificar a seção de detecção de objetos)
# ============================================================================

# ANTES: Apenas detected_objects
detected_objects = []

# DEPOIS: Separar em object_boxes e bag_boxes
if run_obj_det:
    if model_is_specialized:
        # ... código existente para modelo especializado ...
        pass
    else:
        # MODIFICAR ESTA SEÇÃO
        results_obj = model_obj(frame, verbose=False, conf=0.3)
        
        # NOVO: Separar objetos e bolsas
        object_boxes = []  # Produtos que podem ser furtados
        bag_boxes = []     # Bolsas/mochilas (onde podem esconder)
        
        if len(results_obj) > 0:
            boxes_obj = results_obj[0].boxes.xyxy.cpu().numpy().astype(int)
            cls_obj = results_obj[0].boxes.cls.cpu().numpy().astype(int)
            conf_obj = results_obj[0].boxes.conf.cpu().numpy()
            
            for b, c, conf in zip(boxes_obj, cls_obj, conf_obj):
                # Classes COCO de bolsas: 24=backpack, 26=handbag, 28=suitcase
                if c in [24, 26, 28]:
                    bag_boxes.append(b.tolist())
                    # Desenhar bolsas em cor diferente
                    cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (255, 0, 255), 2)
                    cv2.putText(frame, f"BAG: {model_obj.names[c]}", (b[0], b[1]-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                
                elif c in TARGET_CLASSES:
                    object_boxes.append(b.tolist())
                    # Desenhar produtos
                    label = f"ITEM: {model_obj.names[c]} {conf:.2f}"
                    cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 165, 255), 2)
                    cv2.putText(frame, label, (b[0], b[1]-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

# Cache de objetos para frames sem detecção
if run_obj_det:
    cam_data["last_object_boxes"] = object_boxes
    cam_data["last_bag_boxes"] = bag_boxes
else:
    object_boxes = cam_data.get("last_object_boxes", [])
    bag_boxes = cam_data.get("last_bag_boxes", [])

# ============================================================================
# PARTE 4: PROCESSAMENTO DE PESSOAS (substituir a lógica antiga)
# ============================================================================

# PROCESSAR DETECÇÕES
if results_pose[0].boxes.id is not None:
    boxes = results_pose[0].boxes.xyxy.cpu().numpy().astype(int)
    track_ids = results_pose[0].boxes.id.cpu().numpy().astype(int)
    
    try:
        keypoints_all = results_pose[0].keypoints.data.cpu().numpy()
    except:
        keypoints_all = []

    for i, track_id in enumerate(track_ids):
        box = boxes[i]
        kpts = keypoints_all[i] if len(keypoints_all) > i else []
        
        # VALIDAÇÕES DE ANTI-FALSO POSITIVO (manter código existente)
        box_width = box[2] - box[0]
        box_height = box[3] - box[1]
        
        if box_width < MIN_BOX_SIZE or box_height < MIN_BOX_SIZE:
            continue
        
        if len(kpts) >= 17:
            visible_keypoints = sum([1 for kp in kpts if kp[0] > 0 and kp[1] > 0])
            if visible_keypoints < MIN_VISIBLE_KEYPOINTS:
                continue
        else:
            continue
        
        # Estado de pessoa (manter para face recognition e outras features)
        state_key = (cam_id, track_id)
        if state_key not in person_states:
            person_states[state_key] = PersonState(track_id)
        p_state = person_states[state_key]
        
        # FACE RECOGNITION (manter código existente)
        process_face_recognition(
            frame, box, kpts, cam_id, cam_data, 
            name, track_id, p_state, current_time
        )
        
        # ====================================================================
        # THEFT DETECTION - NOVO SISTEMA COM THEFTBEHAVIORTRACKER
        # ====================================================================
        if not model_is_specialized:
            # Atualizar behavior tracker
            result = behavior_tracker.update(
                track_id=track_id,
                keypoints=kpts,
                object_boxes=object_boxes,
                bag_boxes=bag_boxes,
                roi_polys=[cam_roi] if len(cam_roi) > 0 else []
            )
            
            # Desenhar overlay de risco
            draw_theft_risk_overlay(frame, result, box)
            
            # Logar eventos significativos
            if result["events"]:
                for event in result["events"]:
                    print(f"[{name}] Track {track_id}: {event['desc']}")
            
            # Disparar alerta se nível crítico
            if result["level"] in ("HIGH", "ALERT"):
                # Alerta visual forte
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), 
                              (0, 0, 255), 3)
                
                # Disparar alerta ao sistema (respeitando cooldown)
                if result["alert"] and current_time - cam_data["last_alert_time"] > ALERT_COOLDOWN:
                    # Criar descrição detalhada do alerta
                    event_types = [e["type"] for e in result["events"]]
                    alert_desc = f"THEFT RISK {result['risk']:.2f}: " + ", ".join(event_types[:3])
                    
                    alert_payload_wrapper = {}
                    frame_buffer = get_camera_buffer(cam_data)
                    trigger_alert(
                        cam_id, name, alert_desc, 
                        frame, alert_payload_wrapper, frame_buffer
                    )
                    cam_data["last_alert_time"] = current_time
                    
                    with lock:
                        alert_payload = alert_payload_wrapper.get('data')
                    
                    print(f"🚨 ALERTA DISPARADO: {alert_desc}")
        
        # ====================================================================
        # OUTRAS LÓGICAS (manter código existente)
        # ====================================================================
        
        # ROI INTRUSION (manter código existente)
        is_reaching, _ = check_reaching(kpts, cam_roi)
        if is_reaching:
            cv2.putText(frame, "RESTRICTED AREA ENT!", 
                        (box[0], box[1]-40), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.6, (0, 0, 255), 2)
            # ... código de alerta de ROI ...
        
        # FACING AWAY (debug visual)
        if is_person_facing_away(kpts):
            cv2.putText(frame, "FACING AWAY", (box[0], box[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 2)
        
        # LOITERING (manter código existente - ou pode integrar no tracker)
        process_loitering(
            frame, box, cam_data, cam_id, name, 
            cam_roi, track_id, current_time
        )
    
    # CLEANUP DO TRACKER (1x por frame, fora do loop de pessoas)
    behavior_tracker.cleanup()

# ============================================================================
# PARTE 5: FUNÇÃO AUXILIAR PARA DESENHAR OVERLAY DE RISCO
# ============================================================================

def draw_theft_risk_overlay(frame, result, box):
    """
    Desenha informações visuais de risco de furto sobre a pessoa detectada.
    
    Args:
        frame: Frame de vídeo (numpy array)
        result: Resultado do tracker.update()
        box: Bounding box [x1, y1, x2, y2]
    """
    track_id = result["track_id"]
    risk = result["risk"]
    level = result["level"]
    
    # Cores por nível de risco
    color_map = {
        "LOW": (0, 255, 0),       # Verde
        "MEDIUM": (0, 165, 255),   # Laranja
        "HIGH": (0, 100, 255),     # Vermelho-laranja
        "ALERT": (0, 0, 255)       # Vermelho
    }
    color = color_map.get(level, (255, 255, 255))
    
    # Espessura da borda baseada no nível
    thickness = 3 if level in ("HIGH", "ALERT") else 2
    
    # Desenhar borda (já feito no código principal se ALERT, mas reforçar)
    if level in ("MEDIUM", "HIGH"):
        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
    
    # Texto de risco principal
    y_offset = box[1] - 10
    risk_text = f"ID:{track_id} RISK:{risk:.2f} [{level}]"
    cv2.putText(frame, risk_text, (box[0], y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Mostrar últimos eventos (máximo 2 para não poluir)
    y_offset -= 25
    for event in result["events"][:2]:
        desc = event.get("desc", event["type"])
        
        # Truncar se muito longo
        if len(desc) > 45:
            desc = desc[:42] + "..."
        
        cv2.putText(frame, desc, (box[0], y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        y_offset -= 18
    
    # Indicador visual FORTE se ALERT
    if level == "ALERT":
        # Texto piscante de alerta
        cv2.putText(frame, "!!! THEFT ALERT !!!", 
                    (box[0], box[3] + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Opcional: Desenhar círculo/símbolo de alerta
        center_x = (box[0] + box[2]) // 2
        cv2.circle(frame, (center_x, box[1] - 40), 15, (0, 0, 255), -1)
        cv2.putText(frame, "!", (center_x - 5, box[1] - 33),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

# ============================================================================
# PARTE 6: REMOVER/COMENTAR CÓDIGO ANTIGO
# ============================================================================

# REMOVER OU COMENTAR:
# - def process_theft_detection() - substituída pelo tracker.update()
# - Lógica de p_state.holding_object, p_state.last_holding_time
# - check_concealment() manual (agora integrado no tracker)
# - check_object_in_hand() manual (agora integrado no tracker)

# MANTER:
# - PersonState (para face recognition e outras features)
# - process_face_recognition()
# - process_loitering() (ou pode integrar no tracker se quiser)
# - ROI intrusion check
# - Heatmap

# ============================================================================
# NOTAS FINAIS
# ============================================================================

"""
CHECKLIST DE INTEGRAÇÃO:

1. ✅ Adicionar imports (TheftBehaviorTracker, ZONE_LABELS)
2. ✅ Criar behavior_tracker no início de video_loop()
3. ✅ Separar object_boxes e bag_boxes na detecção de objetos
4. ✅ Substituir process_theft_detection() por tracker.update()
5. ✅ Adicionar draw_theft_risk_overlay()
6. ✅ Adicionar tracker.cleanup() no final do loop de cada câmera
7. ✅ Testar com vídeo real
8. ✅ Ajustar thresholds conforme necessário

VANTAGENS:
- ✅ Redução massiva de falsos positivos (score progressivo)
- ✅ Detecção de 6 zonas de ocultação diferentes
- ✅ Comportamentos avançados (scanning, loitering interno, tag removal)
- ✅ Independente de distância da câmera (body scale automático)
- ✅ Histórico temporal de comportamento
- ✅ Configuração fácil (pesos, thresholds)

CONFIGURAÇÃO RECOMENDADA:
- FPS: 15 (ajustar conforme seu vídeo)
- decay_per_frame: 0.98 (risco decai 2% por frame)
- alert_threshold: 1.2 (>= 1.2 dispara alerta)
- risk_cap: 2.5 (máximo de risco acumulável)

Para ambientes com muitos falsos positivos:
- Aumentar alert_threshold para 1.5
- Aumentar decay_per_frame para 0.95 (decai mais rápido)

Para ambientes com furtos frequentes:
- Diminuir alert_threshold para 1.0
- Diminuir decay_per_frame para 0.99 (decai mais devagar)
"""
