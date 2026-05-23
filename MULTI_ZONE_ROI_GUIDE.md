# Sistema de ROI Multi-Zonas - Guia Completo

## Visão Geral

O sistema de detecção de furtos utiliza um avançado mecanismo de **Regiões de Interesse (ROI) multi-zonas** para eliminar falsos positivos e focar a detecção apenas em áreas críticas. Cada câmera pode ter múltiplas zonas polígonais independentes, cada uma com comportamento específico.

## Conceito Fundamental

**Problema Original**: O sistema analisava todo o frame da câmera, gerando alertas para qualquer comportamento suspeito em qualquer lugar - incluindo áreas irrelevantes como corredores, entradas ou áreas de passagem.

**Solução Multi-Zona**: Criação de zonas demarcadas com propósitos diferentes, onde apenas interações dentro das zonas de mercadoria ativam o sistema de pontuação de risco.

## Tipos de Zonas

### 1. Zona de Mercadoria (Merchandise Zone)
**Cor de Identificação**: Amarelo

**Finalidade**: Delimitar prateleiras, displays ou áreas onde produtos ficam expostos.

**Comportamento do Sistema**:
- Apenas pessoas que **interagem** com estas zonas começam a ser pontuadas
- Interação significa: mão dentro da zona OU objeto detectado próximo à mão dentro da zona
- Pessoas que apenas passam perto, mas não interagem, são ignoradas
- Esta é a zona que "ativa" todo o sistema de scoring de risco

**Uso Recomendado**: 
- Desenhe ao redor de cada prateleira de produtos
- Inclua displays de mercadorias
- Não inclua corredores ou áreas de circulação

### 2. Zona Proibida (Forbidden Zone)
**Cor de Identificação**: Vermelho

**Finalidade**: Demarcar áreas onde pessoas absolutamente **não devem estar**.

**Comportamento do Sistema**:
- Qualquer pessoa detectada dentro desta zona gera **alerta imediato**
- Não importa o comportamento ou pontuação - presença = alerta
- Ignora todas as outras regras de scoring
- Alerta classificado automaticamente como alta prioridade

**Uso Recomendado**:
- Áreas de estoque restrito
- Depósitos internos
- Áreas "funcionários apenas"
- Zonas perigosas ou sensíveis

### 3. Zona de Entrada (Entry Zone)
**Cor de Identificação**: Verde

**Finalidade**: Marcar entradas, saídas e áreas de circulação natural.

**Comportamento do Sistema**:
- Pessoas detectadas **apenas** nesta zona **não iniciam pontuação**
- Sistema "aguarda" até a pessoa sair da zona de entrada
- Se pessoa vai direto para mercadoria, aí começa a pontuar
- Evita falsos positivos de pessoas entrando ou apenas passando

**Uso Recomendado**:
- Entrada principal da loja
- Corredores de passagem
- Áreas de circulação entre departamentos
- Proximidade de saídas

## Lógica de Prioridade de Zonas

Quando uma pessoa está em **múltiplas zonas simultaneamente**, a prioridade de processamento é:

**1º - Zona Proibida** (mais alta prioridade)
- Se pessoa está em zona proibida, gera alerta imediato
- Outras zonas são ignoradas

**2º - Zona de Entrada**
- Se pessoa está APENAS em zona de entrada, não pontua
- Bloqueia ativação de scoring

**3º - Zona de Mercadoria**
- Se pessoa interage com esta zona, ativa pontuação
- Demais regras de detecção são aplicadas

## Fluxo de Configuração

### Passo 1: Wizard de Configuração de Detecção
Antes de criar as zonas, você configura **como** o sistema deve se comportar através de um wizard guiado com 8 passos:

1. **Tipos de ROI**: Escolher quais tipos de zona você usará
2. **Gatilho de Mercadoria**: Definir o que conta como "interação"
   - Mão dentro da ROI
   - Objeto detectado próximo à mão na ROI
   - Ambos (mais rigoroso)

3. **Classificação de Bolsas**: Como diferenciar bolsas próprias de produtos roubados
   - Tracking desde chegada
   - Apenas itens rastreados contam como legítimos

4. **Face Oculta**: Diferenciar face oculta (suspeito) de pessoa de costas (normal)
   - Valida se nuca está visível
   - Reduz falsos positivos com pessoas de costas

5. **Supressão de Alça de Bolsa**: Ignorar detecções de mão no peito/axila quando há alça
   - Evita alertas de pessoas mexendo na própria bolsa

6. **Comportamento em Zona de Entrada**: Confirmar que entrada não deve pontuar

7. **Cadeia de Alertas**: Calibrar quando alertar
   - Apenas alertas confirmados (menos sensível)
   - Pré-alertas também geram notificação (mais sensível)

8. **Rótulos de Alerta**: Personalizar mensagens de pré-alerta e alerta confirmado

### Passo 2: Editor Visual de Zonas
Após configurar as regras, você desenha as zonas fisicamente em cada câmera:

**Interface de Edição**:
- **Painel Esquerdo**: Lista de zonas criadas com botões de gerenciamento
  - Nome da zona
  - Tipo da zona (cor identificadora)
  - Botões: Adicionar nova zona, remover zona selecionada

- **Painel Direito**: Canvas do vídeo ao vivo da câmera
  - Clique para adicionar pontos do polígono
  - Mínimo 3 pontos para fechar a zona
  - Zonas renderizadas em tempo real com cores respectivas
  - Como editar: selecione zona existente e redefina pontos

**Coordenadas Normalizadas**:
- Pontos são salvos como porcentagens (0-1) da largura/altura
- Funcionam independente da resolução da câmera
- Redimensionamento da janela não afeta as zonas

## Processamento em Tempo Real

### Etapa 1: Carregamento das Zonas
Ao iniciar o sistema, cada câmera carrega suas zonas salvas:
- Zonas são separadas por tipo (merchandise, forbidden, entry)
- Listas independentes para processamento eficiente
- Pontos convertidos para coordenadas absolutas do frame

### Etapa 2: Detecção de Pessoas
YOLO detecta pessoas no frame:
- Bounding box de cada pessoa
- Keypoints de pose (nariz, ombros, quadris, mãos, etc.)
- Confiança de cada detecção

### Etapa 3: Verificação de Zona Proibida (Prioridade Máxima)
Para cada pessoa detectada:
- Calcula ponto central (bbox ou centroide de pose)
- Verifica se está dentro de **qualquer** zona proibida
- Se SIM: alerta imediato, pula scoring, vai para próxima pessoa
- Se NÃO: continua processamento

### Etapa 4: Verificação de Zona de Entrada
Se pessoa não está em zona proibida:
- Verifica se está **apenas** em zonas de entrada
- Se SIM: marca como "em trânsito", não pontua, monitora posição
- Se NÃO: continua processamento

### Etapa 5: Verificação de Interação com Mercadoria
Esta é a etapa crítica que **ativa ou bloqueia** todo o scoring:

**Verificações Realizadas**:
1. Detecta posição das mãos da pessoa
2. Verifica se alguma mão está dentro de zona de mercadoria
3. Se detecção de objetos ativa: verifica se objetos próximos às mãos estão na zona
4. Se configurado "ambos": exige mão E objeto na zona

**Resultado**:
- **Interação Detectada**: Pessoa "entra no radar" - começa pontuação de risco
- **Sem Interação**: Pessoa ignorada, mesmo que esteja no frame

### Etapa 6: Scoring de Risco (Apenas se Interação Confirmada)
Apenas pessoas que interagiram com mercadoria são analisadas:

**Fatores Avaliados**:
- Pose suspeita (agachado, inclinado anormalmente)
- Movimentos rápidos de mãos
- Face oculta (validando nuca se configurado)
- Proximidade com objetos detectados
- Tempo de interação
- Histórico de comportamento (tracking)

**Pontuação Acumulada**:
- Cada fator adiciona pontos
- Sistema de limiar duplo:
  - Pré-alerta: comportamento suspeito inicial
  - Alerta confirmado: múltiplos fatores + persistência temporal

### Etapa 7: Geração de Alertas
Com base na pontuação e configuração:

**Se Cadeia de Alertas = "Apenas Confirmados"**:
- Apenas alertas de alto risco geram notificação
- Reduz ruído, mas pode perder casos limítrofes

**Se Cadeia de Alertas = "Incluir Pré-Alertas"**:
- Pré-alertas também notificam operador
- Permite intervenção preventiva
- Mais notificações, mas maior cobertura

**Metadata do Alerta**:
- Timestamp exato
- ID da câmera e nome
- Snapshot da pessoa
- Pontuação de risco
- Zona(s) envolvida(s)
- Rótulo personalizado (do wizard)

## Renderização Visual

### No Vídeo ao Vivo (Dashboard)
- Cada zona é desenhada como polígono sobre o frame
- Cores consistentes: amarelo (merchandise), vermelho (forbidden), verde (entry)
- Nome da zona exibido no canto superior esquerdo do polígono
- Pessoas sendo rastreadas têm bounding box colorida conforme risco
- Keypoints de pose visíveis para debugging

### Performance Otimizada
Para garantir fluidez no dashboard com múltiplas câmeras:
- Frames redimensionados para 50% da resolução original antes de envio
- Qualidade JPEG reduzida para 45% (balanço qualidade/tamanho)
- Taxa de atualização de 10 FPS via WebSocket
- Componente React memoizado - só re-renderiza se frame mudou
- Redução total de ~75% no tráfego de dados

## Fluxo Completo: Da Configuração ao Alerta

1. **Operador acessa Dashboard** → Abre página de Câmeras
2. **Configura Detecção via Wizard** → Define regras de comportamento
3. **Edita Zonas por Câmera** → Desenha polígonos específicos
4. **Salva Configuração** → Backend persiste em cameras.json
5. **Sistema Reinicia ou Recarrega** → Zonas são carregadas na memória
6. **Vídeo ao Vivo Inicia** → Loop de processamento começa
7. **Pessoa Entra no Frame** → YOLO detecta pessoa
8. **Verifica Zona Proibida** → Se dentro, alerta imediato e fim
9. **Verifica Zona de Entrada** → Se apenas entrada, aguarda movimento
10. **Pessoa Interage com Mercadoria** → Mão toca zona amarela
11. **Ativa Scoring** → Sistema começa pontuação de risco
12. **Acumula Pontos** → Comportamento suspeito + tempo
13. **Atinge Limiar** → Pré-alerta ou alerta confirmado
14. **Operador Recebe Notificação** → Dashboard + banco de dados
15. **Operador Revisa** → Decide ação (ignorar, observar, intervir)

## Diferencial do Sistema Multi-Zona

### Antes (Sistema Tradicional)
- Uma única ROI por câmera
- Tudo dentro da ROI é analisado igualmente
- Muitos falsos positivos em áreas de circulação
- Difícil calibrar sensibilidade (ou muito ou pouco sensível)

### Depois (Sistema Multi-Zona)
- Múltiplas zonas com comportamentos diferentes
- Análise contextual: "onde" a pessoa está importa
- Falsos positivos drasticamente reduzidos
- Calibração granular por tipo de área
- Operador define estratégia de monitoramento

## Casos de Uso Práticos

### Supermercado Pequeno
- **3 zonas de mercadoria**: Prateleira bebidas, prateleira alimentos, balcão checkout
- **1 zona proibida**: Porta do depósito
- **1 zona de entrada**: Porta principal + corredor de entrada
- **Resultado**: Sistema só alerta em interações com produtos, ignora clientes entrando

### Loja de Eletrônicos
- **5 zonas de mercadoria**: Cada expositor de produtos de alto valor
- **2 zonas proibidas**: Almoxarifado e sala de funcionários
- **2 zonas de entrada**: Porta principal e acesso ao banheiro
- **Resultado**: Alta precisão em produtos caros, sem alertas em áreas comuns

### Farmácia
- **4 zonas de mercadoria**: Prateleiras de cosméticos e medicamentos OTC
- **1 zona proibida**: Área de medicamentos controlados (acesso restrito)
- **1 zona de entrada**: Porta de entrada
- **Resultado**: Alertas focados em áreas de maior risco de furto

### Conveniência 24h
- **6 zonas de mercadoria**: Todas as prateleiras de produtos expostos
- **1 zona proibida**: Acesso aos fundos
- **1 zona de entrada**: Porta automática
- **Configuração especial**: "Incluir pré-alertas" para máxima sensibilidade em período noturno
- **Resultado**: Cobertura completa com intervenção preventiva

## Manutenção e Ajustes

### Quando Re-configurar Zonas
- Layout da loja mudou
- Adição/remoção de prateleiras
- Mudança de categoria de produtos (mercadoria para proibido)
- Falsos positivos persistentes em área específica

### Quando Ajustar Configuração do Wizard
- Taxa de falsos positivos muito alta → Aumentar rigor (exigir "ambos")
- Taxa de falsos negativos (furtos não detectados) → Incluir pré-alertas
- Clientes reclamando de abordagens → Revisar zonas de mercadoria (podem estar grandes demais)

### Monitoramento de Eficácia
- Dashboard mostra histórico de alertas por zona
- Operador identifica zonas com mais falsos positivos
- Ajusta tamanho/posição da zona ou configuração de sensibilidade
- Ciclo iterativo de otimização

## Considerações Técnicas

### Precisão Geométrica
- Algoritmo de "ponto dentro do polígono" com ray-casting
- Funciona com polígonos convexos e côncavos
- Tolerante a formatos irregulares
- Custo computacional: O(n) onde n = número de pontos

### Tracking Multi-Frame
- Pessoas recebem ID único ao entrar no frame
- Estado de "em qual zona está" é rastreado ao longo do tempo
- Histórico de pontuação persiste enquanto pessoa visível
- Re-identificação após oclusão temporária

### Escalabilidade
- Sistema processa múltiplas câmeras em paralelo
- Cada câmera tem thread dedicada
- Zonas carregadas uma vez na inicialização
- Detecção otimizada com GPU (se disponível)

## Conclusão

O sistema de ROI multi-zonas transforma um detector genérico de comportamentos em uma solução **contextualmente inteligente**, onde a localização espacial da pessoa define completamente como ela será analisada. Isso reduz dramaticamente falsos positivos enquanto mantém alta sensibilidade nas áreas críticas - o equilíbrio perfeito para segurança comercial efetiva.
