# Docker Deployment Guide - Theft Detection System

Este guia explica como executar o sistema de detecção de furtos usando Docker containers.

## 📋 Pré-requisitos

- Docker instalado (versão 20.10 ou superior)
- Docker Compose instalado (versão 1.29 ou superior)
- Modelos YOLO configurados no `.env` (`YOLO_POSE_MODEL` e `YOLO_OBJ_MODEL`); os padrões `yolo26x.pt` e `yolo26x-pose.pt` são baixados automaticamente se não existirem
- Arquivos de configuração (`cameras.json` e `settings.json`)

## 🚀 Quick Start

### 1. Usando Docker Compose (Recomendado)

```bash
# Construir e iniciar o backend
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Parar os serviços
docker-compose down
```

### 2. Usando Docker diretamente

```bash
# Construir a imagem
docker build -t theft-detection-backend .

# Executar o container
docker run -d \
  --name theft-detection-backend \
  -p 8000:8000 \
  -v $(pwd)/theft_detection.db:/app/theft_detection.db \
  -v $(pwd)/alerts:/app/alerts \
  -v $(pwd)/faces:/app/faces \
  -v $(pwd)/cameras.json:/app/cameras.json \
  -v $(pwd)/settings.json:/app/settings.json \
  theft-detection-backend

# Ver logs
docker logs -f theft-detection-backend

# Parar o container
docker stop theft-detection-backend

# Remover o container
docker rm theft-detection-backend
```

## 🔧 Configuração

### Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e ajuste as configurações:

```bash
cp .env.example .env
```

Edite o arquivo `.env` conforme necessário:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
SMTP_PASSWORD=your_email_password_or_app_password_here
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

### Volumes Persistentes

O Docker Compose está configurado para montar os seguintes volumes:

- `./theft_detection.db` - Banco de dados SQLite
- `./alerts` - Imagens de alertas capturados
- `./faces` - Dados de reconhecimento facial
- `./cameras.json` - Configuração das câmeras
- `./settings.json` - Configurações do sistema

## 🏗️ Arquitetura do Container

```
┌─────────────────────────────────────┐
│   Theft Detection Backend          │
│   (Container)                       │
│                                     │
│   ┌─────────────────────────────┐  │
│   │   FastAPI + Uvicorn         │  │
│   │   Port: 8000                │  │
│   └─────────────────────────────┘  │
│                                     │
│   ┌─────────────────────────────┐  │
│   │   YOLO Detection            │  │
│   │   - Pose Detection          │  │
│   │   - Object Detection        │  │
│   └─────────────────────────────┘  │
│                                     │
│   ┌─────────────────────────────┐  │
│   │   Face Recognition          │  │
│   │   (InsightFace)             │  │
│   └─────────────────────────────┘  │
└─────────────────────────────────────┘
         │                     ▲
         │ WebSocket           │ HTTP API
         │ Video Stream        │ Requests
         ▼                     │
┌─────────────────────────────────────┐
│   Dashboard (Next.js)               │
│   Port: 3000                        │
└─────────────────────────────────────┘
```

## 📊 Monitoramento

### Health Check

O container inclui um health check que verifica o status da API:

```bash
# Ver status do health check
docker inspect --format='{{json .State.Health}}' theft-detection-backend
```

### Logs

```bash
# Ver logs em tempo real
docker-compose logs -f backend

# Ver últimas 100 linhas
docker-compose logs --tail=100 backend

# Ver logs de um período específico
docker-compose logs --since 2h backend
```

### Recursos do Container

```bash
# Ver uso de recursos
docker stats theft-detection-backend

# Ver processos em execução
docker top theft-detection-backend
```

## 🔄 Atualizações

### Atualizar o Backend

```bash
# Parar o serviço
docker-compose down

# Reconstruir a imagem
docker-compose build --no-cache backend

# Iniciar novamente
docker-compose up -d
```

### Rebuild Rápido (sem cache)

```bash
docker-compose build --no-cache && docker-compose up -d
```

## 🐛 Troubleshooting

### Container não inicia

```bash
# Verificar logs de erro
docker-compose logs backend

# Verificar se a porta 8000 está em uso
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/Mac

# Remover containers antigos
docker-compose down -v
```

### Problemas de permissão (Linux)

```bash
# Dar permissões aos diretórios
chmod -R 755 alerts faces
chown -R $(id -u):$(id -g) alerts faces
```

### Modelos YOLO não encontrados

Os scripts `docker-start.ps1` e `docker-start.sh` baixam automaticamente `yolo26x.pt` e `yolo26x-pose.pt` se estiverem ausentes e se esses nomes estiverem configurados no `.env`.

Se você usar nomes diferentes no `.env`, certifique-se de que os arquivos correspondentes estejam no diretório raiz:

```bash
ls -la *.pt
```

### Banco de dados corrompido

```bash
# Backup do banco atual
cp theft_detection.db theft_detection.db.backup

# Reconstruir banco de dados
docker-compose exec backend python migrate_database.py
```

## 🌐 Acesso à API

Após iniciar o container, a API estará disponível em:

- **API Base**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws

### Endpoints principais:

- `GET /api/settings` - Configurações do sistema
- `GET /api/cameras` - Lista de câmeras
- `GET /api/history` - Histórico de detecções
- `GET /api/stats` - Estatísticas do sistema
- `WS /ws` - Stream de vídeo em tempo real

## 🔐 Segurança

### Práticas recomendadas:

1. **Não exponha a porta 8000 publicamente** sem autenticação
2. **Use variáveis de ambiente** para credenciais sensíveis
3. **Mantenha os volumes com permissões adequadas**
4. **Atualize regularmente** as dependências Python

### Executar em rede restrita:

Edite `docker-compose.yml` e remova a exposição de portas:

```yaml
services:
  backend:
    # ... outras configurações
    # Comente ou remova a linha de portas para não expor:
    # ports:
    #   - "8000:8000"
```

## 🚢 Deploy em Produção

### Usando Docker Swarm

```bash
# Inicializar Swarm
docker swarm init

# Deploy como stack
docker stack deploy -c docker-compose.yml theft-detection

# Ver status
docker stack services theft-detection

# Remover stack
docker stack rm theft-detection
```

### Usando Kubernetes

Crie manifestos Kubernetes baseados no Dockerfile fornecido.

## 📝 Notas Adicionais

### Otimizações de Performance

1. **GPU Support**: Para usar GPU com YOLO, use a imagem base `nvidia/cuda` no Dockerfile
2. **Multi-stage Build**: O Dockerfile usa multi-stage build para reduzir o tamanho da imagem final
3. **Cache de Dependências**: As dependências Python são instaladas em camada separada para aproveitar o cache

### Integração com Dashboard

Para executar o dashboard Next.js também em container, descomente a seção `dashboard` no `docker-compose.yml`.

## 🆘 Suporte

Para problemas ou dúvidas:

1. Verifique os logs: `docker-compose logs -f`
2. Consulte a documentação principal: `README.md`
3. Verifique issues conhecidos no repositório

---

**Última atualização**: Maio 2026  
**Versão Docker**: 1.0.0
