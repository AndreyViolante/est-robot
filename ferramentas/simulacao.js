// Roda programas compilados no simulador (simulador/vm.js e robo.js), sem página, e diz como o robô terminou.
// Usado por ferramentas/teste_simulador.py. Uso: node ferramentas/simulacao.js casos.json resultado.json
// casos.json: [{nome, hex, segundos, pista}]   resultado: [{nome, x, y, ang, giro, tela, mensagens, avisos, erro, t, andou,
//              grafico}] (grafico: o que o gráfico dos sensores no tempo guardou, simulador/grafico.js)
'use strict';
const fs = require('fs');
const path = require('path');

const SIM = path.join(__dirname, '..', 'simulador');
for (const f of ['mundo.js', 'robo.js', 'vm.js', 'grafico.js']) {
  // os arquivos do simulador são scripts de página: rodam aqui do mesmo jeito e se registram em globalThis.EST
  new Function(fs.readFileSync(path.join(SIM, f), 'utf8'))();
}
const EST = globalThis.EST;
const DT = 0.005;                 // segundos por passo (o simulador da página usa o mesmo)

// a leitura de cada sensor ligado no robô, como o app.js anota no gráfico (luz refletida, ou cm do ultrassom)
function lerSensores(robo) {
  const v = {};
  for (const [p, s] of Object.entries(robo.config.portas)) {
    if (s.tipo === 'cor') v[p] = robo.sensorCor(p).luz;
    else if (s.tipo === 'ultrassom') v[p] = robo.sensorUltrassom(p).cm;
  }
  return v;
}

/* o que o gráfico guardou: quantas anotações, o tempo da última, o menor e o maior valor de cada porta, e se os
   pontos reduzidos para 150 pixels mantêm o menor e o maior de cada porta (o desenho não perde picos) */
function resumoDoGrafico(registro) {
  const portas = {};
  for (const a of registro.amostras) {
    for (const [p, v] of Object.entries(a.v)) {
      const r = portas[p] || (portas[p] = {min: Infinity, max: -Infinity});
      r.min = Math.min(r.min, v); r.max = Math.max(r.max, v);
    }
  }
  const {t0, t1} = registro.janela(0);
  let reduzidoOk = true, maiorReduzido = 0;
  for (const [p, r] of Object.entries(portas)) {
    const pts = EST.Grafico.pontos(registro, p, t0, t1, 150).filter(Boolean);
    maiorReduzido = Math.max(maiorReduzido, pts.length);
    const vs = pts.map(pt => pt[1]);
    reduzidoOk = reduzidoOk && Math.min(...vs) === r.min && Math.max(...vs) === r.max &&
                 pts.every((pt, i) => i === 0 || pt[0] >= pts[i - 1][0]);
  }
  return {anotacoes: registro.amostras.length, fim: registro.fim, portas, reduzidoOk, maiorReduzido};
}

const casos = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resultado = casos.map(caso => {
  const base = EST.PISTAS.find(p => p.id === (caso.pista || 'livre')) || EST.PISTAS[0];
  const pista = EST.copiaPista(base);
  const robo = new EST.Robo(JSON.parse(JSON.stringify(EST.ROBO_PADRAO)), pista);
  robo.colocar(pista.largada.x, pista.largada.y, pista.largada.ang);
  const inicio = {x: robo.x, y: robo.y};
  let vm, erro = null, t = 0, andou = 0;
  const registro = new EST.Grafico.Registro();
  try {
    vm = new EST.VM(Uint8Array.from(Buffer.from(caso.hex, 'hex')), robo);
  } catch (e) {
    return {nome: caso.nome, erro: e.message};
  }
  while (!vm.terminou && !vm.erro && t < caso.segundos) {
    const antes = [robo.x, robo.y];
    vm.executar(t, DT);
    robo.avancar(DT, t + DT);
    andou += Math.hypot(robo.x - antes[0], robo.y - antes[1]);
    t += DT;
    registro.anotar(t, lerSensores(robo));        // como o app.js do simulador, a cada passo
  }
  if (vm.erro) erro = `${vm.erro.message} (byte ${vm.erro.pc})`;
  return {
    nome: caso.nome, terminou: vm.terminou, erro, t: Math.round(t * 1000) / 1000,
    x: robo.x - inicio.x, y: robo.y - inicio.y, ang: robo.angGraus, giro: robo.giro * 180 / Math.PI,
    andou, tela: robo.tela.map(o => o.texto), mensagens: robo.mensagens, avisos: [...robo.avisos],
    grafico: resumoDoGrafico(registro),
  };
});
fs.writeFileSync(process.argv[3], JSON.stringify(resultado, null, 1));
