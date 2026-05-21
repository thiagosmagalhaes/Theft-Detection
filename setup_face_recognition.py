"""
Setup script para o sistema de reconhecimento facial com DeepFace
Execute este script para configurar o ambiente
"""

import subprocess
import sys
import os

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def run_command(command, description):
    """Execute um comando e mostra o resultado"""
    print(f"→ {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✓ {description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - FALHOU")
        print(f"Erro: {e.stderr}")
        return False

def check_python_version():
    """Verificar versão do Python"""
    print_header("Verificando Python")
    version = sys.version_info
    print(f"Versão do Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 10:
        print("✓ Versão do Python compatível")
        return True
    else:
        print("✗ Python 3.10+ é recomendado")
        print("Você pode continuar, mas pode ter problemas de compatibilidade")
        return False

def install_dependencies():
    """Instalar dependências do requirements.txt"""
    print_header("Instalando Dependências")
    
    # Atualizar pip
    run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Atualizando pip"
    )
    
    # Instalar requirements
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Instalando pacotes do requirements.txt"
    )
    
    return success

def verify_imports():
    """Verificar se as bibliotecas principais podem ser importadas"""
    print_header("Verificando Instalação")
    
    libraries = [
        ("opencv-python", "cv2"),
        ("insightface", "insightface"),
        ("scipy", "scipy"),
        ("fastapi", "fastapi"),
        ("ultralytics", "ultralytics"),
        ("numpy", "numpy"),
        ("onnxruntime", "onnxruntime")
    ]
    
    all_ok = True
    for lib_name, import_name in libraries:
        try:
            __import__(import_name)
            print(f"✓ {lib_name} - OK")
        except ImportError:
            print(f"✗ {lib_name} - FALTANDO")
            all_ok = False
    
    return all_ok

def create_directories():
    """Criar diretórios necessários"""
    print_header("Criando Diretórios")
    
    directories = [
        "faces",
        "faces/detections",
        "alerts"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Criado: {directory}/")
        else:
            print(f"✓ Já existe: {directory}/")

def migrate_database():
    """Executar migração do banco de dados"""
    print_header("Configurando Banco de Dados")
    
    success = run_command(
        f"{sys.executable} migrate_database.py",
        "Executando migração do banco de dados"
    )
    
    return success

def test_deepface():
    """Testar se o InsightFace está funcionando"""
    print_header("Testando InsightFace")
    
    try:
        print("→ Carregando InsightFace...")
        import insightface
        from insightface.app import FaceAnalysis
        print("✓ InsightFace importado com sucesso")
        
        print("→ Testando modelo ArcFace...")
        print("  (Isso pode demorar na primeira vez - downloads de modelos)")
        
        # Inicializar modelo
        app = FaceAnalysis(providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        # Criar uma imagem de teste
        import numpy as np
        import cv2
        test_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        
        faces = app.get(test_image)
        
        print(f"✓ InsightFace funcionando (modelo carregado)")
        return True
            
    except Exception as e:
        print(f"✗ Erro ao testar InsightFace: {e}")
        return False

def print_summary():
    """Imprimir resumo final"""
    print_header("Setup Concluído!")
    
    print("📋 Próximos passos:\n")
    print("1. Execute o backend:")
    print("   py main.py")
    print()
    print("2. Acesse a API em:")
    print("   http://localhost:8000/docs")
    print()
    print("3. Veja o guia completo em:")
    print("   FACE_RECOGNITION_GUIDE.md")
    print()
    print("4. Exemplo de integração:")
    print("   integration_example.py")
    print()
    print("\n🎯 O sistema está pronto para uso!")
    print("Pessoas serão automaticamente registradas quando detectadas.")
    print()

def main():
    print_header("Setup - Sistema de Reconhecimento Facial")
    print("Este script irá configurar o ambiente completo.\n")
    
    # Passo 1: Verificar Python
    check_python_version()
    
    # Passo 2: Instalar dependências
    if not install_dependencies():
        print("\n⚠️  Falha ao instalar dependências.")
        print("Tente manualmente: pip install -r requirements.txt")
        return
    
    # Passo 3: Verificar importações
    if not verify_imports():
        print("\n⚠️  Algumas bibliotecas não foram instaladas corretamente.")
        print("Verifique os erros acima e tente novamente.")
        return
    
    # Passo 4: Criar diretórios
    create_directories()
    
    # Passo 5: Migrar banco de dados
    migrate_database()
    InsightFace
    print("\n⚠️  Testando Insight
    print("\n⚠️  Testando DeepFace (pode demorar na primeira vez)...")
    test_deepface()
    
    # Resumo final
    print_summary()

if __name__ == "__main__":
    main()
