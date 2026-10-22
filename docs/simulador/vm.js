'use strict';
/* VM do robô EST em JavaScript: executa o bytecode gerado por estc.py, os mesmos bytes que vão
   para o robô. Formato das instruções: docs/formato.md e ferramentas/decodificar.py.

   Registradores: posições de uma memória de bytes. Nas instruções, endereços vão em 4 bytes
   big-endian e floats em 4 bytes little-endian. O código (pc) é outro espaço de endereços.
   Threads cooperativas: cada uma roda até bloquear (espera, motor, outra thread) ou até acabar a
   sua fatia; o corpo de cada loop e cada ramo de switch é uma thread. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const MEMORIA = 0x20000;          // registradores a partir de 0; textos a partir de 0xD7FF
const CUSTO = 20e-6;              // segundos por instrução (estimado; o robô real não foi cronometrado)
const FATIA = 50;                 // instruções seguidas de uma thread antes de passar a vez

// tamanho de cada instrução (o 2F tem tamanho variável: 6 + n)
const TAM = {0x01: 6, 0x02: 9, 0x03: 9, 0x04: 9, 0x07: 9, 0x08: 9, 0x09: 13, 0x0A: 13, 0x0B: 13, 0x0C: 13,
             0x0D: 10, 0x10: 14, 0x11: 13, 0x1A: 9, 0x1B: 9, 0x1D: 7, 0x1E: 11, 0x1F: 11, 0x20: 3, 0x21: 3,
             0x23: 5, 0x24: 1, 0x29: 14, 0x2B: 17, 0x2D: 7, 0x30: 13, 0x31: 13, 0x32: 8, 0x33: 8, 0x37: 14, 0x47: 9,
             0x48: 1};

class ErroVM extends Error {
  constructor(mensagem, pc) { super(mensagem); this.pc = pc; }
}

const hex = (n, d = 2) => '0x' + n.toString(16).toUpperCase().padStart(d, '0');

// comparação com o tipo contado a partir de 1: 1 =, 2 ≠, 3 >, 4 ≥, 5 <, 6 ≤
function compara(tipo, a, b, pc) {
  switch (tipo) {
    case 1: return a === b;
    case 2: return a !== b;
    case 3: return a > b;
    case 4: return a >= b;
    case 5: return a < b;
    case 6: return a <= b;
  }
  throw new ErroVM(`tipo de comparação ${tipo} desconhecido`, pc);
}

// número -> texto da tela (o formato exato do robô não foi conferido)
function numeroParaTexto(v) {
  if (!Number.isFinite(v)) return Number.isNaN(v) ? '---' : (v > 0 ? 'inf' : '-inf');
  const r = Math.round(v * 100) / 100;
  return String(Object.is(r, -0) ? 0 : r);
}

/* Lista as instruções do programa: [{pc, op, tam}]. Serve para achar os marcadores 48 e os
   sensores usados, e para recusar logo um código que a VM não conhece. */
function instrucoes(codigo) {
  const lista = [];
  let pc = 0;
  while (pc < codigo.length) {
    const op = codigo[pc];
    const tam = op === 0x2F ? 6 + (codigo[pc + 5] || 0) : TAM[op];
    if (!tam) throw new ErroVM(`instrução ${hex(op)} ainda não simulada`, pc);
    lista.push({pc, op, tam});
    pc += tam;
  }
  return lista;
}

class VM {
  /* codigo: Uint8Array com o bytecode.
     disp: o robô simulado, com
       ler(porta, tipo, modo, t)                 -> {byte: n} ou {float: x}
       escrever(porta, tipo, modo, dados, t)     -> null ou função pronto(t) (o motor terminou?)
       interno(tipo, modo, dados, t)             -> null ou função pronto(t) (tela, som, luz)
       lerInterno(tipo, modo, t)                 -> {byte: n} ou {float: x} (3 = botões da controladora)
       fim(t)                                    o programa principal terminou */
  constructor(codigo, disp) {
    this.codigo = codigo;
    this.disp = disp;
    this.mem = new Uint8Array(MEMORIA);
    this.dv = new DataView(this.mem.buffer);
    this.lista = instrucoes(codigo);
    this.aoBloco = null;          // aoBloco(pc, thread): chamado no início de cada bloco; true = pausar ali
    this.reiniciar();
  }

  reiniciar() {
    this.mem.fill(0);
    this.threads = new Map();
    this.terminou = false;
    this.parada = false;          // aoBloco pediu pausa: executar() parou logo depois do início do bloco
    this.erro = null;
    this.contador = 0;            // instruções executadas
    this.iniciar(0, 0);
  }

  // ---- memória
  end(pc) {
    const c = this.codigo;
    return ((c[pc] << 24) | (c[pc + 1] << 16) | (c[pc + 2] << 8) | c[pc + 3]) >>> 0;
  }
  confere(a, n, pc) {
    if (a + n > MEMORIA) throw new ErroVM(`endereço ${hex(a, 4)} fora da memória`, pc);
    return a;
  }
  lerByte(a) { return a < MEMORIA ? this.mem[a] : 0; }
  lerFloat(a) { return a + 4 <= MEMORIA ? this.dv.getFloat32(a, true) : NaN; }
  lerTexto(a) {
    let s = '';
    for (let i = a; i < MEMORIA && i < a + 64 && this.mem[i]; i++) s += String.fromCharCode(this.mem[i]);
    return s;
  }
  escreverTexto(a, s, pc) {
    this.confere(a, s.length + 1, pc);
    for (let i = 0; i < s.length; i++) this.mem[a + i] = s.charCodeAt(i) & 0xFF;
    this.mem[a + s.length] = 0;
  }

  // dados de um dispositivo a partir do registrador r: f(i) float no deslocamento i, b(i) byte
  dados(r, pc) {
    const vm = this;
    return {
      f: i => vm.dv.getFloat32(vm.confere(r + i, 4, pc), true),
      b: i => vm.mem[vm.confere(r + i, 1, pc)],
      texto: i => vm.lerTexto(vm.dv.getUint32(vm.confere(r + i, 4, pc), false)),
    };
  }

  // ---- threads
  iniciar(tid, pc) {
    const th = this.threads.get(tid) || {tid};
    th.pc = pc;
    th.ultimo = undefined;
    th.estado = 'rodando';
    th.espera = null;
    this.threads.set(tid, th);
  }

  ativa(tid) {
    const th = this.threads.get(tid);
    return th && th.estado !== 'fim';
  }

  acordou(th, t) {
    const e = th.espera;
    if (e.tipo === 'tempo') return t >= e.ate;
    if (e.tipo === 'thread') return !this.ativa(e.tid);
    return e.pronto(t);
  }

  bloqueia(th, espera) {
    th.estado = 'esperando';
    th.espera = espera;
  }

  /* Roda o programa no intervalo de tempo [t0, t0 + dt). Para antes do fim se aoBloco pedir (this.parada). */
  executar(t0, dt) {
    if (this.terminou || this.erro) return;
    this.parada = false;
    const orcamento = Math.max(1, Math.round(dt / CUSTO));
    let usados = 0;
    try {
      while (usados < orcamento && !this.terminou && !this.parada) {
        let rodou = false;
        for (const th of this.threads.values()) {
          if (th.estado === 'fim') continue;
          const t = t0 + usados * CUSTO;
          if (th.estado === 'esperando') {
            if (!this.acordou(th, t)) continue;
            th.estado = 'rodando';
            th.espera = null;
          }
          let n = 0;
          while (n < FATIA && usados < orcamento && th.estado === 'rodando' && !this.terminou && !this.parada) {
            this.passo(th, t0 + usados * CUSTO);
            n++;
            usados++;
          }
          if (n) rodou = true;
          if (this.terminou || this.parada) break;
        }
        if (!rodou) break;        // todas esperando: o resto do intervalo fica parado
      }
    } catch (e) {
      if (!(e instanceof ErroVM)) throw e;
      this.erro = e;
    }
    this.contador += usados;
  }

  passo(th, t) {
    const c = this.codigo, m = this.mem, dv = this.dv;
    const pc = th.pc;
    if (pc >= c.length) throw new ErroVM('o programa acabou sem a instrução de fim', pc);
    th.ultimo = pc;               // instrução em andamento (para mostrar a linha enquanto o motor anda)
    const op = c[pc];
    const A = i => this.end(pc + i);
    const F = a => dv.getFloat32(this.confere(a, 4, pc), true);
    const setF = (a, v) => dv.setFloat32(this.confere(a, 4, pc), v, true);
    const B = a => m[this.confere(a, 1, pc)];
    const setB = (a, v) => { m[this.confere(a, 1, pc)] = v; };

    switch (op) {
      case 0x48:                                                          // início de bloco
        if (this.aoBloco && this.aoBloco(pc, th)) this.parada = true;
        break;
      case 0x01: setB(A(1), c[pc + 5]); break;                            // r = byte
      case 0x02: m.set(c.subarray(pc + 5, pc + 9), this.confere(A(1), 4, pc)); break;   // r = 4 bytes
      case 0x03: setB(A(1), B(A(5))); break;                              // copia 1 byte
      case 0x04: { const d = this.confere(A(1), 4, pc), s = this.confere(A(5), 4, pc);
                   m.copyWithin(d, s, s + 4); break; }                    // copia 4 bytes
      case 0x07: { const v = F(A(5));                                     // byte = float
                   setB(A(1), Number.isFinite(v) ? Math.trunc(v) & 0xFF : 0); break; }
      case 0x08: setF(A(1), B(A(5))); break;                              // float = byte
      case 0x09: setF(A(1), F(A(5)) + F(A(9))); break;
      case 0x0A: setF(A(1), F(A(5)) - F(A(9))); break;
      case 0x0B: setF(A(1), F(A(5)) * F(A(9))); break;
      case 0x0C: setF(A(1), F(A(5)) / F(A(9))); break;
      case 0x0D:                                                          // conversão
        if (c[pc + 1] !== 0x15) throw new ErroVM(`conversão ${hex(c[pc + 1])} ainda não simulada`, pc);
        setB(A(2), B(A(6)));        // cor lida -> número da cor: o sensor simulado já entrega o número
        break;
      case 0x10: case 0x37:                                               // compara floats, tipo 1..6
        setB(A(2), compara(c[pc + 1], F(A(6)), F(A(10)), pc) ? 1 : 0); break;
      case 0x11: {                                                        // a cor está na máscara?
        const cor = B(A(5)), r = this.confere(A(9), 2, pc);
        const mascara = m[r] | (m[r + 1] << 8);
        setB(A(1), cor < 16 ? (mascara >> cor) & 1 : 0);
        break;
      }
      case 0x1A: if (B(A(5)) !== 0) { th.pc = A(1); return; } break;      // salta se r != 0
      case 0x1B: if (B(A(5)) === 0) { th.pc = A(1); return; } break;      // salta se r == 0
      case 0x1D: th.pc = pc + 7; this.iniciar(c[pc + 5], A(1)); return;   // inicia thread
      case 0x1E: case 0x1F: {                                             // inicia se verdadeiro / falso
        th.pc = pc + 11;
        const v = B(A(5)) !== 0;
        if (v === (op === 0x1E)) this.iniciar(c[pc + 9], A(1));
        return;
      }
      case 0x20: {                                                        // espera a thread terminar
        th.pc = pc + 3;
        const tid = c[pc + 1];
        if (this.ativa(tid) && tid !== th.tid) this.bloqueia(th, {tipo: 'thread', tid});
        return;
      }
      case 0x21: th.pc = pc + 3; th.estado = 'fim'; return;               // fim da thread
      case 0x23: {                                                        // espera segundos
        th.pc = pc + 5;
        const s = F(A(1));
        if (s > 0) this.bloqueia(th, {tipo: 'tempo', ate: t + s});
        return;
      }
      case 0x24:                                                          // fim do programa
        th.pc = pc + 1;
        this.terminou = true;
        for (const outra of this.threads.values()) outra.estado = 'fim';
        this.disp.fim(t);
        return;
      case 0x29:      // compara bytes (só o sensor de toque usa); tipo contado a partir de 0 como no 2B:
                      // com 29 01 (≠ 0) o "esperar toque" e o "se tocado" valem com o sensor apertado
        setB(A(2), compara(c[pc + 1] + 1, B(A(6)), B(A(10)), pc) ? 1 : 0); break;
      case 0x2B:                                                          // compara, tipo 0..5 num registrador
        setB(A(5), compara(B(A(1)) + 1, F(A(9)), F(A(13)), pc) ? 1 : 0); break;
      case 0x2D: { const r = this.confere(A(1), 2, pc); m[r] = c[pc + 5]; m[r + 1] = c[pc + 6]; break; }
      case 0x2F: {                                                        // grava texto
        const n = c[pc + 5];
        m.set(c.subarray(pc + 6, pc + 6 + n), this.confere(A(1), n, pc));
        th.pc = pc + 6 + n;
        return;
      }
      case 0x30: {                                                        // lê dispositivo
        const porta = B(A(2)), tipo = c[pc + 6], modo = c[pc + 7], tam = c[pc + 8], r = A(9);
        const v = this.disp.ler(porta, tipo, modo, t);
        this.confere(r, Math.max(tam, 1), pc);
        m.fill(0, r, r + tam);
        if ('float' in v) dv.setFloat32(r, v.float, true);
        else m[r] = v.byte & 0xFF;
        break;
      }
      case 0x31: {                                                        // escreve dispositivo (motores)
        const porta = B(A(2)), tipo = c[pc + 6], modo = c[pc + 7];
        th.pc = pc + 13;
        const pronto = this.disp.escrever(porta, tipo, modo, this.dados(A(9), pc), t);
        if (pronto && !pronto(t)) this.bloqueia(th, {tipo: 'dispositivo', pronto});
        return;
      }
      case 0x32: {                                                        // lê interno (3 = botões)
        const tipo = c[pc + 1], modo = c[pc + 2], tam = c[pc + 3], r = A(4);
        const v = this.disp.lerInterno(tipo, modo, t);
        this.confere(r, Math.max(tam, 1), pc);
        m.fill(0, r, r + tam);
        if ('float' in v) dv.setFloat32(r, v.float, true);
        else m[r] = v.byte & 0xFF;
        break;
      }
      case 0x33: {                                                        // tela, som, luz
        const tipo = c[pc + 1], modo = c[pc + 2];
        th.pc = pc + 8;
        const pronto = this.disp.interno(tipo, modo, this.dados(A(4), pc), t);
        if (pronto && !pronto(t)) this.bloqueia(th, {tipo: 'dispositivo', pronto});
        return;
      }
      case 0x47: this.escreverTexto(A(1), numeroParaTexto(F(A(5))), pc); break;   // número -> texto
      default:
        throw new ErroVM(`instrução ${hex(op)} ainda não simulada`, pc);
    }
    th.pc = pc + TAM[op];
  }

  /* Threads vivas, para mostrar a linha do programa: [{tid, pc, esperandoThread}]; pc é o da última
     instrução executada (a que ainda espera o motor, o tempo ou a outra thread) */
  ativas() {
    const lista = [];
    for (const th of this.threads.values()) {
      if (th.estado === 'fim') continue;
      lista.push({tid: th.tid, pc: th.ultimo ?? th.pc, esperandoThread: !!(th.espera && th.espera.tipo === 'thread')});
    }
    return lista;
  }
}

EST.VM = VM;
EST.ErroVM = ErroVM;
EST.instrucoes = instrucoes;
EST.numeroParaTexto = numeroParaTexto;
})();
