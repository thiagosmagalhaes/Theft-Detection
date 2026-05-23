"""
pose_analysis.py
================
Análise de pose (YOLO keypoints) para detecção de comportamento suspeito de
furto em supermercado / loja.

Cobre os principais padrões de furto:
  - Pegar mercadoria na prateleira (ROI) e levar ao corpo
  - Esconder no bolso (calça / jaqueta)
  - Esconder na cintura / por dentro da roupa (waistband / inside clothing)
  - Esconder no peito / por baixo da blusa
  - Esconder na axila / por dentro do casaco
  - Colocar dentro de bolsa / mochila
  - Esconder na meia / bota (agachando) — "boosting"
  - Olhar excessivamente para os lados (procurando funcionário / câmera)
  - Virar de costas para a câmera com as mãos na frente do corpo
  - Sumiço do objeto da mão junto ao corpo (concealment confirmado)

A lógica final NÃO é binária: usa um SISTEMA DE PONTUAÇÃO (risk score) por
pessoa, acumulado ao longo do tempo, o que reduz drasticamente falsos alarmes.
Cada gesto isolado (ex: encostar no bolso) soma pouco; a SEQUÊNCIA típica de
furto (pegar mercadoria -> levar ao corpo -> objeto some) soma muito.

Indices COCO-17 (padrão YOLOv8-pose):
0 nose | 1 left_eye 2 right_eye | 3 left_ear 4 right_ear
5 left_shoulder 6 right_shoulder | 7 left_elbow 8 right_elbow
9 left_wrist 10 right_wrist | 11 left_hip 12 right_hip
13 left_knee 14 right_knee | 15 left_ankle 16 right_ankle

Cada keypoint = [x, y] ou [x, y, confidence].
"""

import cv2
import numpy as np
from collections import deque

# ---------------------------------------------------------------------------
# Índices de keypoints (COCO-17)
# ---------------------------------------------------------------------------
NOSE = 0
L_EYE, R_EYE = 1, 2
L_EAR, R_EAR = 3, 4
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

DEFAULT_CONF = 0.3


# ---------------------------------------------------------------------------
# Helpers de baixo nível
# ---------------------------------------------------------------------------
def _kp(keypoints, idx):
    """Retorna (x, y, conf) de um keypoint de forma segura. conf=1.0 se ausente."""
    if keypoints is None or idx >= len(keypoints):
        return (0.0, 0.0, 0.0)
    p = keypoints[idx]
    x = float(p[0])
    y = float(p[1])
    c = float(p[2]) if len(p) > 2 else 1.0
    return (x, y, c)


def _visible(point, conf_thr=DEFAULT_CONF):
    """Keypoint é considerado visível se tem coordenada válida e confiança ok."""
    x, y, c = point
    return x > 0 and y > 0 and c >= conf_thr


def _dist(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _center(keypoints, idxs, conf_thr=DEFAULT_CONF):
    """Centro (média) dos keypoints visíveis em idxs. Retorna None se nenhum visível."""
    pts = [_kp(keypoints, i) for i in idxs]
    vis = [(p[0], p[1]) for p in pts if _visible(p, conf_thr)]
    if not vis:
        return None
    xs = [p[0] for p in vis]
    ys = [p[1] for p in vis]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def body_scale(keypoints, conf_thr=DEFAULT_CONF):
    """
    Escala corporal em pixels, usada para tornar os limiares INDEPENDENTES da
    distância da pessoa à câmera (pessoa perto = corpo grande, longe = pequeno).

    Preferência: distância ombro-quadril (altura do tronco).
    Fallback: largura dos ombros * 1.5. Último recurso: 100px.
    """
    sh_c = _center(keypoints, [L_SHOULDER, R_SHOULDER], conf_thr)
    hip_c = _center(keypoints, [L_HIP, R_HIP], conf_thr)
    if sh_c and hip_c:
        d = _dist(sh_c, hip_c)
        if d > 1:
            return d
    ls, rs = _kp(keypoints, L_SHOULDER), _kp(keypoints, R_SHOULDER)
    if _visible(ls, conf_thr) and _visible(rs, conf_thr):
        d = _dist(ls, rs) * 1.5
        if d > 1:
            return d
    return 100.0


# ===========================================================================
# FUNÇÕES ORIGINAIS (mantidas / levemente melhoradas para compatibilidade)
# ===========================================================================
def is_person_facing_away(keypoints, confidence_threshold=DEFAULT_CONF):
    """
    Detecta se a pessoa está de costas para a câmera.
    Retorna True se estiver de costas.
    """
    if keypoints is None or len(keypoints) < 7:
        return True

    nose = _kp(keypoints, NOSE)
    leye = _kp(keypoints, L_EYE)
    reye = _kp(keypoints, R_EYE)

    facial_visible = sum([
        _visible(nose, confidence_threshold),
        _visible(leye, confidence_threshold),
        _visible(reye, confidence_threshold),
    ])

    if facial_visible < 2:
        return True

    # Checagem extra de alinhamento dos ombros
    ls = _kp(keypoints, L_SHOULDER)
    rs = _kp(keypoints, R_SHOULDER)
    if _visible(ls, confidence_threshold) and _visible(rs, confidence_threshold):
        shoulder_y_diff = abs(ls[1] - rs[1])
        shoulder_width = abs(ls[0] - rs[0])
        if shoulder_width > 1 and shoulder_y_diff < shoulder_width * 0.3 and facial_visible == 0:
            return True

    return False


def check_reaching(keypoints, roi_poly, conf_thr=DEFAULT_CONF):
    """A pessoa está com a mão DENTRO da ROI (prateleira/balcão)? Retorna (bool, mão)."""
    if keypoints is None or len(keypoints) < 11 or roi_poly is None or len(roi_poly) < 3:
        return False, None

    poly = np.array(roi_poly, dtype=np.int32)
    lw = _kp(keypoints, L_WRIST)
    rw = _kp(keypoints, R_WRIST)
    reaching_hand = None

    if _visible(lw, conf_thr):
        if cv2.pointPolygonTest(poly, (int(lw[0]), int(lw[1])), False) >= 0:
            reaching_hand = "LEFT"
    if _visible(rw, conf_thr):
        if cv2.pointPolygonTest(poly, (int(rw[0]), int(rw[1])), False) >= 0:
            reaching_hand = "RIGHT"

    return (reaching_hand is not None), reaching_hand


def check_object_in_hand(keypoints, object_boxes, hand="LEFT", conf_thr=DEFAULT_CONF):
    """
    Há algum objeto detectado próximo / dentro do punho indicado?
    object_boxes: lista de [x1, y1, x2, y2] vindas do detector de objetos.
    O limiar é proporcional à escala corporal (robusto à distância).
    """
    if keypoints is None or len(keypoints) < 11 or not object_boxes:
        return False
    wrist = _kp(keypoints, L_WRIST if hand == "LEFT" else R_WRIST)
    if not _visible(wrist, conf_thr):
        return False

    scale = body_scale(keypoints, conf_thr)
    near_thr = max(scale * 0.6, 40)

    for box in object_boxes:
        bx = (box[0] + box[2]) / 2.0
        by = (box[1] + box[3]) / 2.0
        if _dist(wrist, (bx, by)) < near_thr:
            return True
        if box[0] < wrist[0] < box[2] and box[1] < wrist[1] < box[3]:
            return True
    return False


def check_bending(keypoints, conf_thr=DEFAULT_CONF):
    """Pessoa agachada/curvada? (ombro próximo do quadril verticalmente)."""
    if keypoints is None or len(keypoints) < 12:
        return False
    ls = _kp(keypoints, L_SHOULDER)
    lh = _kp(keypoints, L_HIP)
    if not (_visible(ls, conf_thr) and _visible(lh, conf_thr)):
        return False
    scale = body_scale(keypoints, conf_thr)
    vertical = lh[1] - ls[1]
    # tronco "comprimido" -> menos de 35% da escala normal => agachado/curvado
    return vertical < scale * 0.35


# ===========================================================================
# ZONAS DE OCULTAÇÃO (single-frame) — onde a mão "some" no corpo
# Todas retornam bool. Limiares proporcionais à escala corporal.
# ===========================================================================
def _wrist(keypoints, hand):
    return _kp(keypoints, L_WRIST if hand == "LEFT" else R_WRIST)


def hand_in_pocket_zone(keypoints, hand, scale=None, conf_thr=DEFAULT_CONF):
    """Mão no bolso (frente da calça / jaqueta), do mesmo lado do corpo."""
    scale = scale or body_scale(keypoints, conf_thr)
    w = _wrist(keypoints, hand)
    hip = _kp(keypoints, L_HIP if hand == "LEFT" else R_HIP)
    if not (_visible(w, conf_thr) and _visible(hip, conf_thr)):
        return False
    # âncora do bolso: quadril deslocado para baixo (em direção à coxa)
    anchor = (hip[0], hip[1] + 0.25 * scale)
    return _dist(w, anchor) < 0.45 * scale


def hand_in_waistband_zone(keypoints, hand, scale=None, conf_thr=DEFAULT_CONF):
    """Mão na cintura central (waistband — enfiar por dentro da calça na frente)."""
    scale = scale or body_scale(keypoints, conf_thr)
    w = _wrist(keypoints, hand)
    hip_c = _center(keypoints, [L_HIP, R_HIP], conf_thr)
    if not (_visible(w, conf_thr) and hip_c):
        return False
    return _dist(w, hip_c) < 0.35 * scale


def hand_in_chest_zone(keypoints, hand, scale=None, conf_thr=DEFAULT_CONF):
    """Mão no peito/barriga central (por baixo da blusa). Exige estar de frente."""
    scale = scale or body_scale(keypoints, conf_thr)
    w = _wrist(keypoints, hand)
    sh_c = _center(keypoints, [L_SHOULDER, R_SHOULDER], conf_thr)
    hip_c = _center(keypoints, [L_HIP, R_HIP], conf_thr)
    if not (_visible(w, conf_thr) and sh_c and hip_c):
        return False
    if is_person_facing_away(keypoints, conf_thr):
        return False
    chest = ((sh_c[0] + hip_c[0]) / 2.0, (sh_c[1] + hip_c[1]) / 2.0)
    return _dist(w, chest) < 0.40 * scale


def hand_in_armpit_zone(keypoints, hand, scale=None, conf_thr=DEFAULT_CONF):
    """Mão na axila / dentro do casaco (mesmo lado)."""
    scale = scale or body_scale(keypoints, conf_thr)
    w = _wrist(keypoints, hand)
    sh = _kp(keypoints, L_SHOULDER if hand == "LEFT" else R_SHOULDER)
    if not (_visible(w, conf_thr) and _visible(sh, conf_thr)):
        return False
    anchor = (sh[0], sh[1] + 0.18 * scale)
    return _dist(w, anchor) < 0.28 * scale


def hand_in_ankle_zone(keypoints, hand, scale=None, conf_thr=DEFAULT_CONF):
    """Mão junto ao tornozelo (esconder na meia/bota). Combinar com check_bending()."""
    scale = scale or body_scale(keypoints, conf_thr)
    w = _wrist(keypoints, hand)
    ankle = _kp(keypoints, L_ANKLE if hand == "LEFT" else R_ANKLE)
    if not (_visible(w, conf_thr) and _visible(ankle, conf_thr)):
        return False
    return _dist(w, ankle) < 0.40 * scale


def hand_in_bag_zone(keypoints, hand, bag_boxes, conf_thr=DEFAULT_CONF):
    """
    Mão dentro de uma bolsa/mochila detectada.
    bag_boxes: [x1,y1,x2,y2] do detector (classes COCO: backpack/handbag/suitcase).
    """
    if not bag_boxes:
        return False
    w = _wrist(keypoints, hand)
    if not _visible(w, conf_thr):
        return False
    for box in bag_boxes:
        if box[0] < w[0] < box[2] and box[1] < w[1] < box[3]:
            return True
    return False


def detect_concealment_zone(keypoints, hand, bag_boxes=None, scale=None, conf_thr=DEFAULT_CONF):
    """
    Retorna o nome da zona de ocultação mais específica em que a mão está,
    ou None. Ordem de prioridade: bag > pocket > waistband > chest > armpit > ankle.
    """
    scale = scale or body_scale(keypoints, conf_thr)
    if hand_in_bag_zone(keypoints, hand, bag_boxes, conf_thr):
        return "BAG"
    if hand_in_pocket_zone(keypoints, hand, scale, conf_thr):
        return "POCKET"
    if hand_in_waistband_zone(keypoints, hand, scale, conf_thr):
        return "WAISTBAND"
    if hand_in_chest_zone(keypoints, hand, scale, conf_thr):
        return "CHEST"
    if hand_in_armpit_zone(keypoints, hand, scale, conf_thr):
        return "ARMPIT"
    if hand_in_ankle_zone(keypoints, hand, scale, conf_thr) and check_bending(keypoints, conf_thr):
        return "ANKLE"
    return None


def check_concealment(keypoints, reaching_hand, bag_boxes=None, conf_thr=DEFAULT_CONF):
    """
    Compat. com o código original: True se a mão indicada está em qualquer
    zona de ocultação. Não dispara se a pessoa está de costas (não dá pra ver).
    """
    if keypoints is None or len(keypoints) < 13:
        return False
    if is_person_facing_away(keypoints, conf_thr):
        return False
    if reaching_hand not in ("LEFT", "RIGHT"):
        return False
    return detect_concealment_zone(keypoints, reaching_hand, bag_boxes, conf_thr=conf_thr) is not None


# ===========================================================================
# MOVIMENTOS SUSPEITOS (precisam de histórico temporal -> ver tracker abaixo)
# ===========================================================================
def head_horizontal_offset(keypoints, scale=None, conf_thr=DEFAULT_CONF):
    """
    Deslocamento horizontal do nariz em relação ao centro dos ombros,
    normalizado pela escala. Usado para detectar "olhar para os lados".
    """
    scale = scale or body_scale(keypoints, conf_thr)
    nose = _kp(keypoints, NOSE)
    sh_c = _center(keypoints, [L_SHOULDER, R_SHOULDER], conf_thr)
    if not (_visible(nose, conf_thr) and sh_c) or scale < 1:
        return None
    return (nose[0] - sh_c[0]) / scale


# ===========================================================================
# TRACKER TEMPORAL — junta tudo em um score de risco por pessoa
# ===========================================================================
RISK_WEIGHTS = {
    "merchandise_pickup": 0.15,        # pegou item na prateleira (normal sozinho)
    "object_in_hand": 0.10,            # objeto na mão
    "hand_to_concealment_holding": 0.55,  # levou mão+objeto a uma zona de ocultação
    "object_vanished_at_body": 0.90,   # objeto sumiu da mão JUNTO ao corpo (forte!)
    "ankle_conceal_bending": 0.70,     # agachou e levou mão ao tornozelo (meia/bota)
    "scanning_environment": 0.25,      # olhando muito para os lados
    "facing_away_hands_at_body": 0.30, # virou de costas com mãos no corpo
    "prolonged_concealment_dwell": 0.20,  # mão parada tempo demais numa zona
    "tag_removal": 0.65,               # movimento repetitivo num ponto (tirar etiqueta)
    "loitering": 0.35,                 # tempo demais parado na mesma área
}

ZONE_LABELS = {
    "BAG": "bolsa/mochila",
    "POCKET": "bolso",
    "WAISTBAND": "cintura (por dentro da calça)",
    "CHEST": "peito/por baixo da blusa",
    "ARMPIT": "axila/dentro do casaco",
    "ANKLE": "meia/bota (agachado)",
}


class PersonState:
    """Estado temporal de uma pessoa rastreada (por track_id)."""

    def __init__(self, fps):
        win = max(int(fps * 3), 10)
        self.head_hist = deque(maxlen=win)
        self.holding = {"LEFT": False, "RIGHT": False}
        self.zone = {"LEFT": None, "RIGHT": None}
        self.zone_dwell = {"LEFT": 0, "RIGHT": 0}
        self.had_merchandise = False        # já pegou algo na prateleira/teve objeto
        self.risk = 0.0
        self.frames_since_seen = 0
        self._scan_dir = 0
        self._scan_reversals = deque(maxlen=win)
        # --- destag: histórico de posição dos punhos p/ detectar vai-e-vem num ponto ---
        win_tag = max(int(fps * 2), 8)
        self.wrist_hist = {"LEFT": deque(maxlen=win_tag), "RIGHT": deque(maxlen=win_tag)}
        self._tag_axis_dir = {"LEFT": 0, "RIGHT": 0}
        self._tag_reversals = {"LEFT": deque(maxlen=win_tag), "RIGHT": deque(maxlen=win_tag)}
        self._tag_cooldown = 0
        # --- loitering: âncora de posição + frames dentro do raio ---
        self.loiter_anchor = None
        self.loiter_frames = 0
        self._loiter_fired = False


class TheftBehaviorTracker:
    """
    Acumula sinais de furto por pessoa ao longo dos frames e devolve um nível
    de risco. Espera receber um track_id estável por pessoa (use o tracking
    nativo do YOLO: model.track(..., persist=True)).

    Uso por frame, por pessoa:
        result = tracker.update(
            track_id=tid,
            keypoints=kpts,            # [[x,y,conf], ...] COCO-17
            object_boxes=obj_boxes,    # caixas de produtos detectados (opcional)
            bag_boxes=bag_boxes,       # caixas de bolsa/mochila (opcional)
            roi_polys=[shelf_poly, ...]# polígonos das prateleiras/balcões
        )
        # result -> {"risk": float, "level": str, "events": [...]}
    """

    LEVELS = [(1.2, "ALERT"), (0.8, "HIGH"), (0.4, "MEDIUM"), (0.0, "LOW")]

    def __init__(self, fps=15, decay_per_frame=0.98, alert_threshold=1.2,
                 risk_cap=2.5, conf_thr=DEFAULT_CONF):
        self.fps = fps
        self.decay = decay_per_frame
        self.alert_threshold = alert_threshold
        self.risk_cap = risk_cap
        self.conf_thr = conf_thr
        self.persons = {}

    def _level(self, risk):
        for thr, name in self.LEVELS:
            if risk >= thr:
                return name
        return "LOW"

    def _update_scanning(self, st, keypoints, scale):
        """Conta inversões de direção da cabeça (olhar nervoso p/ os lados)."""
        off = head_horizontal_offset(keypoints, scale, self.conf_thr)
        if off is None:
            return False
        st.head_hist.append(off)
        if len(st.head_hist) >= 2:
            delta = st.head_hist[-1] - st.head_hist[-2]
            if abs(delta) > 0.08:  # movimento significativo
                d = 1 if delta > 0 else -1
                if st._scan_dir != 0 and d != st._scan_dir:
                    st._scan_reversals.append(1)
                st._scan_dir = d
        reversals = sum(st._scan_reversals)
        return reversals >= 4  # muitas trocas de direção na janela -> escaneando

    def _update_destag(self, st, keypoints, scale):
        """
        Detecta movimento repetitivo de vai-e-vem das mãos num ponto pequeno —
        gesto típico de tentar arrancar/forçar a etiqueta antifurto.

        Heurística: o punho fica confinado numa região PEQUENA (não está andando
        pela loja) mas oscila de direção muitas vezes (puxa-empurra/serra). Exige
        que a pessoa tenha mexido com mercadoria, p/ reduzir falso positivo.
        """
        if st._tag_cooldown > 0:
            st._tag_cooldown -= 1
        fired_hand = None
        for hand in ("LEFT", "RIGHT"):
            w = _wrist(keypoints, hand)
            if not _visible(w, self.conf_thr):
                continue
            hist = st.wrist_hist[hand]
            hist.append((w[0], w[1]))
            if len(hist) < hist.maxlen:
                continue

            xs = [p[0] for p in hist]
            ys = [p[1] for p in hist]
            spread = max(np.hypot(max(xs) - min(xs), max(ys) - min(ys)), 1.0)
            # mão confinada num raio pequeno (relativo ao corpo)?
            if spread > 0.40 * scale:
                st._tag_reversals[hand].clear()
                st._tag_axis_dir[hand] = 0
                continue

            # conta inversões de direção (oscilação) no eixo de maior movimento
            if len(hist) >= 2:
                dx = hist[-1][0] - hist[-2][0]
                dy = hist[-1][1] - hist[-2][1]
                step = np.hypot(dx, dy)
                if step > 0.04 * scale:  # movimento real, não tremor
                    primary = dx if abs(dx) >= abs(dy) else dy
                    d = 1 if primary > 0 else -1
                    if st._tag_axis_dir[hand] != 0 and d != st._tag_axis_dir[hand]:
                        st._tag_reversals[hand].append(1)
                    st._tag_axis_dir[hand] = d

            if sum(st._tag_reversals[hand]) >= 5 and st._tag_cooldown == 0:
                fired_hand = hand
                st._tag_reversals[hand].clear()
                st._tag_cooldown = int(self.fps * 3)  # evita re-disparo em sequência
        return fired_hand

    def _update_loitering(self, st, keypoints, scale):
        """
        Permanência prolongada (parado) na mesma área — pode indicar alguém
        estudando a prateleira/preparando o furto. Usa uma ÂNCORA de posição:
        enquanto a pessoa fica dentro de um raio da âncora, conta o tempo; se
        ela se desloca para fora do raio, a âncora é redefinida e o tempo zera.
        Isso evita falso positivo com quem anda devagar pela loja.
        """
        center = _center(keypoints, [L_HIP, R_HIP], self.conf_thr) \
            or _center(keypoints, [L_SHOULDER, R_SHOULDER], self.conf_thr)
        if center is None:
            return False

        radius = 0.5 * scale  # ~meia largura de corpo
        if st.loiter_anchor is None or _dist(center, st.loiter_anchor) > radius:
            st.loiter_anchor = center      # saiu da área -> nova âncora
            st.loiter_frames = 0
            st._loiter_fired = False
            return False

        st.loiter_frames += 1
        if st.loiter_frames >= int(self.fps * 12) and not st._loiter_fired:
            st._loiter_fired = True        # ~12s dentro da mesma área
            return True
        return False

    def update(self, track_id, keypoints, object_boxes=None, bag_boxes=None,
               roi_polys=None):
        object_boxes = object_boxes or []
        bag_boxes = bag_boxes or []
        roi_polys = roi_polys or []

        st = self.persons.get(track_id)
        if st is None:
            st = PersonState(self.fps)
            self.persons[track_id] = st
        st.frames_since_seen = 0

        # decaimento natural do risco
        st.risk *= self.decay

        events = []
        scale = body_scale(keypoints, self.conf_thr)

        # --- 1) pegou mercadoria na prateleira? ---
        for poly in roi_polys:
            reaching, hand = check_reaching(keypoints, poly, self.conf_thr)
            if reaching:
                if not st.had_merchandise:
                    st.risk += RISK_WEIGHTS["merchandise_pickup"]
                    events.append({"type": "merchandise_pickup", "hand": hand,
                                   "desc": "Pegou item em área de mercadoria"})
                st.had_merchandise = True

        # --- 2/3) por mão: objeto na mão, zona de ocultação, sumiço do objeto ---
        for hand in ("LEFT", "RIGHT"):
            holding_now = check_object_in_hand(keypoints, object_boxes, hand, self.conf_thr)
            zone_now = detect_concealment_zone(keypoints, hand, bag_boxes, scale, self.conf_thr)

            if holding_now:
                st.had_merchandise = True
                if not st.holding[hand]:
                    st.risk += RISK_WEIGHTS["object_in_hand"]

            # mão (com objeto) entrou numa zona de ocultação
            if zone_now and holding_now and st.zone[hand] != zone_now:
                w = RISK_WEIGHTS["ankle_conceal_bending"] if zone_now == "ANKLE" \
                    else RISK_WEIGHTS["hand_to_concealment_holding"]
                st.risk += w
                events.append({
                    "type": "hand_to_concealment_holding", "hand": hand,
                    "zone": zone_now,
                    "desc": f"Levou objeto à zona de ocultação: {ZONE_LABELS.get(zone_now, zone_now)}",
                })

            # OBJETO SUMIU: estava segurando, foi a uma zona, agora não segura mais
            if st.holding[hand] and not holding_now and \
               (zone_now is not None or st.zone[hand] is not None) and st.had_merchandise:
                z = zone_now or st.zone[hand]
                st.risk += RISK_WEIGHTS["object_vanished_at_body"]
                events.append({
                    "type": "object_vanished_at_body", "hand": hand,
                    "zone": z,
                    "desc": f"Objeto desapareceu da mão junto ao corpo ({ZONE_LABELS.get(z, z)}) — ocultação provável",
                })

            # dwell: mão parada tempo demais numa zona de ocultação
            if zone_now is not None and zone_now == st.zone[hand]:
                st.zone_dwell[hand] += 1
                if st.zone_dwell[hand] == int(self.fps * 1.5):  # ~1.5s
                    st.risk += RISK_WEIGHTS["prolonged_concealment_dwell"]
                    events.append({
                        "type": "prolonged_concealment_dwell", "hand": hand,
                        "zone": zone_now,
                        "desc": f"Mão permaneceu tempo demais em {ZONE_LABELS.get(zone_now, zone_now)}",
                    })
            else:
                st.zone_dwell[hand] = 0

            st.holding[hand] = holding_now
            st.zone[hand] = zone_now

        # --- 4) de costas para a câmera com as mãos no corpo (esconder sem ser visto) ---
        if is_person_facing_away(keypoints, self.conf_thr):
            hip_c = _center(keypoints, [L_HIP, R_HIP], self.conf_thr)
            if hip_c:
                for hand in ("LEFT", "RIGHT"):
                    w = _wrist(keypoints, hand)
                    if _visible(w, self.conf_thr) and _dist(w, hip_c) < 0.5 * scale:
                        st.risk += RISK_WEIGHTS["facing_away_hands_at_body"] * 0.5
                        events.append({
                            "type": "facing_away_hands_at_body", "hand": hand,
                            "desc": "De costas para a câmera com a mão na região da cintura",
                        })
                        break

        # --- 5) olhando muito para os lados (procurando funcionário/câmera) ---
        if self._update_scanning(st, keypoints, scale):
            st.risk += RISK_WEIGHTS["scanning_environment"]
            st._scan_reversals.clear()
            events.append({"type": "scanning_environment",
                           "desc": "Olhando repetidamente para os lados (comportamento de vigília)"})

        # --- 6) destag: movimento repetitivo num ponto (arrancar etiqueta antifurto) ---
        tag_hand = self._update_destag(st, keypoints, scale)
        if tag_hand:
            # mais grave se a pessoa já mexeu com mercadoria
            w = RISK_WEIGHTS["tag_removal"] * (1.0 if st.had_merchandise else 0.6)
            st.risk += w
            events.append({
                "type": "tag_removal", "hand": tag_hand,
                "desc": "Movimento repetitivo da mão num ponto — possível remoção de etiqueta antifurto",
            })

        # --- 7) loitering: parado tempo demais na mesma área ---
        if self._update_loitering(st, keypoints, scale):
            st.risk += RISK_WEIGHTS["loitering"]
            events.append({"type": "loitering",
                           "desc": "Permanência prolongada parado na mesma área"})

        st.risk = min(st.risk, self.risk_cap)
        level = self._level(st.risk)

        return {
            "track_id": track_id,
            "risk": round(st.risk, 3),
            "level": level,
            "alert": st.risk >= self.alert_threshold,
            "events": events,
        }

    def cleanup(self, max_missing_frames=None):
        """Remove pessoas que sumiram há muitos frames. Chame 1x por frame."""
        max_missing = max_missing_frames or int(self.fps * 5)
        to_del = []
        for tid, st in self.persons.items():
            st.frames_since_seen += 1
            if st.frames_since_seen > max_missing:
                to_del.append(tid)
        for tid in to_del:
            del self.persons[tid]


# ===========================================================================
# EXEMPLO DE INTEGRAÇÃO (pseudo-loop com Ultralytics YOLO)
# ===========================================================================
if __name__ == "__main__":
    # from ultralytics import YOLO
    # pose_model = YOLO("yolov8n-pose.pt")
    # obj_model  = YOLO("yolov8n.pt")   # detecta 'backpack','handbag','suitcase' etc.
    #
    # tracker = TheftBehaviorTracker(fps=15)
    # SHELF_ROIS = [ [(x1,y1),(x2,y1),(x2,y2),(x1,y2)] ]   # prateleiras na imagem
    #
    # for frame in video:
    #     pose_res = pose_model.track(frame, persist=True, verbose=False)[0]
    #     obj_res  = obj_model(frame, verbose=False)[0]
    #
    #     # caixas de objetos / bolsas
    #     object_boxes, bag_boxes = [], []
    #     for b in obj_res.boxes:
    #         xyxy = b.xyxy[0].tolist()
    #         cls  = int(b.cls[0])
    #         name = obj_model.names[cls]
    #         if name in ("backpack", "handbag", "suitcase"):
    #             bag_boxes.append(xyxy)
    #         else:
    #             object_boxes.append(xyxy)   # candidatos a "produto"
    #
    #     if pose_res.keypoints is not None and pose_res.boxes.id is not None:
    #         ids  = pose_res.boxes.id.int().tolist()
    #         kpts = pose_res.keypoints.data.cpu().numpy()  # (N,17,3)
    #         for tid, person_kpts in zip(ids, kpts):
    #             r = tracker.update(tid, person_kpts, object_boxes, bag_boxes, SHELF_ROIS)
    #             if r["level"] in ("HIGH", "ALERT"):
    #                 print(f"[{r['level']}] pessoa {tid} risco={r['risk']}")
    #                 for e in r["events"]:
    #                     print("   ->", e["desc"])
    #     tracker.cleanup()
    print("Modulo pronto. Veja o exemplo de integracao no final do arquivo.")
