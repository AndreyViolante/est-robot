'use strict';
/* Gráfico dos sensores no tempo: guarda a leitura de cada sensor enquanto o robô anda e prepara os pontos para
   desenhar. Sem página: o desenho fica no app.js, e o ferramentas/simulacao.js usa este arquivo nos testes. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const INTERVALO = 0.02;          // s simulados entre duas anotações (50 por segundo)
const MAXIMO = 30000;            // anotações guardadas, no máximo (10 minutos simulados)

/* As leituras ao longo do tempo: {t, v: {porta: valor}}, em ordem de t. */
class Registro {
  constructor(intervalo = INTERVALO, maximo = MAXIMO) {
    this.intervalo = intervalo;
    this.maximo = maximo;
    this.limpar();
  }

  limpar() {
    this.amostras = [];
    this.versao = 0;               // muda a cada anotação: a página só redesenha quando mudou
  }

  /* guarda as leituras do instante t (s), se já passou o intervalo desde a última */
  anotar(t, valores) {
    const ult = this.amostras[this.amostras.length - 1];
    if (ult && t < ult.t) this.limpar();                          // o tempo voltou: simulação recomeçou
    else if (ult && t - ult.t < this.intervalo - 1e-9) return false;
    this.amostras.push({t, v: valores});
    if (this.amostras.length > this.maximo) this.amostras.splice(0, Math.ceil(this.maximo / 10));
    this.versao++;
    return true;
  }

  get fim() {
    const ult = this.amostras[this.amostras.length - 1];
    return ult ? ult.t : 0;
  }

  /* índice da primeira anotação com tempo >= t */
  desde(t) {
    let lo = 0, hi = this.amostras.length;
    while (lo < hi) {
      const m = (lo + hi) >> 1;
      if (this.amostras[m].t < t) lo = m + 1; else hi = m;
    }
    return lo;
  }

  /* índice da anotação mais perto de t (-1 sem anotações) */
  perto(t) {
    const n = this.amostras.length;
    if (!n) return -1;
    const i = this.desde(t);
    if (i >= n) return n - 1;
    if (i > 0 && t - this.amostras[i - 1].t < this.amostras[i].t - t) return i - 1;
    return i;
  }

  /* o trecho de tempo mostrado: os últimos `segundos` (0 = tudo). Enquanto o robô anda há menos tempo que a
     janela, ela fica fixa a partir do 0 e a linha cresce da esquerda para a direita. */
  janela(segundos) {
    const fim = this.fim;
    if (!segundos) return {t0: 0, t1: Math.max(fim, 1)};
    return fim <= segundos ? {t0: 0, t1: segundos} : {t0: fim - segundos, t1: fim};
  }
}

/* Os pontos de uma porta entre t0 e t1 para uma área de `largura` pixels: com mais de uma leitura por coluna de
   pixel, cada coluna guarda a primeira, a menor, a maior e a última (o desenho não perde picos nem vales).
   Devolve [[t, valor], ...] em ordem de tempo; um null no meio = buraco (a porta não tinha leitura). */
function pontos(registro, porta, t0, t1, largura) {
  const lista = registro.amostras;
  const ini = Math.max(0, registro.desde(t0) - 1);
  const fim = Math.min(lista.length, registro.desde(t1) + 1);
  const saida = [];
  const colunas = Math.max(1, Math.round(largura));
  const porColuna = (t1 - t0) / colunas;
  let coluna = null;
  const fecha = () => {
    if (!coluna) return;
    const {primeiro, menor, maior, ultimo} = coluna;
    const meio = menor[0] <= maior[0] ? [menor, maior] : [maior, menor];
    for (const p of [primeiro, ...meio, ultimo]) {
      if (saida[saida.length - 1] !== p) saida.push(p);
    }
    coluna = null;
  };
  for (let i = ini; i < fim; i++) {
    const a = lista[i], v = a.v[porta];
    if (v === undefined || v === null || !Number.isFinite(v)) { fecha(); if (saida.length && saida[saida.length - 1] !== null) saida.push(null); continue; }
    const p = [a.t, v];
    const c = Math.floor((a.t - t0) / porColuna);
    if (!coluna || coluna.c !== c) {
      fecha();
      coluna = {c, primeiro: p, menor: p, maior: p, ultimo: p};
    } else {
      if (v < coluna.menor[1]) coluna.menor = p;
      if (v > coluna.maior[1]) coluna.maior = p;
      coluna.ultimo = p;
    }
  }
  fecha();
  while (saida.length && saida[saida.length - 1] === null) saida.pop();
  return saida;
}

/* um teto redondo para o eixo: 50, 100, 150... (pelo menos `minimo`) */
function teto(maior, passo = 50, minimo = 50) {
  return Math.max(minimo, Math.ceil((Number.isFinite(maior) ? maior : 0) / passo) * passo);
}

EST.Grafico = {Registro, pontos, teto, INTERVALO};
})();
