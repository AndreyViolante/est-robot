'use strict';
/* Trilha de desafios do simulador, do mais fácil ao mais difícil. Cada desafio tem pista, largada, objetivo
   e a verificação automática. A página chama verificar(prova, s) a cada passo da simulação, com
     prova: objeto do desafio em andamento (começa vazio a cada Reiniciar; prova.texto aparece na página)
     s: {t, x, y, frente: [x, y], parado (segundos sem se mexer), terminou, batidas, pista}
   e a resposta é null (continua), {ok: true} ou {ok: false, motivo}.
   Medidas em centímetros, como em mundo.js; x e y são o meio entre as rodas do robô. */
(function () {
const EST = (globalThis.EST = globalThis.EST || {});

const cm = v => (Math.round(v * 10) / 10).toLocaleString('pt-BR');
const dentro = (z, x, y) => x >= z.x && x <= z.x + z.w && y >= z.y && y <= z.y + z.h;

function tempo(d, s) {
  return s.t > d.limite ? {ok: false, motivo: `o tempo acabou (${d.limite} s)`} : null;
}

/* Passa pelos marcos na ordem. d.marcos é uma lista de sequências (o quadrado pode ser para a esquerda ou para
   a direita); vale a que andou mais. Devolve quantos marcos dessa sequência já foram. */
function passarMarcos(d, prova, s) {
  prova.marcos = prova.marcos || d.marcos.map(() => 0);
  d.marcos.forEach((seq, i) => {
    const alvo = seq[prova.marcos[i]];
    if (alvo && Math.hypot(s.x - alvo[0], s.y - alvo[1]) <= d.raio) prova.marcos[i]++;
  });
  prova.seq = prova.marcos.indexOf(Math.max(...prova.marcos));
  return prova.marcos[prova.seq];
}

// uma volta seguindo a linha: passar por todos os marcos sem se afastar da linha
function volta(prova, s) {
  const n = passarMarcos(this, prova, s), total = this.marcos[0].length;
  prova.texto = `Marcos: ${n} de ${total}`;
  if (this.semBater && s.batidas) return {ok: false, motivo: 'o robô bateu na caixa'};
  if (n === total) return {ok: true};
  if (EST.distLinha(s.pista, s.x, s.y) > this.longe) return {ok: false, motivo: 'o robô saiu da linha'};
  if (s.parado > 15) return {ok: false, motivo: 'o robô ficou 15 s parado'};
  if (s.terminou && s.parado >= 0.5) return {ok: false, motivo: 'o programa terminou antes de completar a volta'};
  return tempo(this, s);
}

const DESAFIOS = [
  {
    id: 'andar30', titulo: 'Andar 30 cm e parar', pista: 'livre', largada: {x: 40, y: 75, ang: 0},
    objetivo: 'Ande 30 cm para a frente e pare com as rodas dentro da faixa azul (de 27 a 33 cm da largada).',
    dica: 'andar_cm(...) anda e para sozinho.',
    zonas: [{x: 67, y: 60, w: 6, h: 30, rotulo: 'pare aqui'}],
    limite: 20,
    verificar(prova, s) {
      const andou = s.x - this.largada.x;
      prova.texto = `Andou ${cm(andou)} cm`;
      if (s.parado >= 0.5 && dentro(this.zonas[0], s.x, s.y)) return {ok: true};
      if (andou > 45) return {ok: false, motivo: 'passou da faixa sem parar'};
      if (s.terminou && s.parado >= 0.5) {
        return {ok: false, motivo: `parou depois de andar ${cm(andou)} cm (a faixa vai de 27 a 33 cm)`};
      }
      return tempo(this, s);
    },
  },
  {
    id: 'quadrado', titulo: 'Fazer um quadrado', pista: 'livre', largada: {x: 60, y: 75, ang: 0},
    objetivo: 'Faça um quadrado de 40 cm de lado: passe pelos 3 cantos marcados e pare de volta na largada ' +
              '(a menos de 6 cm dela).',
    dica: 'repita 4 vezes: andar_cm(40) e virar_esquerda(90).',
    marcos: [[[100, 75], [100, 35], [60, 35]], [[100, 75], [100, 115], [60, 115]]], raio: 7,
    limite: 40,
    verificar(prova, s) {
      const n = passarMarcos(this, prova, s), longe = Math.hypot(s.x - this.largada.x, s.y - this.largada.y);
      prova.texto = `Cantos: ${n} de 3`;
      if (n === 3 && s.parado >= 0.5 && longe <= 6) return {ok: true};
      if (s.terminou && s.parado >= 0.5) {
        return {ok: false, motivo: n < 3 ? `passou por ${n} de 3 cantos` : `parou a ${cm(longe)} cm da largada`};
      }
      return tempo(this, s);
    },
  },
  {
    id: 'caixa', titulo: 'Parar antes da caixa',
    pista: {id: 'desafio-caixa', nome: 'Caixa no caminho', largura: 200, altura: 120, quadriculado: true,
            linhas: [], paredes: [], caixas: [{x: 150, y: 45, w: 20, h: 30}]},
    largada: {x: 30, y: 60, ang: 0},
    objetivo: 'Ande até a caixa e pare com a frente do robô na faixa azul, a menos de 10 cm da caixa, sem encostar nela.',
    dica: 'o ultrassom (porta 4) mede a distância até a caixa: esperar_distancia(4, "<", ...).',
    zonas: [{x: 140, y: 45, w: 10, h: 30, rotulo: 'a frente para aqui'}],
    limite: 25,
    verificar(prova, s) {
      const vao = this.pista.caixas[0].x - s.frente[0];
      prova.texto = `Frente a ${cm(Math.max(0, vao))} cm da caixa`;
      if (s.batidas) return {ok: false, motivo: 'o robô encostou na caixa'};
      if (s.parado >= 0.5 && vao > 0 && vao <= 10) return {ok: true};
      if (s.terminou && s.parado >= 0.5) {
        return {ok: false, motivo: `parou com a frente a ${cm(vao)} cm da caixa (precisa ser menos de 10 cm)`};
      }
      return tempo(this, s);
    },
  },
  {
    id: 'oval', titulo: 'Seguir a linha do oval', pista: 'oval', largada: {x: 75, y: 30, ang: 0},
    objetivo: 'Siga a linha e dê uma volta inteira no oval, passando pelos marcos na ordem, sem sair da linha.',
    marcos: [[[180, 70], [100, 110], [20, 70], [95, 30]]], raio: 8, longe: 15,
    limite: 90, verificar: volta,
  },
  {
    id: 'curvas90', titulo: 'Curvas de 90°', pista: 'quadrado', largada: {x: 60, y: 25, ang: 0},
    objetivo: 'Dê uma volta inteira no quadrado seguindo a linha. Os cantos são curvas de 90°.',
    marcos: [[[145, 80], [90, 135], [35, 80], [80, 25]]], raio: 8, longe: 15,
    limite: 90, verificar: volta,
  },
  {
    id: 'falha', titulo: 'Curvas e falha na linha', pista: 'curvas90', largada: {x: 55, y: 30, ang: 0},
    objetivo: 'Uma volta inteira com curvas de 90° para os dois lados e uma falha de 10 cm na linha de cima.',
    marcos: [[[165, 30], [210, 90], [180, 140], [150, 110], [120, 85], [90, 110], [60, 140], [30, 85], [75, 30]]],
    raio: 8, longe: 15,
    limite: 150, verificar: volta,
  },
  {
    id: 'verde', titulo: 'Cruzamentos com verde', pista: 'verde', largada: {x: 50, y: 30, ang: 0},
    objetivo: 'Uma volta inteira obedecendo os quadrados verdes: verde à esquerda vira à esquerda, à direita vira ' +
              'à direita e, sem verde, segue reto. O verde depois do cruzamento não vale.',
    marcos: [[[165, 30], [210, 110], [170, 150], [130, 120], [80, 90], [30, 60], [75, 30]]], raio: 8, longe: 15,
    limite: 180, verificar: volta,
  },
  {
    id: 'obstaculo', titulo: 'Desviar do obstáculo', pista: 'obstaculo', largada: {x: 80, y: 35, ang: 0},
    objetivo: 'Uma volta inteira no oval: desvie da caixa que está em cima da linha sem bater nela e volte para a linha.',
    marcos: [[[205, 80], [60, 125], [15, 80], [100, 35]]], raio: 10, longe: 35, semBater: true,
    limite: 180, verificar: volta,
  },
];

EST.DESAFIOS = DESAFIOS;
})();
