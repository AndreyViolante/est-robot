'use strict';
/* Protocolo do robô EST pelo navegador: USB (WebHID: Chrome e Edge no computador e no Chromebook) e Bluetooth
   (Web Serial: Chrome do Android e do computador).

   Os pacotes são os mesmos de est_protocol.py, byte a byte: SELECT, HEARTBEAT, DOWNLOAD, nome do arquivo,
   dados em pedaços de até 1014 bytes, HEARTBEAT, DOWNLOAD e, para executar, RUN. Pelo USB cada pacote vai num
   output report de 1024 bytes (report ID 0); pelo Bluetooth vai com o tamanho exato. Depois de cada um, a página
   espera a resposta do robô. Antes de enviar, pergunta o que está ligado em cada porta (portas_ligadas de
   est_protocol.py). Se est_protocol.py mudar, mude aqui também. */
(function (raiz) {
const VID = 0x0483, PID = 0x5750;
const TAMANHO_REPORT = 1024;              // bytes de dados de cada report (o report ID 0 vai à parte)
const PEDACO = TAMANHO_REPORT - 10;       // bytes de programa por pacote (o pacote tem mais 10 bytes)

// ---------------------------------------------------------------- checksum e frame

function checksum(bytes) {
  let soma = 0;
  for (const b of bytes) soma += b;
  return soma & 0xFF;
}

function frame(cmd, payload) {
  const corpo = [0x68, 0x11, cmd, ...payload];
  return Uint8Array.from([...corpo, checksum(corpo), 0x16]);
}

function ascii(texto) {
  return Array.from(texto, c => {
    const n = c.codePointAt(0);
    if (n > 127) throw new Error(`o caminho "${texto}" tem letra fora do ASCII`);
    return n;
  });
}

const doisBytes = n => [n & 0xFF, (n >> 8) & 0xFF];       // little-endian, como to_bytes(2, 'little')

// ---------------------------------------------------------------- pacotes do protocolo

const HEARTBEAT = frame(0x01, [0x00, 0x00]);
const DOWNLOAD = frame(0x0C, [0x01, 0x00, 0x01]);
const CONSULTA_ESTADO = frame(0x02, [0x01, 0x00, 0x00]);       // a IDE manda isto sem parar
const NOMES_PORTAS = ['1', '2', '3', '4', 'A', 'B', 'C', 'D'];

/** Resposta da consulta de estado -> {porta: tipo} só das portas com algo ligado, como ler_portas:
    8 grupos [00, porta, tipo, ?] (porta 1-4 sensores, 5-8 = A-D; 0 = nada). null se não for a resposta. */
function lerPortas(resposta) {
  let fim = resposta.length;                  // como o read_response: sem os zeros do fim do report
  while (fim > 0 && resposta[fim - 1] === 0) fim--;
  let i = -1;
  for (let k = 0; k + 2 < fim; k++) {
    if (resposta[k] === 0x68 && resposta[k + 1] === 0x21 && resposta[k + 2] === 0x02) { i = k; break; }
  }
  if (i < 0 || fim < i + 5 + 33) return null;
  const dados = resposta.subarray(i + 5, i + 5 + 33);         // depois de 68 21 02 e do tamanho (2 bytes)
  const portas = {};
  for (let k = 0; k < 8; k++) {
    const porta = dados[2 + 4 * k], tipo = dados[3 + 4 * k];
    if (porta >= 1 && porta <= 8) portas[NOMES_PORTAS[porta - 1]] = tipo;
  }
  return portas;
}

function pacote0A(sub, caminho) {
  const c = ascii(caminho);
  return frame(0x0A, [...doisBytes(1 + c.length), sub, ...c]);
}
const pacoteSelect = caminho => pacote0A(0x02, caminho);
const pacoteRun = caminhoDbf => pacote0A(0x01, caminhoDbf);   // executa o programa gravado

function pacoteNome(caminhoArquivo) {
  const c = ascii(caminhoArquivo);
  const ultimaBarra = caminhoArquivo.lastIndexOf('/') + 1;   // tamanho do diretório, com a barra
  const dentro = [0x01, 0x00, ultimaBarra, ...c];
  return frame(0x04, [...doisBytes(dentro.length + 1), 0x01, ...dentro]);
}

function pacoteDados(dados, total = 1, indice = 0) {
  const dentro = [total, indice, ...dados];
  return frame(0x04, [...doisBytes(dentro.length + 1), 0x02, ...dentro]);
}

function pacotesDeDados(dados) {
  const pedacos = [];
  for (let i = 0; i < dados.length; i += PEDACO) pedacos.push(dados.subarray(i, i + PEDACO));
  if (!pedacos.length) pedacos.push(new Uint8Array(0));
  if (pedacos.length > 255) throw new Error(`programa grande demais (${dados.length} bytes)`);
  return pedacos.map((p, i) => pacoteDados(p, pedacos.length, i));
}

/** A sequência de envio, como build_upload_sequence: [{pacote, nome, espera (s)}]. */
function sequencia(programa, caminho = '/vscode/programa', executar = true) {
  const dados = programa instanceof Uint8Array ? programa : Uint8Array.from(programa);
  const dbf = caminho + '.dbf';
  const pedacos = pacotesDeDados(dados);
  const nomes = pedacos.length === 1 ? ['SEND DATA'] : pedacos.map((_, i) => `SEND DATA ${i + 1}/${pedacos.length}`);
  const lista = [
    {pacote: pacoteSelect(caminho), nome: 'SELECT PROGRAM', espera: 0.15},
    {pacote: HEARTBEAT, nome: 'HEARTBEAT', espera: 0.15},
    {pacote: DOWNLOAD, nome: 'DOWNLOAD trigger', espera: 0.30},
    {pacote: pacoteNome(dbf), nome: 'SEND FILENAME', espera: 0.15},
    ...pedacos.map((p, i) => ({pacote: p, nome: nomes[i], espera: 0.30})),
    {pacote: HEARTBEAT, nome: 'HEARTBEAT', espera: 0.15},
    {pacote: DOWNLOAD, nome: 'DOWNLOAD confirm', espera: 0.20},
  ];
  if (executar) lista.push({pacote: pacoteRun(dbf), nome: 'RUN', espera: 0.20});
  return lista;
}

// ---------------------------------------------------------------- WebHID

const temWebHID = () => typeof navigator !== 'undefined' && 'hid' in navigator && !!navigator.hid;
const ehRobo = d => d.vendorId === VID && d.productId === PID;
// a controladora pode aparecer como mais de um dispositivo HID: o que serve é o que aceita output report
const temSaida = d => (d.collections || []).some(c => (c.outputReports || []).length);
const melhor = lista => lista.find(temSaida) || lista[0] || null;

/** O robô que o navegador já tem permissão para usar (sem perguntar), ou null. */
async function roboPermitido() {
  if (!temWebHID()) return null;
  return melhor((await navigator.hid.getDevices()).filter(ehRobo));
}

/** Mostra a janela do navegador para escolher o robô (precisa vir de um clique). null = cancelou. */
async function escolherRobo() {
  const lista = await navigator.hid.requestDevice({filters: [{vendorId: VID, productId: PID}]});
  return melhor(lista.filter(ehRobo));
}

const hex = (bytes, n = 8) => Array.from(bytes.subarray(0, n), b => b.toString(16).padStart(2, '0').toUpperCase()).join('');

/** Conversa com o robô aberto: manda pacotes num report de 1024 bytes e lê as respostas na ordem em que
    chegam (como o ReadFile do est_protocol.py). fechar() para de ouvir. */
async function abrirCanal(dispositivo) {
  const fila = [];
  let acordar = null;
  const aoReceber = e => {
    fila.push(new Uint8Array(e.data.buffer.slice(e.data.byteOffset, e.data.byteOffset + e.data.byteLength)));
    if (acordar) acordar();
  };
  if (!dispositivo.opened) await dispositivo.open();
  dispositivo.addEventListener('inputreport', aoReceber);
  return {
    async mandar(pacote) {
      if (pacote.length > TAMANHO_REPORT) throw new Error(`pacote de ${pacote.length} bytes não cabe num report HID`);
      const report = new Uint8Array(TAMANHO_REPORT);
      report.set(pacote);
      await dispositivo.sendReport(0, report);
    },
    resposta: ms => new Promise(ok => {
      if (fila.length) return ok(fila.shift());
      const fim = setTimeout(() => { acordar = null; ok(null); }, ms);
      acordar = () => { clearTimeout(fim); acordar = null; ok(fila.shift()); };
    }),
    fechar: () => dispositivo.removeEventListener('inputreport', aoReceber),
  };
}

/** Pergunta pelo canal o que está ligado em cada porta (como portas_ligadas). null se não der para saber. */
async function consultarPortas(canal, ms = 400) {
  while (await canal.resposta(50)) { /* descarta respostas velhas */ }
  for (let i = 0; i < 3; i++) {
    await canal.mandar(CONSULTA_ESTADO);
    const resposta = await canal.resposta(ms);
    const portas = resposta ? lerPortas(resposta) : null;
    if (portas) return portas;
  }
  return null;
}

/** Pelo USB: o que está ligado em cada porta. Deixa o robô aberto para o envio. */
async function portasLigadas(dispositivo, ms = 400) {
  const canal = await abrirCanal(dispositivo);
  try {
    return await consultarPortas(canal, ms);
  } finally {
    canal.fechar();
  }
}

/** Envia o programa pelo canal, lendo a resposta depois de cada pacote (como upload() de est_protocol.py).
    aoAndar({passo, total, nome, tx, rx}) é chamado a cada pacote. Devolve quantos pacotes tiveram resposta. */
async function enviarPorCanal(canal, programa, caminho, executar, aoAndar = () => {}) {
  const lista = sequencia(programa, caminho, executar);
  let respostas = 0;
  for (let i = 0; i < lista.length; i++) {
    const {pacote, nome, espera} = lista[i];
    await canal.mandar(pacote);
    const rx = await canal.resposta(Math.round(espera * 1000) + 300);
    if (rx) respostas++;
    aoAndar({passo: i + 1, total: lista.length, nome, tx: hex(pacote), rx: rx ? hex(rx) : null});
  }
  return respostas;
}

/** Pelo USB: envia e fecha o robô no fim. */
async function enviar(dispositivo, programa, caminho, executar, aoAndar = () => {}) {
  const canal = await abrirCanal(dispositivo);
  try {
    return await enviarPorCanal(canal, programa, caminho, executar, aoAndar);
  } finally {
    canal.fechar();
    try { await dispositivo.close(); } catch (e) { /* já fechado */ }
  }
}

// ---------------------------------------------------------------- Bluetooth (Web Serial)
// Como a IDE: conecta na porta serial do Bluetooth do robô e, antes de tudo, manda uma linha com o nome e o endereço
// de quem conecta, terminada em \r\n (a IDE manda o nome e os 12 dígitos do endereço do Bluetooth do computador).
// Depois, os mesmos pacotes do USB, cada um com o tamanho exato, e as respostas no mesmo formato (68 21 ... 16).
// Ainda não conferido no robô.

const SPP = '00001101-0000-1000-8000-00805f9b34fb';      // porta serial do Bluetooth clássico
const NOME_NO_BLUETOOTH = 'EST-LAB';
const linhaDeApresentacao = (nome = NOME_NO_BLUETOOTH) => Uint8Array.from(ascii(`${nome}000000000000\r\n`));

const temWebSerial = () => typeof navigator !== 'undefined' && 'serial' in navigator && !!navigator.serial;

/** A porta Bluetooth que o navegador já tem permissão para usar (sem perguntar), ou null. */
async function portaBluetoothPermitida() {
  if (!temWebSerial()) return null;
  const portas = await navigator.serial.getPorts();
  return portas.find(p => p.getInfo && p.getInfo().bluetoothServiceClassId) || null;
}

/** Mostra a janela do navegador para escolher o robô pareado (precisa vir de um clique). */
async function escolherPortaBluetooth() {
  return navigator.serial.requestPort({allowedBluetoothServiceClassIds: [SPP]});
}

/** Tamanho do pacote inteiro e válido que começa em i (68 .. tamanho .. soma 16), 0 se não houver um ali,
    ou -1 se ali pode começar um pacote que ainda não chegou inteiro. */
function pacoteEm(bytes, i) {
  if (bytes[i] !== 0x68) return 0;
  if (bytes.length - i < 5) return -1;
  const total = 7 + (bytes[i + 3] | (bytes[i + 4] << 8));
  if (total > 2048) return 0;                                 // tamanho impossível: não era começo de pacote
  if (bytes.length - i < total) return -1;
  const fim = i + total;
  return bytes[fim - 1] === 0x16 && checksum(bytes.subarray(i, fim - 2)) === bytes[fim - 2] ? total : 0;
}

/** Separa os pacotes inteiros que chegaram em pedaços pelo Bluetooth.
    Devolve {pacotes, resto}: o resto é o começo de um pacote que ainda não chegou inteiro. */
function separarPacotes(bytes) {
  const pacotes = [];
  let i = 0;
  while (i < bytes.length) {
    const n = pacoteEm(bytes, i);
    if (n > 0) { pacotes.push(bytes.slice(i, i + n)); i += n; continue; }
    // um 68 no meio de lixo parece começo de pacote incompleto: só espera se não houver um pacote inteiro mais adiante
    if (n < 0 && !bytes.subarray(i + 1).some((b, k) => b === 0x68 && pacoteEm(bytes, i + 1 + k) > 0)) break;
    i++;
  }
  return {pacotes, resto: bytes.slice(i)};
}

/** Abre a conversa pelo Bluetooth: mesma cara do canal USB (mandar, resposta, fechar) e já se apresenta ao robô.
    canal.apresentacao = o que o robô respondeu à linha de apresentação (ou null). */
async function abrirCanalBluetooth(porta) {
  await porta.open({baudRate: 115200});          // no Bluetooth a velocidade não vale, mas a API pede
  const leitor = porta.readable.getReader(), escritor = porta.writable.getWriter();
  const fila = [];
  let acordar = null, resto = new Uint8Array(0);
  const lendo = (async () => {
    try {
      for (;;) {
        const {value, done} = await leitor.read();
        if (done) break;
        const junto = new Uint8Array(resto.length + value.length);
        junto.set(resto);
        junto.set(value, resto.length);
        const r = separarPacotes(junto);
        resto = r.resto;
        if (r.pacotes.length) { fila.push(...r.pacotes); if (acordar) acordar(); }
      }
    } catch (e) { /* a porta fechou */ }
  })();
  const canal = {
    mandar: pacote => escritor.write(pacote),
    resposta: ms => new Promise(ok => {
      if (fila.length) return ok(fila.shift());
      const fim = setTimeout(() => { acordar = null; ok(null); }, ms);
      acordar = () => { clearTimeout(fim); acordar = null; ok(fila.shift()); };
    }),
    async fechar() {
      try { await leitor.cancel(); } catch (e) { /* já parou */ }
      await lendo;
      leitor.releaseLock();
      escritor.releaseLock();
      try { await porta.close(); } catch (e) { /* já fechada */ }
    },
    apresentacao: null,
  };
  try {
    await canal.mandar(linhaDeApresentacao());
    const r = await canal.resposta(600);
    canal.apresentacao = r ? hex(r, r.length) : null;
  } catch (e) {
    await canal.fechar();
    throw e;
  }
  return canal;
}

const API = {VID, PID, TAMANHO_REPORT, PEDACO, checksum, frame, HEARTBEAT, DOWNLOAD, CONSULTA_ESTADO, pacoteSelect,
             pacoteRun, pacoteNome, pacoteDados, pacotesDeDados, sequencia, lerPortas, temWebHID, roboPermitido,
             escolherRobo, consultarPortas, portasLigadas, enviarPorCanal, enviar, SPP, linhaDeApresentacao,
             temWebSerial, portaBluetoothPermitida, escolherPortaBluetooth, separarPacotes, abrirCanalBluetooth};
if (typeof module === 'object' && module.exports) module.exports = API;     // para testar no Node
else raiz.ESTProtocolo = API;
})(typeof globalThis !== 'undefined' ? globalThis : this);
