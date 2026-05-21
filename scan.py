import subprocess
import re
import socket

print("[*] Executando ARP scan para descobrir dispositivos na rede...\n")

try:
    # Usa arp -a para listar todos os dispositivos conectados
    result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
    
    # Padrão para extrair IP e MAC
    pattern = r'(\d+\.\d+\.\d+\.\d+)\s+([\da-f-]+)\s+(\w+)'
    matches = re.findall(pattern, result.stdout, re.IGNORECASE)
    
    encontrados = 0
    for ip, mac, tipo in matches:
        if ip.startswith('224.'):  # Ignora multicast
            continue
        
        # Tenta resolver nome do host
        try:
            nome = socket.gethostbyaddr(ip)[0]
            print(f"✓ {ip:15} → {nome:30} [{mac}]")
        except:
            print(f"✓ {ip:15} → (sem hostname)              [{mac}]")
        
        encontrados += 1
    
    print(f"\n[*] Total: {encontrados} dispositivos encontrados")
    
    if encontrados == 0:
        print("[!] Nenhum dispositivo encontrado. Tente 'arp -a' manualmente no CMD.")
        
except Exception as e:
    print(f"[!] Erro: {e}")
    print("[!] Tente executar como Administrador ou use: arp -a")