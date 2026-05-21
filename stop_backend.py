#!/usr/bin/env python3
"""
Script para parar o backend do sistema de detecção de furtos
"""

import os
import subprocess
import sys

def stop_backend():
    """Para todos os processos Python (backend)"""
    try:
        if sys.platform == 'win32':
            # Windows
            print("Parando backend...")
            subprocess.run(['powershell', '-Command', 'Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force'], check=False)
            print("✅ Backend parado com sucesso!")
        else:
            # Linux/Mac
            print("Parando backend...")
            os.system("pkill -f 'python backend.py'")
            print("✅ Backend parado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao parar backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    stop_backend()
