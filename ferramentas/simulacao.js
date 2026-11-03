// Roda programas compilados no simulador (simulador/vm.js e robo.js), sem página, e diz como o robô terminou.
// Usado por ferramentas/teste_simulador.py. Uso: node ferramentas/simulacao.js casos.json resultado.json
// casos.json: [{nome, hex, segundos, pista}]   resultado: [{nome, x, y, ang, giro, tela, mensagens, avisos, erro, t, andou}]
'use strict';
const fs = require('fs');
const path = require('path');

const SIM = path.join(__dirname, '..', 'simulador');
for (const f of ['mundo.js', 'robo.js', 'vm.js']) {
  // os arquivos do simulador são scripts de página: rodam aqui do mesmo jeito e se registram em globalThis.EST
  new Function(fs.readFileSync(path.join(SIM, f), 'utf8'))();
}
const EST = globalThis.EST;
const DT = 0.005;                 // segundos por passo (o simulador da página usa o mesmo)

const casos = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resultado = casos.map(caso => {
  const base = EST.PISTAS.find(p => p.id === (caso.pista || 'livre')) || EST.PISTAS[0];
  const pista = EST.copiaPista(base);
  const robo = new EST.Robo(JSON.parse(JSON.stringify(EST.ROBO_PADRAO)), pista);
  robo.colocar(pista.largada.x, pista.largada.y, pista.largada.ang);
  const inicio = {x: robo.x, y: robo.y};
  let vm, erro = null, t = 0, andou = 0;
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
  }
  if (vm.erro) erro = `${vm.erro.message} (byte ${vm.erro.pc})`;
  return {
    nome: caso.nome, terminou: vm.terminou, erro, t: Math.round(t * 1000) / 1000,
    x: robo.x - inicio.x, y: robo.y - inicio.y, ang: robo.angGraus, giro: robo.giro * 180 / Math.PI,
    andou, tela: robo.tela.map(o => o.texto), mensagens: robo.mensagens, avisos: [...robo.avisos],
  };
});
fs.writeFileSync(process.argv[3], JSON.stringify(resultado, null, 1));
