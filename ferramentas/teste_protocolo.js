// Testes do protocolo da página de programar (docs/programar/protocolo.js) que não precisam do robô:
// os pacotes do envio e, no Bluetooth, a linha de apresentação e a separação das respostas que chegam em pedaços.
// Uso: node ferramentas/teste_protocolo.js
'use strict';
const path = require('path');
const P = require(path.join(__dirname, '..', 'docs', 'programar', 'protocolo.js'));

let falhas = 0;
function confere(nome, certo, detalhe = '') {
  console.log(`  ${certo ? 'OK   ' : 'FALHA'} ${nome}${certo ? '' : ` -> ${detalhe}`}`);
  if (!certo) falhas++;
}
const hex = b => Buffer.from(b).toString('hex');

// os pacotes são os mesmos do est_protocol.py (conferidos byte a byte no robô pelo USB)
confere('heartbeat', hex(P.HEARTBEAT) === '68110100007a16', hex(P.HEARTBEAT));
const seq = P.sequencia(new Uint8Array(1500), '/vscode/teste', true);
confere('programa de 1500 bytes vai em 2 pedaços, com RUN no fim',
  seq.length === 9 && seq.filter(p => p.nome.startsWith('SEND DATA')).length === 2 && seq[8].nome === 'RUN',
  seq.map(p => p.nome).join(', '));

// Bluetooth: a linha com que a IDE se apresenta ao robô (nome + 12 dígitos do endereço + \r\n)
const linha = Buffer.from(P.linhaDeApresentacao()).toString('latin1');
confere('linha de apresentação', /^EST-LAB[0-9A-F]{12}\r\n$/.test(linha), JSON.stringify(linha));

// respostas do robô: 68 21 cmd tamanho(2) dados soma 16, que pelo Bluetooth podem chegar picadas e com lixo antes
const r1 = P.frame(0x01, [0x05, 0x00, ...Buffer.from('03.04')]);
const r2 = P.frame(0x0C, [0x03, 0x00, 0x02, 0x38, 0x39]);
r1[1] = 0x21; r1[r1.length - 2] = P.checksum(r1.subarray(0, r1.length - 2));        // resposta: 68 21 ...
r2[1] = 0x21; r2[r2.length - 2] = P.checksum(r2.subarray(0, r2.length - 2));
const tudo = Uint8Array.from([0x0D, 0x0A, 0x68, 0x00, ...r1, ...r2]);               // lixo, um 68 solto e duas respostas
let pacotes = [], resto = new Uint8Array(0);
for (let i = 0; i < tudo.length; i += 3) {                                          // chega de 3 em 3 bytes
  const junto = Uint8Array.from([...resto, ...tudo.subarray(i, i + 3)]);
  const r = P.separarPacotes(junto);
  pacotes.push(...r.pacotes);
  resto = r.resto;
}
confere('respostas picadas e com lixo viram os 2 pacotes inteiros',
  pacotes.length === 2 && hex(pacotes[0]) === hex(r1) && hex(pacotes[1]) === hex(r2),
  pacotes.map(hex).join(' | '));
confere('pacote com a soma errada é descartado',
  P.separarPacotes(Uint8Array.from([...r1.subarray(0, r1.length - 2), 0x00, 0x16])).pacotes.length === 0);
// a resposta de estado (portas) que chega pelo Bluetooth é lida como a do USB
const estado = P.frame(0x02, [33, 0, 0, ...[0, 1, 1, 2], ...[0, 4, 8, 3], ...[0, 6, 4, 1], ...new Array(20).fill(0)]);
estado[1] = 0x21; estado[estado.length - 2] = P.checksum(estado.subarray(0, estado.length - 2));
const portas = P.lerPortas(P.separarPacotes(estado).pacotes[0]);
confere('portas pela resposta separada', JSON.stringify(portas) === '{"1":1,"4":8,"B":4}', JSON.stringify(portas));

console.log(`\nprotocolo do navegador: ${falhas ? `${falhas} FALHA(S)` : 'OK'}`);
process.exit(falhas ? 1 : 0);
