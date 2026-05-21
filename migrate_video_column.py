"""Migration script to add video_path column to alerts table"""

import sqlite3
import os

DB_NAME = "theft_detection.db"


def migrate_database():
    """Add video_path column to alerts table if it doesn't exist"""
    
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} não encontrado. Nenhuma migração necessária.")
        return
    
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Check if video_path column exists
        c.execute("PRAGMA table_info(alerts)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'video_path' not in columns:
            print("Adicionando coluna 'video_path' à tabela alerts...")
            c.execute("ALTER TABLE alerts ADD COLUMN video_path TEXT")
            conn.commit()
            print("✓ Migração concluída com sucesso!")
        else:
            print("Coluna 'video_path' já existe. Nenhuma migração necessária.")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro durante migração: {e}")


if __name__ == "__main__":
    print("=== Migração do Banco de Dados ===")
    print("Adicionando suporte para vídeos de alerta...")
    migrate_database()
