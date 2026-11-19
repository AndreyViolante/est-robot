'use strict';
/* Testes da arena da OBR do simulador (simulador/obr.js): as arenas prontas passam na conferência e a
   pontuação de uma rodada sai como no manual da OBR 2026. Um "robô perfeito" anda pelo meio dos ladrilhos.
   Uso: node ferramentas/teste_obr.js   (o GitHub roda a cada envio) */
const path = require('path');
globalThis.EST = {};
require(path.join(__dirname, '..', 'simulador', 'mundo.js'));
require(path.join(__dirname, '..', 'simulador', 'obr.js'));
const {OBR} = globalThis.EST;

let falhas = 0;
function confere(nome, ok, detalhe = '') {
  console.log(`  ${ok ? 'OK   ' : 'FALHA'} ${nome}${detalhe ? ` (${detalhe})` : ''}`);
  if (!ok) falhas++;
}

const centro = t => [OBR.BORDA + t.c * OBR.LADO + OBR.LADO / 2, OBR.BORDA + t.r * OBR.LADO + OBR.LADO / 2];

/* anda de ladrilho em ladrilho (pelos centros) a 20 cm/s; desvio = {i: [c, r]} faz o robô ir para outro
   ladrilho depois do ladrilho i, na primeira vez. Devolve o placar no fim. */
function rodada(pista, desvio = {}) {
  const placar = new OBR.Placar(pista), perc = pista.obr.arena.percurso;
  let t = 0, x, y, i = 0, desviou = false;
  [x, y] = [pista.largada.x, pista.largada.y];
  const anda = alvo => {
    for (let n = 0; n < 2000; n++) {
      const dx = alvo[0] - x, dy = alvo[1] - y, d = Math.hypot(dx, dy);
      if (d < 0.5) return null;
      const passo = Math.min(1, d);
      x += dx / d * passo; y += dy / d * passo; t += 0.05;
      const r = placar.passo({t, x, y, parado: 0, sobreVermelho: false});
      if (r) return r;
    }
    return null;
  };
  while (!placar.fim && t < OBR.RODADA) {
    let alvo = centro(perc[i + 1] || perc[i]);
    if (desvio[i] && !desviou) { alvo = [OBR.BORDA + desvio[i][0] * 30 + 15, OBR.BORDA + desvio[i][1] * 30 + 15]; desviou = true; }
    if (!perc[i + 1]) {                         // na chegada: para em cima da faixa vermelha
      for (let s = 0; s <= 6 && !placar.fim; s += 0.05) placar.passo({t: t += 0.05, x, y, parado: s, sobreVermelho: true});
      break;
    }
    const r = anda(alvo);
    if (r && r.falha) { [x, y] = [r.largada.x, r.largada.y]; i = placar.k; continue; }
    i = placar.k;
  }
  return placar;
}

console.log('Arena da OBR (simulador/obr.js):');
for (const a of OBR.ARENAS) {
  const erros = OBR.conferir(a.arena);
  confere(`${a.nome}: arena válida`, erros.length === 0, erros.join('; '));
}

const treino = OBR.montar(OBR.ARENAS[0].arena, 'obr-treino', '');
let p = rodada(treino);
confere('treino: rodada perfeita = 150 pontos (início 5 + ladrilhos 25 + 50 + gap 10 + chegada 60)',
        p.total === 150 && p.falhas === 0, `deu ${p.total}, ${p.falhas} falhas`);

const completa = OBR.montar(OBR.ARENAS[1].arena, 'obr-completa', '');
confere('completa: 4 quadrados verdes (curva, beco com dois, volta do beco)', completa.verdes.length === 4,
        `tem ${completa.verdes.length}`);
const decisoes = completa.obr.arena.percurso.map((_, i) => OBR.decisao(completa, i));
confere('completa: verdes mandam esquerda no 6, reto no 10 e no 16, meia-volta no 17, direita no 18',
        decisoes[5] === 'esquerda' && decisoes[9] === 'reto' && decisoes[15] === 'reto' && decisoes[16] === 'meia-volta' &&
        decisoes[17] === 'direita', decisoes.slice(5, 18).join(','));
p = rodada(completa);
confere('completa: rodada perfeita = 245 pontos (início 5 + ladrilhos 30+35+35 + perigos 80 + chegada 60)',
        p.total === 245 && p.falhas === 0, `deu ${p.total}, ${p.falhas} falhas`);

p = rodada(completa, {5: [6, 3]});           // no verde do ladrilho 6, segue reto em vez de virar
confere('completa: errar o verde = falha de progresso, volta à partida e a 2ª tentativa vale 3 por ladrilho (228)',
        p.falhas === 1 && p.total === 228, `deu ${p.total}, ${p.falhas} falhas`);

// parado 10 s fora da chegada
const parado = new OBR.Placar(treino);
let r = null;
for (let s = 0; s <= 10.1 && !r; s += 0.1) r = parado.passo({t: s, x: treino.largada.x, y: treino.largada.y, parado: s, sobreVermelho: false});
confere('parado 10 s = falha de progresso', !!(r && r.falha), r ? r.falha : 'nada');

// empurrando a caixa: tremendo no lugar (sem nunca ficar exatamente parado) por 10 s também é falha
const tremendo = new OBR.Placar(treino);
r = null;
for (let s = 0; s <= 10.2 && !r; s += 0.05) {
  r = tremendo.passo({t: s, x: treino.largada.x + Math.sin(s * 20) * 0.6, y: treino.largada.y, parado: 0, sobreVermelho: false});
}
confere('empurrando a caixa (tremendo no lugar) 10 s = falha de progresso', !!(r && r.falha), r ? r.falha : 'nada');

// conferência pega erros de arena
const ruim = {colunas: 3, linhas: 3, nivel: 1, percurso: OBR.percursoDe('0,0 1,0:g10 1,1 2,1:g15')};
const errosRuim = OBR.conferir(ruim);
confere('conferência: gap na curva e gap maior que 10 cm no nível 1', errosRuim.length === 2, errosRuim.join('; '));

// arena sorteada: o mesmo número dá a mesma arena; todas passam na conferência, sem cair na arena de reserva; as
// linhas que saem das interseções para o lado não encostam em outro ladrilho do caminho (não fazem atalho)
confere('arena sorteada: o mesmo número dá a mesma arena',
  JSON.stringify(OBR.sortear(4821)) === JSON.stringify(OBR.sortear(4821)) &&
  JSON.stringify(OBR.sortear(4821)) !== JSON.stringify(OBR.sortear(4822)));
const reserva = JSON.stringify(OBR.ARENAS[0].arena);
const problemas = [], perigos = {gap: 0, obstaculo: 0, beco: 0, T: 0, cruz: 0};
for (let n = 1; n <= 300; n++) {
  const a = OBR.sortear(n), erros = OBR.conferir(a), tipos = OBR.tiposDoPercurso(a.percurso);
  if (JSON.stringify(a) === reserva) problemas.push(`${n}: caiu na reserva`);
  if (erros.length) problemas.push(`${n}: ${erros.join('; ')}`);
  // atalho: um ponto da beirada entre dois ladrilhos aonde chegam linhas dos DOIS, sem eles se seguirem no caminho
  const p = OBR.montar(a, 'x', 'x'), naBeirada = new Map();
  for (const s of p.linhas) {
    if (!s.seg) continue;
    const [x1, y1, x2, y2] = s.seg;
    const dono = `${Math.floor(((x1 + x2) / 2 - OBR.BORDA) / OBR.LADO)},${Math.floor(((y1 + y2) / 2 - OBR.BORDA) / OBR.LADO)}`;
    for (const [x, y] of [[x1, y1], [x2, y2]]) {
      const c = (x - OBR.BORDA) / OBR.LADO, r = (y - OBR.BORDA) / OBR.LADO;
      if (Number.isInteger(c) === Number.isInteger(r)) continue;          // centro ou canto: não é beirada
      const k = `${x},${y}`;
      if (!naBeirada.has(k)) naBeirada.set(k, new Set());
      naBeirada.get(k).add(dono);
    }
  }
  const seguem = new Set(a.percurso.slice(1).map((t, i) => [`${t.c},${t.r}`, `${a.percurso[i].c},${a.percurso[i].r}`].sort().join('|')));
  for (const donos of naBeirada.values()) {
    const d = [...donos].sort();
    if (d.length > 1 && !seguem.has(d.join('|'))) problemas.push(`${n}: linhas de ${d.join(' e ')} se encontram, sem eles se seguirem`);
  }
  a.percurso.forEach((t, i) => { if (t.elemento) perigos[t.elemento]++; if (tipos[i].tipo === 'beco') perigos.beco++; });
}
confere('arena sorteada: 300 números, todas válidas e sem atalho', !problemas.length, problemas.slice(0, 5).join(' | '));
confere('arena sorteada: aparecem gap, obstáculo, beco, T e cruz',
  Object.values(perigos).every(v => v > 0), JSON.stringify(perigos));

console.log(falhas ? `\narena da OBR: ${falhas} FALHA(S)` : '\narena da OBR: OK');
process.exit(falhas ? 1 : 0);
