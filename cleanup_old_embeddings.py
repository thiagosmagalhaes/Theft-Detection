"""
Script para limpar embeddings antigos (128-dim) do banco de dados
e manter apenas embeddings do InsightFace (512-dim)
"""

import sqlite3
import pickle
from backend.config import DB_NAME


def cleanup_old_embeddings():
    """Remove embeddings antigos que não são compatíveis com InsightFace"""
    
    print("=" * 60)
    print("LIMPEZA DE EMBEDDINGS ANTIGOS")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Buscar todas as faces
    c.execute("SELECT id, name, encoding FROM faces")
    rows = c.fetchall()
    
    if len(rows) == 0:
        print("✓ Nenhuma face no banco de dados")
        conn.close()
        return
    
    total_faces = len(rows)
    old_embeddings = []
    valid_embeddings = []
    
    print(f"\n→ Analisando {total_faces} faces...")
    
    for face_id, name, encoding_blob in rows:
        try:
            encoding = pickle.loads(encoding_blob)
            
            # Verificar dimensão
            if len(encoding) == 128:
                old_embeddings.append((face_id, name, len(encoding)))
                print(f"  ✗ {name}: 128-dim (face_recognition antigo)")
            elif len(encoding) == 512:
                valid_embeddings.append((face_id, name, len(encoding)))
                print(f"  ✓ {name}: 512-dim (InsightFace)")
            else:
                old_embeddings.append((face_id, name, len(encoding)))
                print(f"  ? {name}: {len(encoding)}-dim (desconhecido)")
                
        except Exception as e:
            old_embeddings.append((face_id, name, "erro"))
            print(f"  ✗ {name}: erro ao carregar ({e})")
    
    print(f"\n{'='*60}")
    print(f"RESUMO:")
    print(f"  Total de faces: {total_faces}")
    print(f"  ✓ Válidas (512-dim): {len(valid_embeddings)}")
    print(f"  ✗ Antigas/Inválidas: {len(old_embeddings)}")
    print(f"{'='*60}\n")
    
    if len(old_embeddings) == 0:
        print("✓ Nenhuma face antiga encontrada. Banco de dados está limpo!")
        conn.close()
        return
    
    # Perguntar confirmação
    print("⚠️  ATENÇÃO: As seguintes faces serão REMOVIDAS:")
    for face_id, name, dims in old_embeddings:
        print(f"  - {name} ({dims}-dim)")
    
    print("\n❓ Deseja continuar? Digite 'SIM' para confirmar: ", end="")
    confirmation = input().strip().upper()
    
    if confirmation != "SIM":
        print("❌ Operação cancelada")
        conn.close()
        return
    
    # Deletar faces antigas
    print(f"\n→ Removendo {len(old_embeddings)} faces antigas...")
    deleted_count = 0
    
    for face_id, name, _ in old_embeddings:
        try:
            # Deletar detecções associadas
            c.execute("DELETE FROM person_detections WHERE person_id = ?", (face_id,))
            # Deletar face
            c.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            deleted_count += 1
            print(f"  ✓ Removido: {name}")
        except Exception as e:
            print(f"  ✗ Erro ao remover {name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✓ LIMPEZA CONCLUÍDA!")
    print(f"  Faces removidas: {deleted_count}")
    print(f"  Faces restantes: {len(valid_embeddings)}")
    print(f"{'='*60}")
    print("\n💡 Agora você pode registrar novamente as pessoas usando InsightFace")
    print("   Os novos embeddings serão gerados com 512 dimensões.\n")


def clear_all_faces():
    """Limpar TODAS as faces do banco de dados"""
    
    print("=" * 60)
    print("LIMPAR TODAS AS FACES")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM faces")
    total = c.fetchone()[0]
    
    if total == 0:
        print("✓ Banco de dados já está vazio")
        conn.close()
        return
    
    print(f"\n⚠️  ATENÇÃO: Isso vai REMOVER TODAS AS {total} FACES do banco!")
    print("   Todas as detecções associadas também serão removidas.\n")
    print("❓ Tem certeza? Digite 'DELETAR TUDO' para confirmar: ", end="")
    confirmation = input().strip()
    
    if confirmation != "DELETAR TUDO":
        print("❌ Operação cancelada")
        conn.close()
        return
    
    try:
        c.execute("DELETE FROM person_detections")
        c.execute("DELETE FROM faces")
        conn.commit()
        print(f"\n✓ Todas as {total} faces foram removidas")
        print("✓ Banco de dados limpo com sucesso\n")
    except Exception as e:
        print(f"✗ Erro ao limpar banco: {e}")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("  FERRAMENTA DE LIMPEZA DE EMBEDDINGS")
    print("=" * 60)
    print("\nOpções:")
    print("  1. Remover apenas embeddings antigos (128-dim)")
    print("  2. Limpar TODAS as faces do banco")
    print("  3. Cancelar")
    print()
    
    try:
        choice = input("Escolha uma opção [1-3]: ").strip()
        
        if choice == "1":
            cleanup_old_embeddings()
        elif choice == "2":
            clear_all_faces()
        elif choice == "3":
            print("✓ Cancelado")
        else:
            print("✗ Opção inválida")
    except KeyboardInterrupt:
        print("\n\n✗ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n✗ Erro: {e}")
