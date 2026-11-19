'use strict';
/* Teste da página inteira, num Chrome sem janela: abre a página de programar (servida da pasta docs/, como no
   site), compila com o Python do navegador, abre o simulador e executa, mostra um erro em português, passa o
   programa para blocos e compila de novo (mesmos bytes), salva e carrega o progresso, e abre o simulador sozinho.
   Precisa de internet (Python do navegador, Blockly e o editor vêm da CDN) e do pacote playwright-core, que usa o
   Chrome instalado (não baixa navegador).
   Uso: npm install --prefix <pasta> playwright-core@1.59.1
        PLAYWRIGHT_DIR=<pasta>/node_modules/playwright-core node ferramentas/teste_pagina.js   (o GitHub roda a cada envio) */
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');

const {chromium} = require(process.env.PLAYWRIGHT_DIR || 'playwright-core');
const DOCS = path.join(__dirname, '..', 'docs');
const TIPOS = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
               '.json': 'application/json', '.py': 'text/plain; charset=utf-8', '.md': 'text/markdown; charset=utf-8',
               '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.pdf': 'application/pdf',
               '.webmanifest': 'application/manifest+json', '.txt': 'text/plain; charset=utf-8', '.est': 'text/plain'};

/* a pasta docs/ num endereço local, como o GitHub Pages serve */
function servir() {
  const servidor = http.createServer((pedido, resposta) => {
    let caminho = decodeURIComponent(new URL(pedido.url, 'http://x').pathname);
    if (caminho.endsWith('/')) caminho += 'index.html';
    const arquivo = path.join(DOCS, path.normalize(caminho).replace(/^([/\\])+/, ''));
    if (!arquivo.startsWith(DOCS) || !fs.existsSync(arquivo) || fs.statSync(arquivo).isDirectory()) {
      resposta.writeHead(404); resposta.end('não achei'); return;
    }
    resposta.writeHead(200, {'Content-Type': TIPOS[path.extname(arquivo)] || 'application/octet-stream', 'Cache-Control': 'no-store'});
    fs.createReadStream(arquivo).pipe(resposta);
  });
  return new Promise(ok => servidor.listen(0, '127.0.0.1', () => ok(servidor)));
}

let falhas = 0;
function confere(nome, certo, detalhe = '') {
  if (!certo) falhas++;
  console.log(`  ${certo ? 'OK   ' : 'FALHA'} página: ${nome}${certo || !detalhe ? '' : ` -> ${detalhe}`}`);
  return certo;
}

const PROGRAMA = `from robo import *

VEL = 30 if distancia(4) > 20 else 20
zerar_cronometro()
while True:
    motores(VEL, VEL)
    if cronometro() > 1:
        break
parar()
mostrar(abs(luz_refletida(1) - 50))
`;

async function main() {
  const servidor = await servir();
  const base = `http://127.0.0.1:${servidor.address().port}`;
  const navegador = await chromium.launch({channel: process.env.CANAL || 'chrome', headless: true});
  const contexto = await navegador.newContext({serviceWorkers: 'block', acceptDownloads: true, viewport: {width: 1280, height: 900}});
  const erros = [];
  contexto.on('weberror', e => erros.push(String(e.error())));
  const pagina = await contexto.newPage();
  // o 404 aparece no console sem o endereço: anota o endereço pela resposta (o favicon do navegador não conta)
  pagina.on('console', m => { if (m.type() === 'error' && !/status of 404/.test(m.text())) erros.push(m.text()); });
  pagina.on('response', r => { if (r.status() >= 400 && !/favicon\.ico$/.test(r.url())) erros.push(`${r.status()} ${r.url()}`); });
  pagina.on('dialog', d => d.accept());                       // "trocar os blocos?", "carregar o progresso?"
  pagina.setDefaultTimeout(30000);

  const ultimaMensagem = async (classe, contem, tempo = 150000) => {
    const el = pagina.locator(`#mensagens .msg.${classe}`, {hasText: contem}).last();
    await el.waitFor({timeout: tempo});
    return el.innerText();
  };
  const limpar = () => pagina.evaluate(() => { document.getElementById('mensagens').replaceChildren(); });
  const escrever = texto => pagina.evaluate(t => document.querySelector('.CodeMirror').CodeMirror.setValue(t), texto);
  const bytesDe = texto => Number((/(\d[\d.]*) bytes/.exec(texto) || [])[1]?.replace(/\./g, ''));

  try {
    // ---- abrir
    await pagina.goto(`${base}/programar/`);
    await pagina.locator('.CodeMirror').waitFor();
    confere('a página de programar abre com o editor', true);

    // ---- Python: compilar com o Python do navegador e simular
    await escrever(PROGRAMA);
    await limpar();
    await pagina.click('#btSimular');
    const ok = await ultimaMensagem('ok', 'bytes');
    const bytesPython = bytesDe(ok);
    confere('compila com o Python do navegador (if numa linha, break, abs)', bytesPython > 0, ok);
    await pagina.locator('#sim').waitFor({state: 'visible'});
    const quadro = pagina.frameLocator('#quadroSim');
    await quadro.locator('#btExecutar:not([disabled])').waitFor();
    await quadro.locator('#btExecutar').click();
    await pagina.waitForTimeout(2500);
    const relogio = await quadro.locator('#relogio').innerText();
    confere('o simulador abre com o programa e executa', !/^0,0 s$/.test(relogio.trim()), relogio);
    await pagina.click('#btFecharSim');
    await pagina.locator('#sim').waitFor({state: 'hidden'});

    // ---- erro em português, na linha certa
    await escrever('from robo import *\n\nandr(rotacoes=2)\n');
    await limpar();
    await pagina.click('#btSimular');
    const erro = await ultimaMensagem('erro', 'linha');
    confere('erro de escrita vira mensagem em português com a linha', /linha 3/.test(erro) && erro.includes('Você quis dizer "andar"'), erro);

    // ---- blocos: trazer do Python e compilar de novo, com os mesmos bytes
    await escrever(PROGRAMA);
    await pagina.click('#abaBlocos');
    await pagina.locator('#areaBlocos .injectionDiv').waitFor({timeout: 60000});
    await limpar();
    await pagina.click('#btTrazer');
    const trouxe = await ultimaMensagem('ok', 'agora está em blocos');
    confere('o programa vira blocos, todas as linhas', trouxe.includes('Todas as linhas viraram blocos'), trouxe);
    await limpar();
    await pagina.click('#btSimular');
    const okBlocos = await ultimaMensagem('ok', 'bytes');
    confere('os blocos compilam com os mesmos bytes do Python', bytesDe(okBlocos) === bytesPython, `${okBlocos} / Python ${bytesPython}`);
    await pagina.click('#btFecharSim');
    await pagina.click('#abaPython');

    // ---- progresso: salvar num arquivo e carregar de volta
    await escrever(PROGRAMA.replace('mostrar(', 'bip()\nmostrar('));
    await pagina.evaluate(() => document.querySelector('.CodeMirror').CodeMirror.focus());
    await pagina.keyboard.press('Control+s');                 // guarda neste navegador agora
    await pagina.click('#btExtras');
    const [baixado] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#btSalvarProgresso')]);
    const arquivo = path.join(os.tmpdir(), `progresso-teste-${process.pid}.json`);
    await baixado.saveAs(arquivo);
    const salvo = JSON.parse(fs.readFileSync(arquivo, 'utf8'));
    const fonteSalva = salvo.dados && salvo.dados['est-programar-v1'] && salvo.dados['est-programar-v1'].fonte;
    confere('salvar o progresso baixa o arquivo com o programa', salvo.formato === 'est-lab-progresso' && /bip\(\)/.test(fonteSalva || ''),
            JSON.stringify(salvo).slice(0, 200));
    await escrever('from robo import *\n\nparar()\n');
    await pagina.keyboard.press('Control+s');
    await pagina.click('#btExtras');
    const [escolha] = await Promise.all([pagina.waitForEvent('filechooser'), pagina.click('#btCarregarProgresso')]);
    await Promise.all([pagina.waitForEvent('load'), escolha.setFiles(arquivo)]);
    await pagina.locator('.CodeMirror').waitFor();
    const voltou = await pagina.evaluate(() => document.querySelector('.CodeMirror').CodeMirror.getValue());
    confere('carregar o progresso traz o programa de volta', voltou.includes('bip()'), voltou.slice(0, 120));
    fs.rmSync(arquivo, {force: true});

    // ---- o simulador sozinho, com o exemplo do site
    await pagina.goto(`${base}/simulador/`);
    await pagina.locator('#btExecutar:not([disabled])').waitFor();
    await pagina.click('#btExecutar');
    await pagina.waitForTimeout(2000);
    const relogio2 = await pagina.locator('#relogio').innerText();
    confere('o simulador do site abre e executa o exemplo', !/^0,0 s$/.test(relogio2.trim()), relogio2);
  } catch (e) {
    confere('o teste chegou até o fim', false, e.message.split('\n')[0]);
  } finally {
    const reais = erros.filter(t => !/favicon|WebHID|navigator\.(hid|bluetooth)/i.test(t));
    confere('nenhum erro no console', !reais.length, reais.slice(0, 3).join(' | '));
    await navegador.close();
    servidor.close();
  }
  console.log(`\npágina inteira: ${falhas ? `${falhas} FALHA(S)` : 'OK'}`);
  process.exit(falhas ? 1 : 0);
}

main();
