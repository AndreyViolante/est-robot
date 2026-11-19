// Testa o "Salvar/Carregar progresso" (simulador/progresso.js), sem navegador: o arquivo leva o que o EST-LAB guarda
// no navegador, volta igual em outro navegador, recusa arquivos que não são progresso e não deixa nada pela metade
// quando o navegador está cheio.
// Uso: node ferramentas/teste_progresso.js
'use strict';
const fs = require('fs');
const path = require('path');

new Function(fs.readFileSync(path.join(__dirname, '..', 'simulador', 'progresso.js'), 'utf8'))();
const P = globalThis.EST.Progresso;

/* um localStorage de mentira; com limite, recusa gravar acima de tantos caracteres no total (navegador cheio) */
function armazenamento(inicial = {}, limite = Infinity) {
  const dados = new Map(Object.entries(inicial));
  const total = () => [...dados.values()].reduce((s, v) => s + v.length, 0);
  return {
    getItem: k => (dados.has(k) ? dados.get(k) : null),
    setItem: (k, v) => {
      const antes = dados.get(k);
      dados.set(k, String(v));
      if (total() > limite) {
        if (antes == null) dados.delete(k); else dados.set(k, antes);
        throw new Error('QuotaExceededError');
      }
    },
    removeItem: k => dados.delete(k),
    dados,
  };
}

let falhas = 0;
function confere(nome, certo, detalhe = '') {
  if (!certo) falhas++;
  console.log(`  ${certo ? 'OK   ' : 'FALHA'} progresso: ${nome}${certo ? '' : ` -> ${detalhe}`}`);
}
const erroDe = f => { try { f(); return ''; } catch (e) { return e.message; } };

const SIMULADOR = {desafios: {andar30: {feito: true, tempo: 3.2}, quadrado: {feito: true, tempo: 9}, caixa: {feito: false}},
                   arenaOBR: {colunas: 6, linhas: 4, nivel: 1, percurso: [{c: 0, r: 1}, {c: 1, r: 1}, {c: 2, r: 1}]},
                   minha: {largura: 200, altura: 150, linhas: [[10, 10, 50, 10]]}, sementeOBR: 1234, velocidade: 2};
const PROGRAMA = {fonte: 'from robo import *\n\nandar_cm(30)\n', nome: 'meu_programa', modo: 'python'};
const VERSOES = [{fonte: 'from robo import *\n', quando: 1, motivo: 'simulou'}, {fonte: 'bip()\n', quando: 2}];

// salvar num navegador e carregar em outro: tudo volta igual
{
  const a = armazenamento({'est-simulador-v1': JSON.stringify(SIMULADOR), 'est-programar-v1': JSON.stringify(PROGRAMA),
                           'est-programar-versoes-v1': JSON.stringify(VERSOES), 'outra-pagina': '{"x": 1}'});
  const progresso = P.juntar(a, new Date(Date.UTC(2026, 10, 19, 15)));
  const arquivo = P.texto(progresso);
  confere('o arquivo diz que é do EST-LAB e quando foi salvo',
          progresso.formato === 'est-lab-progresso' && progresso.salvoEm === '2026-11-19T15:00:00.000Z', arquivo.slice(0, 80));
  confere('só o que é do EST-LAB vai para o arquivo',
          Object.keys(progresso.dados).sort().join() === 'est-programar-v1,est-programar-versoes-v1,est-simulador-v1',
          Object.keys(progresso.dados).join());
  const b = armazenamento({'est-programar-blocos-v1': '{"velho": true}'});
  const gravadas = P.aplicar(P.ler(arquivo), b);
  confere('carregado em outro navegador, volta igual', gravadas.length === 3
          && JSON.stringify(JSON.parse(b.getItem('est-simulador-v1'))) === JSON.stringify(SIMULADOR)
          && JSON.stringify(JSON.parse(b.getItem('est-programar-v1'))) === JSON.stringify(PROGRAMA)
          && JSON.stringify(JSON.parse(b.getItem('est-programar-versoes-v1'))) === JSON.stringify(VERSOES),
          JSON.stringify([...b.dados.keys()]));
  confere('o que o arquivo não tem continua no navegador', b.getItem('est-programar-blocos-v1') === '{"velho": true}');
  const partes = P.resumo(progresso);
  confere('o resumo conta desafios, arena, pista, programa e versões',
          P.juntarComVirgulas(partes) === '2 desafios cumpridos, Minha arena OBR com 3 ladrilhos, Minha pista, '
                                          + 'o programa meu_programa.py e 2 versões guardadas', P.juntarComVirgulas(partes));
  confere('nome do arquivo com a data', P.nomeDoArquivo(new Date(2026, 10, 9)) === 'progresso-est-lab-2026-11-09.json',
          P.nomeDoArquivo(new Date(2026, 10, 9)));
}

// guardado estragado no navegador fica de fora (não impede salvar o resto)
{
  const a = armazenamento({'est-simulador-v1': '{estragado', 'est-programar-v1': JSON.stringify(PROGRAMA)});
  const p = P.juntar(a);
  confere('guardado estragado fica de fora', Object.keys(p.dados).join() === 'est-programar-v1', Object.keys(p.dados).join());
}

// arquivos que não são progresso: uma mensagem em português, e nada muda
{
  const ruins = {'texto qualquer': 'from robo import *\n', 'JSON de outra coisa': '{"pista": 1}',
                 'progresso sem dados': '{"formato": "est-lab-progresso", "versao": 1}',
                 'lista': '[1, 2, 3]', 'vazio': ''};
  const erros = Object.entries(ruins).map(([nome, t]) => [nome, erroDe(() => P.ler(t))]);
  confere('recusa o que não é progresso do EST-LAB', erros.every(([, e]) => e.includes('não é um progresso do EST-LAB')),
          JSON.stringify(erros));
  const novo = JSON.stringify({formato: 'est-lab-progresso', versao: 2, dados: {}});
  confere('progresso de uma versão mais nova pede para atualizar', erroDe(() => P.ler(novo)).includes('atualize a página'),
          erroDe(() => P.ler(novo)));
  const comBom = '﻿' + P.texto({formato: 'est-lab-progresso', versao: 1, salvoEm: '', dados: {'est-programar-v1': PROGRAMA}});
  confere('aceita o arquivo com BOM (salvo pelo Bloco de Notas)', !erroDe(() => P.ler(comBom)), erroDe(() => P.ler(comBom)));
  const estranho = P.ler(JSON.stringify({formato: 'est-lab-progresso', versao: 1,
                                         dados: {'est-simulador-v1': SIMULADOR, 'chave-estranha': {a: 1}}}));
  confere('chaves que não são do EST-LAB ficam de fora', Object.keys(estranho.dados).join() === 'est-simulador-v1',
          Object.keys(estranho.dados).join());
}

// navegador cheio: não fica nada pela metade
{
  const antes = {'est-simulador-v1': JSON.stringify({desafios: {}}), 'est-programar-v1': JSON.stringify({fonte: 'x'})};
  const a = armazenamento(antes, 200);
  const grande = {formato: 'est-lab-progresso', versao: 1, salvoEm: '',
                  dados: {'est-simulador-v1': SIMULADOR, 'est-programar-v1': {fonte: 'y'.repeat(500)}}};
  const erro = erroDe(() => P.aplicar(P.ler(JSON.stringify(grande)), a));
  confere('navegador cheio: avisa e desfaz', erro.includes('não deixou guardar')
          && a.getItem('est-simulador-v1') === antes['est-simulador-v1'] && a.getItem('est-programar-v1') === antes['est-programar-v1'],
          `${erro}; ${JSON.stringify([...a.dados])}`);
}

console.log(`\nprogresso em arquivo: ${falhas ? `${falhas} FALHA(S)` : 'OK'}`);
process.exit(falhas ? 1 : 0);
