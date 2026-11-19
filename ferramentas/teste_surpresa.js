'use strict';
/* Testes do desafio surpresa do simulador (simulador/desafios.js): a mesma semente dá a mesma arena e a mesma
   tarefa, toda tarefa aparece, e a conferência de cada tarefa aceita quem fez e recusa quem não fez, com o motivo.
   O percurso em si é o do desafio da OBR (testado com os programas de referência, que não ficam no projeto);
   aqui a prova começa com os marcos já passados e só a tarefa muda.
   Uso: node ferramentas/teste_surpresa.js   (o GitHub roda a cada envio) */
const fs = require('fs');
const path = require('path');
for (const f of ['mundo.js', 'robo.js', 'desafios.js', 'obr.js']) {
  new Function(fs.readFileSync(path.join(__dirname, '..', 'simulador', f), 'utf8'))();
}
const EST = globalThis.EST, {LADO, BORDA} = EST.OBR;

let falhas = 0;
function confere(nome, ok, detalhe = '') {
  console.log(`  ${ok ? 'OK   ' : 'FALHA'} surpresa: ${nome}${ok || !detalhe ? '' : ` -> ${detalhe}`}`);
  if (!ok) falhas++;
}

// mesma semente, mesma arena e mesma tarefa; todas as tarefas aparecem; sementes vizinhas variam
const porTarefa = {}, sementes = {};
let iguais = true, vizinhasIguais = 0;
for (let s = 1; s <= 400; s++) {
  const a = EST.desafioSurpresa(s), b = EST.desafioSurpresa(s);
  if (a.tarefa.id !== b.tarefa.id || JSON.stringify(a.arena) !== JSON.stringify(b.arena)) iguais = false;
  porTarefa[a.tarefa.id] = (porTarefa[a.tarefa.id] || 0) + 1;
  (sementes[a.tarefa.id] = sementes[a.tarefa.id] || []).push(s);
  if (s > 1 && EST.desafioSurpresa(s - 1).tarefa.id === a.tarefa.id) vizinhasIguais++;
  if (!a.lugares.length) iguais = false;
}
confere('a mesma semente dá a mesma arena e a mesma tarefa (com lugar na arena)', iguais);
confere('todas as tarefas aparecem em 400 sementes',
        EST.TAREFAS_SURPRESA.every(t => porTarefa[t.id] >= 5), JSON.stringify(porTarefa));
confere('sementes vizinhas quase sempre trocam de tarefa', vizinhasIguais < 400 * 0.3, `${vizinhasIguais} iguais`);

/* uma prova da tarefa: o robô parado no meio do ladrilho de cada lugar (faz a tarefa lá, se fizer) e depois 5 s
   parado na faixa vermelha. faz(s, k): muda o estado no lugar k; noFim(s): muda o estado na chegada. */
function prova(d, faz = () => {}, noFim = () => {}) {
  const p = {marcos: [d.marcos[0].length]};                      // percurso já feito: só a tarefa conta
  const s = {t: 0, x: 0, y: 0, frente: [0, 0], parado: 0, terminou: false, batidas: 0, pista: d.pista,
             sobreVermelho: false, luz: null, sons: 0, tela: []};
  const em = (x, y) => Object.assign(s, {x, y, frente: [x, y]});
  for (const k of d.lugares) {
    const [c, r] = k.split(',').map(Number);
    em(BORDA + c * LADO + LADO / 2, BORDA + r * LADO + LADO / 2);
    s.parado = 0;
    for (let i = 0; i < 40; i++) {
      s.t += 0.1;
      s.parado += 0.1;
      if (i === 5) faz(s, k);
      const r1 = d.verificar(p, s);
      if (r1) return r1;
    }
  }
  const v = d.pista.vermelhos[0];
  em(v.x + v.w / 2, v.y + v.h / 2);
  s.sobreVermelho = true;
  s.parado = 0;
  noFim(s);
  for (let i = 0; i < 60; i++) {
    s.t += 0.1;
    s.parado += 0.1;
    const r2 = d.verificar(p, s);
    if (r2) return r2;
  }
  return null;
}

const motivo = r => (r ? (r.ok ? 'cumpriu' : r.motivo) : 'sem resultado');
const bip = n => s => { s.sons += n; };
const casos = {
  'bips-gap': {feito: [bip(2)], errado: [[bip(1), 'deu 1 de 2 bips no gap'], [bip(3), 'deu 3 bips no gap (eram 2)']]},
  'parar-gap': {feito: [() => {}], errado: [[s => { s.parado = -10; }, 'não parou 2 s no gap']]},
  'luz-obstaculo': {feito: [s => { s.luz = 2; }, s => { s.luz = 0; }],
                    errado: [[null, 'não acendeu a luz vermelha no desvio do obstáculo'],
                             [s => { s.luz = 2; }, 'a luz não estava azul na chegada']]},
  'luz-verde': {feito: [s => { s.luz = 1; }, s => { s.luz = 0; }],
                errado: [[s => { s.luz = 2; }, 'não acendeu a luz roxa nas interseções com verde']]},
  'parar-verde': {feito: [() => {}], errado: [[s => { s.parado = -10; }, 'parou 3 s em 0 de']]},
  'bips-beco': {feito: [bip(3)], errado: [[bip(2), 'deu 2 de 3 bips no beco sem saída']]},
  'fim-na-tela': {feito: [null, s => { s.tela = ['FIM']; }],
                  errado: [[null, 'não mostrou FIM na tela na chegada']]},
  'notas-chegada': {feito: [bip(3)], errado: [[bip(4), 'tocou 4 notas na chegada (eram 3)']]},
};
for (const t of EST.TAREFAS_SURPRESA) {
  const caso = casos[t.id];
  if (!caso) { confere(`${t.id}: tem caso de teste`, false); continue; }
  const d = EST.desafioSurpresa(sementes[t.id][0]);
  // feito: [no lugar, na chegada]; na chegada (tarefa de chegada), "no lugar" é a própria faixa: faz no fim
  const [noLugar, naChegada] = caso.feito;
  const r = t.onde === 'chegada' ? prova(d, () => {}, s => { (naChegada || noLugar)(s); })
                                 : prova(d, noLugar || (() => {}), naChegada || (() => {}));
  confere(`${t.id}: quem faz a tarefa cumpre`, r && r.ok, motivo(r));
  for (const [errado, esperado] of caso.errado) {
    const f = errado || (() => {});
    const r2 = t.onde === 'chegada' ? prova(d, () => {}, f) : prova(d, f, t.luz !== undefined ? s => { if (s.luz === null) s.luz = 0; } : () => {});
    confere(`${t.id}: avisa "${esperado}"`, r2 && !r2.ok && r2.motivo.includes(esperado), motivo(r2));
  }
}
{
  const d = EST.desafioSurpresa(sementes['fim-na-tela'][0]);
  const p = {marcos: [d.marcos[0].length]};
  const r = d.verificar(p, {t: 1, x: d.largada.x, y: d.largada.y, frente: [d.largada.x, d.largada.y], parado: 0,
                            terminou: false, batidas: 0, pista: d.pista, sobreVermelho: false, luz: null, sons: 0, tela: ['FIM']});
  confere('fim-na-tela: FIM antes da chegada já falha', r && !r.ok && r.motivo.includes('antes da chegada'), motivo(r));
}

console.log(falhas ? `\ndesafio surpresa: ${falhas} FALHA(S)` : '\ndesafio surpresa: OK');
process.exit(falhas ? 1 : 0);
