'use strict';
/* Pistas do simulador. Medidas em centímetros, com x para a direita e y para baixo (como na tela).
   O chão é calculado pela geometria (não por pixels): um ponto é preto se estiver a menos de meia
   largura de linha de algum trecho. Paredes e caixas valem para o ultrassom e para as batidas. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const LINHA = 2;                  // largura da linha preta (fita isolante tem 1,9 cm)
const PAREDE = 2;                 // espessura das paredes, desenhadas por fora do segmento (a face é o segmento)

// trechos de linha: segmento {seg: [x1, y1, x2, y2]} ou arco {arco: [cx, cy, raio, inicio, varredura]} (graus)
function caminho(pontos, fechado) {
  const trechos = [];
  const n = pontos.length;
  for (let i = 0; i < (fechado ? n : n - 1); i++) {
    const [x1, y1] = pontos[i], [x2, y2] = pontos[(i + 1) % n];
    trechos.push({seg: [x1, y1, x2, y2]});
  }
  return trechos;
}

// segmento entre (x1, y1) e (x2, y2) com uma falha de 'falha' cm começando a 'em' cm do início
function comFalha(x1, y1, x2, y2, em, falha) {
  const L = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / L, uy = (y2 - y1) / L;
  return [{seg: [x1, y1, x1 + ux * em, y1 + uy * em]},
          {seg: [x1 + ux * (em + falha), y1 + uy * (em + falha), x2, y2]}];
}

function contorno(w, h) {
  return [[0, 0, w, 0], [w, 0, w, h], [w, h, 0, h], [0, h, 0, 0]];
}

const PISTAS = [
  {
    id: 'livre', nome: 'Chão livre (quadriculado)', largura: 200, altura: 150, quadriculado: true,
    linhas: [], paredes: [], caixas: [],
    largada: {x: 60, y: 50, ang: 0},
    dica: 'Para os exemplos 1 e 2: o rastro mostra o caminho do robô.',
  },
  {
    id: 'oval', nome: 'Oval', largura: 200, altura: 140,
    linhas: [{seg: [60, 30, 140, 30]}, {arco: [140, 70, 40, -90, 180]},
             {seg: [140, 110, 60, 110]}, {arco: [60, 70, 40, 90, 180]}],
    paredes: [], caixas: [],
    largada: {x: 75, y: 30, ang: 0},
    dica: 'Para os seguidores de linha (exemplos 3, 4 e 9).',
  },
  {
    id: 'quadrado', nome: 'Quadrado (cantos de 90°)', largura: 180, altura: 160,
    linhas: caminho([[35, 25], [145, 25], [145, 135], [35, 135]], true),
    paredes: [], caixas: [],
    largada: {x: 60, y: 25, ang: 0},
    dica: 'Cantos retos: o seguidor precisa de uma estratégia para a curva de 90°.',
  },
  {
    id: 'curvas90', nome: 'Curvas de 90° e falha na linha', largura: 240, altura: 170,
    linhas: [...comFalha(30, 30, 210, 30, 95, 10),
             ...caminho([[210, 30], [210, 140], [150, 140], [150, 85], [90, 85], [90, 140], [30, 140], [30, 30]], false)],
    paredes: [], caixas: [],
    largada: {x: 55, y: 30, ang: 0},
    dica: 'Curvas de 90° para os dois lados e uma falha de 10 cm na reta de cima (exemplo 10).',
  },
  {
    id: 'arena', nome: 'Arena com obstáculo', largura: 200, altura: 160,
    linhas: [], paredes: contorno(200, 160), caixas: [{x: 100, y: 66, w: 25, h: 25}],
    largada: {x: 40, y: 80, ang: 0},
    dica: 'Para o exemplo 5: arraste a caixa para mudar o obstáculo de lugar.',
  },
];

// ---------------------------------------------------------------- chão

function distSegmento(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1;
  const L2 = dx * dx + dy * dy;
  let t = L2 ? ((px - x1) * dx + (py - y1) * dy) / L2 : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

function distArco(px, py, cx, cy, r, inicio, varredura) {
  const a0 = inicio * Math.PI / 180, va = varredura * Math.PI / 180;
  let a = Math.atan2(py - cy, px - cx) - (va >= 0 ? a0 : a0 + va);
  a = ((a % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  if (a <= Math.abs(va)) return Math.abs(Math.hypot(px - cx, py - cy) - r);
  const e1 = [cx + r * Math.cos(a0), cy + r * Math.sin(a0)];
  const e2 = [cx + r * Math.cos(a0 + va), cy + r * Math.sin(a0 + va)];
  return Math.min(Math.hypot(px - e1[0], py - e1[1]), Math.hypot(px - e2[0], py - e2[1]));
}

const BRANCO = [1, 1, 1], PRETO = [0, 0, 0], FORA = [0.05, 0.05, 0.05];

/* Cor do chão no ponto (x, y): [r, g, b] de 0 a 1. Fora da mesa é quase preto (nada reflete). */
function corDoChao(pista, x, y) {
  if (x < 0 || y < 0 || x > pista.largura || y > pista.altura) return FORA;
  const meia = LINHA / 2;
  for (const t of pista.linhas) {
    const d = t.seg ? distSegmento(x, y, ...t.seg) : distArco(x, y, ...t.arco);
    if (d <= meia) return PRETO;
  }
  return BRANCO;
}

// ---------------------------------------------------------------- paredes e caixas

/* Segmentos sólidos (paredes e lados das caixas) */
function solidos(pista) {
  const lista = pista.paredes.map(p => p.slice());
  for (const c of pista.caixas) {
    lista.push([c.x, c.y, c.x + c.w, c.y], [c.x + c.w, c.y, c.x + c.w, c.y + c.h],
               [c.x + c.w, c.y + c.h, c.x, c.y + c.h], [c.x, c.y + c.h, c.x, c.y]);
  }
  return lista;
}

/* Distância ao longo do raio (x, y) + t*(dx, dy) até o primeiro sólido, ou Infinity. */
function raio(pista, x, y, dx, dy) {
  let melhor = Infinity;
  for (const [x1, y1, x2, y2] of solidos(pista)) {
    const ex = x2 - x1, ey = y2 - y1;
    const den = dx * ey - dy * ex;
    if (Math.abs(den) < 1e-12) continue;
    const t = ((x1 - x) * ey - (y1 - y) * ex) / den;
    const u = ((x1 - x) * dy - (y1 - y) * dx) / den;
    if (t >= 0 && u >= 0 && u <= 1 && t < melhor) melhor = t;
  }
  return melhor;
}

function copiaPista(p) {
  return JSON.parse(JSON.stringify(p));
}

EST.LINHA = LINHA;
EST.PAREDE = PAREDE;
EST.PISTAS = PISTAS;
EST.corDoChao = corDoChao;
EST.FORA = FORA;
EST.solidos = solidos;
EST.raio = raio;
EST.distSegmento = distSegmento;
EST.copiaPista = copiaPista;
})();
