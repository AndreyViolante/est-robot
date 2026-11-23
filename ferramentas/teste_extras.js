'use strict';
/* Testes dos extras com código (simulador/cifra.js e os ganchos EXTRAS do mundo.js), sem navegador: cifrar e abrir
   com o código certo, recusar o código errado e o arquivo mexido, e um extra de teste mudando o chão e o ultrassom de
   uma pista. Se existir um simulador/extras.dat, confere só o formato (sem o código, não dá para abrir).
   Uso: node ferramentas/teste_extras.js   (o GitHub roda a cada envio) */
const fs = require('fs');
const path = require('path');
const SIM = path.join(__dirname, '..', 'simulador');
for (const f of ['mundo.js', 'cifra.js']) new Function(fs.readFileSync(path.join(SIM, f), 'utf8'))();
const EST = globalThis.EST, C = EST.Cifra;

let falhas = 0;
function confere(nome, ok, detalhe = '') {
  console.log(`  ${ok ? 'OK   ' : 'FALHA'} extras: ${nome}${ok || !detalhe ? '' : ` -> ${detalhe}`}`);
  if (!ok) falhas++;
}
const erroDe = async f => { try { await f(); return ''; } catch (e) { return e.message; } };

(async () => {
  const extra = `EST.EXTRAS['teste-extra'] = {
    chao: (x, y) => (x < 10 ? [0.5, 0.5, 0.5] : null),
    raio: () => 42,
  };`;
  const pacote = await C.fechar(extra, 'codigo-de-teste', 1000);
  confere('o arquivo cifrado não mostra o que está dentro', !JSON.stringify(pacote).includes('EXTRAS') && pacote.formato === 'est-extras');
  const texto = await C.abrir(pacote, 'codigo-de-teste');
  confere('com o código certo, abre igual', texto === extra);
  confere('com o código errado, não abre', (await erroDe(() => C.abrir(pacote, 'outro-codigo'))) === 'código errado');
  const mexido = {...pacote, dados: pacote.dados.slice(0, -4) + (pacote.dados.endsWith('AAAA') ? 'BBBB' : 'AAAA')};
  confere('arquivo mexido não abre', (await erroDe(() => C.abrir(mexido, 'codigo-de-teste'))) === 'código errado');

  new Function(texto)();
  const pista = {id: 'teste-extra', largura: 100, altura: 100, linhas: [], verdes: [], paredes: [], caixas: []};
  const outra = {...pista, id: 'outra'};
  confere('o extra muda o chão só da pista dele', JSON.stringify(EST.corDoChao(pista, 5, 5)) === '[0.5,0.5,0.5]'
          && EST.corDoChao(outra, 5, 5) !== EST.corDoChao(pista, 5, 5) && EST.corDoChao(pista, 50, 50) === EST.corDoChao(outra, 50, 50));
  confere('o extra entra no ultrassom só da pista dele', EST.raio(pista, 50, 50, 1, 0) === 42 && EST.raio(outra, 50, 50, 1, 0) === Infinity);

  const dat = path.join(SIM, 'extras.dat');
  if (fs.existsSync(dat)) {
    let p = null;
    try { p = JSON.parse(fs.readFileSync(dat, 'utf8')); } catch (e) { /* estragado */ }
    confere('simulador/extras.dat tem o formato certo', p && p.formato === 'est-extras' && p.versao === 1 && p.voltas >= 100000
            && typeof p.dados === 'string' && p.dados.length > 100);
  }
  console.log(falhas ? `\nextras: ${falhas} FALHA(S)` : '\nextras: OK');
  process.exit(falhas ? 1 : 0);
})();
