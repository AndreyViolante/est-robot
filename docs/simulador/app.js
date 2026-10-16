'use strict';
/* Página do simulador: desenha a pista e o robô, controla a execução e mostra a tela, a luz, o som,
   os sensores, os motores, as variáveis e a linha do programa que está rodando.
   O programa vem de programa.js, gerado por simular.py. Na demonstração da página do projeto
   (ferramentas/publicar_simulador.py) o programa.js traz vários exemplos e aparece o seletor. */
(function () {
const EST = globalThis.EST;
const DT = 0.002;                 // passo da simulação (s)
const MAX_PASSOS = 2500;          // passos por quadro de animação, no máximo
const MARGEM = 8;                 // cm de mesa em volta da pista
const LUPA = 3;                   // aumento da lupa
const CHAVE = 'est-simulador-v1';
const CORES_SENSOR = {1: '#2f8cff', 2: '#ff8a1f', 3: '#18b07a', 4: '#b27cff'};
const NOMES_LUZ = ['azul', 'roxo', 'vermelho'];

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
function salvar() {
  try { localStorage.setItem(CHAVE, JSON.stringify(salvo)); } catch (e) { /* navegador sem armazenamento */ }
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
let P = null, codigo = null, erroCarga = null, marcas = [], usaToque = false;

function lerPrograma(dados) {
  P = dados || null;
  codigo = null; erroCarga = null; marcas = []; usaToque = false;
  if (!P) return;
  try {
    codigo = new Uint8Array(P.bytes.match(/../g).map(h => parseInt(h, 16)));
    const lista = EST.instrucoes(codigo);
    marcas = lista.filter(i => i.op === 0x48).map(i => i.pc);
    usaToque = lista.some(i => i.op === 0x30 && codigo[i.pc + 6] === 0x07);
    if (!P.linhas || P.linhas.length !== marcas.length) marcas = [];     // sem linhas: só não destaca
  } catch (e) {
    erroCarga = e;
  }
}

// o endereço guarda o exemplo escolhido (simulador/#9_seguidor_pid), para recarregar e para links
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

let exemplo = Math.max(0, exemploDoEndereco());
lerPrograma(PROGRAMAS[exemplo]);

function linhaDoPc(pc) {
  let lo = 0, hi = marcas.length - 1, r = -1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (marcas[m] <= pc) { r = m; lo = m + 1; } else hi = m - 1;
  }
  return r >= 0 ? P.linhas[r] || 0 : 0;
}

// ---------------------------------------------------------------- pista, robô e VM

function montarPista(id) {
  const base = EST.PISTAS.find(p => p.id === id) || EST.PISTAS[0];
  const pista = EST.copiaPista(base);
  const caixas = salvo.caixas[pista.id];
  if (Array.isArray(caixas) && caixas.length === pista.caixas.length) {
    caixas.forEach((c, i) => { if (Number.isFinite(c.x) && Number.isFinite(c.y)) Object.assign(pista.caixas[i], {x: c.x, y: c.y}); });
  }
  return pista;
}

let pista = montarPista((P && P.pista) || salvo.pista);     // o exemplo da demonstração já diz a pista
const robo = new EST.Robo(mesclar(copia(EST.ROBO_PADRAO), salvo.robo), pista);
let vm = codigo && !erroCarga ? new EST.VM(codigo, robo) : null;

function largada() {
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
  estado = vm ? 'pronto' : 'sem';
  desenharLcd(true);
  atualizarTudo();
}

function executarOuPausar() {
  if (!vm) return;
  if (estado === 'rodando') {
    estado = 'pausado';
    if (audio) audio.suspend();
  } else {
    if (estado === 'terminou' || estado === 'erro') reiniciar();
    prepararAudio();
    estado = 'rodando';
  }
  atualizarTudo();
}

function passo() {
  if (estado === 'rodando') {
    vm.executar(tSim, DT);
    if (vm.erro) {
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
  robo.avancar(DT, tSim + DT, arraste !== null && arraste.tipo !== 'caixa');
  tSim += DT;
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
  if (pista.quadriculado) {
    for (let x = 10; x < W; x += 10) linha(c, x, 0, x, H, x % 50 ? '#e6eaf1' : '#cfd6e2', 0.2);
    for (let y = 10; y < H; y += 10) linha(c, 0, y, W, y, y % 50 ? '#e6eaf1' : '#cfd6e2', 0.2);
  }
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
  if (estado === 'rodando' && !(arraste && arraste.tipo === 'girar')) return;
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
}

// ---------------------------------------------------------------- arrastar o robô e as caixas

let arraste = null;          // {tipo: 'mover' | 'girar' | 'caixa', dx, dy, caixa}

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
  const cx = pista.caixas.find(c => x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h);
  return cx ? {tipo: 'caixa', caixa: cx} : null;
}

cena.addEventListener('pointerdown', ev => {
  const [x, y] = paraMundo(ev);
  const alvo = oQueTemAqui(x, y);
  if (!alvo) return;
  arraste = alvo;
  if (alvo.tipo === 'mover') { alvo.dx = robo.x - x; alvo.dy = robo.y - y; }
  if (alvo.tipo === 'caixa') { alvo.dx = alvo.caixa.x - x; alvo.dy = alvo.caixa.y - y; }
  cena.setPointerCapture(ev.pointerId);
  cena.className = 'arrastando';
  ev.preventDefault();
});

cena.addEventListener('pointermove', ev => {
  const [x, y] = paraMundo(ev);
  if (!arraste) {
    const alvo = oQueTemAqui(x, y);
    cena.className = alvo ? (alvo.tipo === 'girar' ? 'girar' : 'pega') : '';
    return;
  }
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
  }
  if (arraste.tipo !== 'caixa') {
    if (estado === 'pronto') robo.rastro = [[robo.x, robo.y]];
    else if (robo.rastro[robo.rastro.length - 1] !== null) robo.rastro.push(null);
  }
});

function soltar() {
  if (!arraste) return;
  if (arraste.tipo === 'caixa') {
    salvo.caixas[pista.id] = pista.caixas.map(c => ({x: c.x, y: c.y}));
  } else if (estado === 'pronto') {
    salvo.largadas[pista.id] = {x: robo.x, y: robo.y, ang: robo.angGraus};
  }
  salvar();
  arraste = null;
  cena.className = '';
  atualizarPainel();
}
cena.addEventListener('pointerup', soltar);
cena.addEventListener('pointercancel', soltar);

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
      <code>python simular.py exemplos/2_quadrado.py</code></p>`;
    return;
  }
  pre.innerHTML = P.fonte.replace(/\r/g, '').split('\n').map((t, i) => {
    let html = escapar(t);
    const k = t.indexOf('#');
    if (k >= 0 && !/['"]/.test(t.slice(0, k))) html = escapar(t.slice(0, k)) + `<span class="c">${escapar(t.slice(k))}</span>`;
    return `<span class="ln" data-n="${i + 1}">${html || ' '}</span>`;
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
  bt.textContent = {rodando: '⏸ Pausar', pausado: '▶ Continuar', terminou: '▶ Executar de novo', erro: '▶ Executar de novo'}[estado] || '▶ Executar';
  const el = $('estado');
  el.className = 'estado' + (estado === 'terminou' ? ' ok' : estado === 'erro' ? ' erro' : '');
  if (erroCarga) el.textContent = `Este programa não pode ser simulado: ${erroCarga.message} (byte ${erroCarga.pc})`;
  else if (estado === 'terminou') el.textContent = `O programa terminou em ${num(tFim)} s`;
  else if (estado === 'erro') el.textContent = `Erro na simulação: ${vm.erro.message} (byte ${vm.erro.pc})`;
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
  $('dica').textContent = `${pista.dica} Arraste o robô para mudar a largada; a bolinha azul na frente gira o robô.`;
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
  montarFonte();
  btToque.hidden = !usaToque;
  apertar(false);
  atualizarAvisos();
}

function trocarExemplo(i) {
  exemplo = i;
  lerPrograma(PROGRAMAS[i]);
  vm = codigo && !erroCarga ? new EST.VM(codigo, robo) : null;
  try { location.replace('#' + encodeURIComponent(chaveDe(P))); } catch (e) { /* fica sem guardar */ }
  if (P.pista && EST.PISTAS.some(p => p.id === P.pista)) trocarPista(P.pista);
  else reiniciar();
  mostrarPrograma();
}

$('pista').innerHTML = EST.PISTAS.map(p => `<option value="${p.id}">${escapar(p.nome)}</option>`).join('');
$('pista').value = pista.id;
$('pista').addEventListener('change', ev => trocarPista(ev.target.value));
$('btExecutar').addEventListener('click', executarOuPausar);
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

// sensor de toque: aparece se o programa lê um
const btToque = $('btToque');
const apertar = v => { robo.toque = v; btToque.classList.toggle('apertado', v); };
btToque.addEventListener('pointerdown', ev => { apertar(true); btToque.setPointerCapture(ev.pointerId); });
btToque.addEventListener('pointerup', () => apertar(false));
btToque.addEventListener('pointercancel', () => apertar(false));
btToque.addEventListener('keydown', ev => { if ((ev.key === ' ' || ev.key === 'Enter') && !ev.repeat) { apertar(true); ev.preventDefault(); } });
btToque.addEventListener('keyup', ev => { if (ev.key === ' ' || ev.key === 'Enter') apertar(false); });

document.addEventListener('keydown', ev => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const tag = ev.target.tagName;
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'SUMMARY') return;
  if (ev.key === ' ') { executarOuPausar(); ev.preventDefault(); }
  else if (ev.key === 'r' || ev.key === 'R') reiniciar();
});

// ---------------------------------------------------------------- início

if (typeof salvo.velocidade === 'number' && [...$('velocidade').options].some(o => +o.value === salvo.velocidade)) {
  velocidade = salvo.velocidade;
  $('velocidade').value = String(velocidade);
}
if (typeof salvo.rastro === 'boolean') $('rastro').checked = salvo.rastro;
if (typeof salvo.som === 'boolean') $('somLigado').checked = salvo.som;
if (typeof salvo.lupa === 'boolean') $('lupa').checked = salvo.lupa;

if (PROGRAMAS.length > 1) {
  $('exemplo').innerHTML = PROGRAMAS.map((p, i) => `<option value="${i}">${escapar(rotulo(p))}</option>`).join('');
  $('exemplo').value = String(exemplo);
  $('exemplo').addEventListener('change', ev => trocarExemplo(+ev.target.value));
  window.addEventListener('hashchange', () => {        // link para outro exemplo na mesma página
    const i = exemploDoEndereco();
    if (i >= 0 && i !== exemplo) { $('exemplo').value = String(i); trocarExemplo(i); }
  });
  $('campoExemplo').hidden = false;
  $('notaDemo').hidden = false;
}
lerCores();
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { lerCores(); desenharLcd(true); });
mostrarPrograma();
montarMedidas();
new ResizeObserver(dimensionar).observe($('quadro'));
window.addEventListener('resize', dimensionar);
trocarPista(pista.id);

let anterior = null, ultimoPainel = 0;
function quadro(agora) {
  const real = anterior === null ? 0 : Math.min(0.1, (agora - anterior) / 1000);
  anterior = agora;
  if (estado === 'rodando' || estado === 'terminou' || estado === 'erro') {
    acumulado += real * velocidade;
    let n = 0;
    while (acumulado >= DT && n < MAX_PASSOS) { passo(); acumulado -= DT; n++; }
    if (n >= MAX_PASSOS) acumulado = 0;
    desenharLcd();
  }
  desenhar();
  if (agora - ultimoPainel > 100) { ultimoPainel = agora; atualizarPainel(); }
  requestAnimationFrame(quadro);
}
requestAnimationFrame(quadro);
})();
