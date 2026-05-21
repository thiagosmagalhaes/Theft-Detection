"""
Exemplo de integração do sistema de reconhecimento facial com InsightFace
no loop de processamento de vídeo
"""

from backend.face_recognition.auto_register import auto_register_or_track_person
import cv2

# EXEMPLO 1: Integração simples no loop de detecção
def process_detected_person(frame, person_bbox, person_track_id, camera_id):
    """
    Processar pessoa detectada e auto-registrar/rastrear
    
    Args:
        frame: Frame completo da câmera
        person_bbox: Bounding box da pessoa [x1, y1, x2, y2]
        person_track_id: ID de tracking da pessoa
        camera_id: ID da câmera
    """
    x1, y1, x2, y2 = person_bbox
    
    # Extrair região da pessoa (idealmente, região da face)
    # Se você tem detecção de face, use a face crop
    # Se não, use a parte superior do corpo (onde geralmente está a face)
    
    # Opção 1: Se você já tem face crop
    face_crop = frame[y1:y2, x1:x2]  # Substituir com face crop real
    
    # Opção 2: Usar parte superior do bbox da pessoa (estimativa da cabeça)
    person_height = y2 - y1
    head_region_y2 = y1 + int(person_height * 0.3)  # 30% superior do corpo
    face_estimate = frame[y1:head_region_y2, x1:x2]
    
    # Auto-registrar ou rastrear a pessoa
    person_id = auto_register_or_track_person(
        face_image=face_crop,  # ou face_estimate
        cam_id=camera_id,
        track_id=person_track_id
    )
    
    return person_id


# EXEMPLO 2: Integração com YOLO pose detection
def process_frame_with_yolo(frame, camera_id, yolo_results):
    """
    Processar frame com resultados do YOLO
    """
    for result in yolo_results:
        # Iterar sobre cada pessoa detectada
        for idx, box in enumerate(result.boxes):
            # Obter bounding box
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Track ID (se usando tracking)
            track_id = box.id[0] if hasattr(box, 'id') and box.id is not None else idx
            
            # Processar pessoa
            person_id = process_detected_person(
                frame=frame,
                person_bbox=[x1, y1, x2, y2],
                person_track_id=track_id,
                camera_id=camera_id
            )
            
            if person_id:
                # Pessoa foi identificada/registrada
                print(f"Tracked person: {person_id}")
                
                # Você pode adicionar lógica adicional aqui
                # Por exemplo: verificar se está em lista negra, etc.


# EXEMPLO 3: Integração com detecção de face existente
def process_with_face_detection(frame, camera_id, face_detector):
    """
    Se você já tem um detector de faces separado
    """
    # Detectar faces no frame
    faces = face_detector.detect(frame)
    
    for idx, face in enumerate(faces):
        # Extrair região da face
        x1, y1, x2, y2 = face.bbox
        face_crop = frame[y1:y2, x1:x2]
        
        # Garantir que a face crop tem tamanho mínimo
        if face_crop.shape[0] < 50 or face_crop.shape[1] < 50:
            continue  # Face muito pequena, pular
        
        # Track ID (pode vir do seu sistema de tracking)
        track_id = face.track_id if hasattr(face, 'track_id') else idx
        
        # Auto-registrar/rastrear
        person_id = auto_register_or_track_person(
            face_image=face_crop,
            cam_id=camera_id,
            track_id=track_id
        )


# EXEMPLO 4: Consultar histórico de detecções
def get_person_history(person_id):
    """Obter histórico de detecções de uma pessoa"""
    from backend.database import get_person_detections, get_person_stats
    
    # Obter estatísticas
    stats = get_person_stats(person_id)
    print(f"Total de detecções: {stats['total_detections']}")
    print(f"Primeira vez visto: {stats['first_seen']}")
    print(f"Última vez visto: {stats['last_seen']}")
    print(f"Por câmera: {stats['by_camera']}")
    
    # Obter histórico detalhado
    detections = get_person_detections(person_id=person_id, limit=50)
    for detection in detections:
        print(f"  - {detection['timestamp']}: Câmera {detection['camera_id']}")


# EXEMPLO 5: Listar todas as pessoas registradas
def list_all_persons():
    """Listar todas as pessoas registradas com estatísticas"""
    from backend.database import get_all_persons_with_stats
    
    persons = get_all_persons_with_stats()
    
    print(f"\nTotal de pessoas registradas: {len(persons)}\n")
    
    for person in persons:
        print(f"Nome: {person['name']}")
        print(f"  ID: {person['id']}")
        print(f"  Tipo: {person['type']}")
        print(f"  Detecções: {person['detection_count']}")
        print(f"  Primeira vez: {person['first_seen']}")
        print(f"  Última vez: {person['last_seen']}")
        print()


# EXEMPLO 6: Limpeza periódica de registros pendentes
import threading
import time

def cleanup_thread():
    """Thread para limpar registros pendentes periodicamente"""
    from backend.face_recognition.auto_register import cleanup_pending_registrations
    
    while True:
        time.sleep(60)  # A cada 60 segundos
        cleanup_pending_registrations()

# Iniciar thread de limpeza (chamar uma vez no início do programa)
def start_cleanup_thread():
    thread = threading.Thread(target=cleanup_thread, daemon=True)
    thread.start()


# EXEMPLO 7: Integração completa em video_loop.py
"""
# No seu backend/video/video_loop.py, adicionar:

from backend.face_recognition.auto_register import auto_register_or_track_person

# No loop de processamento:
for track in tracked_objects:
    # ... seu código existente ...
    
    # Extrair face crop (ajustar conforme sua implementação)
    face_crop = get_face_crop(frame, track.bbox)
    
    if face_crop is not None:
        # Auto-registrar/rastrear pessoa
        person_id = auto_register_or_track_person(
            face_image=face_crop,
            cam_id=cam_id,
            track_id=track.id
        )
        
        # Armazenar person_id no estado do track para uso posterior
        track.person_id = person_id
"""


if __name__ == "__main__":
    # Exemplo de uso
    print("Exemplos de integração do sistema de reconhecimento facial")
    print("\nPara usar:")
    print("1. Importe as funções necessárias no seu código de processamento de vídeo")
    print("2. Chame auto_register_or_track_person() para cada pessoa detectada")
    print("3. Use as funções de histórico para consultar detecções")
    
    # Listar pessoas existentes
    # list_all_persons()
