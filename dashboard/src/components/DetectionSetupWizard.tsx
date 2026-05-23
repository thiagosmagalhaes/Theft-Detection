"use client";

import { useState } from "react";
import {
  X,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  ShoppingBag,
  Eye,
  MapPin,
  Bell,
  Tag,
  Shield,
  Sliders,
  Save,
  AlertTriangle,
  Info,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface DetectionConfig {
  // Q1 – ROI types per camera
  roiTypes: {
    merchandiseZone: boolean;
    forbiddenZone: boolean;
    entryCounterZone: boolean;
  };

  // Q2 – What activates "person interacted with merchandise"
  merchandiseTrigger: "hand_in_roi" | "object_near_hand" | "both";

  // Q3 – How to handle bags the person arrived with
  bagClassification: "arrival_frames" | "always_personal" | "only_if_tracked_item";
  bagArrivalFrames: number; // only used when bagClassification === "arrival_frames"

  // Q4 – What to do when face is not detected (helmet, mask, low light)
  hiddenFaceBehavior: "ignore" | "half_weight" | "only_if_nape";

  // Q5 – Suppress chest/armpit when bag strap crosses torso
  bagStrapSuppression: "full" | "half" | "none";

  // Q6 – How to treat people in entry/counter zone
  entryZoneBehavior: "no_score" | "half_score" | "ignore_completely";

  // Q7 – What triggers ALERT (maximum level)
  alertChain: "confirmed_chain_only" | "confirmed_chain_or_high_score" | "recalibrate_weights";
  highScoreThreshold: number; // used when alertChain !== "confirmed_chain_only"

  // Q8 – Label shown before confirmed theft chain
  preAlertLabel: "atencao_revisar" | "comportamento_suspeito" | "monitorar" | "suspeito";
  confirmedAlertLabel: "furto_detectado" | "ocultacao_confirmada" | "revisar_urgente";
}

const DEFAULT_CONFIG: DetectionConfig = {
  roiTypes: { merchandiseZone: true, forbiddenZone: false, entryCounterZone: true },
  merchandiseTrigger: "hand_in_roi",
  bagClassification: "only_if_tracked_item",
  bagArrivalFrames: 30,
  hiddenFaceBehavior: "only_if_nape",
  bagStrapSuppression: "full",
  entryZoneBehavior: "no_score",
  alertChain: "confirmed_chain_only",
  highScoreThreshold: 2.0,
  preAlertLabel: "atencao_revisar",
  confirmedAlertLabel: "ocultacao_confirmada",
};

// ─── Sub-components ──────────────────────────────────────────────────────────

function OptionCard({
  selected,
  onClick,
  children,
  recommended,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  recommended?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 relative ${
        selected
          ? "border-brand bg-brand/15 shadow-[0_0_0_1px_rgba(59,130,246,0.3)]"
          : "border-white/8 bg-white/3 hover:border-white/20 hover:bg-white/6"
      }`}
    >
      {recommended && (
        <span className="absolute top-2 right-2 text-[10px] font-semibold bg-brand/20 text-brand px-2 py-0.5 rounded-full border border-brand/30">
          Recomendado
        </span>
      )}
      <div className="flex items-start gap-3">
        <div
          className={`mt-0.5 w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
            selected ? "border-brand bg-brand" : "border-white/30"
          }`}
        >
          {selected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
        </div>
        <div>{children}</div>
      </div>
    </button>
  );
}

function CheckCard({
  checked,
  onClick,
  children,
}: {
  checked: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
        checked
          ? "border-brand bg-brand/15"
          : "border-white/8 bg-white/3 hover:border-white/20 hover:bg-white/6"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`mt-0.5 w-4 h-4 rounded-md border-2 flex-shrink-0 flex items-center justify-center ${
            checked ? "border-brand bg-brand" : "border-white/30"
          }`}
        >
          {checked && (
            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
        <div>{children}</div>
      </div>
    </button>
  );
}

function InfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2 p-3 rounded-lg bg-blue-500/8 border border-blue-500/20 text-blue-300/80 text-xs leading-relaxed">
      <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-400" />
      <span>{children}</span>
    </div>
  );
}

function WarningBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2 p-3 rounded-lg bg-amber-500/8 border border-amber-500/20 text-amber-300/80 text-xs leading-relaxed">
      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
      <span>{children}</span>
    </div>
  );
}

// ─── Step definitions ────────────────────────────────────────────────────────

const STEPS = [
  { id: "roi_types",       icon: MapPin,      title: "Tipos de ROI por Câmera" },
  { id: "merch_trigger",   icon: ShoppingBag, title: "Ativação de Mercadoria" },
  { id: "bag_class",       icon: ShoppingBag, title: "Classificação de Bolsas" },
  { id: "hidden_face",     icon: Eye,         title: "Rosto Oculto vs De Costas" },
  { id: "bag_strap",       icon: Shield,      title: "Alça de Bag no Tronco" },
  { id: "entry_zone",      icon: MapPin,      title: "Zona de Entrada / Balcão" },
  { id: "alert_chain",     icon: Sliders,     title: "Calibração de Alertas" },
  { id: "alert_labels",    icon: Bell,        title: "Rótulos de Alerta" },
];

// ─── Main component ──────────────────────────────────────────────────────────

interface Props {
  onClose: () => void;
  onSave: (config: DetectionConfig) => void;
  initialConfig?: Partial<DetectionConfig>;
  apiBaseUrl: string;
}

export default function DetectionSetupWizard({ onClose, onSave, initialConfig, apiBaseUrl }: Props) {
  const [step, setStep] = useState(0);
  const [config, setConfig] = useState<DetectionConfig>({ ...DEFAULT_CONFIG, ...initialConfig });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof DetectionConfig>(key: K, value: DetectionConfig[K]) =>
    setConfig((prev) => ({ ...prev, [key]: value }));

  const setRoiType = (key: keyof DetectionConfig["roiTypes"], value: boolean) =>
    setConfig((prev) => ({ ...prev, roiTypes: { ...prev.roiTypes, [key]: value } }));

  const canGoNext = () => {
    if (step === 0) return config.roiTypes.merchandiseZone; // at least merchandise zone required
    return true;
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl}/detection-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      setSaved(true);
      onSave(config);
      setTimeout(onClose, 1200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setSaving(false);
    }
  };

  // ── Render step content ───────────────────────────────────────────────────

  const renderStep = () => {
    switch (STEPS[step].id) {

      // ── Q1: ROI Types ────────────────────────────────────────────────────
      case "roi_types":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Defina quais tipos de polígono você quer desenhar em cada câmera.
              Cada câmera pode ter <strong className="text-foreground/90">múltiplos ROIs</strong> de tipos diferentes.
            </p>
            <InfoBox>
              O tipo determina o comportamento: entrar na <em>Zona Proibida</em> gera alerta imediato; 
              entrar na <em>Área de Mercadoria</em> ativa o scoring de ocultação; 
              a <em>Zona de Entrada/Balcão</em> neutraliza o scoring (entregadores, clientes na fila).
            </InfoBox>
            <div className="space-y-3 mt-2">
              <CheckCard
                checked={config.roiTypes.merchandiseZone}
                onClick={() => setRoiType("merchandiseZone", !config.roiTypes.merchandiseZone)}
              >
                <p className="font-semibold text-sm text-foreground">
                  🛍️ Área de Mercadoria
                  <span className="ml-2 text-[10px] bg-red-500/20 text-red-400 border border-red-400/30 px-1.5 py-0.5 rounded-full font-semibold">OBRIGATÓRIO</span>
                </p>
                <p className="text-xs text-foreground/50 mt-1">
                  Só depois que a mão entrar aqui o scoring de ocultação (bolso, peito, bag…) fica ativo.
                  Sem interação com este polígono, esconder a mão no corpo não conta.
                </p>
              </CheckCard>

              <CheckCard
                checked={config.roiTypes.forbiddenZone}
                onClick={() => setRoiType("forbiddenZone", !config.roiTypes.forbiddenZone)}
              >
                <p className="font-semibold text-sm text-foreground">🚫 Zona Proibida</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Qualquer pessoa que entrar neste polígono gera alerta imediato (ex: área de estoque,
                  fundo da loja restrito). Não precisa de interação com mercadoria.
                </p>
              </CheckCard>

              <CheckCard
                checked={config.roiTypes.entryCounterZone}
                onClick={() => setRoiType("entryCounterZone", !config.roiTypes.entryCounterZone)}
              >
                <p className="font-semibold text-sm text-foreground">🚪 Zona de Entrada / Balcão</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Pessoas nesta área não recebem nenhuma pontuação de risco. Ideal para demarcar
                  a porta de entrada, fila do caixa ou balcão de atendimento — elimina falso positivo
                  com motoboy e entregadores.
                </p>
              </CheckCard>
            </div>
            {!config.roiTypes.merchandiseZone && (
              <WarningBox>
                A Área de Mercadoria é obrigatória — sem ela, toda a lógica de "pegou item → escondeu"
                fica desativada e o sistema não consegue distinguir furto de comportamento normal.
              </WarningBox>
            )}
          </div>
        );

      // ── Q2: Merchandise trigger ──────────────────────────────────────────
      case "merch_trigger":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Quando considerar que a pessoa <strong className="text-foreground/90">"interagiu com mercadoria"</strong>{" "}
              e liberar o scoring de ocultação?
            </p>
            <InfoBox>
              Esta é a trava principal contra falsos positivos. Enquanto a condição não for satisfeita,
              gestos de ocultação (bolso, peito, bag, axila) têm peso zero.
            </InfoBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.merchandiseTrigger === "hand_in_roi"}
                onClick={() => set("merchandiseTrigger", "hand_in_roi")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">📍 Mão dentro do polígono de mercadoria</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Ativado quando o keypoint do punho cruza a fronteira da Área de Mercadoria.
                  Mais preciso e direto — a câmera viu a mão no local.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.merchandiseTrigger === "object_near_hand"}
                onClick={() => set("merchandiseTrigger", "object_near_hand")}
              >
                <p className="font-semibold text-sm text-foreground">📦 Objeto detectado próximo da mão dentro da área</p>
                <p className="text-xs text-foreground/50 mt-1">
                  O detector YOLO encontra um objeto (produto) perto do punho da pessoa enquanto ela
                  está na área monitorada. Exige que o detector de objetos funcione bem.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.merchandiseTrigger === "both"}
                onClick={() => set("merchandiseTrigger", "both")}
              >
                <p className="font-semibold text-sm text-foreground">🔗 Ambos (mão no ROI OU objeto próximo)</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Qualquer um dos dois critérios basta. Mais sensível, pode gerar mais alertas.
                  Use apenas se as câmeras e o detector de objetos forem de alta qualidade.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q3: Bag classification ───────────────────────────────────────────
      case "bag_class":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Uma mochila/bolsa que a pessoa <strong className="text-foreground/90">trouxe de casa</strong> não é
              esconderijo — é propriedade dela. Como o sistema deve distinguir?
            </p>
            <InfoBox>
              Hoje, qualquer "mão na bolsa" pontua como suspeito. Isso gera falso positivo com todo
              cliente que usa mochila. A correção é classificar bolsas por origem antes de pontuar.
            </InfoBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.bagClassification === "only_if_tracked_item"}
                onClick={() => set("bagClassification", "only_if_tracked_item")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">🎯 Só pontuar se objeto rastreado foi para dentro da bolsa</p>
                <p className="text-xs text-foreground/50 mt-1">
                  hand_in_bag_zone só conta se uma mão <em>levou um item detectado</em> da loja para dentro
                  da bolsa. Mão indo à mochila sem objeto → ignorado. Elimina praticamente todos os
                  falsos positivos com mochileiros.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.bagClassification === "arrival_frames"}
                onClick={() => set("bagClassification", "arrival_frames")}
              >
                <p className="font-semibold text-sm text-foreground">⏱️ Bolsas presentes nos primeiros N frames são pessoais</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Uma bolsa detectada nos primeiros <strong className="text-foreground/80">{config.bagArrivalFrames}</strong>{" "}
                  frames após a pessoa aparecer é marcada como pessoal e ignorada pelo scoring.
                </p>
                {config.bagClassification === "arrival_frames" && (
                  <div className="mt-3">
                    <label className="text-xs text-foreground/60 font-medium">Frames de chegada:</label>
                    <div className="flex items-center gap-3 mt-1">
                      <input
                        type="range"
                        min={10}
                        max={90}
                        step={5}
                        value={config.bagArrivalFrames}
                        onChange={(e) => set("bagArrivalFrames", Number(e.target.value))}
                        className="flex-1 accent-brand"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="text-sm font-mono text-brand w-8 text-center">
                        {config.bagArrivalFrames}
                      </span>
                    </div>
                    <p className="text-[10px] text-foreground/40 mt-1">
                      ≈ {(config.bagArrivalFrames / 15).toFixed(1)}s em 15fps
                    </p>
                  </div>
                )}
              </OptionCard>

              <OptionCard
                selected={config.bagClassification === "always_personal"}
                onClick={() => set("bagClassification", "always_personal")}
              >
                <p className="font-semibold text-sm text-foreground">🚫 Nunca pontuar hand_in_bag</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Desativa completamente o evento de "mão na bolsa". Escolha esta opção se sua loja
                  tem muitos clientes com mochilas e o detector de objetos é impreciso.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q4: Hidden face ──────────────────────────────────────────────────
      case "hidden_face":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Capacete, máscara ou pouca luz escondem o rosto <strong className="text-foreground/90">sem a pessoa
              estar de costas</strong>. Hoje o sistema confunde os dois. Como resolver?
            </p>
            <WarningBox>
              O problema atual: <code className="font-mono bg-white/8 px-1 rounded">is_person_facing_away</code> retorna
              True quando o nariz/olhos não são detectados — inclusive para capacetes e câmeras escuras.
              Isso faz motoboys virarem "suspeitos de costas".
            </WarningBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.hiddenFaceBehavior === "only_if_nape"}
                onClick={() => set("hiddenFaceBehavior", "only_if_nape")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">🧠 Só "de costas" se nuca visível (ombros + orelhas)</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Considera "de costas" apenas quando: face não detectada E ombros paralelos à câmera
                  (horizontal) E pelo menos uma orelha visível mas nariz não. Capacetes nunca disparam
                  facing_away porque as orelhas também ficam ocultas. É o método mais preciso.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.hiddenFaceBehavior === "ignore"}
                onClick={() => set("hiddenFaceBehavior", "ignore")}
              >
                <p className="font-semibold text-sm text-foreground">🔕 Ignorar completamente quando rosto não detectado</p>
                <p className="text-xs text-foreground/50 mt-1">
                  facing_away_hands_at_body nunca dispara se os keypoints faciais estiverem ausentes.
                  Elimina falsos positivos com capacetes/câmeras noturnas, mas perde detecções legítimas
                  de pessoa de costas com casaco/capuz.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.hiddenFaceBehavior === "half_weight"}
                onClick={() => set("hiddenFaceBehavior", "half_weight")}
              >
                <p className="font-semibold text-sm text-foreground">⚖️ Peso reduzido quando rosto oculto</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Quando a face não é detectada, o evento facing_away pontua com 25% do peso normal
                  em vez de 100%. Equilibra sensibilidade e falsos positivos.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q5: Bag strap suppression ────────────────────────────────────────
      case "bag_strap":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Um entregador com <strong className="text-foreground/90">mochila transversal</strong> tem a alça
              cruzando o peito o tempo todo. Hoje as zonas chest e armpit pontuam mesmo assim.
            </p>
            <InfoBox>
              Quando uma bolsa detectada cruza a linha vertical do tronco (caixa da bolsa sobrepõe a região
              entre ombros e quadril no eixo X), a mão provavelmente está na alça — não escondendo nada.
            </InfoBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.bagStrapSuppression === "full"}
                onClick={() => set("bagStrapSuppression", "full")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">❌ Suprimir completamente chest e armpit</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Se uma bag cruzar o tronco, as zonas chest e armpit ficam com peso zero para aquela
                  pessoa. Elimina falso positivo com entregadores sem perder detecções em quem não tem bag.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.bagStrapSuppression === "half"}
                onClick={() => set("bagStrapSuppression", "half")}
              >
                <p className="font-semibold text-sm text-foreground">⚖️ Reduzir peso para 50%</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Meia supressão — ainda pontua um pouco se a mão ficar muito tempo na zona, mas
                  não o suficiente para gerar alerta isolado.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.bagStrapSuppression === "none"}
                onClick={() => set("bagStrapSuppression", "none")}
              >
                <p className="font-semibold text-sm text-foreground">✅ Não suprimir</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Mantém o comportamento atual. Escolha apenas se sua loja não tem entregadores ou
                  clientes com mochilas transversais.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q6: Entry zone behavior ──────────────────────────────────────────
      case "entry_zone":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              A <strong className="text-foreground/90">Zona de Entrada/Balcão</strong> serve para ignorar
              motoboys, entregadores, clientes aguardando — pessoas que estão visivelmente
              no local sem intenção de circular pelos produtos.
            </p>
            <InfoBox>
              Esta zona desativa o scoring enquanto a pessoa permanecer dentro dela. Assim que ela
              se mover para a área de mercadoria, o scoring é ativado normalmente (mas ainda precisa
              da interação com o ROI de mercadoria para liberar ocultação).
            </InfoBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.entryZoneBehavior === "no_score"}
                onClick={() => set("entryZoneBehavior", "no_score")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">🔇 Sem pontuação na zona de entrada</p>
                <p className="text-xs text-foreground/50 mt-1">
                  A pessoa é rastreada mas todos os eventos de risco têm peso zero enquanto ela
                  estiver nesta zona. Se ela sair para a área de mercadoria, o histórico de risco
                  continua do zero (não carrega pontuação acumulada).
                </p>
              </OptionCard>

              <OptionCard
                selected={config.entryZoneBehavior === "half_score"}
                onClick={() => set("entryZoneBehavior", "half_score")}
              >
                <p className="font-semibold text-sm text-foreground">⚖️ Pontuação 50% na zona de entrada</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Ainda acumula risco, mas na metade da taxa. Útil se a zona de entrada tem prateleiras
                  próximas e você quer continuar monitorando parcialmente.
                </p>
              </OptionCard>

              <OptionCard
                selected={config.entryZoneBehavior === "ignore_completely"}
                onClick={() => set("entryZoneBehavior", "ignore_completely")}
              >
                <p className="font-semibold text-sm text-foreground">👁️‍🗨️ Ignorar completamente (não rastrear)</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Pessoas detectadas apenas nesta zona não aparecem no sistema. Mais agressivo —
                  se a pessoa se mover para a área de mercadoria ela começa do zero sem histórico.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q7: Alert chain ──────────────────────────────────────────────────
      case "alert_chain":
        return (
          <div className="space-y-4">
            <p className="text-sm text-foreground/60 leading-relaxed">
              O que deve acionar o nível máximo de alerta (<strong className="text-foreground/90">ALERT</strong>)?
              Hoje sinais médios empilhados (scanning + loitering + bag) conseguem chegar a ALERT sozinhos.
            </p>
            <WarningBox>
              Com calibração atual: scanning (0.25) + facing_away (0.30) + loitering (0.35) + bag_nearby = ~0.90 — próximo
              do threshold de ALERT (1.2). Somar com decay lento e a pessoa vira suspeita sem nunca ter tocado em nada.
            </WarningBox>
            <div className="space-y-3 mt-2">
              <OptionCard
                selected={config.alertChain === "confirmed_chain_only"}
                onClick={() => set("alertChain", "confirmed_chain_only")}
                recommended
              >
                <p className="font-semibold text-sm text-foreground">🔐 Somente cadeia confirmada chega a ALERT</p>
                <p className="text-xs text-foreground/50 mt-1">
                  ALERT só é acionado quando a cadeia completa ocorre:{" "}
                  <em>pegou mercadoria → levou ao corpo → objeto sumiu</em>. Sinais médios sozinhos
                  cap em MEDIUM (0.8). Escanear + loitar + bag = no máximo "Observar".
                </p>
              </OptionCard>

              <OptionCard
                selected={config.alertChain === "confirmed_chain_or_high_score"}
                onClick={() => set("alertChain", "confirmed_chain_or_high_score")}
              >
                <p className="font-semibold text-sm text-foreground">🔀 Cadeia confirmada OU score muito alto</p>
                <p className="text-xs text-foreground/50 mt-1">
                  ALERT também é acionado se o score acumulado ultrapassar{" "}
                  <strong className="text-foreground/80">{config.highScoreThreshold.toFixed(1)}</strong>, mesmo
                  sem cadeia confirmada. Permite capturar padrões atípicos não cobertos pela cadeia.
                </p>
                {config.alertChain === "confirmed_chain_or_high_score" && (
                  <div className="mt-3">
                    <label className="text-xs text-foreground/60 font-medium">Threshold de score alto:</label>
                    <div className="flex items-center gap-3 mt-1">
                      <input
                        type="range"
                        min={1.4}
                        max={3.0}
                        step={0.1}
                        value={config.highScoreThreshold}
                        onChange={(e) => set("highScoreThreshold", Number(e.target.value))}
                        className="flex-1 accent-brand"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="text-sm font-mono text-brand w-8 text-center">
                        {config.highScoreThreshold.toFixed(1)}
                      </span>
                    </div>
                  </div>
                )}
              </OptionCard>

              <OptionCard
                selected={config.alertChain === "recalibrate_weights"}
                onClick={() => set("alertChain", "recalibrate_weights")}
              >
                <p className="font-semibold text-sm text-foreground">🎚️ Recalibrar pesos mantendo threshold atual</p>
                <p className="text-xs text-foreground/50 mt-1">
                  Reduz os pesos de sinais médios (scanning, loitering, facing_away, bag_nearby) para que
                  nunca alcancem ALERT isolados, mas mantém o sistema de score contínuo. Menos disruptivo
                  que a cadeia obrigatória.
                </p>
              </OptionCard>
            </div>
          </div>
        );

      // ── Q8: Alert labels ─────────────────────────────────────────────────
      case "alert_labels":
        return (
          <div className="space-y-5">
            <p className="text-sm text-foreground/60 leading-relaxed">
              Em CCTV de loja, alertas são para <strong className="text-foreground/90">revisão humana</strong>,
              não acusação automática. Rotular tudo como "Furto Detectado" gera problema
              com clientes inocentes e entregadores.
            </p>

            <div>
              <h4 className="text-xs font-semibold text-foreground/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5" />
                Rótulo para alertas antes da cadeia confirmada
              </h4>
              <div className="space-y-2">
                {(
                  [
                    { v: "atencao_revisar",        label: "⚠️ Atenção / Revisar",          desc: "Neutro e profissional — indica que algo merece atenção humana." },
                    { v: "comportamento_suspeito",  label: "🔍 Comportamento Suspeito",     desc: "Mais direto mas não acusa. Bom para sistemas de segurança internos." },
                    { v: "monitorar",               label: "👁️ Monitorar",                  desc: "Mínimo impacto — só pede que o operador mantenha atenção." },
                    { v: "suspeito",                label: "⚠️ Suspeito",                   desc: "Curto, mas pode soar como acusação se exibido em lugar errado." },
                  ] as const
                ).map(({ v, label, desc }) => (
                  <OptionCard
                    key={v}
                    selected={config.preAlertLabel === v}
                    onClick={() => set("preAlertLabel", v)}
                    recommended={v === "atencao_revisar"}
                  >
                    <p className="font-semibold text-sm text-foreground">{label}</p>
                    <p className="text-xs text-foreground/50 mt-0.5">{desc}</p>
                  </OptionCard>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-foreground/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Bell className="w-3.5 h-3.5" />
                Rótulo quando a cadeia completa é confirmada
              </h4>
              <div className="space-y-2">
                {(
                  [
                    { v: "furto_detectado",     label: "🚨 Furto Detectado",         desc: "Direto, mas use apenas quando o sistema for confiável o suficiente." },
                    { v: "ocultacao_confirmada", label: "📦 Ocultação Confirmada",    desc: "Mais preciso tecnicamente — descreve o que o sistema viu, não acusa." },
                    { v: "revisar_urgente",     label: "🔴 Revisar Urgente",          desc: "Chama atenção sem acusar. Recomendado para ambientes com público." },
                  ] as const
                ).map(({ v, label, desc }) => (
                  <OptionCard
                    key={v}
                    selected={config.confirmedAlertLabel === v}
                    onClick={() => set("confirmedAlertLabel", v)}
                    recommended={v === "ocultacao_confirmada"}
                  >
                    <p className="font-semibold text-sm text-foreground">{label}</p>
                    <p className="text-xs text-foreground/50 mt-0.5">{desc}</p>
                  </OptionCard>
                ))}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const isLastStep = step === STEPS.length - 1;
  const StepIcon = STEPS[step].icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl max-h-[92vh] glass-panel flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/8 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-brand/20 text-brand">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Configuração de Detecção</h2>
              <p className="text-xs text-foreground/50">
                Passo {step + 1} de {STEPS.length} — {STEPS[step].title}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/8 transition-colors text-foreground/50 hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-white/8 flex-shrink-0">
          <div
            className="h-full bg-brand transition-all duration-300 rounded-full"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        {/* Step tabs */}
        <div className="flex gap-1 px-4 pt-3 pb-0 overflow-x-auto flex-shrink-0 scrollbar-none">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                title={s.title}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                  i === step
                    ? "bg-brand/20 text-brand border border-brand/30"
                    : i < step
                    ? "bg-green-500/10 text-green-400 border border-green-500/20"
                    : "text-foreground/40 hover:text-foreground/70 border border-transparent"
                }`}
              >
                {i < step ? (
                  <CheckCircle className="w-3.5 h-3.5" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
                <span className="hidden sm:inline">{s.title}</span>
                <span className="sm:hidden">{i + 1}</span>
              </button>
            );
          })}
        </div>

        {/* Step title */}
        <div className="px-6 pt-4 pb-2 flex-shrink-0">
          <div className="flex items-center gap-2">
            <StepIcon className="w-5 h-5 text-brand" />
            <h3 className="text-base font-semibold text-foreground">{STEPS[step].title}</h3>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-4">
          {renderStep()}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/8 flex-shrink-0 bg-white/2">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 text-sm font-medium text-foreground/60 hover:text-foreground hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Anterior
          </button>

          <div className="flex items-center gap-2">
            {error && (
              <span className="text-xs text-red-400 max-w-[200px] truncate">{error}</span>
            )}
            {saved && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="w-3.5 h-3.5" /> Salvo!
              </span>
            )}
            {isLastStep ? (
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-brand text-white text-sm font-semibold hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-lg shadow-brand/25"
              >
                {saving ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Salvar Configuração
              </button>
            ) : (
              <button
                onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
                disabled={!canGoNext()}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-brand text-white text-sm font-semibold hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Próximo
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
