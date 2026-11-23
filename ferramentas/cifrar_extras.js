'use strict';
/* Cifra um arquivo de extras do simulador com um código (simulador/cifra.js). Quem chama é o
   ferramentas/cifrar_extras.py, que pede o código sem mostrar na tela e manda por aqui pela entrada:
   {"codigo": "...", "entrada": "arquivo.js", "saida": "simulador/extras.dat"} */
const fs = require('fs');
const path = require('path');

new Function(fs.readFileSync(path.join(__dirname, '..', 'simulador', 'cifra.js'), 'utf8'))();
const C = globalThis.EST.Cifra;

let entrada = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', d => { entrada += d; });
process.stdin.on('end', async () => {
  const {codigo, entrada: arquivo, saida} = JSON.parse(entrada);
  const texto = fs.readFileSync(arquivo, 'utf8');
  const pacote = await C.fechar(texto, codigo);
  if (await C.abrir(pacote, codigo) !== texto) throw new Error('a conferência do arquivo cifrado falhou');
  fs.writeFileSync(saida, JSON.stringify(pacote) + '\n');
  console.log(`[OK] ${saida}: ${Math.round(fs.statSync(saida).size / 1024)} KB cifrados (de ${Math.round(texto.length / 1024)} KB)`);
});
