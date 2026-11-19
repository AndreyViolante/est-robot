'use strict';
/* Testes da impressão da arena da OBR (simulador/imprimir.js), sem navegador: 4 folhas por ladrilho, cada parte
   com 15 cm de verdade (150 mm e 15 unidades de cm no desenho), o beco não sai duas vezes, e o desenho tem a
   linha, os verdes, a faixa vermelha e o lugar do obstáculo.
   Uso: node ferramentas/teste_impressao.js   (o GitHub roda a cada envio) */
const fs = require('fs');
const path = require('path');
for (const f of ['mundo.js', 'obr.js', 'imprimir.js']) {
  new Function(fs.readFileSync(path.join(__dirname, '..', 'simulador', f), 'utf8'))();
}
const EST = globalThis.EST, O = EST.OBR, I = EST.ImprimirArena;

let falhas = 0;
function confere(nome, ok, detalhe = '') {
  console.log(`  ${ok ? 'OK   ' : 'FALHA'} impressão: ${nome}${ok || !detalhe ? '' : ` -> ${detalhe}`}`);
  if (!ok) falhas++;
}

const completa = O.ARENAS.find(a => a.id === 'obr-completa');
const pista = O.montar(completa.arena, completa.id, completa.nome);
const html = I.paginas(pista);
const unicos = new Set(completa.arena.percurso.map(t => `${t.c},${t.r}`)).size;
const folhas = (html.match(/<section class="folha/g) || []).length;
confere('uma capa e 4 folhas por ladrilho (sem repetir o do beco)', folhas === 1 + 4 * unicos && I.ladrilhos(pista).length === unicos,
        `${folhas} folhas, ${unicos} ladrilhos`);
const partes = [...html.matchAll(/<svg class="parte" width="([\d.]+)mm" height="([\d.]+)mm" viewBox="([\d. -]+)"/g)];
confere('cada parte tem 150 mm e mostra 15 cm (tamanho real)',
        partes.length === 4 * unicos && partes.every(m => m[1] === '150' && m[2] === '150' && m[3].split(' ').slice(2).join(' ') === '15 15'),
        partes.slice(0, 2).map(m => m.slice(1).join(' ')).join(' | '));
const primeiro = completa.arena.percurso[0], {LADO, BORDA} = O;
const esperado = `${BORDA + primeiro.c * LADO} ${BORDA + primeiro.r * LADO} 15 15`;
confere('a primeira parte é o canto de cima à esquerda do ladrilho 1 (a partida)', partes[0] && partes[0][3] === esperado,
        `${partes[0] && partes[0][3]} / ${esperado}`);
confere('o desenho tem linha de 2 cm, verde, faixa vermelha e o obstáculo',
        html.includes('stroke-width="2"') && html.includes('#00a651') && html.includes('#e2231a') && html.includes('>obstáculo<'));
confere('A4 em pé, uma parte por folha', /@page \{ size: A4 portrait/.test(html) && /page-break-after: always/.test(html));
const curva = O.montar(O.sortear(7), 'x', 'x');
const arcos = (I.paginas(curva).match(/<path d="M /g) || []).length;
confere('curva suave vira arco no desenho (arena sorteada nº 7)', arcos > 0 || !curva.linhas.some(t => t.arco), `${arcos} arcos`);
let erro = '';
try { I.paginas({nome: 'oval', linhas: []}); } catch (e) { erro = e.message; }
confere('pista que não é arena da OBR: avisa', erro.includes('arena da OBR'), erro);

console.log(falhas ? `\nimpressão da arena: ${falhas} FALHA(S)` : '\nimpressão da arena: OK');
process.exit(falhas ? 1 : 0);
