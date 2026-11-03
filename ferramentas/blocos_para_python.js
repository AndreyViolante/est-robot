// O Python que os blocos da página de programar geram (o gerador do docs/programar/modo_blocos.js), sem página:
// usado por ferramentas/teste_blocos.py para conferir a ida e volta Python -> blocos -> Python.
// Precisa do Blockly do npm (a mesma versão da página): BLOCKLY_DIR = pasta do pacote, ou "blockly" instalado.
// Uso: node ferramentas/blocos_para_python.js areas.json resultado.json   (areas: [{nome, estado}] -> [{nome, codigo}])
'use strict';
const fs = require('fs');
const path = require('path');

function acharBlockly() {
  const lugares = [process.env.BLOCKLY_DIR, 'blockly', path.join(__dirname, 'node_modules', 'blockly')].filter(Boolean);
  for (const lugar of lugares) {
    try { return require(lugar); } catch (e) { /* tenta o próximo */ }
  }
  console.error('Não achei o Blockly. Instale a mesma versão da página, por exemplo:\n' +
                '  npm install --prefix ferramentas blockly@12.3.1');
  process.exit(2);
}

const avisar = console.warn;            // os avisos de "obsoleto" do próprio Blockly só poluem a saída do teste
console.warn = (...a) => { if (!/deprecated|will be deleted/.test(String(a[0]))) avisar(...a); };
globalThis.Blockly = acharBlockly();
new Function(fs.readFileSync(path.join(__dirname, '..', 'docs', 'programar', 'modo_blocos.js'), 'utf8'))();
const B = globalThis.ESTBlocos;
B.definir();
const G = B.criarGerador();

const areas = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resultado = areas.map(({nome, estado}) => {
  const ws = new Blockly.Workspace();
  try {
    Blockly.serialization.workspaces.load(estado, ws);
    return {nome, codigo: B.pythonDaArea(ws, G)};
  } catch (e) {
    return {nome, erro: String(e && e.message || e)};
  } finally {
    ws.dispose();
  }
});
fs.writeFileSync(process.argv[3], JSON.stringify(resultado, null, 1));
