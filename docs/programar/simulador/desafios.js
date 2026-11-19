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

// chegada da OBR: passar pelos marcos na ordem e ficar 5 s parado em cima da faixa vermelha (s.sobreVermelho)
function chegada(prova, s) {
  const n = passarMarcos(this, prova, s), total = this.marcos[0].length, naFaixa = !!s.sobreVermelho;
  prova.texto = n < total ? `Marcos: ${n} de ${total}`
    : naFaixa ? `Na faixa vermelha: ${cm(Math.min(s.parado, 5))} de 5 s parado` : 'Agora pare na faixa vermelha';
  if (this.semBater && s.batidas) return {ok: false, motivo: 'o robô bateu na caixa'};
  if (n === total && naFaixa && s.parado >= 5) return {ok: true};
  if (n < total && naFaixa && s.parado >= 5) {
    return {ok: false, motivo: `parou na faixa vermelha, mas pulou parte do percurso (faltou o marco ${n + 1})`};
  }
  if (EST.distLinha(s.pista, s.x, s.y) > this.longe) {
    return {ok: false, motivo: n === total ? 'passou da faixa vermelha sem parar' : 'o robô saiu da linha'};
  }
  if (s.parado > 15) return {ok: false, motivo: 'o robô ficou 15 s parado fora da faixa vermelha'};
  if (s.terminou && s.parado >= 0.5 && !naFaixa) return {ok: false, motivo: 'o programa terminou antes da faixa vermelha'};
  return tempo(this, s);
}

const PASSO = {N: [0, -1], S: [0, 1], L: [1, 0], O: [-1, 0]};

/* Desafio numa arena da OBR (obr.js), pelo id de uma arena pronta (d.arena) ou por um percurso (d.percurso,
   d.colunas, d.linhas). A pista, a largada e os marcos só são montados quando a página pede, porque o obr.js
   carrega depois deste arquivo. Os marcos ficam na entrada de cada ladrilho; no beco sem saída, logo depois da
   entrada (o robô dá meia-volta antes do meio dele) e, na volta, no meio do ladrilho seguinte. Perto do
   obstáculo não há marco: no desvio o robô sai da linha. */
function naArena(d) {
  let feito = null;
  const montar = () => {
    if (feito) return feito;
    const pronta = d.arena && typeof d.arena === 'object' ? {arena: d.arena} : EST.OBR.ARENAS.find(a => a.id === d.arena);
    const arena = pronta ? pronta.arena
      : {colunas: d.colunas, linhas: d.linhas, nivel: 1, percurso: EST.OBR.percursoDe(d.percurso)};
    const p = EST.OBR.montar(arena, 'desafio-' + d.id, d.titulo);
    const {LADO, BORDA} = EST.OBR, perc = arena.percurso, tipos = p.obr.tipos, marcos = [];
    perc.forEach((t, i) => {
      if (i === 0 || t.elemento === 'obstaculo' || perc[i - 1].elemento === 'obstaculo') return;
      const cx = BORDA + t.c * LADO + LADO / 2, cy = BORDA + t.r * LADO + LADO / 2, [ex, ey] = PASSO[tipos[i].entrada];
      if (tipos[i].tipo === 'beco') marcos.push([cx + ex * (LADO / 2 - 4), cy + ey * (LADO / 2 - 4)]);
      else if (tipos[i - 1].tipo === 'beco') marcos.push([cx, cy]);
      else marcos.push([cx + ex * LADO / 2, cy + ey * LADO / 2]);
    });
    const {obr, ...pista} = p;           // sem a arena: no desafio não há a rodada da OBR nem falha de progresso
    feito = {pista, largada: p.largada, marcos: [marcos]};
    return feito;
  };
  for (const campo of ['pista', 'largada', 'marcos']) {
    Object.defineProperty(d, campo, {get: () => montar()[campo], enumerable: true});
  }
  return d;
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
    id: 'cruzamentos', titulo: 'Cruzamentos sem verde',
    pista: {id: 'desafio-cruzamentos', nome: 'Oito com cruzamentos', largura: 240, altura: 180,
            linhas: [{seg: [30, 30, 120, 30]}, {seg: [120, 30, 120, 150]}, {seg: [120, 150, 210, 150]},
                     {seg: [210, 150, 210, 90]}, {seg: [210, 90, 30, 90]}, {seg: [30, 90, 30, 30]},
                     {seg: [75, 14, 75, 46]}],
            paredes: [], caixas: []},
    largada: {x: 50, y: 30, ang: 0},
    objetivo: 'Uma volta inteira no oito. Os cruzamentos não têm verde: siga reto em todos, inclusive no do meio, ' +
              'por onde o robô passa duas vezes. Os cantos são curvas de 90° para os dois lados.',
    dica: 'os dois sensores no preto ao mesmo tempo é um cruzamento. Atravesse reto alguns centímetros de uma vez ' +
          '(andar_cm(3)): decidindo a cada leitura, o robô vira para a linha que cruza.',
    marcos: [[[100, 30], [120, 120], [170, 150], [210, 110], [80, 90], [30, 60], [62, 30]]], raio: 8, longe: 15,
    limite: 150, verificar: volta,
  },
  {
    id: 'verde', titulo: 'Cruzamentos com verde', pista: 'verde', largada: {x: 50, y: 30, ang: 0},
    objetivo: 'Uma volta inteira obedecendo os quadrados verdes: verde à esquerda vira à esquerda, à direita vira ' +
              'à direita e, sem verde, segue reto. O verde depois do cruzamento não vale.',
    dica: 'no modo cor, o verde é VERDE. O verde que aparece logo depois de um cruzamento é o "verde depois": ' +
          'marque quando passou pelo cruzamento (zerar_cronometro()) e ignore o verde por um instante.',
    marcos: [[[165, 30], [210, 110], [170, 150], [130, 120], [80, 90], [30, 60], [75, 30]]], raio: 8, longe: 15,
    limite: 180, verificar: volta,
  },
  {
    id: 'obstaculo', titulo: 'Desviar do obstáculo', pista: 'obstaculo', largada: {x: 80, y: 35, ang: 0},
    objetivo: 'Uma volta inteira no oval: desvie da caixa que está em cima da linha sem bater nela e volte para a linha.',
    marcos: [[[205, 80], [60, 125], [15, 80], [100, 35]]], raio: 10, longe: 35, semBater: true,
    limite: 180, verificar: volta,
  },
  // ---- mais difíceis: velocidade e a prova da OBR por partes, até o percurso completo
  {
    id: 'rapido', titulo: 'Volta rápida', pista: 'oval', largada: {x: 75, y: 30, ang: 0},
    objetivo: 'Uma volta inteira no oval em até 20 segundos, sem sair da linha.',
    dica: 'o seguidor liga-desliga perde tempo balançando. Um seguidor proporcional ' +
          '(erro = luz_refletida(1) - luz_refletida(2)) anda mais rápido: suba a velocidade aos poucos e acerte o KP.',
    marcos: [[[180, 70], [100, 110], [20, 70], [95, 30]]], raio: 8, longe: 15,
    limite: 20, verificar: volta,
  },
  naArena({
    id: 'chegada', titulo: 'Chegada na faixa vermelha', arena: 'obr-treino',
    objetivo: 'Siga a linha pelos ladrilhos da OBR (curvas de 90°, curvas suaves e um gap de 10 cm) e pare na faixa ' +
              'vermelha do fim, ficando 5 s parado em cima dela.',
    dica: 'no modo cor, a faixa vermelha é VERMELHO. No gap a linha some: siga reto até achar a linha de novo.',
    raio: 8, longe: 15, limite: 150, verificar: chegada,
  }),
  naArena({
    id: 'beco', titulo: 'Beco sem saída', colunas: 5, linhas: 3, percurso: '0,2 1,2 2,2:t 3,2:t 2,2:t+r 2,1 3,1 4,1',
    objetivo: 'Dois verdes antes do cruzamento, um de cada lado, é um beco sem saída: dê meia-volta. Na volta, o verde ' +
              'do cruzamento manda virar. Termine parado na faixa vermelha por 5 s.',
    dica: 'os dois verdes ficam lado a lado, mas um sensor pode ver o seu antes do outro: quando um sensor vir verde, ' +
          'ande devagar um pouco olhando os dois lados antes de decidir.',
    raio: 8, longe: 15, limite: 150, verificar: chegada,
  }),
  naArena({
    id: 'obr', titulo: 'Percurso completo da OBR', arena: 'obr-completa',
    objetivo: 'Tudo junto, como na prova: interseções com e sem verde, beco sem saída, gap, um obstáculo para desviar ' +
              'e a chegada na faixa vermelha (5 s parado), em até 5 minutos.',
    dica: 'junte o que funcionou nos desafios anteriores, cada parte numa função, e um laço principal que só decide ' +
          'qual chamar (veja o guia da OBR).',
    raio: 8, longe: 35, semBater: true, limite: 300, verificar: chegada,
  }),
];

// ---------------------------------------------------------------- desafio surpresa

/* Como o desafio surpresa da OBR: a arena sorteada (obr.js) e uma tarefa a mais, sorteada junto com ela. A equipe
   muda o programa que já faz o percurso para fazer também a tarefa. A mesma semente dá a mesma arena e a mesma
   tarefa: a turma toda pode tentar a mesma. Cada tarefa vale em alguns ladrilhos (onde) e confere lá:
     bips: quantos sons começam com o robô nesses ladrilhos (passou disso, já falha);
     parar: os segundos parado num desses ladrilhos (todos: em cada um deles);
     luz: a cor da luz em algum momento ali (0 azul, 1 roxo, 2 vermelho), e azul na chegada;
     tela: o texto na tela na chegada (e nunca antes do último ladrilho).
   O robô está num ladrilho quando o meio entre as rodas ou a frente dele está lá. */
const TAREFAS = [
  {id: 'bips-gap', onde: 'gap', bips: 2, titulo: 'dois bips no gap',
   texto: 'quando chegar no gap, dê exatamente 2 bips antes de atravessar',
   dica: 'no gap a linha some dos três sensores por mais tempo que no balanço do seguidor: zere um cronômetro sempre ' +
         'que algum sensor vê a linha e, quando ele passar de uns 0,3 s, é o gap. Dê os bips uma vez só e atravesse reto.'},
  {id: 'parar-gap', onde: 'gap', parar: 2, titulo: 'parar no gap',
   texto: 'quando chegar no gap, pare 2 s antes de atravessar',
   dica: 'no gap a linha some dos três sensores por mais tempo que no balanço do seguidor: zere um cronômetro sempre ' +
         'que algum sensor vê a linha e, quando ele passar de uns 0,3 s, é o gap. Pare 2 s uma vez só e atravesse reto.'},
  {id: 'luz-obstaculo', onde: 'obstaculo', luz: 2, titulo: 'luz vermelha no desvio',
   texto: 'acenda a luz vermelha enquanto desvia do obstáculo e a luz azul quando voltar para a linha',
   dica: "luz('vermelho') no começo da parte que desvia e luz('azul') no fim dela."},
  {id: 'luz-verde', onde: 'verde', luz: 1, titulo: 'luz roxa no verde',
   texto: 'acenda a luz roxa quando virar por causa do verde e volte para a luz azul depois da curva',
   dica: "na parte do programa que vira por causa do verde: luz('roxo') antes do virar_...(90) e luz('azul') depois."},
  {id: 'parar-verde', onde: 'verde', parar: 3, todos: true, titulo: 'parar antes de virar no verde',
   texto: 'em cada interseção em que o verde manda virar, pare 3 s antes de virar',
   dica: 'na parte do programa que vira por causa do verde, pare e espere 3 s antes do virar_...(90).'},
  {id: 'bips-beco', onde: 'beco', bips: 3, titulo: 'três bips no beco',
   texto: 'no beco sem saída, dê exatamente 3 bips antes da meia-volta',
   dica: 'na parte do programa que vê os dois verdes, toque os 3 bips antes de virar 180°.'},
  {id: 'fim-na-tela', onde: 'chegada', tela: 'FIM', titulo: 'FIM na tela',
   texto: 'quando parar na faixa vermelha, mostre FIM na tela (e não antes)',
   dica: "depois do laço principal: parar(), mostrar('FIM') e esperar."},
  {id: 'notas-chegada', onde: 'chegada', bips: 3, titulo: 'três notas na chegada',
   texto: "quando parar na faixa vermelha, toque exatamente 3 notas, como melodia('do re mi')",
   dica: 'depois do laço principal: parar(), a melodia e esperar até completar os 5 s parado.'},
];
const COR_DA_LUZ = ['azul', 'roxa', 'vermelha'];
const ONDE = {gap: 'no gap', obstaculo: 'no desvio do obstáculo', verde: 'nas interseções com verde',
              beco: 'no beco sem saída', chegada: 'na chegada'};

/* os ladrilhos ("c,r") de cada lugar onde uma tarefa pode valer */
function lugaresDaArena(arena) {
  const tipos = EST.OBR.tiposDoPercurso(arena.percurso), p = arena.percurso;
  const lugares = {gap: [], obstaculo: [], verde: [], beco: [], chegada: []};
  p.forEach((t, i) => {
    const k = `${t.c},${t.r}`, tipo = tipos[i].tipo;
    if (t.elemento === 'gap') lugares.gap.push(k);
    if (t.elemento === 'obstaculo') lugares.obstaculo.push(k);
    if (tipo === 'beco') lugares.beco.push(k);
    if (tipo === 'curva' && (t.elemento === 'T' || t.elemento === 'cruz')) lugares.verde.push(k);   // o verde manda virar
    if (i === p.length - 1) lugares.chegada.push(k);
  });
  for (const nome of Object.keys(lugares)) lugares[nome] = [...new Set(lugares[nome])];
  return lugares;
}

function verificarSurpresa(prova, s) {
  const t = this.tarefa, {LADO, BORDA} = EST.OBR;
  const chave = (x, y) => `${Math.floor((x - BORDA) / LADO)},${Math.floor((y - BORDA) / LADO)}`;
  const aqui = new Set([chave(s.x, s.y), chave(s.frente[0], s.frente[1])]);
  const p = prova.surpresa || (prova.surpresa = {sons: s.sons || 0, bips: 0, parado: {}, luz: false, cedo: false});
  const novos = (s.sons || 0) - p.sons;
  p.sons = s.sons || 0;
  const dentro = this.lugares.filter(k => aqui.has(k));
  const naTela = (s.tela || []).some(texto => String(texto).toUpperCase().includes(t.tela));
  if (dentro.length) {
    if (t.bips) p.bips += novos;
    if (t.parar) for (const k of dentro) p.parado[k] = Math.max(p.parado[k] || 0, s.parado);
    if (t.luz !== undefined && s.luz === t.luz) p.luz = true;
  } else if (t.tela && naTela) {
    p.cedo = true;
  }
  const onde = ONDE[t.onde];
  const paradosOk = this.lugares.filter(k => (p.parado[k] || 0) >= t.parar).length;
  const andamento = t.bips ? `${p.bips} de ${t.bips} ${t.onde === 'chegada' ? 'notas' : 'bips'} ${onde}`
    : t.parar && t.todos ? `parou ${t.parar} s em ${paradosOk} de ${this.lugares.length} interseções com verde`
    : t.parar ? `parado ${onde}: ${cm(Math.min(t.parar, Math.max(0, ...Object.values(p.parado))))} de ${t.parar} s`
    : t.luz !== undefined ? `luz ${COR_DA_LUZ[t.luz]} ${onde}: ${p.luz ? 'feito' : 'ainda não'}`
    : `${t.tela} na tela ${onde}`;
  const r = chegada.call(this, prova, s);
  prova.texto = `${prova.texto} · Surpresa: ${andamento}`;
  if (t.bips && p.bips > t.bips) {
    return {ok: false, motivo: `${t.onde === 'chegada' ? 'tocou' : 'deu'} ${p.bips} ${t.onde === 'chegada' ? 'notas' : 'bips'} ${onde} (eram ${t.bips})`};
  }
  if (p.cedo) return {ok: false, motivo: `mostrou ${t.tela} na tela antes da chegada`};
  if (!r || !r.ok) return r;
  const falta = t.bips && p.bips < t.bips ? `${t.onde === 'chegada' ? 'tocou' : 'deu'} ${p.bips} de ${t.bips} ${t.onde === 'chegada' ? 'notas' : 'bips'} ${onde}`
    : t.parar && (t.todos ? paradosOk < this.lugares.length : !paradosOk)
      ? (t.todos ? `parou ${t.parar} s em ${paradosOk} de ${this.lugares.length} interseções com verde` : `não parou ${t.parar} s ${onde}`)
    : t.luz !== undefined && !p.luz ? `não acendeu a luz ${COR_DA_LUZ[t.luz]} ${onde}`
    : t.luz !== undefined && s.luz !== 0 ? 'a luz não estava azul na chegada'
    : t.tela && !naTela ? `não mostrou ${t.tela} na tela na chegada`
    : '';
  return falta ? {ok: false, motivo: `completou o percurso, mas ${falta}`} : r;
}

// sementes vizinhas dão tarefas sem relação (a semente sozinha repetiria a mesma tarefa várias vezes seguidas)
function misturar(n) {
  let t = Math.imul((n >>> 0) ^ 0x9e3779b9, 0x85ebca6b);
  t = Math.imul(t ^ (t >>> 13), 0xc2b2ae35);
  return (t ^ (t >>> 16)) >>> 0;
}

/* O desafio surpresa da arena nº semente (1 a 9999). */
function surpresa(semente) {
  const arena = EST.OBR.sortear(semente), lugares = lugaresDaArena(arena);
  // primeiro o lugar, entre os que a arena tem (nem toda arena tem obstáculo ou beco), depois a tarefa de lá
  const possiveis = TAREFAS.filter(t => lugares[t.onde].length), h = misturar(semente);
  const onde = [...new Set(possiveis.map(t => t.onde))], daqui = possiveis.filter(t => t.onde === onde[h % onde.length]);
  const tarefa = daqui[Math.floor(h / onde.length) % daqui.length];
  return naArena({
    id: 'surpresa', surpresa: true, semente, tarefa, lugares: lugares[tarefa.onde], arena,
    titulo: `Surpresa: ${tarefa.titulo}`,
    objetivo: `Faça o percurso da arena sorteada nº ${semente} até a faixa vermelha (5 s parado em cima dela) e, além ` +
              `disso, ${tarefa.texto}.`,
    dica: tarefa.dica, raio: 8, longe: 35, semBater: true, limite: 300, verificar: verificarSurpresa,
  });
}

EST.DESAFIOS = DESAFIOS;
EST.TAREFAS_SURPRESA = TAREFAS;
EST.desafioSurpresa = surpresa;
})();
