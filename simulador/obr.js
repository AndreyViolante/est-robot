'use strict';
/* Arena da OBR no simulador: o percurso com linha da prova prática (Robótica de Resgate), montado com
   ladrilhos de 30 x 30 cm, e a pontuação da rodada, como no manual de regras da OBR 2026 (etapa
   regional/estadual, versão 1.2):
     - perigos: gap 10 pontos por ladrilho, obstáculo 20, interseção ou beco sem saída 10;
     - checkpoints: 5, 3 ou 1 ponto por ladrilho desde o último checkpoint (1ª, 2ª ou 3ª tentativa), depois 0;
     - ladrilho de início 5 pontos; chegada 60 - 5 por falha de progresso, parando 5 s na faixa vermelha;
     - falha de progresso: perder a linha, ficar 10 s parado, ir para o ladrilho errado; volta ao último checkpoint;
     - rodada de 5 minutos.
   Visto de cima não dá para simular rampa, gangorra, lombada, passagem nem a sala de resgate.

   Uma arena é {colunas, linhas, nivel, percurso: [{c, r, elemento, ...}]}: o percurso é a sequência de
   ladrilhos que o robô deve seguir, do de partida (o primeiro) ao de chegada (o último). O tipo de cada
   ladrilho (reta, curva, beco) sai dos vizinhos no percurso; o elemento é '', 'gap', 'obstaculo', 'cruz' ou
   'T', e o ladrilho pode ter checkpoint: true, curva: 'suave', ramo: 'direita' (T numa reta) e verdeDepois. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const LADO = 30;                   // cm: lado do ladrilho
const BORDA = 15;                  // cm de chão branco em volta dos ladrilhos
const CAIXA_OBR = 10;              // cm: lado do obstáculo (fica com 10 cm de linha antes e depois)
const FAIXA = 2.5;                 // cm: largura da faixa vermelha de chegada
const GAP_MAXIMO = {1: 10, 2: 15};
const RODADA = 300;                // s
const PONTOS = {gap: 10, obstaculo: 20, cruz: 10, T: 10, beco: 10, inicio: 5, chegada: 60, porFalha: 5};
const POR_LADRILHO = [0, 5, 3, 1];  // pela tentativa (1ª, 2ª, 3ª); da 4ª em diante, 0
const VERMELHO = [0.85, 0.12, 0.12, 0.55];

const PASSO = {N: [0, -1], S: [0, 1], L: [1, 0], O: [-1, 0]};
const OPOSTO = {N: 'S', S: 'N', L: 'O', O: 'L'};
const ESQUERDA = {N: 'O', O: 'S', S: 'L', L: 'N'};      // o lado esquerdo de quem anda para N, O, S, L
const DIREITA = {N: 'L', L: 'S', S: 'O', O: 'N'};
const ANGULO = {L: 0, S: 90, O: 180, N: 270};           // graus, como o robô do simulador (sentido horário)

function direcao(a, b) {
  const dc = b.c - a.c, dr = b.r - a.r;
  return Object.keys(PASSO).find(k => PASSO[k][0] === dc && PASSO[k][1] === dr) || null;
}
const vizinhos = (a, b) => direcao(a, b) !== null;

/* entrada e saída de cada ladrilho do percurso (o lado por onde o robô entra e por onde sai) e o tipo */
function tiposDoPercurso(percurso) {
  return percurso.map((t, i) => {
    const ant = percurso[i - 1], prox = percurso[i + 1];
    let saida = prox ? direcao(t, prox) : null;
    let entrada = ant ? direcao(t, ant) : null;
    if (!entrada) entrada = saida ? OPOSTO[saida] : 'O';
    if (!saida) saida = OPOSTO[entrada];
    let tipo = 'reta';
    if (saida === entrada) tipo = 'beco';
    else if (saida !== OPOSTO[entrada]) tipo = 'curva';
    return {entrada, saida, tipo, anda: OPOSTO[entrada]};     // anda: a direção do robô quando entra
  });
}

/* problemas do percurso, em português (vazio = arena válida) */
function conferir(arena) {
  const p = arena.percurso, erros = [];
  if (p.length < 2) erros.push('o percurso precisa de pelo menos 2 ladrilhos (partida e chegada)');
  for (let i = 1; i < p.length; i++) {
    if (!vizinhos(p[i - 1], p[i])) erros.push(`o ladrilho ${i + 1} não encosta no ${i}`);
  }
  const tipos = tiposDoPercurso(p), gapMax = GAP_MAXIMO[arena.nivel] || 10;
  p.forEach((t, i) => {
    const n = i + 1, k = tipos[i];
    if ((t.elemento === 'gap' || t.elemento === 'obstaculo') && k.tipo !== 'reta') {
      erros.push(`ladrilho ${n}: ${t.elemento === 'gap' ? 'gap' : 'obstáculo'} só em linha reta`);
    }
    if (t.elemento === 'gap' && !(t.gap > 0 && t.gap <= gapMax)) erros.push(`ladrilho ${n}: o gap vai até ${gapMax} cm no nível ${arena.nivel}`);
    if (t.checkpoint && (t.elemento || k.tipo === 'beco' || i === 0 || i === p.length - 1)) {
      erros.push(`ladrilho ${n}: checkpoint só em ladrilho sem perigo (e não na partida nem na chegada)`);
    }
    if (k.tipo === 'beco' && i === 0) erros.push('a partida não pode ser um beco sem saída');
  });
  if (erros.length) return erros;
  // em cada interseção, o que os verdes mandam (para quem chega por aquele lado) tem que ser o caminho
  const pista = montar(arena, 'conferir', '');
  p.forEach((t, i) => {
    if (ramosNaCelula(pista, t) < 3) return;
    const k = tipos[i], manda = decisao(pista, i);
    const vai = k.tipo === 'reta' ? 'reto' : k.tipo === 'beco' ? 'meia-volta'
      : k.saida === ESQUERDA[k.anda] ? 'esquerda' : 'direita';
    if (manda !== vai) erros.push(`ladrilho ${i + 1}: os verdes mandam ${TEXTO_DECISAO[manda]}, mas o percurso vai ${TEXTO_DECISAO[vai]}`);
  });
  return erros;
}

const TEXTO_DECISAO = {reto: 'seguir reto', esquerda: 'virar à esquerda', direita: 'virar à direita', 'meia-volta': 'dar meia-volta'};

/* quantos lados do ladrilho têm linha chegando (3 ou 4 = interseção) */
function ramosNaCelula(pista, t) {
  const cx = BORDA + t.c * LADO + LADO / 2, cy = BORDA + t.r * LADO + LADO / 2;
  return Object.values(PASSO).filter(([dx, dy]) => EST.distLinha(pista, cx + dx * (LADO / 2 - 0.5), cy + dy * (LADO / 2 - 0.5)) < 0.5).length;
}

/* o que os quadrados verdes antes da interseção mandam fazer, para quem chega no ladrilho i do percurso:
   nenhum = 'reto', só à esquerda = 'esquerda', só à direita = 'direita', os dois = 'meia-volta' */
function decisao(pista, i) {
  const t = pista.obr.arena.percurso[i], k = pista.obr.tipos[i];
  const cx = BORDA + t.c * LADO + LADO / 2, cy = BORDA + t.r * LADO + LADO / 2;
  const [fx, fy] = PASSO[k.anda], [ex, ey] = [fy, -fx];          // para a frente e para a esquerda do robô
  let esq = false, dir = false;
  for (const q of pista.verdes) {
    const gx = q.x + q.w / 2 - cx, gy = q.y + q.h / 2 - cy;
    if (Math.abs(gx) > LADO / 2 || Math.abs(gy) > LADO / 2) continue;          // de outro ladrilho
    if (gx * fx + gy * fy >= 0) continue;                                       // depois do cruzamento: não vale
    if (gx * ex + gy * ey > 0) esq = true; else dir = true;
  }
  return esq && dir ? 'meia-volta' : esq ? 'esquerda' : dir ? 'direita' : 'reto';
}

// ---------------------------------------------------------------- geometria

/* pista do simulador a partir da arena: linhas, quadrados verdes, faixa vermelha, obstáculos e a largada */
function montar(arena, id, nome) {
  const p = arena.percurso, tipos = tiposDoPercurso(p);
  const pista = {
    id, nome, largura: arena.colunas * LADO + 2 * BORDA, altura: arena.linhas * LADO + 2 * BORDA,
    linhas: [], verdes: [], vermelhos: [], caixas: [], paredes: [],
    obr: {arena, tipos, LADO, BORDA},
  };
  const origem = t => [BORDA + t.c * LADO, BORDA + t.r * LADO];
  p.forEach((t, i) => {
    const [x0, y0] = origem(t), k = tipos[i];
    const centro = [x0 + LADO / 2, y0 + LADO / 2];
    const meio = lado => [centro[0] + PASSO[lado][0] * LADO / 2, centro[1] + PASSO[lado][1] * LADO / 2];
    const seg = (a, b) => pista.linhas.push({seg: [a[0], a[1], b[0], b[1]]});
    const verde = (lado, depois = false) =>
      pista.verdes.push(EST.quadradoVerde(centro[0], centro[1], k.anda, lado, depois));
    const ultimo = i === p.length - 1;
    let ramos = null;                      // interseção: os lados que têm linha saindo do centro
    if (k.tipo === 'beco') {
      ramos = t.elemento === 'cruz' ? ['N', 'S', 'L', 'O'] : [k.entrada, ESQUERDA[k.anda], DIREITA[k.anda]];
      verde('esquerda');
      verde('direita');
    } else if (t.elemento === 'cruz' || t.elemento === 'T') {
      if (t.elemento === 'cruz') ramos = ['N', 'S', 'L', 'O'];
      else if (k.tipo === 'curva' && t.ramo === 'reto') ramos = [k.entrada, k.anda, k.saida];       // chega pela barra do T
      else if (k.tipo === 'curva') ramos = [k.entrada, ESQUERDA[k.anda], DIREITA[k.anda]];          // chega pelo pé do T
      else ramos = [k.entrada, k.saida, t.ramo === 'direita' ? DIREITA[k.anda] : ESQUERDA[k.anda]];
      if (k.tipo === 'curva') verde(k.saida === ESQUERDA[k.anda] ? 'esquerda' : 'direita');
      if (t.verdeDepois) verde(t.verdeDepois === 'direita' ? 'direita' : 'esquerda', true);    // não vale: segue
    }
    if (ramos) {
      for (const lado of ramos) seg(centro, meio(lado));
    } else if (k.tipo === 'curva') {
      if (t.curva === 'suave') {
        const ce = PASSO[k.entrada], cs = PASSO[k.saida];
        const canto = [centro[0] + (ce[0] + cs[0]) * LADO / 2, centro[1] + (ce[1] + cs[1]) * LADO / 2];
        const ang = q => Math.atan2(q[1] - canto[1], q[0] - canto[0]) * 180 / Math.PI;
        const a0 = ang(meio(k.entrada));
        let varre = ang(meio(k.saida)) - a0;
        varre = ((varre + 540) % 360) - 180;
        pista.linhas.push({arco: [canto[0], canto[1], LADO / 2, a0, varre]});
      } else {
        seg(meio(k.entrada), centro);
        seg(centro, meio(k.saida));
      }
    } else if (t.elemento === 'gap') {
      const g = t.gap || 10, a = meio(k.entrada), [dx, dy] = PASSO[k.anda];
      const ate = (LADO - g) / 2;
      seg(a, [a[0] + dx * ate, a[1] + dy * ate]);
      seg([a[0] + dx * (ate + g), a[1] + dy * (ate + g)], meio(k.saida));
    } else {
      seg(meio(k.entrada), ultimo ? centro : meio(k.saida));
      if (t.elemento === 'obstaculo') {
        pista.caixas.push({x: centro[0] - CAIXA_OBR / 2, y: centro[1] - CAIXA_OBR / 2, w: CAIXA_OBR, h: CAIXA_OBR});
      }
    }
    if (ultimo) {                          // faixa vermelha no meio do ladrilho, de lado a lado
      const em_x = PASSO[k.anda][0] !== 0;
      pista.vermelhos.push(em_x ? {x: centro[0] - FAIXA / 2, y: y0, w: FAIXA, h: LADO}
                                : {x: x0, y: centro[1] - FAIXA / 2, w: LADO, h: FAIXA});
    }
  });
  pista.largada = largadaNoLadrilho(pista, 0);
  return pista;
}

/* robô no ladrilho i do percurso, virado para a saída dele (largada e volta depois de uma falha de progresso) */
function largadaNoLadrilho(pista, i) {
  const t = pista.obr.arena.percurso[i], k = pista.obr.tipos[i];
  if (!t) return {x: pista.largura / 2, y: pista.altura / 2, ang: 0};
  const cx = BORDA + t.c * LADO + LADO / 2, cy = BORDA + t.r * LADO + LADO / 2;
  const [dx, dy] = PASSO[k.saida];
  return {x: cx - dx * 5, y: cy - dy * 5, ang: ANGULO[k.saida]};
}

// ---------------------------------------------------------------- pontuação da rodada

class Placar {
  constructor(pista) {
    this.pista = pista;
    this.percurso = pista.obr.arena.percurso;
    this.tipos = pista.obr.tipos;
    this.k = 0;                    // último ladrilho do percurso alcançado
    this.checkpoint = 0;           // último checkpoint alcançado (a partida conta como o primeiro)
    this.tentativa = 1;            // tentativa no trecho desde o último checkpoint
    this.falhas = 0;
    this.pontos = {ladrilhos: 0, perigos: 0, chegada: 0};
    this.feitos = new Set();       // perigos já pontuados (cada um vale uma vez)
    this.longeDesde = null;        // instante em que o robô se afastou da linha
    this.lugar = null;             // {x, y, t}: onde o robô estava; "parado" = não saiu 2 cm dali (empurrando a caixa conta)
    this.fim = null;               // {motivo}: a rodada acabou
    this.ultimo = 'Valendo! Siga a linha até a faixa vermelha.';
  }

  get total() { return this.pontos.ladrilhos + this.pontos.perigos + this.pontos.chegada; }

  celula(x, y) {
    return {c: Math.floor((x - BORDA) / LADO), r: Math.floor((y - BORDA) / LADO)};
  }

  /* quanto o ponto entrou na célula (cm até a borda mais perto, por dentro) */
  dentro(x, y, cel) {
    const x0 = BORDA + cel.c * LADO, y0 = BORDA + cel.r * LADO;
    return Math.min(x - x0, x0 + LADO - x, y - y0, y0 + LADO - y);
  }

  perigo(i) {
    const t = this.percurso[i], k = this.tipos[i];
    if (!t) return null;
    if (k.tipo === 'beco') return 'beco';
    return t.elemento || null;
  }

  /* um passo da simulação: s = {t, x, y, parado, sobreVermelho}. Devolve null, {falha: motivo, largada}
     (o robô volta ao último checkpoint e o programa recomeça) ou {fim: motivo}. */
  passo(s) {
    if (this.fim) return null;
    if (s.t >= RODADA) return this.terminar('acabaram os 5 minutos da rodada');
    const cel = this.celula(s.x, s.y), atual = this.percurso[this.k], prox = this.percurso[this.k + 1];
    const mesma = (a, b) => a && b && a.c === b.c && a.r === b.r;
    const chegada = this.k === this.percurso.length - 1;
    const pertoDeObstaculo = [this.k, this.k + 1].some(i => this.perigo(i) === 'obstaculo');

    if (prox && mesma(cel, prox) && this.dentro(s.x, s.y, cel) > 1) {
      this.avancar();
      return null;
    }
    if (!mesma(cel, atual) && !(prox && mesma(cel, prox))) {
      const fundo = this.dentro(s.x, s.y, cel);
      if (!pertoDeObstaculo && fundo > 5) {
        return this.falha(chegada ? 'passou da faixa vermelha sem parar' : 'foi para um ladrilho fora do caminho');
      }
      if (pertoDeObstaculo && fundo > 12) return this.falha('não voltou para a linha depois do obstáculo');
    }
    // perdeu a linha: longe dela por mais de 2 s (no desvio do obstáculo pode sair)
    const longe = EST.distLinha(this.pista, s.x, s.y) > 10 && !pertoDeObstaculo;
    if (longe) {
      if (this.longeDesde === null) this.longeDesde = s.t;
      else if (s.t - this.longeDesde > 2) return this.falha('perdeu a linha');
    } else {
      this.longeDesde = null;
    }
    if (chegada && s.sobreVermelho && s.parado >= 5) return this.chegar();
    if (!this.lugar || Math.hypot(s.x - this.lugar.x, s.y - this.lugar.y) > 2) this.lugar = {x: s.x, y: s.y, t: s.t};
    if (Math.max(s.parado, s.t - this.lugar.t) >= 10) {
      return this.falha(chegada ? 'parou fora da faixa vermelha' : 'ficou 10 s sem sair do lugar');
    }
    return null;
  }

  avancar() {
    const deixou = this.k, p = this.perigo(deixou);
    if (deixou === 0 && !this.feitos.has('inicio')) {
      this.feitos.add('inicio');
      this.pontos.ladrilhos += PONTOS.inicio;
    }
    if (p && !this.feitos.has(deixou)) {
      this.feitos.add(deixou);
      this.pontos.perigos += PONTOS[p];
      this.ultimo = `+${PONTOS[p]}: ${NOMES_PERIGO[p]} no ladrilho ${deixou + 1}`;
    }
    this.k++;
    const t = this.percurso[this.k];
    if (t.checkpoint || this.k === this.percurso.length - 1) {
      if (this.k > this.checkpoint) {
        const ganhou = (this.k - this.checkpoint) * (POR_LADRILHO[this.tentativa] || 0);
        this.pontos.ladrilhos += ganhou;
        this.ultimo = `+${ganhou}: ${this.k - this.checkpoint} ladrilhos até o ${t.checkpoint ? 'checkpoint' : 'ladrilho de chegada'} ` +
                      `(${this.tentativa}ª tentativa)`;
        this.checkpoint = this.k;
        this.tentativa = 1;
      }
    }
  }

  falha(motivo) {
    this.falhas++;
    this.tentativa++;
    this.k = this.checkpoint;
    this.longeDesde = null;
    this.lugar = null;
    this.ultimo = `Falha de progresso: ${motivo}. Volta ao ${this.checkpoint ? `checkpoint (ladrilho ${this.checkpoint + 1})` : 'ladrilho de partida'}.`;
    return {falha: motivo, largada: largadaNoLadrilho(this.pista, this.checkpoint)};
  }

  chegar() {
    this.pontos.chegada = Math.max(0, PONTOS.chegada - PONTOS.porFalha * this.falhas);
    return this.terminar(`parou na faixa vermelha: +${this.pontos.chegada} da chegada`);
  }

  terminar(motivo) {
    this.fim = {motivo};
    this.ultimo = `Fim da rodada: ${motivo}.`;
    return {fim: motivo};
  }
}

const NOMES_PERIGO = {gap: 'gap', obstaculo: 'obstáculo', cruz: 'interseção', T: 'interseção', beco: 'beco sem saída'};

// ---------------------------------------------------------------- arenas prontas

/* percurso escrito como texto: 'c,r' ladrilho por ladrilho, com o elemento depois de ':' (juntos com +):
   g10 = gap de 10 cm, o = obstáculo, x = cruz, t = T, td = T com o ramo à direita (numa reta),
   r = T de quem chega pela barra (numa curva), cp = checkpoint, s = curva suave, vd = verde depois (não vale) */
function percursoDe(texto) {
  return texto.trim().split(/\s+/).map(item => {
    const [pos, extra = ''] = item.split(':'), [c, r] = pos.split(',').map(Number), t = {c, r, elemento: ''};
    for (const e of extra.split('+').filter(Boolean)) {
      if (/^g\d+$/.test(e)) { t.elemento = 'gap'; t.gap = +e.slice(1); }
      else if (e === 'o') t.elemento = 'obstaculo';
      else if (e === 'x') t.elemento = 'cruz';
      else if (e === 't') t.elemento = 'T';
      else if (e === 'td') { t.elemento = 'T'; t.ramo = 'direita'; }
      else if (e === 'r') t.ramo = 'reto';
      else if (e === 'cp') t.checkpoint = true;
      else if (e === 's') t.curva = 'suave';
      else if (e === 'vd') t.verdeDepois = 'direita';
    }
    return t;
  });
}

const ARENAS = [
  {
    id: 'obr-treino', nome: 'Arena OBR: treino (curvas e gap)',
    dica: 'Arena da OBR por ladrilhos de 30 cm: curvas de 90°, curva suave, um gap de 10 cm e a faixa vermelha ' +
          'de chegada. A pontuação aparece no cartão "Rodada da OBR".',
    arena: {colunas: 5, linhas: 4, nivel: 1,
            percurso: percursoDe('0,3 1,3 2,3 3,3:g10 4,3 4,2:cp 4,1 4,0 3,0 2,0 1,0 0,0:s 0,1 0,2:s 1,2 2,2')},
  },
  {
    /* verde à esquerda no ladrilho 6; interseção sem verde no 10 (segue reto); no 16 passa reto, faz a
       meia-volta no beco (17) e, voltando ao 16, o verde (que estava depois para quem vinha antes) manda subir */
    id: 'obr-completa', nome: 'Arena OBR: verdes, beco e obstáculo',
    dica: 'Interseções com e sem verde, um beco sem saída (dois verdes antes: meia-volta), um obstáculo para ' +
          'desviar, gap e checkpoints, como no manual da OBR 2026 (sem rampa, gangorra e sala de resgate).',
    arena: {colunas: 7, linhas: 4, nivel: 1,
            percurso: percursoDe('0,3 1,3 2,3:g10 3,3 4,3 5,3:t+r 5,2:cp 5,1:o 5,0 4,0:t 3,0 2,0 1,0:s 1,1:cp ' +
                                 '1,2 2,2:t 3,2:t 2,2:t+r 2,1 3,1 4,1')},
  },
];

/* a "Minha arena OBR" guardada no navegador (ou uma arena vazia) */
function arenaGuardada(dados) {
  const d = dados && typeof dados === 'object' ? dados : {};
  const medida = (v, min, max, padrao) => Number.isInteger(v) ? Math.max(min, Math.min(max, v)) : padrao;
  const arena = {colunas: medida(d.colunas, 2, 12, 6), linhas: medida(d.linhas, 2, 9, 4), nivel: d.nivel === 2 ? 2 : 1, percurso: []};
  for (const t of Array.isArray(d.percurso) ? d.percurso.slice(0, 200) : []) {
    if (!t || !Number.isInteger(t.c) || !Number.isInteger(t.r) || t.c < 0 || t.r < 0 || t.c >= arena.colunas || t.r >= arena.linhas) continue;
    const ladrilho = {c: t.c, r: t.r, elemento: ['gap', 'obstaculo', 'cruz', 'T'].includes(t.elemento) ? t.elemento : ''};
    if (ladrilho.elemento === 'gap') ladrilho.gap = [5, 10, 15].includes(t.gap) ? t.gap : 10;
    if (t.checkpoint === true) ladrilho.checkpoint = true;
    if (t.curva === 'suave') ladrilho.curva = 'suave';
    if (t.ramo === 'direita' || t.ramo === 'reto') ladrilho.ramo = t.ramo;
    if (t.verdeDepois === 'direita' || t.verdeDepois === 'esquerda') ladrilho.verdeDepois = t.verdeDepois;
    arena.percurso.push(ladrilho);
  }
  return arena;
}

EST.OBR = {LADO, BORDA, RODADA, PONTOS, GAP_MAXIMO, VERMELHO, ARENAS, NOMES_PERIGO,
           montar, conferir, decisao, tiposDoPercurso, largadaNoLadrilho, arenaGuardada, vizinhos, percursoDe, Placar};
})();
