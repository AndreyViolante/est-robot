'use strict';
/* Página do simulador: desenha a pista e o robô, controla a execução e mostra a tela, a luz, o som,
   os sensores, os motores, as variáveis e a linha do programa que está rodando.
   O programa vem de programa.js, gerado por simular.py. Na demonstração da página do projeto
   (ferramentas/publicar_simulador.py) o programa.js traz uma lista de exemplos; com mais de um,
   aparece o seletor. */
(function () {
const EST = globalThis.EST;
const DT = 0.002;                 // passo da simulação (s)
const MAX_PASSOS = 2500;          // passos por quadro de animação, no máximo
const MARGEM = 8;                 // cm de mesa em volta da pista
const LUPA = 3;                   // aumento da lupa
const CHAVE = 'est-simulador-v1';
const CORES_SENSOR = {1: '#2f8cff', 2: '#ff8a1f', 3: '#18b07a', 4: '#b27cff'};
const NOMES_LUZ = ['azul', 'roxo', 'vermelho'];
const MINHA = 'minha';            // id da pista que o aluno desenha (fica guardada no navegador)
const MINHA_OBR = 'obr-minha';    // id da arena da OBR que o aluno monta com ladrilhos (também fica guardada)
const GRADE = 5;                  // cm: as pontas das linhas desenhadas grudam nesta grade
const CAIXA = 10;                 // cm: lado da caixa que o editor coloca
const MAX_ITENS = 500;            // linhas, quadrados ou caixas guardados na "Minha pista", no máximo

const COR_VERDE = `rgb(${EST.VERDE.slice(0, 3).map(v => Math.round(v * 255)).join(', ')})`;     // a mesma cor que o sensor vê

const $ = id => document.getElementById(id);
const copia = o => JSON.parse(JSON.stringify(o));
const num = (v, casas = 1) => v.toLocaleString('pt-BR', {minimumFractionDigits: casas, maximumFractionDigits: casas});

// ---------------------------------------------------------------- o que fica guardado no navegador

function lerSalvo() {
  try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; } catch (e) { return {}; }
}
const salvo = lerSalvo();
salvo.largadas = salvo.largadas || {};
salvo.caixas = salvo.caixas || {};
salvo.paradas = salvo.paradas && typeof salvo.paradas === 'object' ? salvo.paradas : {};
salvo.desafios = salvo.desafios && typeof salvo.desafios === 'object' ? salvo.desafios : {};     // id -> {feito, tempo}
let semGuardar = false;           // o navegador não deixou guardar: tudo vale só até fechar a página
function salvar() {
  try { localStorage.setItem(CHAVE, JSON.stringify(salvo)); semGuardar = false; } catch (e) { semGuardar = true; }
}

// copia de 'origem' só os valores com o mesmo tipo do padrão
function mesclar(destino, origem) {
  for (const [k, v] of Object.entries(origem || {})) {
    if (!(k in destino)) continue;
    if (destino[k] && typeof destino[k] === 'object') { if (v && typeof v === 'object') mesclar(destino[k], v); }
    else if (typeof v === typeof destino[k] && (typeof v !== 'number' || Number.isFinite(v))) destino[k] = v;
  }
  return destino;
}

// ---------------------------------------------------------------- programa

// window.PROGRAMA: um programa (simular.py); window.PROGRAMAS: uma lista (a demonstração)
const PROGRAMAS = Array.isArray(globalThis.PROGRAMAS) ? globalThis.PROGRAMAS
  : globalThis.PROGRAMA ? [globalThis.PROGRAMA] : [];
let P = null, codigo = null, erroCarga = null, marcas = [], usaToque = false, usaBotoes = false;
let linhasComCodigo = new Set();     // linhas do arquivo do aluno que viraram blocos (podem ter ponto de parada)

function lerPrograma(dados) {
  P = dados || null;
  codigo = null; erroCarga = null; marcas = []; usaToque = false; usaBotoes = false;
  linhasComCodigo = new Set();
  if (!P) return;
  try {
    codigo = new Uint8Array(P.bytes.match(/../g).map(h => parseInt(h, 16)));
    const lista = EST.instrucoes(codigo);
    marcas = lista.filter(i => i.op === 0x48).map(i => i.pc);
    usaToque = lista.some(i => i.op === 0x30 && codigo[i.pc + 6] === 0x07);
    usaBotoes = lista.some(i => i.op === 0x32 && codigo[i.pc + 1] === 3);
    if (!P.linhas || P.linhas.length !== marcas.length) marcas = [];     // sem linhas: só não destaca
    if (marcas.length) linhasComCodigo = new Set(P.linhas.filter(n => n > 0));
  } catch (e) {
    erroCarga = e;
  }
}

// o endereço guarda o exemplo escolhido (simulador/#11_seguidor_dois_sensores), para recarregar e para links
const chaveDe = p => String(p.nome || '').replace(/\.py$/, '');
function exemploDoEndereco() {
  let h = '';
  try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { /* endereço estranho: nenhum */ }
  return PROGRAMAS.findIndex(p => chaveDe(p) === h);
}
function rotulo(p) {
  const n = /^(\d+)_/.exec(p.nome || '');
  return p.titulo ? (n ? `${n[1]}. ${p.titulo}` : p.titulo) : p.nome;
}

let exemplo = exemploDoEndereco();
if (exemplo < 0) exemplo = Math.max(0, PROGRAMAS.findIndex(p => p.inicial));     // sem #: o que abre primeiro
lerPrograma(PROGRAMAS[exemplo]);

function linhaDoPc(pc) {
  let lo = 0, hi = marcas.length - 1, r = -1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (marcas[m] <= pc) { r = m; lo = m + 1; } else hi = m - 1;
  }
  return r >= 0 ? P.linhas[r] || 0 : 0;
}

// ---------------------------------------------------------------- passo a passo e pontos de parada

let passoAPasso = false;          // "Próxima linha": pausa quando o programa chegar numa linha
let paradas = new Set();          // linhas com ponto de parada
let motivoParada = null;          // {linha, tipo: 'passo' | 'parada'}: por que a execução pausou sozinha

/* A VM chama no início de cada bloco; true = pausar ali (antes do bloco fazer alguma coisa).
   Blocos seguidos da mesma linha (painel, melodia...) contam como um só: pausa quando a thread chega numa
   linha nova ou volta para o começo da mesma linha (a volta seguinte de um laço). */
function aoBloco(pc, th) {
  const n = linhaDoPc(pc);
  const continua = n === th.linhaAnterior && pc > th.blocoAnterior;
  th.linhaAnterior = n;
  th.blocoAnterior = pc;
  if (!n || continua || !(passoAPasso || paradas.has(n))) return false;
  motivoParada = {linha: n, tipo: passoAPasso ? 'passo' : 'parada'};
  passoAPasso = false;
  return true;
}

function novaVM() {
  const v = codigo && !erroCarga ? new EST.VM(codigo, robo) : null;
  if (v) v.aoBloco = aoBloco;
  return v;
}

function carregarParadas() {
  const lista = P && salvo.paradas[chaveDe(P)];
  paradas = new Set(Array.isArray(lista) ? lista.filter(n => linhasComCodigo.has(n)) : []);
}

function alternarParada(n) {
  if (!linhasComCodigo.has(n)) return;
  if (paradas.has(n)) paradas.delete(n); else paradas.add(n);
  const el = $('fonte').children[n - 1], nl = el && el.querySelector('.nl');
  if (nl) { nl.classList.toggle('parada', paradas.has(n)); nl.setAttribute('aria-pressed', String(paradas.has(n))); }
  if (paradas.size) salvo.paradas[chaveDe(P)] = [...paradas].sort((a, b) => a - b);
  else delete salvo.paradas[chaveDe(P)];
  salvar();
}

// ---------------------------------------------------------------- pista, robô e VM

// largada da "Minha pista": no começo da primeira linha desenhada, virado para o lado dela
function largadaPadrao(p) {
  const t = p.linhas[0];
  if (!t) return {x: p.largura / 2, y: p.altura / 2, ang: 0};
  const [x1, y1, x2, y2] = t.seg, L = Math.hypot(x2 - x1, y2 - y1), d = Math.min(5, L / 2);
  return {x: x1 + (x2 - x1) / L * d, y: y1 + (y2 - y1) / L * d, ang: Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI};
}

// a "Minha pista" guardada: {largura, altura, linhas: [[x1, y1, x2, y2]], verdes: [[x, y]], caixas: [[x, y]]}
function pistaMinha() {
  const m = salvo.minha && typeof salvo.minha === 'object' ? salvo.minha : {};
  const medida = (v, min, max, padrao) => Number.isFinite(v) ? Math.max(min, Math.min(max, Math.round(v))) : padrao;
  const lista = (v, n) => (Array.isArray(v) ? v : [])
    .filter(a => Array.isArray(a) && a.length === n && a.every(Number.isFinite)).slice(0, MAX_ITENS);
  const Q = EST.QUADRADO_VERDE;
  const p = {
    id: MINHA, nome: 'Minha pista', largura: medida(m.largura, 60, 400, 200), altura: medida(m.altura, 60, 300, 150),
    linhas: lista(m.linhas, 4).map(s => ({seg: s.slice()})),
    verdes: lista(m.verdes, 2).map(([x, y]) => ({x, y, w: Q, h: Q})),
    caixas: lista(m.caixas, 2).map(([x, y]) => ({x, y, w: CAIXA, h: CAIXA})),
    paredes: [],
  };
  p.largada = largadaPadrao(p);
  return p;
}

// arena da OBR (obr.js): uma das prontas ou a "Minha arena OBR" guardada no navegador
function pistaOBR(id) {
  if (id === MINHA_OBR) {
    const arena = EST.OBR.arenaGuardada(salvo.arenaOBR);
    const p = EST.OBR.montar(arena, MINHA_OBR, 'Minha arena OBR (ladrilhos)');
    p.obr.erros = arena.percurso.length ? EST.OBR.conferir(arena) : [];
    return p;
  }
  const a = EST.OBR.ARENAS.find(q => q.id === id);
  const p = EST.OBR.montar(a.arena, a.id, a.nome);
  p.dica = a.dica;
  p.obr.erros = [];
  return p;
}
const ehOBR = id => id === MINHA_OBR || EST.OBR.ARENAS.some(a => a.id === id);

function montarPista(id) {
  if (id === MINHA) return pistaMinha();
  if (ehOBR(id)) return pistaOBR(id);
  const base = EST.PISTAS.find(p => p.id === id) || EST.PISTAS[0];
  const pista = EST.copiaPista(base);
  const caixas = salvo.caixas[pista.id];
  if (Array.isArray(caixas) && caixas.length === pista.caixas.length) {
    caixas.forEach((c, i) => { if (Number.isFinite(c.x) && Number.isFinite(c.y)) Object.assign(pista.caixas[i], {x: c.x, y: c.y}); });
  }
  return pista;
}

let desafio = null, prova = null;     // desafio escolhido e a tentativa em andamento (ver "trilha de desafios")
let placar = null;                    // rodada da OBR em andamento (ver "arena da OBR")
let editandoOBR = false, escolhidoOBR = -1;     // montando a "Minha arena OBR" e o ladrilho escolhido nela
let pista = montarPista((P && P.pista) || salvo.pista);     // o exemplo da demonstração já diz a pista
const robo = new EST.Robo(mesclar(copia(EST.ROBO_PADRAO), salvo.robo), pista);
let vm = novaVM();

function largada() {
  if (desafio) return desafio.largada;              // no desafio o robô sempre sai da largada dele
  if (pista.obr) return pista.largada;              // na arena da OBR, do ladrilho de partida
  const l = salvo.largadas[pista.id];
  return l && Number.isFinite(l.x) && Number.isFinite(l.y) && Number.isFinite(l.ang) ? l : pista.largada;
}

let estado = vm ? 'pronto' : 'sem';      // sem | pronto | rodando | pausado | terminou | erro
let tSim = 0, tFim = 0, acumulado = 0, velocidade = 1;
let somAte = -1, somTexto = '';

// ---------------------------------------------------------------- som

let audio = null;
const osciladores = new Set();
function prepararAudio() {
  if (!audio) {
    try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audio = null; }
  }
  if (audio && audio.state === 'suspended') audio.resume();
}
function tocar(freq, dur, vol) {
  if (!audio || !$('somLigado').checked) return;
  const real = dur / velocidade, agora = audio.currentTime;
  const o = audio.createOscillator(), g = audio.createGain();
  const v = 0.12 * Math.max(0, Math.min(100, Number.isFinite(vol) ? vol : 100)) / 100;
  o.type = 'square';
  o.frequency.value = Math.max(20, Math.min(12000, Number.isFinite(freq) ? freq : 440));
  g.gain.setValueAtTime(v, agora);
  g.gain.setValueAtTime(v, agora + Math.max(0, real - 0.01));
  g.gain.linearRampToValueAtTime(0, agora + real);
  o.connect(g).connect(audio.destination);
  o.start(agora);
  o.stop(agora + real + 0.02);
  osciladores.add(o);
  o.onended = () => osciladores.delete(o);
}
function silenciar() {
  for (const o of osciladores) { try { o.stop(); } catch (e) { /* já parou */ } }
  osciladores.clear();
}
robo.aoEvento = e => {
  if (e.tipo === 'som') {
    somAte = e.t + e.dur;
    somTexto = `♪ ${Math.round(e.freq)} Hz`;
    tocar(e.freq, e.dur, e.vol);
  }
};

// ---------------------------------------------------------------- execução

function colocarNaLargada() {
  const l = largada();
  robo.colocar(l.x, l.y, l.ang);
  robo.rastro = [[robo.x, robo.y]];
}

function reiniciar() {
  silenciar();
  robo.reiniciar();
  colocarNaLargada();
  if (vm) vm.reiniciar();
  tSim = 0; tFim = 0; acumulado = 0; somAte = -1;
  passoAPasso = false; motivoParada = null;
  estado = vm ? 'pronto' : 'sem';
  novaProva();
  placar = pista.obr && !editandoOBR && pista.obr.arena.percurso.length >= 2 && !pista.obr.erros.length
    ? new EST.OBR.Placar(pista) : null;
  desenharLcd(true);
  atualizarTudo();
}

function executarOuPausar() {
  if (!vm) return;
  if (estado === 'rodando') {
    estado = 'pausado';
    passoAPasso = false; motivoParada = null;
    if (audio) audio.suspend();
  } else {
    if (estado === 'terminou' || estado === 'erro') reiniciar();
    prepararAudio();
    estado = 'rodando';
    motivoParada = null;
  }
  atualizarTudo();
}

// executa até o programa chegar numa linha (a próxima, ou a mesma de novo num laço) e pausa
function proximaLinha() {
  if (!vm || !marcas.length) return;
  if (estado === 'terminou' || estado === 'erro') reiniciar();
  passoAPasso = true;
  motivoParada = null;
  if (estado !== 'rodando') { prepararAudio(); estado = 'rodando'; }
  atualizarTudo();
}

function passo() {
  if (estado === 'rodando') {
    vm.executar(tSim, DT);
    if (vm.parada) {                // "Próxima linha" ou ponto de parada
      estado = 'pausado';
      if (audio) audio.suspend();
      atualizarTudo();
    } else if (vm.erro) {
      estado = 'erro';
      tFim = tSim;
      robo.fim();
      atualizarTudo();
    } else if (vm.terminou) {
      estado = 'terminou';
      tFim = tSim + DT;
      atualizarTudo();
    }
  }
  robo.avancar(DT, tSim + DT, arraste !== null && (arraste.tipo === 'mover' || arraste.tipo === 'girar'));
  tSim += DT;
  if (soltarPendente && tSim >= soltarPendente.t) { const f = soltarPendente.soltar; soltarPendente = null; f(); }
  if (estado !== 'rodando' && estado !== 'terminou') return;
  if ((prova && !prova.resultado) || (placar && !placar.fim)) contarParado();
  if (prova && !prova.resultado) verificarDesafio();
  if (placar && !placar.fim) verificarOBR();
}

// há quanto tempo o robô está parado (desafios e rodada da OBR)
function contarParado() {
  if (Math.hypot(robo.x - posAnterior[0], robo.y - posAnterior[1]) > 1e-4 || Math.abs(robo.ang - posAnterior[2]) > 1e-5) {
    ultimoMovimento = tSim;
  }
  posAnterior = [robo.x, robo.y, robo.ang];
}

// ---------------------------------------------------------------- desenho da pista

const cena = $('cena');
const ctx = cena.getContext('2d');
let cores = {};
let vista = {escala: 4, x0: 0, y0: 0, base: 4};      // px (do canvas) por cm e deslocamento

function lerCores() {
  const s = getComputedStyle(document.documentElement);
  for (const nome of ['mesa', 'fg', 'muted', 'led-azul', 'led-roxo', 'led-vermelho', 'panel', 'line']) {
    cores[nome] = s.getPropertyValue('--' + nome).trim();
  }
}

function dimensionar() {
  const quadro = $('quadro');
  const larg = quadro.clientWidth || 600;
  const W = pista.largura + 2 * MARGEM, H = pista.altura + 2 * MARGEM;
  const maxAlt = Math.max(260, window.innerHeight * 0.62);    // sobra lugar para os botões embaixo
  let s = larg / W;
  if (H * s > maxAlt) s = maxAlt / H;
  const alt = Math.round(H * s);
  const dpr = window.devicePixelRatio || 1;
  cena.style.height = alt + 'px';
  cena.width = Math.round(larg * dpr);
  cena.height = Math.round(alt * dpr);
  vista.base = s * dpr;
}

// a lupa segue o robô; sem lupa, a pista inteira fica no meio
function ajustarVista() {
  const lupa = $('lupa') && $('lupa').checked;
  vista.escala = vista.base * (lupa ? LUPA : 1);
  const cx = lupa ? robo.x : pista.largura / 2, cy = lupa ? robo.y : pista.altura / 2;
  vista.x0 = cena.width / 2 - cx * vista.escala;
  vista.y0 = cena.height / 2 - cy * vista.escala;
}

function paraMundo(ev) {
  const r = cena.getBoundingClientRect();
  const px = (ev.clientX - r.left) * cena.width / r.width, py = (ev.clientY - r.top) * cena.height / r.height;
  return [(px - vista.x0) / vista.escala, (py - vista.y0) / vista.escala];
}

function retanguloArredondado(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

function desenharPista(c) {
  const W = pista.largura, H = pista.altura;
  c.fillStyle = 'rgba(0, 0, 0, 0.14)';
  c.fillRect(0.5, 0.7, W, H);
  c.fillStyle = '#ffffff';
  c.fillRect(0, 0, W, H);
  if (editando) {                 // desenhando a pista: grade de 5 cm, onde as pontas das linhas grudam
    const cor = v => v % 50 ? v % 10 ? '#eef1f6' : '#dfe4ec' : '#c6cedb';
    for (let x = GRADE; x < W; x += GRADE) linha(c, x, 0, x, H, cor(x), 0.2);
    for (let y = GRADE; y < H; y += GRADE) linha(c, 0, y, W, y, cor(y), 0.2);
  } else if (pista.quadriculado) {
    for (let x = 10; x < W; x += 10) linha(c, x, 0, x, H, x % 50 ? '#e6eaf1' : '#cfd6e2', 0.2);
    for (let y = 10; y < H; y += 10) linha(c, 0, y, W, y, y % 50 ? '#e6eaf1' : '#cfd6e2', 0.2);
  }
  if (pista.obr) desenharLadrilhos(c);
  // quadrados verdes (por baixo da linha preta, como no chão)
  c.fillStyle = COR_VERDE;
  for (const q of pista.verdes || []) c.fillRect(q.x, q.y, q.w, q.h);
  c.strokeStyle = '#111111';
  c.lineWidth = EST.LINHA;
  c.lineCap = 'round';
  for (const t of pista.linhas) {
    c.beginPath();
    if (t.seg) {
      c.moveTo(t.seg[0], t.seg[1]);
      c.lineTo(t.seg[2], t.seg[3]);
    } else {
      const [cx, cy, r, ini, varr] = t.arco, a0 = ini * Math.PI / 180, a1 = (ini + varr) * Math.PI / 180;
      c.arc(cx, cy, r, a0, a1, varr < 0);
    }
    c.stroke();
  }
  // faixa vermelha de chegada da arena da OBR (por cima da linha)
  c.fillStyle = '#d71f1f';
  for (const q of pista.vermelhos || []) c.fillRect(q.x, q.y, q.w, q.h);
  if (pista.obr) desenharMarcasOBR(c);
  // paredes: a face é o segmento; a espessura fica do lado de fora da mesa
  for (const [x1, y1, x2, y2] of pista.paredes) {
    const L = Math.hypot(x2 - x1, y2 - y1);
    let nx = (y2 - y1) / L, ny = -(x2 - x1) / L;
    const mx = (x1 + x2) / 2 - W / 2, my = (y1 + y2) / 2 - H / 2;
    if (nx * mx + ny * my < 0) { nx = -nx; ny = -ny; }
    const e = EST.PAREDE / 2;
    linha(c, x1 + nx * e - (x2 - x1) / L * e * 2, y1 + ny * e - (y2 - y1) / L * e * 2,
          x2 + nx * e + (x2 - x1) / L * e * 2, y2 + ny * e + (y2 - y1) / L * e * 2, '#5d6577', EST.PAREDE, 'butt');
  }
  for (const cx of pista.caixas) {
    c.fillStyle = 'rgba(0, 0, 0, 0.18)';
    c.fillRect(cx.x + 0.8, cx.y + 1, cx.w, cx.h);
    c.fillStyle = '#c99f62';
    c.fillRect(cx.x, cx.y, cx.w, cx.h);
    c.strokeStyle = '#8b6837';
    c.lineWidth = 0.5;
    c.strokeRect(cx.x, cx.y, cx.w, cx.h);
    linha(c, cx.x + cx.w / 2, cx.y, cx.x + cx.w / 2, cx.y + cx.h, '#e0c08d', 1.6, 'butt');
  }
  if (desafio) desenharDesafio(c);
  // régua de 10 cm na margem de baixo
  const ry = H + MARGEM * 0.45;
  linha(c, 0, ry, 10, ry, cores.muted, 0.35, 'butt');
  linha(c, 0, ry - 0.8, 0, ry + 0.8, cores.muted, 0.35, 'butt');
  linha(c, 10, ry - 0.8, 10, ry + 0.8, cores.muted, 0.35, 'butt');
}

function linha(c, x1, y1, x2, y2, cor, larg, ponta = 'round') {
  c.strokeStyle = cor;
  c.lineWidth = larg;
  c.lineCap = ponta;
  c.beginPath();
  c.moveTo(x1, y1);
  c.lineTo(x2, y2);
  c.stroke();
}

function desenharRastro(c) {
  const r = robo.rastro;
  if (!$('rastro').checked || r.length < 2) return;
  c.strokeStyle = 'rgba(34, 80, 255, 0.6)';
  c.lineWidth = 0.45;
  c.lineCap = 'round';
  c.lineJoin = 'round';
  c.beginPath();
  let novo = true;                // null no rastro = o robô foi levado com a mão: o traço recomeça
  for (const ponto of r) {
    if (!ponto) { novo = true; continue; }
    if (novo) c.moveTo(ponto[0], ponto[1]); else c.lineTo(ponto[0], ponto[1]);
    novo = false;
  }
  if (!novo) c.lineTo(robo.x, robo.y);
  c.stroke();
}

function corDaLuz() {
  return robo.luz === null ? null : cores['led-' + NOMES_LUZ[robo.luz]];
}

function desenharRobo(c) {
  const cfg = robo.config, corpo = cfg.corpo;
  const comp = corpo.frente + corpo.tras, meiaL = corpo.largura / 2;

  // feixe do ultrassom, enquanto o programa estiver lendo
  for (const [p, s] of Object.entries(cfg.portas)) {
    if (s.tipo !== 'ultrassom' || tSim - (robo.lidas[p] ?? -9) > 0.3 || estado === 'pronto') continue;
    const u = robo.sensorUltrassom(p), d = Math.min(u.cm, 255), a = 10 * Math.PI / 180;
    c.fillStyle = 'rgba(178, 124, 255, 0.16)';
    c.beginPath();
    c.moveTo(u.x, u.y);
    c.arc(u.x, u.y, d, robo.ang - a, robo.ang + a);
    c.closePath();
    c.fill();
  }

  c.save();
  c.translate(robo.x, robo.y);
  c.rotate(robo.ang);            // aqui x é para a frente e y para a direita do robô

  c.fillStyle = 'rgba(0, 0, 0, 0.22)';
  retanguloArredondado(c, -corpo.tras + 0.7, -meiaL + 0.9, comp, corpo.largura, 2.2);
  c.fill();
  c.globalAlpha = 0.8;           // dá para ver a linha embaixo do robô
  c.fillStyle = '#283050';
  retanguloArredondado(c, -corpo.tras, -meiaL, comp, corpo.largura, 2.2);
  c.fill();
  c.strokeStyle = '#0d1120';
  c.lineWidth = 0.3;
  c.stroke();

  // rodas
  const rw = Math.max(cfg.roda_cm, 3), mr = cfg.entre_rodas_cm / 2;
  c.fillStyle = '#07090f';
  for (const lado of [-1, 1]) {
    retanguloArredondado(c, -rw / 2, lado * mr - 1.1, rw, 2.2, 0.6);
    c.fill();
  }

  // controladora com a luz
  const bx = -corpo.tras + 1.5, bw = Math.max(4, Math.min(11, comp - 6)), bh = Math.max(4, corpo.largura - 5);
  c.fillStyle = '#3b4468';
  retanguloArredondado(c, bx, -bh / 2, bw, bh, 1.2);
  c.fill();
  const luz = corDaLuz();
  c.save();
  if (luz) { c.shadowColor = luz; c.shadowBlur = 3 * vista.escala; }
  c.fillStyle = luz || '#59627a';
  retanguloArredondado(c, bx + bw / 2 - 1.4, -bh / 2 + 0.8, 2.8, bh - 1.6, 0.8);
  c.fill();
  c.restore();

  c.globalAlpha = 1;

  // seta da frente
  c.fillStyle = 'rgba(255, 255, 255, 0.8)';
  c.beginPath();
  c.moveTo(corpo.frente - 1.2, 0);
  c.lineTo(corpo.frente - 3.6, -1.5);
  c.lineTo(corpo.frente - 3.6, 1.5);
  c.closePath();
  c.fill();

  // sensores
  for (const [p, s] of Object.entries(cfg.portas)) {
    const cor = CORES_SENSOR[p];
    const px = s.frente, py = -s.esquerda;
    if (s.tipo === 'cor') {
      const l = robo.sensorCor(p);
      c.fillStyle = '#11141f';
      c.fillRect(px - 0.9, py - 0.9, 1.8, 1.8);
      const g = Math.round(255 * (l ? l.luz : 0) / 100);
      c.fillStyle = `rgb(${g}, ${g}, ${g})`;
      c.beginPath();
      c.arc(px, py, 0.5, 0, 2 * Math.PI);
      c.fill();
      c.strokeStyle = cor;
      c.lineWidth = 0.32;
      c.stroke();
    } else if (s.tipo === 'ultrassom') {
      c.fillStyle = '#11141f';
      c.fillRect(px - 1.4, py - 2.4, 1.4, 4.8);
      c.fillStyle = cor;
      for (const o of [-1.2, 1.2]) { c.beginPath(); c.arc(px - 0.2, py + o, 0.8, 0, 2 * Math.PI); c.fill(); }
    }
  }
  c.restore();
}

// alça para girar: uma bolinha à frente do robô
function posicaoAlca() {
  return robo.ponto(robo.config.corpo.frente + 6, 0);
}

function desenharAlca(c) {
  if (desafio || (estado === 'rodando' && !(arraste && arraste.tipo === 'girar'))) return;     // no desafio não gira
  const [ax, ay] = posicaoAlca(), [fx, fy] = robo.ponto(robo.config.corpo.frente, 0);
  linha(c, fx, fy, ax, ay, 'rgba(34, 80, 255, 0.55)', 0.35);
  c.fillStyle = '#ffffff';
  c.strokeStyle = '#2250ff';
  c.lineWidth = 0.45;
  c.beginPath();
  c.arc(ax, ay, 1.6, 0, 2 * Math.PI);
  c.fill();
  c.stroke();
}

function desenhar() {
  ajustarVista();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = cores.mesa;
  ctx.fillRect(0, 0, cena.width, cena.height);
  ctx.setTransform(vista.escala, 0, 0, vista.escala, vista.x0, vista.y0);
  desenharPista(ctx);
  desenharEditor(ctx);
  desenharRastro(ctx);
  desenharRobo(ctx);
  desenharAlca(ctx);
  // texto da régua em pixels de tela, para ficar nítido
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const dpr = window.devicePixelRatio || 1;
  ctx.fillStyle = cores.muted;
  ctx.font = `${11 * dpr}px "Segoe UI", system-ui, sans-serif`;
  ctx.textBaseline = 'middle';
  ctx.fillText('10 cm', vista.x0 + 11.5 * vista.escala, vista.y0 + (pista.altura + MARGEM * 0.45) * vista.escala);
  // comprimento da linha que está sendo desenhada
  if (arraste && arraste.tipo === 'linha') {
    const [x1, y1, x2, y2] = arraste.seg, L = Math.round(Math.hypot(x2 - x1, y2 - y1) * 10) / 10;
    if (L > 0) {
      const texto = `${num(L, Number.isInteger(L) ? 0 : 1)} cm`, w = ctx.measureText(texto).width;
      const tx = vista.x0 + x2 * vista.escala + 10 * dpr, ty = vista.y0 + y2 * vista.escala - 12 * dpr;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
      ctx.fillRect(tx - 4 * dpr, ty - 9 * dpr, w + 8 * dpr, 18 * dpr);
      ctx.fillStyle = '#0d1222';
      ctx.fillText(texto, tx, ty);
    }
  }
}

// ---------------------------------------------------------------- editor da "Minha pista"

let editando = false, ferramenta = 'linha';
let mira = null, marcado = null;     // ponteiro sobre a pista e o item que o "Apagar" vai tirar
const historico = [];                // a pista antes de cada mudança, para o Desfazer

// a "Minha pista" como fica guardada no navegador
function dadosMinha() {
  const r = v => Math.round(v * 10) / 10;
  return {largura: pista.largura, altura: pista.altura, linhas: pista.linhas.map(t => t.seg.map(r)),
          verdes: pista.verdes.map(q => [r(q.x), r(q.y)]), caixas: pista.caixas.map(c => [r(c.x), r(c.y)])};
}

function guardarDesfazer(antes = JSON.stringify(dadosMinha())) {
  historico.push(antes);
  if (historico.length > 100) historico.shift();
}

function mudouMinha() {
  salvo.minha = dadosMinha();
  salvar();
  pista.largada = largadaPadrao(pista);
  robo.cache.clear();
  atualizarEditor();
}

function desfazer() {
  const antes = historico.pop();
  if (!antes || pista.id !== MINHA) return;
  salvo.minha = JSON.parse(antes);
  salvar();
  arraste = null;
  marcado = null;
  pista = pistaMinha();
  robo.pista = pista;
  robo.cache.clear();
  dimensionar();
  atualizarEditor();
}

// ponta de linha: na grade de 5 cm, ou de meio em meio centímetro com Shift
function encaixar(x, y, livre) {
  const g = livre ? 0.5 : GRADE, r = v => Math.round(v / g) * g;
  return [Math.max(0, Math.min(pista.largura, r(x))), Math.max(0, Math.min(pista.altura, r(y)))];
}

/* quadrado verde onde se clicou; perto de uma linha reta (de pé ou deitada) ele gruda nela, do lado do clique.
   Num cruzamento, grudando nas duas, fica no canto. */
function quadradoVerdeEm(x, y, livre) {
  const Q = EST.QUADRADO_VERDE, m = EST.LINHA / 2;
  let qx = Math.round((x - Q / 2) * 2) / 2, qy = Math.round((y - Q / 2) * 2) / 2;
  if (!livre) {
    let gx = null, gy = null;
    const perto = (novo, atual, melhor) => Math.abs(novo - atual) < 2.5 && (melhor === null || Math.abs(novo - atual) < Math.abs(melhor - atual));
    for (const {seg: [x1, y1, x2, y2]} of pista.linhas) {
      if (y1 === y2 && qx + Q > Math.min(x1, x2) - m && qx < Math.max(x1, x2) + m) {          // linha deitada
        const novo = y < y1 ? y1 - m - Q : y1 + m;
        if (perto(novo, qy, gy)) gy = novo;
      }
      if (x1 === x2 && qy + Q > Math.min(y1, y2) - m && qy < Math.max(y1, y2) + m) {          // linha de pé
        const novo = x < x1 ? x1 - m - Q : x1 + m;
        if (perto(novo, qx, gx)) gx = novo;
      }
    }
    if (gx !== null) qx = gx;
    if (gy !== null) qy = gy;
  }
  return {x: qx, y: qy, w: Q, h: Q};
}

function caixaEm(x, y) {
  return {x: Math.max(0, Math.min(pista.largura - CAIXA, Math.round(x - CAIXA / 2))),
          y: Math.max(0, Math.min(pista.altura - CAIXA, Math.round(y - CAIXA / 2))), w: CAIXA, h: CAIXA};
}

// o que o "Apagar" pega no ponto: {lista: 'caixas' | 'verdes' | 'linhas', i} ou null
function itemEm(x, y) {
  const folga = Math.max(1, 6 * (window.devicePixelRatio || 1) / vista.escala);
  const dentro = (q, f) => x >= q.x - f && x <= q.x + q.w + f && y >= q.y - f && y <= q.y + q.h + f;
  for (let i = pista.caixas.length - 1; i >= 0; i--) if (dentro(pista.caixas[i], 0)) return {lista: 'caixas', i};
  for (let i = pista.verdes.length - 1; i >= 0; i--) if (dentro(pista.verdes[i], folga / 2)) return {lista: 'verdes', i};
  let achou = null, dmin = EST.LINHA / 2 + folga;
  pista.linhas.forEach((t, i) => {
    const d = EST.distSegmento(x, y, ...t.seg);
    if (d < dmin) { dmin = d; achou = {lista: 'linhas', i}; }
  });
  return achou;
}

function apagarEm(x, y, a) {
  const item = itemEm(x, y);
  if (!item) return;
  if (!a.apagou) { guardarDesfazer(a.antes); a.apagou = true; }
  pista[item.lista].splice(item.i, 1);
  marcado = null;
  mudouMinha();
}

// quadrado verde ou caixa: um clique põe
function porItem(x, y, livre) {
  const verde = ferramenta === 'verde', lista = verde ? pista.verdes : pista.caixas;
  if (lista.length >= MAX_ITENS) return;
  guardarDesfazer();
  lista.push(verde ? quadradoVerdeEm(x, y, livre) : caixaEm(x, y));
  mudouMinha();
}

function terminarLinha(seg) {
  const [x1, y1, x2, y2] = seg;
  if (Math.hypot(x2 - x1, y2 - y1) < 1 || pista.linhas.length >= MAX_ITENS) return;
  guardarDesfazer();
  pista.linhas.push({seg});
  mudouMinha();
  // a primeira linha leva o robô para o começo dela (se a largada não foi escolhida)
  if (pista.linhas.length === 1 && !salvo.largadas[MINHA] && estado === 'pronto') colocarNaLargada();
}

function desenharEditor(c) {
  if (!editando) return;
  c.fillStyle = 'rgba(34, 80, 255, 0.6)';          // pontas das linhas, para emendar uma na outra
  for (const t of pista.linhas) {
    for (const k of [0, 2]) { c.beginPath(); c.arc(t.seg[k], t.seg[k + 1], 0.5, 0, 2 * Math.PI); c.fill(); }
  }
  const item = marcado && pista[marcado.lista][marcado.i];
  if (item && item.seg) linha(c, ...item.seg, 'rgba(226, 54, 58, 0.75)', EST.LINHA + 0.8);
  else if (item) { c.strokeStyle = '#e2363a'; c.lineWidth = 0.8; c.strokeRect(item.x, item.y, item.w, item.h); }
  if (arraste && arraste.tipo === 'linha') {
    linha(c, ...arraste.seg, 'rgba(17, 17, 17, 0.6)', EST.LINHA);
  } else if (mira && !arraste) {                   // onde a linha começa, ou onde o quadrado ou a caixa vai ficar
    c.globalAlpha = 0.55;
    if (ferramenta === 'linha') {
      const [px, py] = encaixar(mira.x, mira.y, mira.livre);
      c.fillStyle = '#2250ff';
      c.beginPath(); c.arc(px, py, 1, 0, 2 * Math.PI); c.fill();
    } else if (ferramenta === 'verde') {
      const q = quadradoVerdeEm(mira.x, mira.y, mira.livre);
      c.fillStyle = COR_VERDE; c.fillRect(q.x, q.y, q.w, q.h);
    } else if (ferramenta === 'caixa') {
      const q = caixaEm(mira.x, mira.y);
      c.fillStyle = '#c99f62'; c.fillRect(q.x, q.y, q.w, q.h);
    }
    c.globalAlpha = 1;
  }
}

const DICAS_EDITOR = {
  linha: 'Linha: arraste na pista para desenhar um trecho de linha preta. As pontas grudam na grade de 5 cm ' +
         '(segure Shift para soltar da grade); comece um trecho onde o outro termina para fazer o caminho.',
  verde: 'Quadrado verde: clique ao lado da linha, logo antes do cruzamento; ele gruda na linha (Shift: solto).',
  caixa: 'Caixa: clique para pôr um obstáculo de 10 cm em cima da linha; arraste a caixa para mudar de lugar.',
  apagar: 'Apagar: clique numa linha, num quadrado verde ou numa caixa (ou passe por cima com o botão apertado).',
};

function atualizarDica() {
  const arrastar = ' Arraste o robô para mudar a largada; a bolinha azul na frente gira o robô.';
  let texto;
  if (desafio) texto = 'No desafio o robô sempre sai da largada marcada (o contorno tracejado). Executar tenta; ' +
                       'Reiniciar volta para a largada. Para treinar com o robô e a caixa soltos, saia do desafio.';
  else if (pista.obr) texto = dicaOBR();
  else if (pista.id !== MINHA) texto = pista.dica + arrastar;
  else if (editando) texto = DICAS_EDITOR[ferramenta] + ' Ctrl+Z desfaz.';
  else if (!pista.linhas.length) texto = 'Pista em branco: aperte "✎ Desenhar a pista" para fazer a sua.';
  else texto = 'A pista que você desenhou, guardada neste navegador.' + arrastar;
  if (pista.id === MINHA && semGuardar) texto += ' Atenção: este navegador não deixa guardar, a pista some quando a página fechar.';
  $('dica').textContent = texto;
}

function atualizarEditor() {
  const minha = pista.id === MINHA;
  if (!minha) editando = false;
  $('editor').hidden = !minha;
  $('itensEditor').hidden = !editando;
  $('btEditar').setAttribute('aria-pressed', String(editando));
  $('btEditar').textContent = editando ? '✓ Pronto' : '✎ Desenhar a pista';
  $('btDesfazer').disabled = !historico.length;
  $('btApagarTudo').disabled = !minha || !(pista.linhas.length + pista.verdes.length + pista.caixas.length);
  $('larguraMinha').value = pista.largura;
  $('alturaMinha').value = pista.altura;
  if (!editando) mira = marcado = null;
  atualizarEditorOBR();
  atualizarDica();
}

$('btEditar').addEventListener('click', () => { editando = !editando; atualizarEditor(); });
for (const el of document.querySelectorAll('input[name="ferramenta"]')) {
  el.addEventListener('change', () => { ferramenta = el.value; marcado = null; atualizarDica(); });
}
$('btDesfazer').addEventListener('click', desfazer);
$('btApagarTudo').addEventListener('click', () => {
  guardarDesfazer();
  pista.linhas = []; pista.verdes = []; pista.caixas = [];
  mudouMinha();
});
for (const [id, chave, min, max] of [['larguraMinha', 'largura', 60, 400], ['alturaMinha', 'altura', 60, 300]]) {
  $(id).addEventListener('change', ev => {
    const v = parseFloat(ev.target.value);
    const novo = Number.isFinite(v) ? Math.max(min, Math.min(max, Math.round(v))) : pista[chave];
    ev.target.value = novo;
    if (novo === pista[chave]) return;
    guardarDesfazer();
    pista[chave] = novo;
    mudouMinha();
    dimensionar();
  });
}

// ---------------------------------------------------------------- arrastar o robô e as caixas

let arraste = null;          // {tipo: 'mover' | 'girar' | 'caixa' | 'linha' | 'apagar', dx, dy, caixa, seg}

function dentroDoRobo(x, y) {
  const dx = x - robo.x, dy = y - robo.y, c = Math.cos(robo.ang), s = Math.sin(robo.ang);
  const f = dx * c + dy * s, l = -dx * s + dy * c;
  const corpo = robo.config.corpo;
  return f >= -corpo.tras - 1 && f <= corpo.frente + 1 && Math.abs(l) <= corpo.largura / 2 + 1;
}

function oQueTemAqui(x, y) {
  const [ax, ay] = posicaoAlca();
  if (Math.hypot(x - ax, y - ay) < Math.max(2.5, 10 / vista.escala * (window.devicePixelRatio || 1))) return {tipo: 'girar'};
  if (dentroDoRobo(x, y)) return {tipo: 'mover'};
  if (pista.obr) return null;               // na OBR os obstáculos são fixos no ladrilho
  const cx = pista.caixas.find(c => x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h);
  return cx ? {tipo: 'caixa', caixa: cx} : null;
}

cena.addEventListener('pointerdown', ev => {
  if (desafio) return;                      // no desafio o robô e a caixa ficam onde o desafio manda
  const [x, y] = paraMundo(ev);
  if (pista.obr && editandoOBR) { cliqueOBR(x, y, ev.shiftKey); ev.preventDefault(); return; }
  let alvo = oQueTemAqui(x, y);
  // editando: a alça de girar vale sempre; o robô e as caixas se arrastam, menos quando o "Apagar" pega algo
  if (editando && !(alvo && alvo.tipo === 'girar')) {
    if (ferramenta === 'apagar') {
      if (itemEm(x, y)) alvo = {tipo: 'apagar', antes: JSON.stringify(dadosMinha())};
    } else if (!alvo) {
      if (ferramenta !== 'linha') { porItem(x, y, ev.shiftKey); ev.preventDefault(); return; }
      const [px, py] = encaixar(x, y, ev.shiftKey);
      alvo = {tipo: 'linha', seg: [px, py, px, py]};
    }
  }
  if (!alvo) return;
  arraste = alvo;
  mira = marcado = null;
  if (alvo.tipo === 'mover') { alvo.dx = robo.x - x; alvo.dy = robo.y - y; }
  if (alvo.tipo === 'caixa') { alvo.dx = alvo.caixa.x - x; alvo.dy = alvo.caixa.y - y; alvo.antes = pista.id === MINHA && JSON.stringify(dadosMinha()); }
  if (alvo.tipo === 'apagar') apagarEm(x, y, alvo);
  cena.setPointerCapture(ev.pointerId);
  cena.className = alvo.tipo === 'linha' ? 'desenhar' : alvo.tipo === 'apagar' ? 'apagar' : 'arrastando';
  ev.preventDefault();
});

cena.addEventListener('pointermove', ev => {
  const [x, y] = paraMundo(ev);
  if (!arraste) {
    if (desafio) { cena.className = ''; return; }
    if (pista.obr && editandoOBR) { cena.className = 'desenhar'; return; }
    const alvo = oQueTemAqui(x, y), girar = alvo && alvo.tipo === 'girar';
    marcado = editando && ferramenta === 'apagar' && !girar ? itemEm(x, y) : null;
    mira = editando && ferramenta !== 'apagar' && !alvo ? {x, y, livre: ev.shiftKey} : null;
    cena.className = marcado ? 'apagar' : alvo ? (girar ? 'girar' : 'pega') : editando ? 'desenhar' : '';
    return;
  }
  if (arraste.tipo === 'linha') {
    const [px, py] = encaixar(x, y, ev.shiftKey);
    arraste.seg[2] = px; arraste.seg[3] = py;
    return;
  }
  if (arraste.tipo === 'apagar') { apagarEm(x, y, arraste); return; }
  if (arraste.tipo === 'mover') {
    robo.colocar(x + arraste.dx, y + arraste.dy, robo.angGraus);
  } else if (arraste.tipo === 'girar') {
    let a = Math.atan2(y - robo.y, x - robo.x) * 180 / Math.PI;
    if (!ev.shiftKey) a = Math.round(a / 5) * 5;          // de 5 em 5 graus (Shift: livre)
    robo.colocar(robo.x, robo.y, a);
  } else {
    const c = arraste.caixa;
    c.x = Math.max(-c.w / 2, Math.min(pista.largura - c.w / 2, x + arraste.dx));
    c.y = Math.max(-c.h / 2, Math.min(pista.altura - c.h / 2, y + arraste.dy));
    arraste.moveu = true;
  }
  if (arraste.tipo !== 'caixa') {
    if (estado === 'pronto') robo.rastro = [[robo.x, robo.y]];
    else if (robo.rastro[robo.rastro.length - 1] !== null) robo.rastro.push(null);
  }
});

function soltar(ev) {
  if (!arraste) return;
  const a = arraste;
  arraste = null;
  if (a.tipo === 'linha') {
    if (ev.type !== 'pointercancel') terminarLinha(a.seg);
  } else if (a.tipo === 'apagar') {
    // já apagou e guardou ao passar
  } else if (a.tipo === 'caixa' && pista.id === MINHA) {
    if (a.moveu) { guardarDesfazer(a.antes); mudouMinha(); }
  } else {
    if (a.tipo === 'caixa') {
      salvo.caixas[pista.id] = pista.caixas.map(c => ({x: c.x, y: c.y}));
    } else if (estado === 'pronto') {
      salvo.largadas[pista.id] = {x: robo.x, y: robo.y, ang: robo.angGraus};
    }
    salvar();
  }
  cena.className = editando ? 'desenhar' : '';
  atualizarPainel();
}
cena.addEventListener('pointerup', soltar);
cena.addEventListener('pointercancel', soltar);
cena.addEventListener('pointerleave', () => { if (!arraste) mira = marcado = null; });

// ---------------------------------------------------------------- painel

function desenharLcd(forcar) {
  const lcd = $('lcd'), c = lcd.getContext('2d');
  if (!forcar && desenharLcd.versao === robo.telaVersao) return;
  desenharLcd.versao = robo.telaVersao;
  const s = getComputedStyle(document.documentElement);
  c.fillStyle = s.getPropertyValue('--lcd-bg').trim();
  c.fillRect(0, 0, lcd.width, lcd.height);
  c.fillStyle = s.getPropertyValue('--lcd-fg').trim();
  c.font = 'bold 30px Consolas, "Cascadia Mono", monospace';
  c.textBaseline = 'top';
  for (const item of robo.tela) c.fillText(item.texto, item.x * 2, item.y * 2 + 2);   // a tela tem 128 x 64 pontos
}

function linhaSensor(p, s) {
  const bola = `<span class="amostra" style="background:${CORES_SENSOR[p]}"></span>`;
  const lido = `<span class="lido${tSim - (robo.lidas[p] ?? -9) < 0.25 && estado !== 'pronto' ? ' sim' : ''}" title="lido pelo programa agora"></span>`;
  if (s.tipo === 'cor') {
    const l = robo.sensorCor(p);
    return `<tr><td>${bola}S${p}${lido}</td><td>cor</td><td class="num">luz ${l.luz}</td><td class="num">${EST.NOMES_COR[l.cor]} (${l.cor})</td></tr>`;
  }
  if (s.tipo === 'ultrassom') {
    const u = robo.sensorUltrassom(p);
    return `<tr><td>${bola}S${p}${lido}</td><td>ultrassom</td><td class="num" colspan="2">${num(u.cm)} cm</td></tr>`;
  }
  return `<tr><td>S${p}</td><td colspan="3">sem sensor</td></tr>`;
}

function atualizarSensores() {
  $('sensores').innerHTML = Object.entries(robo.config.portas).map(([p, s]) => linhaSensor(p, s)).join('');
}

function atualizarMotores() {
  const cfg = robo.config;
  const html = [];
  for (const [l, m] of Object.entries(robo.motores)) {
    const papel = l === cfg.motor_esquerdo ? 'esquerda' : l === cfg.motor_direito ? 'direita' : '';
    if (!papel && !m.cmd) continue;
    const p = Math.round(m.pot);
    const w = Math.min(50, Math.abs(p) / 2), x = p >= 0 ? 50 : 50 - w;
    html.push(`<div class="motor"><span><b>${l}</b> ${papel}</span><span class="barra"><i style="left:${x}%;width:${w}%"></i></span><span class="num">${p}</span></div>`);
  }
  $('motores').innerHTML = html.join('');
}

function atualizarVariaveis() {
  const nomes = P && vm ? Object.keys(P.variaveis || {}) : [];
  $('cartaoVariaveis').hidden = !nomes.length;
  if (!nomes.length) return;
  $('variaveis').innerHTML = nomes.map(n => {
    const v = vm.lerFloat(P.variaveis[n]);
    return `<tr><td>${escapar(n)}</td><td class="num">${EST.numeroParaTexto(v).replace('.', ',')}</td></tr>`;
  }).join('');
}

function escapar(s) {
  return String(s).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
}

function montarFonte() {
  const pre = $('fonte');
  if (!P) {
    pre.outerHTML = `<p class="vazio" id="fonte">Nenhum programa carregado. No VS Code, abra o seu programa e escolha
      <b>Terminal → Executar Tarefa → Simular no computador</b>. Pelo terminal:
      <code>python simular.py meu_programa.py</code></p>`;
    return;
  }
  pre.innerHTML = P.fonte.replace(/\r/g, '').split('\n').map((t, i) => {
    let html = escapar(t);
    const k = t.indexOf('#');
    if (k >= 0 && !/['"]/.test(t.slice(0, k))) html = escapar(t.slice(0, k)) + `<span class="c">${escapar(t.slice(k))}</span>`;
    const n = i + 1, p = paradas.has(n);
    // o número de uma linha com código liga e desliga o ponto de parada
    const nl = linhasComCodigo.has(n)
      ? `<span class="nl cod${p ? ' parada' : ''}" role="button" tabindex="0" aria-pressed="${p}" aria-label="Ponto de parada na linha ${n}">${n}</span>`
      : `<span class="nl">${n}</span>`;
    return `<span class="ln" data-n="${n}">${nl}${html || ' '}</span>`;
  }).join('');
  pre.scrollTop = 0;
  linhasMarcadas = [];
}

let linhasMarcadas = [];
function marcarLinhas() {
  const pre = $('fonte');
  if (!vm || !pre || pre.tagName !== 'PRE') return;
  for (const el of linhasMarcadas) el.classList.remove('ativa', 'dentro', 'erro');
  linhasMarcadas = [];
  const marcar = (n, classe) => {
    const el = pre.children[n - 1];
    if (el) { el.classList.add(classe); linhasMarcadas.push(el); }
    return el;
  };
  if (estado === 'erro' && vm.erro) { marcar(linhaDoPc(vm.erro.pc), 'erro'); return; }
  if (estado !== 'rodando' && estado !== 'pausado') return;
  let principal = null;
  for (const th of vm.ativas()) {
    const n = linhaDoPc(th.pc);
    if (!n) continue;
    const el = marcar(n, th.esperandoThread ? 'dentro' : 'ativa');
    if (!th.esperandoThread) principal = el;
  }
  // mantém a linha que está rodando visível dentro da caixa do programa
  if (principal && (principal.offsetTop < pre.scrollTop || principal.offsetTop > pre.scrollTop + pre.clientHeight - 20)) {
    pre.scrollTop = principal.offsetTop - pre.clientHeight / 3;
  }
}

function atualizarAvisos() {
  const lista = [...(P && P.avisos ? P.avisos : []), ...robo.avisos];
  const caixa = $('avisos');
  caixa.hidden = !lista.length;
  caixa.innerHTML = lista.map(a => `<p>⚠ ${escapar(a)}</p>`).join('');
}

const TEXTO_ESTADO = {
  sem: 'Nenhum programa',
  pronto: 'Pronto: arraste o robô para a largada e aperte Executar',
  rodando: 'Executando',
  pausado: 'Pausado',
};

function atualizarEstado() {
  const bt = $('btExecutar');
  bt.disabled = !vm;
  $('btProxima').disabled = !vm || !marcas.length;
  bt.textContent = {rodando: '⏸ Pausar', pausado: '▶ Continuar', terminou: '▶ Executar de novo', erro: '▶ Executar de novo'}[estado] || '▶ Executar';
  const el = $('estado');
  el.className = 'estado' + (estado === 'terminou' ? ' ok' : estado === 'erro' ? ' erro' : '');
  if (erroCarga) el.textContent = `Este programa não pode ser simulado: ${erroCarga.message} (byte ${erroCarga.pc})`;
  else if (prova && prova.resultado && estado !== 'rodando' && estado !== 'erro') {
    el.textContent = prova.resultado.ok ? 'Desafio cumprido!' : 'Desafio não cumprido';
    el.className = 'estado ' + (prova.resultado.ok ? 'ok' : 'erro');
  } else if (estado === 'terminou') el.textContent = `O programa terminou em ${num(tFim)} s`;
  else if (estado === 'erro') el.textContent = `Erro na simulação: ${vm.erro.message} (byte ${vm.erro.pc})`;
  else if (desafio && estado === 'pronto') el.textContent = 'Pronto: aperte Executar para tentar o desafio';
  else if (estado === 'pausado' && motivoParada) {
    el.textContent = motivoParada.tipo === 'parada' ? `Ponto de parada: pausado na linha ${motivoParada.linha}`
      : `Pausado na linha ${motivoParada.linha}: aperte Próxima linha ou Continuar`;
  } else if (estado === 'rodando' && passoAPasso) el.textContent = 'Executando até a próxima linha';
  else el.textContent = TEXTO_ESTADO[estado];
  if (erroCarga) el.className = 'estado erro';
}

function atualizarRelogio() {
  $('relogio').textContent = `${num(estado === 'terminou' || estado === 'erro' ? tFim : tSim)} s`;
}

function atualizarLuzSom() {
  const luz = corDaLuz(), el = $('luz');
  el.className = 'luz' + (luz ? ' acesa' : '');
  el.style.background = luz || '';
  el.style.color = luz || '';
  $('luzNome').textContent = robo.luz === null ? 'luz apagada' : `luz ${NOMES_LUZ[robo.luz]}`;
  $('som').textContent = tSim < somAte && estado !== 'pronto' ? somTexto : '';
}

function atualizarPainel() {
  atualizarSensores();
  atualizarMotores();
  atualizarVariaveis();
  atualizarLuzSom();
  atualizarRelogio();
  marcarLinhas();
  atualizarStatusDesafio();
  atualizarOBR();
  if (atualizarPainel.avisos !== robo.avisos.size) { atualizarPainel.avisos = robo.avisos.size; atualizarAvisos(); }
}

function atualizarTudo() {
  atualizarEstado();
  atualizarPainel();
  desenharLcd();
}

// ---------------------------------------------------------------- medidas do robô

const CAMPOS_ROBO = [
  ['roda_cm', 'Diâmetro da roda', 1, 20, 0.1],
  ['entre_rodas_cm', 'Entre as rodas', 3, 40, 0.1],
  ['rpm_max', 'Rotação com potência 100 (rpm)', 10, 600, 1],
];
const CAMPOS_CORPO = [['frente', 'à frente'], ['tras', 'atrás'], ['largura', 'largura']];

function montarMedidas() {
  const cfg = robo.config;
  const motor = (chave) => `<select data-chave="${chave}">${'ABCD'.split('').map(l => `<option${cfg[chave] === l ? ' selected' : ''}>${l}</option>`).join('')}</select>`;
  let html = '<table class="medidas"><tbody>';
  for (const [k, rotulo, min, max, passo] of CAMPOS_ROBO) {
    html += `<tr><td colspan="3" class="rotulo">${rotulo}</td><td colspan="2"><input type="number" data-chave="${k}" min="${min}" max="${max}" step="${passo}" value="${cfg[k]}"></td></tr>`;
  }
  html += `<tr><td colspan="3" class="rotulo">Motor da roda esquerda / direita</td><td>${motor('motor_esquerdo')}</td><td>${motor('motor_direito')}</td></tr>`;
  html += `<tr><td colspan="5" class="rotulo"><label class="marcar"><input type="checkbox" data-chave="invertido"${cfg.invertido ? ' checked' : ''}> Motores invertidos (potência positiva anda de ré)</label></td></tr>`;
  html += '</tbody></table><table class="medidas"><thead><tr><th>Porta</th><th>Sensor</th><th>à frente</th><th>à esquerda</th><th>preto</th></tr></thead><tbody>';
  for (const [p, s] of Object.entries(cfg.portas)) {
    const tipo = ['cor', 'ultrassom', 'nenhum'].map(t => `<option value="${t}"${s.tipo === t ? ' selected' : ''}>${t}</option>`).join('');
    html += `<tr><td><span class="amostra" style="background:${CORES_SENSOR[p]}"></span>S${p}</td>
      <td><select data-porta="${p}" data-chave="tipo">${tipo}</select></td>
      <td><input type="number" data-porta="${p}" data-chave="frente" min="-30" max="40" step="0.1" value="${s.frente}"></td>
      <td><input type="number" data-porta="${p}" data-chave="esquerda" min="-20" max="20" step="0.1" value="${s.esquerda}"></td>
      <td><input type="number" data-porta="${p}" data-chave="preto" min="0" max="90" step="1" value="${s.preto ?? 10}"${s.tipo === 'cor' ? '' : ' disabled'}></td></tr>`;
  }
  html += '</tbody></table><table class="medidas"><thead><tr><th>Corpo</th>' + CAMPOS_CORPO.map(c => `<th>${c[1]}</th>`).join('') + '</tr></thead><tbody><tr><td></td>';
  for (const [k] of CAMPOS_CORPO) html += `<td><input type="number" data-corpo="${k}" min="1" max="60" step="0.5" value="${cfg.corpo[k]}"></td>`;
  html += '</tr></tbody></table>';
  $('formMedidas').innerHTML = html;
}

$('formMedidas').addEventListener('change', ev => {
  const el = ev.target, cfg = robo.config, chave = el.dataset.chave;
  let v = el.type === 'checkbox' ? el.checked : el.tagName === 'SELECT' ? el.value : parseFloat(el.value);
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) { montarMedidas(); return; }
    v = Math.max(+el.min, Math.min(+el.max, v));
  }
  if (el.dataset.corpo) cfg.corpo[el.dataset.corpo] = v;
  else if (el.dataset.porta) {
    const s = cfg.portas[el.dataset.porta];
    s[chave] = v;
    if (chave === 'tipo' && v === 'cor' && !Number.isFinite(s.preto)) s.preto = 10;
  } else cfg[chave] = v;
  salvo.robo = cfg;
  salvar();
  robo.cache.clear();
  if (chave === 'tipo') montarMedidas();          // liga/desliga o campo "preto"
  else if (typeof v === 'number') el.value = v;
  atualizarPainel();
});

$('btPadrao').addEventListener('click', () => {
  const padrao = copia(EST.ROBO_PADRAO);
  for (const k of Object.keys(robo.config)) delete robo.config[k];
  Object.assign(robo.config, padrao);
  delete salvo.robo;
  salvar();
  robo.cache.clear();
  montarMedidas();
  atualizarPainel();
});

// ---------------------------------------------------------------- controles

function trocarPista(id) {
  pista = montarPista(id);
  robo.pista = pista;
  if (!P || !P.pista) {             // a pista de um exemplo da demonstração não fica guardada
    salvo.pista = pista.id;
    salvar();
  }
  $('pista').value = pista.id;
  if (pista.id === MINHA && !pista.linhas.length) editando = true;      // pista em branco: já abre desenhando
  if (pista.id === MINHA_OBR && !pista.obr.arena.percurso.length) editandoOBR = true;
  atualizarEditor();
  dimensionar();
  reiniciar();
}

// nome no topo, programa no painel, botão de toque e avisos de compilação do programa atual
function mostrarPrograma() {
  if (P) {
    const gerado = P.gerado ? ` · gerado em ${escapar(P.gerado)}` : '';
    $('arquivo').innerHTML = `<strong>${escapar(P.nome)}</strong> · ${codigo ? codigo.length : 0} bytes${gerado}`;
    document.title = `${P.nome}: simulador do robô EST`;
  }
  carregarParadas();
  montarFonte();
  btToque.hidden = !usaToque;
  soltarPendente = null;
  apertar(false);
  $('botoes').hidden = !usaBotoes;
  apertarBotao(0);
  atualizarAvisos();
}

function trocarExemplo(i) {
  exemplo = i;
  lerPrograma(PROGRAMAS[i]);
  vm = novaVM();
  try { location.replace('#' + encodeURIComponent(chaveDe(P))); } catch (e) { /* fica sem guardar */ }
  if (!desafio && P.pista && EST.PISTAS.some(p => p.id === P.pista)) trocarPista(P.pista);
  else reiniciar();
  mostrarPrograma();
}

// ---------------------------------------------------------------- arena da OBR (obr.js)

// as marcas de lápis entre os ladrilhos (montando: a grade inteira, para escolher onde vai cada um)
function desenharLadrilhos(c) {
  const {LADO, BORDA} = EST.OBR, a = pista.obr.arena;
  c.save();
  c.lineWidth = 0.3;
  if (editandoOBR) {
    c.setLineDash([1, 1]);
    c.strokeStyle = '#c6cedb';
    for (let col = 0; col < a.colunas; col++) {
      for (let lin = 0; lin < a.linhas; lin++) c.strokeRect(BORDA + col * LADO, BORDA + lin * LADO, LADO, LADO);
    }
    c.setLineDash([]);
  }
  c.strokeStyle = '#d2d8e2';
  for (const t of a.percurso) c.strokeRect(BORDA + t.c * LADO, BORDA + t.r * LADO, LADO, LADO);
  c.restore();
}

// checkpoints (marcador laranja), partida, números do percurso (montando) e o ladrilho onde o robô está (rodada)
function desenharMarcasOBR(c) {
  const {LADO, BORDA} = EST.OBR, perc = pista.obr.arena.percurso;
  const canto = t => [BORDA + t.c * LADO, BORDA + t.r * LADO];
  c.save();
  c.textAlign = 'center';
  c.textBaseline = 'middle';
  for (const t of perc) {
    if (!t.checkpoint) continue;
    const [x0, y0] = canto(t);
    c.fillStyle = '#f08a24';
    c.strokeStyle = '#a4520c';
    c.lineWidth = 0.3;
    c.beginPath(); c.arc(x0 + 4, y0 + 4, 2, 0, 2 * Math.PI); c.fill(); c.stroke();
  }
  if (perc.length) {
    const [x0, y0] = canto(perc[0]);
    c.fillStyle = '#586079';
    c.font = 'bold 2.6px "Segoe UI", system-ui, sans-serif';
    c.fillText('PARTIDA', x0 + LADO / 2, y0 + 3);
  }
  c.font = 'bold 2.8px "Segoe UI", system-ui, sans-serif';
  if (editandoOBR) {
    perc.forEach((t, i) => {
      const [x0, y0] = canto(t);
      const vez = perc.slice(0, i).filter(q => q.c === t.c && q.r === t.r).length;    // passa de novo: ao lado
      const x = x0 + LADO - 4 - vez * 5.5, y = y0 + LADO - 4;
      c.fillStyle = i === escolhidoOBR ? '#e8792b' : 'rgba(34, 80, 255, 0.85)';
      c.beginPath(); c.arc(x, y, 2.4, 0, 2 * Math.PI); c.fill();
      c.fillStyle = '#ffffff';
      c.fillText(String(i + 1), x, y + 0.1);
    });
    const t = perc[escolhidoOBR];
    if (t) {
      const [x0, y0] = canto(t);
      c.strokeStyle = '#e8792b';
      c.lineWidth = 0.8;
      c.strokeRect(x0 + 0.4, y0 + 0.4, LADO - 0.8, LADO - 0.8);
    }
  } else if (placar && !placar.fim && estado !== 'pronto' && perc[placar.k]) {
    const [x0, y0] = canto(perc[placar.k]);
    c.setLineDash([1.2, 0.8]);
    c.strokeStyle = 'rgba(34, 80, 255, 0.7)';
    c.lineWidth = 0.5;
    c.strokeRect(x0 + 0.5, y0 + 0.5, LADO - 1, LADO - 1);
  }
  c.restore();
}

function dicaOBR() {
  const rodada = ' Executar começa a rodada de 5 minutos; Reiniciar recomeça. O robô sai sempre do ladrilho de partida.';
  if (pista.id !== MINHA_OBR) return pista.dica + rodada;
  if (editandoOBR) {
    return 'Clique nos quadrados da grade, um depois do outro, para fazer o caminho do robô: o primeiro é a partida e o ' +
           'último é a chegada (faixa vermelha). "Meia-volta" faz um beco sem saída; Shift + clique passa de novo por um ' +
           'ladrilho (cruzamento). Clique num ladrilho já colocado para escolher o perigo dele ou pôr um checkpoint.';
  }
  if (!pista.obr.arena.percurso.length) return 'Arena em branco: aperte "✎ Montar o percurso" para fazer a sua com ladrilhos de 30 cm.';
  return 'A arena que você montou, guardada neste navegador.' + rodada;
}

function atualizarEditorOBR() {
  const minha = pista.id === MINHA_OBR;
  if (!minha) { editandoOBR = false; escolhidoOBR = -1; }
  $('editorOBR').hidden = !minha;
  $('itensOBR').hidden = !editandoOBR;
  $('btMontarOBR').setAttribute('aria-pressed', String(editandoOBR));
  $('btMontarOBR').textContent = editandoOBR ? '✓ Pronto' : '✎ Montar o percurso';
  if (!minha) return;
  const a = pista.obr.arena, t = a.percurso[escolhidoOBR];
  $('btTirarOBR').disabled = !a.percurso.length;
  $('btBecoOBR').disabled = a.percurso.length < 2;
  $('btApagarOBR').disabled = !a.percurso.length;
  $('colunasOBR').value = a.colunas;
  $('linhasOBR').value = a.linhas;
  $('nivelOBR').value = String(a.nivel);
  $('escolhidoOBR').hidden = !t;
  if (t) {
    const n = escolhidoOBR + 1, papel = n === 1 ? ' (partida)' : n === a.percurso.length ? ' (chegada)' : '';
    $('numeroOBR').textContent = `Ladrilho ${n}${papel}`;
    $('elementoOBR').value = t.elemento === 'gap' ? `gap${t.gap}` : t.elemento === 'T' && t.ramo ? `T${t.ramo}` : t.elemento;
    $('checkpointOBR').checked = !!t.checkpoint;
    $('suaveOBR').checked = t.curva === 'suave';
    $('verdeDepoisOBR').value = t.verdeDepois || '';
  }
  const erros = pista.obr.erros;
  $('errosOBR').hidden = !erros.length;
  $('errosOBR').textContent = erros.length ? `Para valer a rodada, corrija: ${erros.join('; ')}.` : '';
}

// montando a arena: clique num quadrado da grade encostado no último ladrilho para pôr o próximo; num ladrilho já
// colocado, escolhe ele (se o percurso passa mais de uma vez, cada clique escolhe uma das vezes); Shift: passa de novo
function cliqueOBR(x, y, shift) {
  const {LADO, BORDA} = EST.OBR, a = pista.obr.arena, perc = a.percurso;
  const c = Math.floor((x - BORDA) / LADO), r = Math.floor((y - BORDA) / LADO);
  if (c < 0 || r < 0 || c >= a.colunas || r >= a.linhas) return;
  const ultimo = perc[perc.length - 1], encosta = !ultimo || EST.OBR.vizinhos(ultimo, {c, r});
  const vezes = perc.map((t, i) => (t.c === c && t.r === r ? i : -1)).filter(i => i >= 0);
  if (vezes.length && !(shift && encosta)) {
    const k = vezes.indexOf(escolhidoOBR);
    escolhidoOBR = k < 0 ? vezes[vezes.length - 1] : vezes[(k + vezes.length - 1) % vezes.length];
    atualizarEditor();
    return;
  }
  if (!encosta) return;
  perc.push({c, r, elemento: ''});
  escolhidoOBR = -1;
  mudouArenaOBR();
}

function mudouArenaOBR() {
  salvo.arenaOBR = copia(pista.obr.arena);
  salvar();
  const antes = [pista.largura, pista.altura];
  pista = montarPista(MINHA_OBR);
  robo.pista = pista;
  robo.cache.clear();
  if (antes[0] !== pista.largura || antes[1] !== pista.altura) dimensionar();
  reiniciar();
  atualizarEditor();
}

const ladrilhoEscolhido = () => pista.obr && pista.obr.arena.percurso[escolhidoOBR];

// a faixa vermelha está embaixo do robô (de trás até a frente, pela linha do meio)?
function sobreVermelho() {
  const corpo = robo.config.corpo;
  for (let f = -corpo.tras; f <= corpo.frente; f += 1) {
    const [px, py] = robo.ponto(f, 0);
    if (pista.vermelhos.some(q => px >= q.x && px <= q.x + q.w && py >= q.y && py <= q.y + q.h)) return true;
  }
  return false;
}

function verificarOBR() {
  const r = placar.passo({t: tSim, x: robo.x, y: robo.y, parado: tSim - ultimoMovimento, sobreVermelho: sobreVermelho()});
  if (!r) return;
  if (r.falha) {
    falhaDeProgresso(r);
  } else if (r.fim) {
    if (estado === 'rodando') { estado = 'pausado'; if (audio) audio.suspend(); }     // o robô para onde acabou
    silenciar();
    atualizarTudo();
  }
}

// falha de progresso: o robô volta ao último checkpoint e o programa recomeça do início (como na OBR)
function falhaDeProgresso(r) {
  silenciar();
  robo.reiniciar();
  robo.colocar(r.largada.x, r.largada.y, r.largada.ang);
  robo.rastro = [[robo.x, robo.y]];
  if (vm) vm.reiniciar();
  if (estado === 'terminou') estado = 'rodando';
  ultimoMovimento = tSim;
  posAnterior = [robo.x, robo.y, robo.ang];
  desenharLcd(true);
  atualizarTudo();
}

function atualizarOBR() {
  const mostra = !!pista.obr && !desafio;
  $('cartaoOBR').hidden = !mostra;
  if (!mostra) return;
  let pontos = '0', tempo = '5:00', conta = '', texto, classe = 'desafio-status';
  if (!placar) {
    texto = editandoOBR ? 'Montando a arena: aperte "✓ Pronto" para correr.'
      : pista.obr.erros.length ? 'A arena tem problemas: veja a lista embaixo da pista.' : 'Monte o percurso para correr.';
  } else {
    const p = placar.pontos, resta = Math.max(0, EST.OBR.RODADA - tSim);
    pontos = String(placar.total);
    tempo = `${Math.floor(resta / 60)}:${String(Math.floor(resta % 60)).padStart(2, '0')}`;
    conta = `ladrilhos ${p.ladrilhos} · perigos ${p.perigos} · chegada ${p.chegada} · falhas de progresso ${placar.falhas} · ` +
            `ladrilho ${placar.k + 1} de ${placar.percurso.length} · ${placar.tentativa}ª tentativa`;
    texto = estado === 'pronto' ? 'Aperte Executar para começar a rodada.' : placar.ultimo;
    if (placar.fim) classe += placar.pontos.chegada ? ' ok' : ' falhou';
  }
  $('obrPontos').textContent = pontos;
  $('obrTempo').textContent = tempo;
  $('obrConta').textContent = conta;
  if ($('obrStatus').textContent !== texto) $('obrStatus').textContent = texto;
  $('obrStatus').className = classe;
  $('btFalhaOBR').disabled = !placar || !!placar.fim || estado === 'pronto';
}

$('btFalhaOBR').addEventListener('click', () => {
  if (placar && !placar.fim && estado !== 'pronto') falhaDeProgresso(placar.falha('declarada pelo capitão'));
});
$('btMontarOBR').addEventListener('click', () => {
  editandoOBR = !editandoOBR;
  escolhidoOBR = -1;
  reiniciar();
  atualizarEditor();
});
$('btTirarOBR').addEventListener('click', () => { pista.obr.arena.percurso.pop(); escolhidoOBR = -1; mudouArenaOBR(); });
$('btBecoOBR').addEventListener('click', () => {
  const perc = pista.obr.arena.percurso;
  if (perc.length < 2) return;
  const antes = perc[perc.length - 2];
  perc.push({c: antes.c, r: antes.r, elemento: ''});
  mudouArenaOBR();
});
$('btApagarOBR').addEventListener('click', () => {
  if (!window.confirm('Apagar o percurso inteiro desta arena?')) return;
  pista.obr.arena.percurso = [];
  escolhidoOBR = -1;
  mudouArenaOBR();
});
for (const [id, campo, min, max] of [['colunasOBR', 'colunas', 2, 12], ['linhasOBR', 'linhas', 2, 9]]) {
  $(id).addEventListener('change', ev => {
    const v = parseInt(ev.target.value, 10);
    if (Number.isFinite(v)) pista.obr.arena[campo] = Math.max(min, Math.min(max, v));
    escolhidoOBR = -1;
    mudouArenaOBR();
  });
}
$('nivelOBR').addEventListener('change', ev => { pista.obr.arena.nivel = ev.target.value === '2' ? 2 : 1; mudouArenaOBR(); });
$('elementoOBR').addEventListener('change', ev => {
  const t = ladrilhoEscolhido(), v = ev.target.value;
  if (!t) return;
  delete t.gap;
  delete t.ramo;
  if (v.startsWith('gap')) { t.elemento = 'gap'; t.gap = Number(v.slice(3)); }
  else if (v === 'Tdireita' || v === 'Treto') { t.elemento = 'T'; t.ramo = v === 'Tdireita' ? 'direita' : 'reto'; }
  else t.elemento = v;
  mudouArenaOBR();
});
$('checkpointOBR').addEventListener('change', ev => {
  const t = ladrilhoEscolhido();
  if (!t) return;
  if (ev.target.checked) t.checkpoint = true; else delete t.checkpoint;
  mudouArenaOBR();
});
$('suaveOBR').addEventListener('change', ev => {
  const t = ladrilhoEscolhido();
  if (!t) return;
  if (ev.target.checked) t.curva = 'suave'; else delete t.curva;
  mudouArenaOBR();
});
$('verdeDepoisOBR').addEventListener('change', ev => {
  const t = ladrilhoEscolhido();
  if (!t) return;
  if (ev.target.value) t.verdeDepois = ev.target.value; else delete t.verdeDepois;
  mudouArenaOBR();
});

// ---------------------------------------------------------------- trilha de desafios

let ultimoMovimento = 0, posAnterior = null;      // para saber há quanto tempo o robô está parado

const cumprido = id => !!(salvo.desafios[id] && salvo.desafios[id].feito);
// um desafio destrava quando o anterior é cumprido (ou quando o professor libera todos)
const liberado = i => i === 0 || salvo.desafiosLivres === true || cumprido(EST.DESAFIOS[i - 1].id);

function pistaDoDesafio(d) {
  const p = EST.copiaPista(typeof d.pista === 'string' ? EST.PISTAS.find(q => q.id === d.pista) : d.pista);
  p.largada = d.largada;
  return p;
}

function novaProva() {
  prova = desafio ? {} : null;
  ultimoMovimento = 0;
  posAnterior = [robo.x, robo.y, robo.ang];
  $('avisoDesafio').textContent = '';
  mostrarDesafio();
}

function montarSeletorDesafio() {
  $('desafio').innerHTML = '<option value="">Nenhum (treino livre)</option>' + EST.DESAFIOS.map((d, i) => {
    const livre = liberado(i);
    return `<option value="${d.id}"${livre ? '' : ' disabled'}>${livre ? '' : '🔒 '}${i + 1}. ${escapar(d.titulo)}${cumprido(d.id) ? ' ✓' : ''}</option>`;
  }).join('');
  $('desafio').value = desafio ? desafio.id : '';
}

function entrarDesafio(id) {
  const i = EST.DESAFIOS.findIndex(d => d.id === id);
  if (i < 0 || !liberado(i)) return;
  desafio = EST.DESAFIOS[i];
  salvo.desafio = id;                       // o simular.py abre a página de novo: volta neste desafio
  salvar();
  pista = pistaDoDesafio(desafio);
  robo.pista = pista;
  $('pista').value = 'desafio';
  montarSeletorDesafio();
  atualizarEditor();
  dimensionar();
  reiniciar();
}

function sairDesafio() {
  desafio = null;
  salvo.desafio = '';
  salvar();
  montarSeletorDesafio();
  trocarPista((P && P.pista) || salvo.pista);
}

function verificarDesafio() {
  const r = desafio.verificar(prova, {
    t: tSim, x: robo.x, y: robo.y, frente: robo.ponto(robo.config.corpo.frente, 0), parado: tSim - ultimoMovimento,
    terminou: estado === 'terminou', batidas: robo.batidas, pista,
  });
  if (!r) return;
  prova.resultado = r;
  prova.tempo = tSim;
  if (r.ok) {
    const antes = salvo.desafios[desafio.id];
    const melhor = Math.min(antes && Number.isFinite(antes.tempo) ? antes.tempo : Infinity, Math.round(tSim * 10) / 10);
    salvo.desafios[desafio.id] = {feito: true, tempo: melhor};
    salvar();
    montarSeletorDesafio();
  }
  if (estado === 'rodando') { estado = 'pausado'; if (audio) audio.suspend(); }      // o robô para onde acabou
  $('avisoDesafio').textContent = r.ok ? 'Desafio cumprido!' : `Desafio não cumprido: ${r.motivo}`;
  mostrarDesafio();
  atualizarTudo();
}

function mostrarDesafio() {
  $('cartaoDesafio').hidden = !desafio;
  $('pista').disabled = !!desafio;
  $('btLargada').hidden = !!desafio || !!pista.obr;
  if (!desafio) return;
  const i = EST.DESAFIOS.indexOf(desafio), total = EST.DESAFIOS.length;
  $('desafioNum').textContent = `Desafio ${i + 1} de ${total}`;
  $('desafioProgresso').textContent = `cumpridos: ${EST.DESAFIOS.filter(d => cumprido(d.id)).length} de ${total}`;
  $('desafioTitulo').textContent = desafio.titulo;
  $('desafioObjetivo').textContent = desafio.objetivo;
  $('desafioDica').hidden = !desafio.dica;
  $('desafioDica').textContent = desafio.dica ? `Dica: ${desafio.dica}` : '';
  atualizarStatusDesafio();
}

function atualizarStatusDesafio() {
  if (!desafio || !prova) return;
  const r = prova.resultado, proximo = EST.DESAFIOS[EST.DESAFIOS.indexOf(desafio) + 1];
  let texto, classe = 'desafio-status';
  if (r && r.ok) {
    texto = `🏆 Desafio cumprido em ${num(prova.tempo)} s!` + (proximo ? '' : ' Você completou a trilha!');
    classe += ' ok';
  } else if (r) {
    texto = `Ainda não: ${r.motivo}. Aperte Reiniciar e tente de novo.`;
    classe += ' falhou';
  } else if (estado === 'pronto') {
    const feito = salvo.desafios[desafio.id];
    texto = feito && feito.feito ? `Já cumprido (melhor tempo ${num(feito.tempo)} s). Aperte Executar para tentar de novo.`
      : 'Aperte Executar para tentar.';
  } else {
    texto = prova.texto ? `Valendo: ${prova.texto}` : 'Valendo!';
  }
  const el = $('desafioStatus');
  if (el.textContent !== texto) el.textContent = texto;
  el.className = classe;
  $('cartaoDesafio').classList.toggle('cumprido', !!(r && r.ok));
  $('btProximoDesafio').hidden = !(r && r.ok && proximo);
}

// faixas onde parar, marcos para passar (o número fica verde quando o robô passa) e o contorno da largada
function desenharDesafio(c) {
  c.save();
  c.setLineDash([1.2, 0.8]);
  c.font = '3px "Segoe UI", system-ui, sans-serif';
  c.textAlign = 'center';
  for (const z of desafio.zonas || []) {
    c.fillStyle = 'rgba(34, 80, 255, 0.14)';
    c.fillRect(z.x, z.y, z.w, z.h);
    c.strokeStyle = '#2250ff';
    c.lineWidth = 0.35;
    c.strokeRect(z.x, z.y, z.w, z.h);
    if (z.rotulo) { c.fillStyle = '#2250ff'; c.textBaseline = 'bottom'; c.fillText(z.rotulo, z.x + z.w / 2, z.y - 0.8); }
  }
  if (desafio.marcos) {
    const seq = (prova && prova.seq) || 0, feitos = prova && prova.marcos ? prova.marcos[seq] : 0;
    desafio.marcos[seq].forEach(([x, y], k) => {
      const cor = k < feitos ? '#1d7f4e' : '#2250ff';
      c.setLineDash([1.2, 0.8]);
      c.strokeStyle = cor;
      c.lineWidth = 0.4;
      c.beginPath(); c.arc(x, y, desafio.raio, 0, 2 * Math.PI); c.stroke();
      const nx = x + desafio.raio * 0.72, ny = y - desafio.raio * 0.72;
      c.fillStyle = cor;
      c.beginPath(); c.arc(nx, ny, 2.2, 0, 2 * Math.PI); c.fill();
      c.fillStyle = '#ffffff';
      c.font = 'bold 2.8px "Segoe UI", system-ui, sans-serif';
      c.textBaseline = 'middle';
      c.fillText(k < feitos ? '✓' : String(k + 1), nx, ny + 0.1);
    });
  }
  const l = desafio.largada, corpo = robo.config.corpo;
  c.setLineDash([1.2, 0.8]);
  c.translate(l.x, l.y);
  c.rotate(l.ang * Math.PI / 180);
  c.strokeStyle = 'rgba(88, 96, 121, 0.85)';
  c.lineWidth = 0.35;
  c.strokeRect(-corpo.tras, -corpo.largura / 2, corpo.frente + corpo.tras, corpo.largura);
  c.restore();
}

$('desafio').addEventListener('change', ev => { if (ev.target.value) entrarDesafio(ev.target.value); else sairDesafio(); });
$('btSairDesafio').addEventListener('click', sairDesafio);
$('btProximoDesafio').addEventListener('click', () => {
  const proximo = EST.DESAFIOS[EST.DESAFIOS.indexOf(desafio) + 1];
  if (proximo) entrarDesafio(proximo.id);
});
$('btLiberar').addEventListener('click', () => {
  salvo.desafiosLivres = true;
  salvar();
  montarSeletorDesafio();
});
$('btZerar').addEventListener('click', () => {
  if (!window.confirm('Apagar o progresso dos desafios guardado neste navegador?')) return;
  salvo.desafios = {};
  salvo.desafiosLivres = false;
  salvar();
  if (desafio && !liberado(EST.DESAFIOS.indexOf(desafio))) sairDesafio();
  else { montarSeletorDesafio(); mostrarDesafio(); }
});

$('pista').innerHTML = [...EST.PISTAS, {id: MINHA, nome: 'Minha pista'}, ...EST.OBR.ARENAS,
                        {id: MINHA_OBR, nome: 'Minha arena OBR (ladrilhos)'}]
  .map(p => `<option value="${p.id}">${escapar(p.nome)}</option>`).join('') +
  '<option value="desafio" hidden>Pista do desafio</option>';
$('pista').value = pista.id;
$('pista').addEventListener('change', ev => { if (!desafio) trocarPista(ev.target.value); });
$('btExecutar').addEventListener('click', executarOuPausar);
$('btProxima').addEventListener('click', proximaLinha);
$('fonte').addEventListener('click', ev => {
  const el = ev.target.closest && ev.target.closest('.nl.cod');
  if (el) alternarParada(+el.parentElement.dataset.n);
});
$('fonte').addEventListener('keydown', ev => {
  const el = ev.target.closest && ev.target.closest('.nl.cod');
  if (el && (ev.key === 'Enter' || ev.key === ' ')) { alternarParada(+el.parentElement.dataset.n); ev.preventDefault(); }
});
$('btReiniciar').addEventListener('click', reiniciar);
$('velocidade').addEventListener('change', ev => { velocidade = parseFloat(ev.target.value) || 1; salvo.velocidade = velocidade; salvar(); });
$('btLimparRastro').addEventListener('click', () => { robo.rastro = [[robo.x, robo.y]]; });
$('rastro').addEventListener('change', ev => { salvo.rastro = ev.target.checked; salvar(); });
$('somLigado').addEventListener('change', ev => { salvo.som = ev.target.checked; salvar(); if (!ev.target.checked) silenciar(); });
$('btLargada').addEventListener('click', () => {
  delete salvo.largadas[pista.id];
  delete salvo.caixas[pista.id];
  salvar();
  trocarPista(pista.id);
});

$('lupa').addEventListener('change', ev => { salvo.lupa = ev.target.checked; salvar(); });

// ruído nos sensores: a luz refletida varia alguns pontos a cada leitura, como no robô de verdade
function aplicarRuido() {
  robo.ruido = $('ruido').checked ? EST.RUIDO : 0;
  robo.cache.clear();
  $('etiquetaRuido').hidden = !robo.ruido;
}
$('ruido').addEventListener('change', ev => { salvo.ruido = ev.target.checked; salvar(); aplicarRuido(); atualizarPainel(); });

// sensor de toque: aparece se o programa lê um
/* Um botão da página aperta enquanto segura. Um clique rápido fica apertado pelo menos APERTO_MIN segundos
   da simulação, para o programa (que lê o botão a cada volta do laço) chegar a ver. */
const APERTO_MIN = 0.15;
let soltarPendente = null;          // {soltar, t}: solta quando o tempo simulado chegar em t
function segurando(el, apertarFn, soltarFn) {
  let desde = 0;
  const aperta = () => { soltarPendente = null; desde = tSim; apertarFn(); };
  const solta = () => {
    if (estado === 'rodando' && tSim - desde < APERTO_MIN) soltarPendente = {soltar: soltarFn, t: desde + APERTO_MIN};
    else soltarFn();
  };
  el.addEventListener('pointerdown', ev => { aperta(); el.setPointerCapture(ev.pointerId); });
  el.addEventListener('pointerup', solta);
  el.addEventListener('pointercancel', solta);
  el.addEventListener('keydown', ev => { if ((ev.key === ' ' || ev.key === 'Enter') && !ev.repeat) { aperta(); ev.preventDefault(); } });
  el.addEventListener('keyup', ev => { if (ev.key === ' ' || ev.key === 'Enter') solta(); });
}

const btToque = $('btToque');
const apertar = v => { robo.toque = v; btToque.classList.toggle('apertado', v); };
segurando(btToque, () => apertar(true), () => apertar(false));

// botões da controladora: aparecem se o programa lê algum
function apertarBotao(n) {
  robo.botao = n;
  for (const b of document.querySelectorAll('#botoes button')) b.classList.toggle('apertado', +b.dataset.botao === n);
}
for (const b of document.querySelectorAll('#botoes button')) {
  segurando(b, () => apertarBotao(+b.dataset.botao), () => apertarBotao(0));
}

document.addEventListener('keydown', ev => {
  const tag = ev.target.tagName;
  const digitando = tag === 'TEXTAREA' || (tag === 'INPUT' && !['radio', 'checkbox'].includes(ev.target.type));
  if (editando && (ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.key === 'z' || ev.key === 'Z') && !digitando) {
    desfazer();
    ev.preventDefault();
    return;
  }
  if (ev.key === 'Escape' && arraste && arraste.tipo === 'linha') { arraste = null; return; }   // desiste da linha
  if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'SUMMARY') return;
  if (ev.key === ' ') { executarOuPausar(); ev.preventDefault(); }
  else if (ev.key === 'r' || ev.key === 'R') reiniciar();
  else if (ev.key === 'n' || ev.key === 'N') proximaLinha();
});

// ---------------------------------------------------------------- início

if (typeof salvo.velocidade === 'number' && [...$('velocidade').options].some(o => +o.value === salvo.velocidade)) {
  velocidade = salvo.velocidade;
  $('velocidade').value = String(velocidade);
}
if (typeof salvo.rastro === 'boolean') $('rastro').checked = salvo.rastro;
if (typeof salvo.som === 'boolean') $('somLigado').checked = salvo.som;
if (typeof salvo.lupa === 'boolean') $('lupa').checked = salvo.lupa;
if (typeof salvo.ruido === 'boolean') $('ruido').checked = salvo.ruido;
aplicarRuido();

if (Array.isArray(globalThis.PROGRAMAS)) $('notaDemo').hidden = false;    // demonstração da página do projeto
if (PROGRAMAS.length > 1) {
  $('exemplo').innerHTML = PROGRAMAS.map((p, i) => `<option value="${i}">${escapar(rotulo(p))}</option>`).join('');
  $('exemplo').value = String(exemplo);
  $('exemplo').addEventListener('change', ev => trocarExemplo(+ev.target.value));
  window.addEventListener('hashchange', () => {        // link para outro exemplo na mesma página
    const i = exemploDoEndereco();
    if (i >= 0 && i !== exemplo) { $('exemplo').value = String(i); trocarExemplo(i); }
  });
  $('campoExemplo').hidden = false;
}
lerCores();
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { lerCores(); desenharLcd(true); });
mostrarPrograma();
montarMedidas();
new ResizeObserver(dimensionar).observe($('quadro'));
window.addEventListener('resize', dimensionar);
montarSeletorDesafio();
const ultimoDesafio = EST.DESAFIOS.findIndex(d => d.id === salvo.desafio);
if (ultimoDesafio >= 0 && liberado(ultimoDesafio)) entrarDesafio(salvo.desafio);      // abre no desafio da última vez
else trocarPista(pista.id);

let anterior = null, ultimoPainel = 0;
function quadro(agora) {
  const real = anterior === null ? 0 : Math.min(0.1, (agora - anterior) / 1000);
  anterior = agora;
  if (estado === 'rodando' || estado === 'terminou' || estado === 'erro') {
    acumulado += real * velocidade;
    let n = 0;
    while (acumulado >= DT && n < MAX_PASSOS && estado !== 'pausado') { passo(); acumulado -= DT; n++; }
    if (n >= MAX_PASSOS || estado === 'pausado') acumulado = 0;
    desenharLcd();
  }
  desenhar();
  if (agora - ultimoPainel > 100) { ultimoPainel = agora; atualizarPainel(); }
  requestAnimationFrame(quadro);
}
requestAnimationFrame(quadro);
})();
