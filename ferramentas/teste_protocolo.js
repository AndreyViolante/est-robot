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

// o envio confere a resposta de cada pacote (68 21 e o mesmo comando): um robô de mentira que responde cada pacote,
// às vezes com uma resposta velha antes, ou que não responde o RUN
function roboDeMentira({semRun = false, velhaAntes = ''} = {}) {
  const fila = [];
  const resposta = cmd => Uint8Array.from([0x68, 0x21, cmd, 1, 0, 1, 0, 0x16]);
  return {
    async mandar(pacote) {
      const nome = P.sequencia(new Uint8Array(10), '/vscode/t', true).find(p => hex(p.pacote) === hex(pacote));
      if (velhaAntes && nome && nome.nome === velhaAntes) fila.push(resposta(0x02));     // de outro pedido
      if (!(semRun && pacote[2] === 0x0A && pacote[5] === 0x01)) fila.push(resposta(pacote[2]));
    },
    resposta: async () => fila.shift() || null,
    fechar() {},
  };
}
(async () => {
  const certo = await P.enviarPorCanal(roboDeMentira(), new Uint8Array(10), '/vscode/t', true);
  confere('envio confirmado: rodou, nada faltou', certo.rodou === true && !certo.semResposta.length && certo.respostas === 8,
    JSON.stringify(certo));
  const velha = await P.enviarPorCanal(roboDeMentira({velhaAntes: 'SEND DATA'}), new Uint8Array(10), '/vscode/t', true);
  confere('resposta velha antes da certa é deixada de lado', velha.rodou === true && !velha.semResposta.length,
    JSON.stringify(velha));
  const parado = await P.enviarPorCanal(roboDeMentira({semRun: true}), new Uint8Array(10), '/vscode/t', true);
  confere('sem a resposta do RUN: gravou, mas não confirmou que rodou',
    parado.rodou === false && JSON.stringify(parado.semResposta) === '["RUN"]', JSON.stringify(parado));
  const gravar = await P.enviarPorCanal(roboDeMentira(), new Uint8Array(10), '/vscode/t', false);
  confere('só gravar: rodou fica null', gravar.rodou === null && !gravar.semResposta.length, JSON.stringify(gravar));

  // bateria: a resposta do 0C 01 traz o nível (0 a 4) no primeiro byte depois do tamanho (ler_info do est_protocol.py)
  const respostaBateria = (nivel, soma = true) => {
    const r = P.frame(0x0C, [0x04, 0x00, nivel, 0x56, 0x31, 0x00]);
    r[1] = 0x21;
    r[r.length - 2] = soma ? P.checksum(r.subarray(0, r.length - 2)) : 0;
    return r;
  };
  confere('bateria: lê o nível da resposta', P.lerBateria(Uint8Array.from([0, 0, ...respostaBateria(3), 0, 0])) === 3);
  confere('bateria: resposta com a soma errada não vale', P.lerBateria(respostaBateria(3, false)) === null);
  confere('bateria: resposta de outro comando não vale', P.lerBateria(Uint8Array.from([0x68, 0x21, 0x02, 1, 0, 4, 0x70, 0x16])) === null);
  const roboComBateria = nivel => {
    const fila = [];
    return {
      async mandar(pacote) { fila.push(pacote[2] === 0x0C ? respostaBateria(nivel) : Uint8Array.from([0x68, 0x21, pacote[2], 1, 0, 1, 0, 0x16])); },
      resposta: async () => fila.shift() || null,
      fechar() {},
    };
  };
  confere('bateria: consulta pelo canal', await P.consultarBateria(roboComBateria(1), 50) === 1);
  const comNivel = await P.enviarPorCanal(roboComBateria(4), new Uint8Array(10), '/vscode/t', true);
  confere('o envio também traz a bateria (da resposta do DOWNLOAD)', comNivel.bateria === 4, JSON.stringify(comNivel));

  console.log(`\nprotocolo do navegador: ${falhas ? `${falhas} FALHA(S)` : 'OK'}`);
  process.exit(falhas ? 1 : 0);
})();
