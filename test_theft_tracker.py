"""
Teste do sistema avançado de detecção de furto com TheftBehaviorTracker
========================================================================

Este script demonstra como usar o TheftBehaviorTracker com dados reais
de YOLO para detectar comportamento suspeito de furto.

O TheftBehaviorTracker usa um sistema de PONTUAÇÃO DE RISCO (risk score)
ao invés de detecção binária, acumulando evidências ao longo do tempo:

- Cada ação isolada (ex: tocar no bolso) soma pouco risco
- Uma SEQUÊNCIA típica de furto (pegar item -> esconder -> objeto some) 
  soma muito risco
- O risco decai naturalmente ao longo do tempo se não houver novos sinais

Níveis de risco:
- LOW: 0.0 - 0.4 (comportamento normal)
- MEDIUM: 0.4 - 0.8 (atenção)
- HIGH: 0.8 - 1.2 (suspeito)
- ALERT: >= 1.2 (alerta de furto!)

Principais comportamentos detectados:
1. Pegar mercadoria na prateleira (ROI)
2. Objeto na mão próximo de zona de ocultação
3. Esconder em: bolso, cintura, peito, axila, bolsa, meia/bota
4. Objeto desaparece da mão no corpo (forte sinal!)
5. Olhar constantemente para os lados (vigília)
6. Virar de costas com mãos no corpo
7. Movimento repetitivo (arrancar etiqueta)
8. Permanência prolongada na mesma área (loitering)
"""

import cv2
import numpy as np
from ultralytics import YOLO
from backend.detection import TheftBehaviorTracker, ZONE_LABELS

# Configuração
VIDEO_SOURCE = 0  # 0 = webcam, ou caminho para arquivo de vídeo
SHELF_ROI = [(100, 100), (500, 100), (500, 300), (100, 300)]  # Exemplo de prateleira
FPS = 15  # FPS estimado do vídeo


def draw_roi(frame, roi_points, color=(0, 255, 255), thickness=2):
    """Desenha a ROI (prateleira) no frame."""
    if len(roi_points) >= 3:
        pts = np.array(roi_points, dtype=np.int32)
        cv2.polylines(frame, [pts], True, color, thickness)
        cv2.putText(frame, "SHELF ROI", (roi_points[0][0], roi_points[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def draw_risk_info(frame, result, box):
    """Desenha informações de risco sobre a pessoa detectada."""
    track_id = result["track_id"]
    risk = result["risk"]
    level = result["level"]
    
    # Cor baseada no nível de risco
    color_map = {
        "LOW": (0, 255, 0),      # Verde
        "MEDIUM": (0, 165, 255),  # Laranja
        "HIGH": (0, 100, 255),    # Vermelho-laranja
        "ALERT": (0, 0, 255)      # Vermelho
    }
    color = color_map.get(level, (255, 255, 255))
    
    # Borda da pessoa
    thickness = 3 if level in ("HIGH", "ALERT") else 2
    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
    
    # Informações de risco
    y_offset = box[1] - 10
    cv2.putText(frame, f"ID:{track_id} Risk:{risk:.2f} [{level}]",
                (box[0], y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Eventos suspeitos
    y_offset -= 25
    for event in result["events"][:3]:  # Mostra até 3 eventos recentes
        text = event.get("desc", event["type"])
        if len(text) > 40:
            text = text[:37] + "..."
        cv2.putText(frame, text, (box[0], y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        y_offset -= 20
    
    # Alerta visual forte se ALERT
    if level == "ALERT":
        cv2.putText(frame, "!!! THEFT ALERT !!!", (box[0], box[3] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)


def main():
    """Loop principal de teste."""
    print("=" * 70)
    print("THEFT BEHAVIOR TRACKER - TESTE")
    print("=" * 70)
    print("\nCarregando modelos YOLO...")
    
    # Carregar modelos
    try:
        pose_model = YOLO("yolov8n-pose.pt")
        obj_model = YOLO("yolov8n.pt")
        print("✓ Modelos carregados com sucesso!")
    except Exception as e:
        print(f"✗ Erro ao carregar modelos: {e}")
        return
    
    # Inicializar tracker
    tracker = TheftBehaviorTracker(
        fps=FPS,
        decay_per_frame=0.98,      # Risco decai 2% por frame se sem novos sinais
        alert_threshold=1.2,        # >= 1.2 = ALERT
        risk_cap=2.5,               # Risco máximo possível
        conf_thr=0.3                # Confiança mínima de keypoints
    )
    print("✓ TheftBehaviorTracker inicializado!")
    print(f"  - FPS: {FPS}")
    print(f"  - Alert Threshold: {tracker.alert_threshold}")
    print(f"  - Risk Cap: {tracker.risk_cap}")
    
    # Abrir vídeo
    print(f"\nAbrindo fonte de vídeo: {VIDEO_SOURCE}")
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print("✗ Erro ao abrir vídeo!")
        return
    print("✓ Vídeo aberto!")
    
    print("\n" + "=" * 70)
    print("CONTROLES:")
    print("  Q - Sair")
    print("  ESPAÇO - Pausar/Continuar")
    print("=" * 70)
    print("\nProcessando frames...\n")
    
    frame_count = 0
    paused = False
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("\nFim do vídeo ou erro de leitura.")
                    break
                
                frame_count += 1
                
                # 1. Detecção de pose com tracking
                pose_results = pose_model.track(frame, persist=True, verbose=False,
                                                classes=[0], conf=0.5)
                
                # 2. Detecção de objetos (produtos, bolsas, etc.)
                obj_results = obj_model(frame, verbose=False, conf=0.3)
                
                # Separar objetos detectados em categorias
                object_boxes = []  # Produtos genéricos
                bag_boxes = []     # Bolsas/mochilas
                
                if len(obj_results) > 0:
                    boxes = obj_results[0].boxes.xyxy.cpu().numpy()
                    classes = obj_results[0].boxes.cls.cpu().numpy().astype(int)
                    
                    for box, cls in zip(boxes, classes):
                        class_name = obj_model.names[cls]
                        # Classes COCO de bolsas: 24=backpack, 26=handbag, 28=suitcase
                        if cls in [24, 26, 28]:
                            bag_boxes.append(box.tolist())
                        else:
                            object_boxes.append(box.tolist())
                
                # 3. Processar cada pessoa detectada
                if pose_results[0].boxes.id is not None:
                    track_ids = pose_results[0].boxes.id.cpu().numpy().astype(int)
                    boxes_pose = pose_results[0].boxes.xyxy.cpu().numpy().astype(int)
                    keypoints_all = pose_results[0].keypoints.data.cpu().numpy()
                    
                    for i, track_id in enumerate(track_ids):
                        box = boxes_pose[i]
                        kpts = keypoints_all[i]  # Shape: (17, 3) - COCO keypoints
                        
                        # Atualizar tracker com dados da pessoa
                        result = tracker.update(
                            track_id=track_id,
                            keypoints=kpts,
                            object_boxes=object_boxes,
                            bag_boxes=bag_boxes,
                            roi_polys=[SHELF_ROI]
                        )
                        
                        # Desenhar informações de risco
                        draw_risk_info(frame, result, box)
                        
                        # Log de eventos importantes
                        if result["events"]:
                            print(f"\n[Frame {frame_count}] Pessoa {track_id} - Risk: {result['risk']:.3f} [{result['level']}]")
                            for event in result["events"]:
                                zone = event.get("zone", "")
                                zone_label = ZONE_LABELS.get(zone, zone) if zone else ""
                                print(f"  → {event['desc']}")
                        
                        # Alerta sonoro/visual se ALERT
                        if result["alert"]:
                            print(f"\n{'!' * 70}")
                            print(f"🚨 ALERTA DE FURTO! Pessoa {track_id} - Risco: {result['risk']:.3f}")
                            print(f"{'!' * 70}\n")
                
                # Limpar pessoas que sumiram há muito tempo
                tracker.cleanup()
                
                # Desenhar ROI da prateleira
                draw_roi(frame, SHELF_ROI)
                
                # Plotar keypoints no frame
                if pose_results[0].keypoints is not None:
                    frame = pose_results[0].plot()
                
                # Info do frame
                cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Tracked Persons: {len(tracker.persons)}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Mostrar frame
            cv2.imshow("Theft Behavior Tracker - Test", frame)
            
            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q ou ESC
                break
            elif key == ord(' '):  # ESPAÇO
                paused = not paused
                print(f"\n{'[PAUSADO]' if paused else '[CONTINUANDO]'}")
    
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n" + "=" * 70)
        print("ESTATÍSTICAS FINAIS:")
        print(f"  - Frames processados: {frame_count}")
        print(f"  - Pessoas rastreadas: {len(tracker.persons)}")
        print("=" * 70)
        print("\nTeste concluído!")


if __name__ == "__main__":
    main()
