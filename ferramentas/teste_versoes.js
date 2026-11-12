// Testa as versões do programa da página de programar (docs/programar/versoes.js), sem navegador: guardar, não
// repetir, o limite de versões e de espaço, o navegador cheio, voltar para uma versão e os textos da lista.
// Uso: node ferramentas/teste_versoes.js
'use strict';
const fs = require('fs');
const path = require('path');

new Function(fs.readFileSync(path.join(__dirname, '..', 'docs', 'programar', 'versoes.js'), 'utf8'))();
const V = globalThis.ESTVersoes;

/* um localStorage de mentira; com limite, ele recusa gravar acima de tantos caracteres (navegador cheio) */
function armazenamento(limite = Infinity) {
  const dados = new Map();
  return {
    getItem: k => (dados.has(k) ? dados.get(k) : null),
    setItem: (k, v) => {
      if (String(v).length > limite) throw new Error('QuotaExceededError');
      dados.set(k, String(v));
    },
    dados,
  };
}

let falhas = 0;
function confere(nome, certo, detalhe = '') {
  if (!certo) falhas++;
  console.log(`  ${certo ? 'OK   ' : 'FALHA'} versões: ${nome}${certo ? '' : ` -> ${detalhe}`}`);
}

let relogio = Date.UTC(2026, 10, 12, 13, 0, 0);
const agora = () => relogio;

// guardar, mais nova primeiro, e não repetir quando nada mudou
{
  const a = armazenamento(), v = V.criar(a, agora);
  const p1 = 'from robo import *\n\nandar_cm(10)\n';
  const g1 = v.guardar({fonte: p1, nome: 'meu', motivo: 'simulou'});
  relogio += 1000;
  const repetida = v.guardar({fonte: p1, nome: 'meu', motivo: 'Ctrl+S'});
  relogio += 1000;
  v.guardar({fonte: p1 + 'bip()\n', nome: 'meu', motivo: 'enviou ao robô'});
  const l = v.lista();
  confere('guarda e não repete quando nada mudou', g1 && !repetida && l.length === 2 && l[0].motivo === 'enviou ao robô' &&
          l[1].fonte === p1 && l[0].quando > l[1].quando, JSON.stringify(l.map(x => x.motivo)));
  confere('acha e apaga uma versão', v.achar(l[1].id).fonte === p1 && v.apagar(l[1].id) && v.lista().length === 1 &&
          !v.achar(l[1].id));
  confere('programa vazio não vira versão', v.guardar({fonte: '  \n', nome: 'x'}) === null && v.lista().length === 1);
}

// no máximo 30: a mais velha sai
{
  const v = V.criar(armazenamento(), agora);
  for (let i = 0; i < 35; i++) { relogio += 1000; v.guardar({fonte: `mostrar(${i})\n`, nome: 'p', motivo: 'simulou'}); }
  const l = v.lista();
  confere(`no máximo ${V.MAXIMO} versões, sai a mais velha`, l.length === V.MAXIMO && l[0].fonte === 'mostrar(34)\n' &&
          l[l.length - 1].fonte === 'mostrar(5)\n', `${l.length} versões`);
}

// navegador cheio: tira as mais velhas até caber, e a nova fica
{
  const a = armazenamento(9000), v = V.criar(a, agora);
  const grande = n => `# ${'x'.repeat(2000)}\nmostrar(${n})\n`;
  let todas = true;
  for (let i = 0; i < 8; i++) { relogio += 1000; todas = todas && !!v.guardar({fonte: grande(i), nome: 'p'}); }
  const l = v.lista();
  confere('navegador cheio: as mais velhas saem e a nova fica', todas && l.length >= 1 && l.length < 8 &&
          l[0].fonte === grande(7) && a.getItem(V.CHAVE).length <= 9000, `${l.length} versões`);
}

// guardado estragado ou sem armazenamento: a lista fica vazia e a página continua
{
  const a = armazenamento();
  a.setItem(V.CHAVE, '{isto não é json');
  const v = V.criar(a, agora);
  const ok = v.lista().length === 0 && !!v.guardar({fonte: 'bip()\n', nome: 'p'}) && v.lista().length === 1;
  const semNada = V.criar({getItem() { throw new Error('bloqueado'); }, setItem() { throw new Error('bloqueado'); }}, agora);
  confere('guardado estragado ou navegador sem armazenamento', ok && semNada.lista().length === 0 &&
          semNada.guardar({fonte: 'bip()\n'}) === null && semNada.idadeDaMaisNova() === Infinity);
}

// versão dos blocos: guarda a área de blocos e só repete se nem o Python nem os blocos mudaram
{
  const v = V.criar(armazenamento(), agora);
  const area = {blocks: {blocks: [{type: 'robo_inicio', id: 'a'}]}};
  v.guardar({fonte: 'from robo import *\n', nome: 'p', modo: 'blocos', blocos: area});
  relogio += 1000;
  const igual = v.guardar({fonte: 'from robo import *\n', nome: 'p', modo: 'blocos', blocos: JSON.parse(JSON.stringify(area))});
  const outra = v.guardar({fonte: 'from robo import *\n', nome: 'p', modo: 'blocos', blocos: {blocks: {blocks: []}}});
  confere('versão dos blocos guarda a área de blocos', !igual && !!outra && v.lista().length === 2 &&
          v.lista()[1].blocos.blocks.blocks[0].type === 'robo_inicio');
}

// de quanto tempo é a versão mais nova (a página guarda outra enquanto o aluno escreve, a cada 5 minutos)
{
  const v = V.criar(armazenamento(), agora);
  const antes = v.idadeDaMaisNova();
  v.guardar({fonte: 'bip()\n'});
  relogio += 6 * 60 * 1000;
  confere('idade da versão mais nova', antes === Infinity && v.idadeDaMaisNova() === 6 * 60 * 1000);
}

// os textos da lista: quando foi guardada e quanto muda do programa de agora
{
  const base = new Date(2026, 10, 12, 15, 30).getTime();
  const casos = [
    [base - 20 * 1000, 'agora há pouco'], [base - 5 * 60 * 1000, 'há 5 min'],
    [new Date(2026, 10, 12, 9, 5).getTime(), 'hoje às 09:05'], [new Date(2026, 10, 11, 16, 3).getTime(), 'ontem às 16:03'],
    [new Date(2026, 9, 2, 8, 0).getTime(), '02/10 às 08:00'], [new Date(2025, 11, 31, 23, 59).getTime(), '31/12/2025 às 23:59'],
  ];
  const errados = casos.filter(([ms, texto]) => V.quando(ms, base) !== texto).map(([ms, t]) => `${t} != ${V.quando(ms, base)}`);
  confere('quando cada versão foi guardada', !errados.length, errados.join('; '));
  const prog = 'from robo import *\n\nandar_cm(10)\nvirar_direita()\n';
  const d0 = V.diferenca(prog, prog);
  const d1 = V.diferenca(prog, prog.replace('andar_cm(10)', 'andar_cm(20)'));
  const d2 = V.diferenca(prog, prog + 'bip()\nesperar(1)\n');
  const d3 = V.diferenca(prog.replace(/\n/g, '\r\n'), prog);
  confere('linhas diferentes do programa de agora', d0.mais === 0 && d0.menos === 0 && d1.mais === 1 && d1.menos === 1 &&
          d2.mais === 0 && d2.menos === 2 && d3.mais === 0 && d3.menos === 0, JSON.stringify([d0, d1, d2, d3]));
  const enorme = Array.from({length: 3000}, (_, i) => `mostrar(${i})`).join('\n');
  const dg = V.diferenca(enorme, enorme.replace('mostrar(7)', 'mostrar(-7)'));
  confere('programa enorme também compara', dg.mais === 1 && dg.menos === 1, JSON.stringify(dg));
}

console.log(`\nversões do programa: ${falhas ? `${falhas} FALHA(S)` : 'OK'}`);
process.exit(falhas ? 1 : 0);
