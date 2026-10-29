'use strict';
/* O robô simulado: motores, movimento visto de cima, sensores, tela, som e luz.
   É ele quem atende as instruções de dispositivo da VM (30 ler, 31 escrever, 33 interno).
   Medidas em centímetros e graus; x para a direita, y para baixo, ângulo no sentido horário. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

/* Medidas padrão: as do robô do laboratório. Roda e entre rodas são os padrões medidos do robo.py.
   As posições dos sensores são estimadas: S1 e S2 um de cada lado da linha, S3 no meio e mais à
   frente, ultrassom na frente. Ajuste em "Medidas do robô" na página. */
const ROBO_PADRAO = {
  roda_cm: 4.3,
  entre_rodas_cm: 12,
  rpm_max: 170,                       // rotação da roda com potência 100 (170 rpm = 1020 graus/s)
  motor_esquerdo: 'B',
  motor_direito: 'C',
  invertido: false,                   // true: potência positiva anda de ré (use com configurar(invertido=True))
  corpo: {frente: 13, tras: 7, largura: 15},
  portas: {
    1: {tipo: 'cor', frente: 7, esquerda: 1.6, preto: 18},
    2: {tipo: 'cor', frente: 7, esquerda: -1.6, preto: 21},
    3: {tipo: 'cor', frente: 10, esquerda: 0, preto: 10},
    4: {tipo: 'ultrassom', frente: 12, esquerda: 0, preto: 10},     // preto: se virar sensor de cor
  },
};

const TAU_ACELERA = 0.05;     // s: o motor chega na velocidade pedida
const TAU_DESLIZA = 0.12;     // s: sem freio, a roda perde velocidade aos poucos
const RAIO_MANCHA = 0.5;      // cm: raio da área do chão que o sensor de cor enxerga
const ULTRASSOM_MAX = 255;    // cm: leitura quando não há nada na frente
const CONE_ULTRASSOM = [-10, -5, 0, 5, 10];     // graus
const RUIDO = 6;              // "Sensores com ruído": a luz refletida varia até 6 pontos para cima ou para baixo

// pontos da mancha do sensor de cor (centro, 6 a meio raio, 12 na borda): pesa mais o centro, como o sensor real
const MANCHA = [[0, 0]];
for (let i = 0; i < 6; i++) MANCHA.push([0.5 * RAIO_MANCHA * Math.cos(i * Math.PI / 3), 0.5 * RAIO_MANCHA * Math.sin(i * Math.PI / 3)]);
for (let i = 0; i < 12; i++) MANCHA.push([RAIO_MANCHA * Math.cos(i * Math.PI / 6), RAIO_MANCHA * Math.sin(i * Math.PI / 6)]);

// quanto a cor do chão reflete no modo luz refletida: a luminosidade, ou o 4º número da cor (o verde reflete pouco)
const reflexo = c => c.length > 3 ? c[3] : 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];

// número de -1 a 1, mais vezes perto de 0 (soma de dois sorteios)
const sorteio = () => Math.random() + Math.random() - 1;

/* botões da controladora (leitura interna 0x32, tipo 3): o número de cada um, 0 = nenhum apertado.
   Como no robo.py (BOTAO_CIMA = 4, BOTAO_BAIXO = 5) e no EV3; ainda não conferidos no robô. */
const BOTOES = {1: 'esquerda', 2: 'centro', 3: 'direita', 4: 'cima', 5: 'baixo'};

const NOMES_COR = ['nenhuma', 'PRETO', 'AZUL', 'VERDE', 'AMARELO', 'VERMELHO', 'BRANCO', 'MARROM'];
const LETRAS = 'ABCD';

/* número da cor (como no robô: 1 preto ... 6 branco, 0 = não reconheceu) a partir da cor média vista */
function classificaCor(r, g, b) {
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  if (lum < 0.25) return 1;
  if (max - min < 0.25) return lum > 0.75 ? 6 : 0;     // cinza: borda da linha, nem preto nem branco
  let h;
  if (max === r) h = ((g - b) / (max - min) + 6) % 6;
  else if (max === g) h = (b - r) / (max - min) + 2;
  else h = (r - g) / (max - min) + 4;
  h *= 60;
  if (h < 20 || h >= 330) return 5;
  if (h < 45) return lum < 0.45 ? 7 : 5;
  if (h < 75) return 4;
  if (h < 170) return 3;
  if (h < 270) return 2;
  return 5;
}

function potencia(p) {
  return Number.isFinite(p) ? Math.max(-100, Math.min(100, p)) : 0;
}

// "mover com direção": direção de -100 a 100 vira potências esquerda/direita (como no EV3)
function comDirecao(direcao, p) {
  const d = Math.max(-100, Math.min(100, Number.isFinite(direcao) ? direcao : 0));
  return d >= 0 ? [p, p * (1 - d / 50)] : [p * (1 + d / 50), p];
}

class Motor {
  constructor(nome) {
    this.nome = nome;
    this.reiniciar();
  }

  reiniciar() {
    this.ang = 0;              // graus acumulados (o "encoder")
    this.vel = 0;              // graus/s
    this.alvoVel = 0;
    this.pot = 0;              // potência pedida, para o painel
    this.modo = 'livre';       // livre | freado | ligado | curso | tempo
    this.cmd = 0;
    this.feito = true;
  }

  novo(modo, pot) {
    this.cmd++;
    this.modo = modo;
    this.pot = pot;
    this.feito = modo === 'livre' || modo === 'freado' || modo === 'ligado';
    return this.cmd;
  }

  parar(freio) {
    this.novo(freio ? 'freado' : 'livre', 0);
    if (freio) this.vel = 0;
  }

  ligar(p, k) {
    this.novo('ligado', p);
    this.alvoVel = p * k;
  }

  curso(p, graus, freio, k) {
    if (!p || !graus || !Number.isFinite(graus)) { this.parar(freio); return; }
    this.novo('curso', p);
    this.sentido = Math.sign(p) * Math.sign(graus);
    this.alvoVel = Math.abs(p) * k * this.sentido;
    this.alvoAng = this.ang + Math.abs(graus) * this.sentido;
    this.freio = freio;
  }

  tempo(p, segundos, freio, k, t) {
    if (!(segundos > 0)) { this.parar(freio); return; }
    this.novo('tempo', p);
    this.alvoVel = p * k;
    this.fimT = t + segundos;
    this.freio = freio;
  }

  terminar() {
    this.modo = this.freio ? 'freado' : 'livre';
    this.pot = 0;
    this.feito = true;
    if (this.freio) this.vel = 0;
  }

  /* avança dt segundos; devolve quantos graus a roda girou */
  atualizar(dt, t) {
    if (this.modo === 'ligado' || this.modo === 'curso' || this.modo === 'tempo') {
      this.vel += (this.alvoVel - this.vel) * Math.min(1, dt / TAU_ACELERA);
    } else if (this.modo === 'freado') {
      this.vel = 0;
    } else {
      this.vel *= Math.exp(-dt / TAU_DESLIZA);
      if (Math.abs(this.vel) < 0.5) this.vel = 0;
    }
    const antes = this.ang;
    this.ang += this.vel * dt;
    if (this.modo === 'curso' && (this.ang - this.alvoAng) * this.sentido >= 0) {
      if (this.freio) this.ang = this.alvoAng;
      this.terminar();
    } else if (this.modo === 'tempo' && t >= this.fimT) {
      this.terminar();
    }
    return this.ang - antes;
  }
}

class Robo {
  constructor(config, pista) {
    this.config = config;
    this.pista = pista;
    this.motores = {};
    for (const l of LETRAS) this.motores[l] = new Motor(l);
    this.aoEvento = null;      // a página recebe os sons por aqui
    this.x = 0; this.y = 0; this.ang = 0;
    this.toque = false;
    this.botao = 0;            // botão da controladora apertado na página (0 = nenhum)
    this.ruido = 0;            // pontos de variação aleatória na luz refletida (0 = sensores perfeitos)
    this.reiniciar();
  }

  reiniciar() {
    for (const m of Object.values(this.motores)) m.reiniciar();
    this.tela = [];            // [{texto, x, y}] desde a última limpeza
    this.telaVersao = 0;
    this.luz = null;           // null apagada, 0 azul, 1 roxo, 2 vermelho
    this.lidas = {};           // porta -> instante da última leitura pelo programa
    this.avisos = new Set();
    this.cache = new Map();
    this.passoN = 0;
    this.rastro = [];
    this.batidas = 0;          // passos em que o robô encostou numa parede ou caixa
    this.zeroMotor = {};       // letra -> graus do motor no último "zerar"
    this.giro = 0;             // radianos que o robô girou desde o começo ou o último "zerar" (giroscópio perfeito)
    this.giroVel = 0;          // graus/s no último passo
    this.cronos = {};          // número do cronômetro -> instante do último "zerar" (sem zerar, conta desde 0)
  }

  colocar(x, y, angGraus) {
    this.x = x; this.y = y; this.ang = angGraus * Math.PI / 180;
    this.cache.clear();
  }

  get angGraus() {
    const a = this.ang * 180 / Math.PI;
    return ((a % 360) + 360) % 360;
  }

  // graus/s por ponto de potência
  get k() { return this.config.rpm_max * 6 / 100; }

  avisar(texto) { this.avisos.add(texto); }

  evento(e) { if (this.aoEvento) this.aoEvento(e); }

  // ---------------------------------------------------------------- geometria

  /* ponto do robô (frente, esquerda) em coordenadas da pista */
  ponto(frente, esquerda) {
    const c = Math.cos(this.ang), s = Math.sin(this.ang);
    return [this.x + frente * c + esquerda * s, this.y + frente * s - esquerda * c];
  }

  // ---------------------------------------------------------------- sensores

  sensorCor(porta) {
    const cfg = this.config.portas[porta];
    if (!cfg || cfg.tipo !== 'cor') return null;
    const chave = 'c' + porta;
    const guardado = this.cache.get(chave);
    if (guardado && guardado.passo === this.passoN) return guardado;
    const [px, py] = this.ponto(cfg.frente, cfg.esquerda);
    const preto = Number.isFinite(cfg.preto) ? cfg.preto : 10;
    let r = 0, g = 0, b = 0, luz = 0;
    for (const [ox, oy] of MANCHA) {
      const c = EST.corDoChao(this.pista, px + ox, py + oy);
      r += c[0]; g += c[1]; b += c[2];
      if (c !== EST.FORA) luz += preto + (100 - preto) * reflexo(c);
    }
    const n = MANCHA.length;
    let lm = luz / n, rm = r / n, gm = g / n, bm = b / n;
    if (this.ruido > 0) {
      // sensor de verdade: a luz varia alguns pontos a cada leitura e, na borda da linha, a cor vista pode mudar
      const z = sorteio(), k = this.ruido / 100;
      lm += this.ruido * z;
      rm += k * (z + sorteio() / 2); gm += k * (z + sorteio() / 2); bm += k * (z + sorteio() / 2);
    }
    const leitura = {passo: this.passoN, x: px, y: py, luz: Math.round(Math.max(0, Math.min(100, lm))),
                     cor: classificaCor(rm, gm, bm)};
    this.cache.set(chave, leitura);
    return leitura;
  }

  sensorUltrassom(porta) {
    const cfg = this.config.portas[porta];
    if (!cfg || cfg.tipo !== 'ultrassom') return null;
    const chave = 'u' + porta;
    const guardado = this.cache.get(chave);
    if (guardado && guardado.passo === this.passoN) return guardado;
    const [px, py] = this.ponto(cfg.frente, cfg.esquerda);
    let d = Infinity;
    for (const a of CONE_ULTRASSOM) {
      const ang = this.ang + a * Math.PI / 180;
      d = Math.min(d, EST.raio(this.pista, px, py, Math.cos(ang), Math.sin(ang)));
    }
    const cm = d > ULTRASSOM_MAX ? ULTRASSOM_MAX : Math.round(d * 10) / 10;
    const leitura = {passo: this.passoN, x: px, y: py, cm};
    this.cache.set(chave, leitura);
    return leitura;
  }

  // ---------------------------------------------------------------- instruções da VM

  ler(porta, tipo, modo, t) {
    this.lidas[porta] = t;
    if (tipo === 0x01) {
      const l = this.sensorCor(porta);
      if (!l) {
        this.avisar(`O programa lê um sensor de cor na porta ${porta}, mas no robô simulado ela não tem sensor de cor (veja "Medidas do robô").`);
        return modo === 1 ? {byte: 0} : {float: 0};
      }
      if (modo === 1) return {byte: l.cor};
      if (modo === 2) return {float: l.luz};
      return {float: 5};                                   // luz ambiente
    }
    if (tipo === 0x07) return {byte: this.toque ? 1 : 0};
    if (tipo === 0x04) {                                   // rotação do motor: 1 graus, 2 rotações, 3 potência, 4 zerar
      const m = porta >= 5 && porta <= 8 ? this.motores[LETRAS[porta - 5]] : null;
      if (!m) { this.avisar(`Rotação do motor numa porta que não é de motor (${porta}).`); return {float: 0}; }
      if (modo === 4) { this.zeroMotor[m.nome] = m.ang; return {byte: 0}; }
      const graus = m.ang - (this.zeroMotor[m.nome] || 0);
      return {float: modo === 1 ? Math.round(graus) : modo === 2 ? graus / 360 : m.pot};
    }
    if (tipo === 0x02) {                                   // giroscópio (em qualquer porta): 1 ângulo, 2 graus/s, 4 zerar
      if (modo === 4) { this.giro = 0; return {byte: 0}; }
      return {float: modo === 1 ? Math.round(this.giro * 180 / Math.PI) : Math.round(this.giroVel)};
    }
    if (tipo === 0x08) {
      const u = this.sensorUltrassom(porta);
      if (!u) {
        this.avisar(`O programa lê um ultrassom na porta ${porta}, mas no robô simulado ela não tem ultrassom (veja "Medidas do robô").`);
        return {float: ULTRASSOM_MAX};
      }
      return {float: u.cm};
    }
    this.avisar(`Sensor do tipo 0x${tipo.toString(16)} (porta ${porta}) ainda não simulado: a leitura dá 0.`);
    return {float: 0};
  }

  /* leitura interna: tipo 3 = botões da controladora */
  lerInterno(tipo, modo) {
    if (tipo === 3) return {byte: this.botao};
    this.avisar(`Leitura interna ${tipo} (modo ${modo}) ainda não simulada: a leitura dá 0.`);
    return {byte: 0};
  }

  /* cronômetros 1..8: segundos desde o último zerar (ou desde o começo do programa) */
  cronometro(n, t) { return t - (this.cronos[n] || 0); }
  zerarCronometro(n, t) { this.cronos[n] = t; }

  portasDoByte(b) {
    if (b >= 5 && b <= 8) return [LETRAS[b - 5]];
    return [LETRAS[(b >> 4) & 3], LETRAS[(b >> 6) & 3]];
  }

  /* Escreve num motor. Devolve uma função pronto(t) quando o comando tem fim (graus, rotações, segundos). */
  escrever(porta, tipo, modo, d, t) {
    const ms = this.portasDoByte(porta).map(l => this.motores[l]);
    const k = this.k;
    let pots, n;
    if (tipo === 0x83 || tipo === 0x82) {                  // mover tanque / mover com direção
      if (ms.length !== 2) { this.avisar(`Mover com dois motores numa porta de um motor só (${porta}).`); return null; }
      n = 8;
      pots = tipo === 0x83 ? [potencia(d.f(0)), potencia(d.f(4))] : comDirecao(d.f(0), potencia(d.f(4)));
    } else if (tipo === 0x81 || tipo === 0x80) {           // motor grande / médio
      n = 4;
      pots = [potencia(d.f(0))];
    } else {
      this.avisar(`Dispositivo 0x${tipo.toString(16)} ainda não simulado.`);
      return null;
    }
    const usados = ms.slice(0, pots.length);
    if (modo === 1) {                                       // desligar
      const freio = d.b(0) !== 0;
      for (const m of usados) m.parar(freio);
      return null;
    }
    if (modo === 2) {                                       // ligar
      usados.forEach((m, i) => m.ligar(pots[i], k));
      return null;
    }
    if (modo < 3 || modo > 5) { this.avisar(`Modo ${modo} de motor ainda não simulado.`); return null; }
    const valor = d.f(n), freio = d.b(n + 4) !== 0;
    if (modo === 3) {
      usados.forEach((m, i) => m.tempo(pots[i], valor, freio, k, t));
    } else {
      // graus (4) ou rotações (5): o motor mais rápido anda o valor pedido e o outro, na proporção
      const graus = modo === 5 ? valor * 360 : valor;
      const maior = Math.max(...pots.map(Math.abs));
      usados.forEach((m, i) => m.curso(pots[i], maior ? graus * Math.abs(pots[i]) / maior : 0, freio, k));
    }
    const ids = usados.map(m => [m, m.cmd]);
    return () => ids.every(([m, id]) => m.cmd !== id || m.feito);
  }

  /* Tela (tipo 1), som (2) e luz (4) */
  interno(tipo, modo, d, t) {
    if (tipo === 1 && modo === 1) {
      // 10 bytes: endereço do texto, reservado, limpar, x, y, cor, fonte
      if (d.b(5)) this.tela = [];
      const item = {texto: d.texto(0), x: d.b(6), y: d.b(7)};
      // o texto novo cobre o que estava no mesmo lugar: num laço com painel() a lista não cresce sem fim
      this.tela = this.tela.filter(o => o.x !== item.x || o.y !== item.y);
      this.tela.push(item);
      if (this.tela.length > 100) this.tela.splice(0, this.tela.length - 100);
      this.telaVersao++;
      return null;
    }
    if (tipo === 2 && modo === 1) {
      // 13 bytes: frequência, duração, volume (floats) e se espera o som terminar
      const freq = d.f(0), dur = d.f(4), vol = d.f(8), espera = d.b(12) !== 0;
      if (dur > 0) this.evento({tipo: 'som', freq, dur, vol, t});
      const fim = t + Math.max(0, dur || 0);
      return espera ? tt => tt >= fim : null;
    }
    if (tipo === 4) {
      this.luz = modo === 0 ? null : d.b(0) % 3;
      return null;
    }
    this.avisar(`Dispositivo interno ${tipo} modo ${modo} ainda não simulado.`);
    return null;
  }

  /* fim do programa: os motores ficam soltos, como no robô quando o programa acaba */
  fim() {
    for (const m of Object.values(this.motores)) {
      if (m.modo === 'ligado' || m.modo === 'curso' || m.modo === 'tempo') m.parar(false);
    }
  }

  // ---------------------------------------------------------------- movimento

  avancar(dt, t, segurando = false) {
    const giro = {};
    for (const m of Object.values(this.motores)) giro[m.nome] = m.atualizar(dt, t);
    this.passoN++;
    this.giroVel = 0;
    if (segurando) return;
    const r = this.config.roda_cm / 2, W = this.config.entre_rodas_cm;
    const e = this.config.motor_esquerdo, dd = this.config.motor_direito;
    const k = (this.config.invertido ? -1 : 1) * Math.PI / 180 * r;
    const sl = (giro[e] || 0) * k, sr = (giro[dd] || 0) * k;
    if (!sl && !sr) return;
    const ds = (sl + sr) / 2, dth = (sl - sr) / W;
    this.giro += dth;
    if (dt > 0) this.giroVel = dth / dt * 180 / Math.PI;
    const am = this.ang + dth / 2;
    this.x += ds * Math.cos(am);
    this.y += ds * Math.sin(am);
    this.ang += dth;
    this.colisao();
    const ult = this.rastro[this.rastro.length - 1];
    if (!ult || Math.hypot(this.x - ult[0], this.y - ult[1]) > 0.4) {
      this.rastro.push([this.x, this.y]);
      if (this.rastro.length > 60000) this.rastro.splice(0, 10000);
    }
  }

  /* o corpo do robô são círculos ao longo do comprimento; se entrar numa parede ou caixa, é empurrado para fora */
  colisao() {
    const segs = EST.solidos(this.pista);
    const {frente, tras, largura} = this.config.corpo;
    const R = largura / 2;
    const L = frente + tras;
    const n = L > 2 * R ? Math.ceil((L - 2 * R) / R) + 1 : 1;
    let bateu = false;
    for (let volta = 0; volta < 3 && segs.length; volta++) {
      for (let i = 0; i < n; i++) {
        const f = n === 1 ? (frente - tras) / 2 : -tras + R + (L - 2 * R) * i / (n - 1);
        const cx = this.x + f * Math.cos(this.ang), cy = this.y + f * Math.sin(this.ang);
        for (const [x1, y1, x2, y2] of segs) {
          const dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy;
          let u = L2 ? ((cx - x1) * dx + (cy - y1) * dy) / L2 : 0;
          u = u < 0 ? 0 : u > 1 ? 1 : u;
          const qx = x1 + u * dx, qy = y1 + u * dy;
          const dist = Math.hypot(cx - qx, cy - qy);
          if (dist < R && dist > 1e-6) {
            this.x += (cx - qx) / dist * (R - dist);
            this.y += (cy - qy) / dist * (R - dist);
            bateu = true;
          }
        }
      }
    }
    if (bateu) this.batidas++;
    // não deixa o robô sumir da mesa
    const m = 15;
    this.x = Math.max(-m, Math.min(this.pista.largura + m, this.x));
    this.y = Math.max(-m, Math.min(this.pista.altura + m, this.y));
  }
}

EST.ROBO_PADRAO = ROBO_PADRAO;
EST.RUIDO = RUIDO;
EST.BOTOES = BOTOES;
EST.Robo = Robo;
EST.NOMES_COR = NOMES_COR;
EST.classificaCor = classificaCor;
})();
