'use strict';
/* Teste da página inteira, num Chrome sem janela: abre a página de programar (servida da pasta docs/, como no
   site), compila com o Python do navegador, abre o simulador e executa, mostra um erro em português, completa
   comandos no editor (autocompletar), passa o
   programa para blocos (com uma função em "Meus blocos") e compila de novo (mesmos bytes), liga a tela cheia, manda o programa por
   link (com o modo blocos e o desafio aberto), salva e carrega o progresso e abre o simulador sozinho (grava um
   vídeo da pista). Depois, num celular (390 x 844, toque): a página começa nos blocos, não
   rola para o lado, o teclado de programação aparece no código, o menu Arquivo cabe na tela e o simulador roda.
   Por fim, com um robô de mentira no USB (WebHID), a Conexão mostra a bateria e avisa quando está fraca.
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



def acelerar(vel):
    motores(vel, vel)


VEL = 30 if distancia(4) > 20 else 20
zerar_cronometro()
while True:
    acelerar(VEL)
    if cronometro() > 1:
        break
parar()
mostrar(abs(luz_refletida(1) - 50))
mostrar(media(luz_refletida(2), 3), linha=2)
`;

/* o celular: a mesma página numa tela de 390 x 844 com toque (Chrome do Android) */
async function celular(navegador, base, erros) {
  const contexto = await navegador.newContext({
    serviceWorkers: 'block', viewport: {width: 390, height: 844}, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36'});
  contexto.on('weberror', e => erros.push(`celular: ${e.error()}`));
  const pagina = await contexto.newPage();
  pagina.on('console', m => { if (m.type() === 'error' && !/status of 404/.test(m.text())) erros.push(`celular: ${m.text()}`); });
  pagina.on('dialog', d => d.accept());
  pagina.setDefaultTimeout(30000);
  const semRolarDeLado = () => pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  try {
    await pagina.goto(`${base}/programar/`);
    await pagina.locator('#areaBlocos .injectionDiv').waitFor({timeout: 60000});
    confere('celular: a primeira visita começa nos blocos', await pagina.getAttribute('#abaBlocos', 'aria-selected') === 'true');
    confere('celular: a página não rola para o lado (blocos)', await semRolarDeLado());
    await pagina.locator('#btExtras').tap();
    const menu = await pagina.locator('#extras').boundingBox();
    confere('celular: o menu Arquivo abre dentro da tela', !!menu && menu.x >= 0 && menu.x + menu.width <= 391,
            JSON.stringify(menu));
    await pagina.locator('#btExtras').tap();
    await pagina.locator('#abaPython').tap();
    await pagina.locator('#areaPython .CodeMirror').waitFor();
    confere('celular: a página não rola para o lado (Python)', await semRolarDeLado());
    await pagina.locator('#areaPython .CodeMirror-lines').tap();
    await pagina.locator('#teclado').waitFor({state: 'visible', timeout: 5000}).catch(() => {});
    confere('celular: tocar no código mostra o teclado de programação', await pagina.isVisible('#teclado'));
    await pagina.locator('#btSimular').tap();
    await pagina.locator('#mensagens .msg.ok', {hasText: 'bytes'}).last().waitFor({timeout: 150000});
    await pagina.locator('#sim').waitFor({state: 'visible'});
    const quadro = pagina.frameLocator('#quadroSim');
    await quadro.locator('#btExecutar:not([disabled])').waitFor();
    await quadro.locator('#btExecutar').tap();
    await pagina.waitForTimeout(2500);
    const relogio = await quadro.locator('#relogio').innerText();
    const simDeLado = await pagina.frame({url: /simulador\/index\.html/}).evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1);
    confere('celular: o simulador abre, executa e não rola para o lado', !/^0,0 s$/.test(relogio.trim()) && simDeLado,
            `${relogio}, sem rolar de lado: ${simDeLado}`);
  } catch (e) {
    confere('celular: o teste chegou até o fim', false, e.message.split('\n')[0]);
  } finally {
    await contexto.close();
  }
}

/* um robô de mentira no USB (WebHID) que responde o 0C 01 com o nível da bateria: a Conexão tem que mostrar */
async function roboNoUsb(navegador, base, erros) {
  const contexto = await navegador.newContext({serviceWorkers: 'block'});
  await contexto.addInitScript(() => {
    const ouvintes = [];
    const robo = {
      vendorId: 0x0483, productId: 0x5750, productName: 'EST robô', opened: false, perguntas: 0,
      async open() { this.opened = true; },
      async close() { this.opened = false; },
      addEventListener(tipo, f) { if (tipo === 'inputreport') ouvintes.push(f); },
      removeEventListener(tipo, f) { const i = ouvintes.indexOf(f); if (i >= 0) ouvintes.splice(i, 1); },
      async sendReport(id, report) {
        if (report[2] !== 0x0C) return;
        this.perguntas++;
        const P = window.ESTProtocolo;
        const r = P.frame(0x0C, [0x04, 0x00, 1, 0x56, 0x31, 0x00]);        // nível 1 de 4: fraca
        r[1] = 0x21;
        r[r.length - 2] = P.checksum(r.subarray(0, r.length - 2));
        setTimeout(() => ouvintes.slice().forEach(f => f({data: new DataView(r.buffer)})), 20);
      },
    };
    window.roboDeMentira = robo;
    Object.defineProperty(navigator, 'hid', {configurable: true, value: {
      getDevices: async () => [robo], requestDevice: async () => [robo], addEventListener() {}, removeEventListener() {}}});
  });
  const pagina = await contexto.newPage();
  pagina.on('console', m => { if (m.type() === 'error') erros.push(m.text()); });
  try {
    await pagina.goto(`${base}/programar/`);
    const linha = pagina.locator('#estadoRobo', {hasText: 'Bateria'});
    await linha.waitFor({timeout: 15000});
    const estado = await pagina.evaluate(() => {
      const p = document.getElementById('estadoRobo');
      return {texto: p.textContent, classe: p.className, aberto: window.roboDeMentira.opened};
    });
    confere('robô no USB: a Conexão mostra a bateria, avisa que está fraca e fecha o robô',
      /Bateria 1 de 4: carregue o robô/.test(estado.texto) && /fraca/.test(estado.classe) && !estado.aberto, JSON.stringify(estado));
  } catch (e) {
    confere('robô no USB: o teste chegou até o fim', false, e.message.split('\n')[0]);
  } finally {
    await contexto.close();
  }
}

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
    confere('compila com o Python do navegador (função, if numa linha, break, abs, media)', bytesPython > 0, ok);
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

    // ---- autocompletar: "andar_" sugere andar_cm; Enter escreve andar_cm(20) com o 20 selecionado; num bloco
    // "with", a linha de baixo já vem com o recuo. O Enter vem logo depois da última letra, sem esperar a lista
    await escrever('from robo import *\n\n');
    await pagina.evaluate(() => { const cm = document.querySelector('.CodeMirror').CodeMirror; cm.focus(); cm.setCursor(2, 0); });
    await pagina.keyboard.type('andar_');
    const sugeriu = await pagina.locator('.CodeMirror-hint-active').innerText();
    await pagina.keyboard.press('Enter');
    const completou = await pagina.evaluate(() => {
      const cm = document.querySelector('.CodeMirror').CodeMirror;
      return {linha: cm.getLine(2), selecionado: cm.getSelection()};
    });
    await pagina.keyboard.press('End');
    await pagina.keyboard.press('Enter');
    await pagina.keyboard.type('repet');
    await pagina.keyboard.press('Enter');
    const bloco = await pagina.evaluate(() => document.querySelector('.CodeMirror').CodeMirror.getValue());
    await pagina.keyboard.type('xyz');
    const semLista = await pagina.locator('.CodeMirror-hints').count();
    confere('autocompletar: sugere, completa com o número selecionado e escreve o bloco "with" com o recuo',
      /^andar_cm/.test(sugeriu) && completou.linha === 'andar_cm(20)' && completou.selecionado === '20' &&
      bloco.endsWith('andar_cm(20)\nwith repetir(4):\n    ') && semLista === 0,
      JSON.stringify({sugeriu, completou, bloco: bloco.slice(-50), semLista}));

    // com a palavra inteira, o Enter só pula a linha (não troca por um nome mais comprido)
    const aoTeclarEnter = async (antes, digitado) => {
      await escrever(antes);
      await pagina.evaluate(() => { const cm = document.querySelector('.CodeMirror').CodeMirror; cm.focus(); cm.setCursor(cm.lineCount(), 0); });
      await pagina.keyboard.type(digitado);
      await pagina.keyboard.press('Enter');
      await pagina.keyboard.type('z');
      return (await pagina.evaluate(() => document.querySelector('.CodeMirror').CodeMirror.getValue())).slice(antes.length);
    };
    const trocados = [];
    for (const [antes, digitado] of [['erro = 0\nerro_anterior = 0\n', 'erro_anterior = erro'], ['vel = 1\nvelocidade = 2\n', 'y = vel'],
      ['luz = 1\n', 'y = luz'], ['velocidade = 1\ndef f(vel):\n    bip()\n', 'y = vel'], ['passo = 1\n', 'pass'],
      ['velocidade = 1\na, vel = 1, 2\n', 'y = vel'], ['bip()\n', 'contador']]) {
      const ficou = await aoTeclarEnter(antes, digitado);
      if (ficou.replace(/\n\s*/, '\n') !== `${digitado}\nz`) trocados.push(`${digitado} -> ${ficou}`);
    }
    confere('autocompletar: com a palavra inteira, o Enter não troca o nome', !trocados.length, JSON.stringify(trocados));

    // ---- blocos: trazer do Python e compilar de novo, com os mesmos bytes
    await escrever(PROGRAMA);
    await pagina.click('#abaBlocos');
    await pagina.locator('#areaBlocos .injectionDiv').waitFor({timeout: 60000});
    await limpar();
    await pagina.click('#btTrazer');
    const trouxe = await ultimaMensagem('ok', 'agora está em blocos');
    confere('o programa vira blocos, todas as linhas (a função em "Meus blocos")', trouxe.includes('Todas as linhas viraram blocos')
            && await pagina.locator('#areaBlocos .blocklyDraggable').count() > 5, trouxe);
    await limpar();
    await pagina.click('#btSimular');
    const okBlocos = await ultimaMensagem('ok', 'bytes');
    confere('os blocos compilam com os mesmos bytes do Python', bytesDe(okBlocos) === bytesPython, `${okBlocos} / Python ${bytesPython}`);
    await pagina.click('#btFecharSim');

    // ---- tela cheia: os blocos ocupam a janela (sem o topo e o painel), fica guardada e o botão volta
    const medir = () => pagina.evaluate(() => ({
      topo: getComputedStyle(document.querySelector('.topo')).display,
      largura: Math.round(100 * document.querySelector('.editor').getBoundingClientRect().width / innerWidth),
      blocos: Math.round(100 * document.getElementById('blockly').getBoundingClientRect().height / innerHeight),
      guardada: localStorage.getItem('est-tela-cheia')}));
    await pagina.click('#btExibir');
    await pagina.click('#btTelaCheia');
    await pagina.waitForTimeout(400);
    const cheia = await medir();
    await pagina.click('#btExibir');
    await pagina.click('#btTelaCheia');
    await pagina.waitForTimeout(400);
    const normal = await medir();
    confere('tela cheia: os blocos ocupam a janela, fica guardada e o botão volta', cheia.topo === 'none' && cheia.largura >= 97
            && cheia.blocos >= 80 && cheia.guardada === '1' && normal.topo !== 'none' && normal.guardada === '',
            JSON.stringify({cheia, normal}));

    // ---- link do programa: leva o modo blocos e o desafio aberto no simulador; quem abre vê o programa nele
    await pagina.evaluate(() => {
      const s = JSON.parse(localStorage.getItem('est-simulador-v1') || '{}');
      localStorage.setItem('est-simulador-v1', JSON.stringify({...s, desafio: 'quadrado'}));
    });
    await limpar();
    await pagina.click('#btExtras');
    await pagina.click('#btLink');
    const link = await pagina.locator('#mensagens input.link').inputValue();
    confere('o link do programa leva o modo blocos e o desafio aberto', link.includes('&modo=blocos') && link.includes('&desafio=quadrado'),
            link.slice(-80));
    await pagina.evaluate(() => localStorage.setItem('est-simulador-v1', '{}'));     // quem recebe não destravou o desafio 2
    const outra = await contexto.newPage();
    outra.on('dialog', d => d.accept());
    outra.setDefaultTimeout(30000);
    await outra.goto(link);
    await outra.locator('#sim').waitFor({state: 'visible', timeout: 150000});
    const quadro2 = outra.frameLocator('#quadroSim');
    await quadro2.locator('#cartaoDesafio:not([hidden])').waitFor();
    const noDesafio = await outra.frame({url: /simulador\/index\.html/}).evaluate(() => document.getElementById('desafio').value);
    confere('quem abre o link vê o programa nos blocos e no simulador, no desafio (mesmo sem ter destravado)',
            noDesafio === 'quadrado' && await outra.getAttribute('#abaBlocos', 'aria-selected') === 'true', noDesafio);
    await quadro2.locator('#btLinkDesafio').click();
    await quadro2.locator('#linkDesafio:not([hidden])').waitFor();
    const campo = quadro2.locator('#linkDesafio input');
    const doCartao = (await quadro2.locator('#linkDesafio').innerText()) + (await campo.count() ? await campo.inputValue() : '');
    confere('o botão do cartão do desafio dá o link do programa', /Link copiado|desafio=quadrado/.test(doCartao), doCartao.slice(0, 120));
    await outra.close();
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

    // ---- gravar a pista em vídeo: baixa um mp4 (ou webm) com alguma coisa dentro
    await pagina.click('#btGravar');
    await pagina.waitForTimeout(2000);
    const [video] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#btGravar')]);
    const arqVideo = path.join(os.tmpdir(), `video-teste-${process.pid}-${video.suggestedFilename()}`);
    await video.saveAs(arqVideo);
    const tamanho = fs.statSync(arqVideo).size;
    confere('"Gravar vídeo" baixa o vídeo da pista', /\.(mp4|webm)$/.test(video.suggestedFilename()) && tamanho > 5000,
            `${video.suggestedFilename()} ${tamanho} bytes`);
    fs.rmSync(arqVideo, {force: true});

    // ---- um seletor só para a pista ou o desafio, e o menu Opções
    const grupos = await pagina.$$eval('#onde optgroup', gs => gs.map(g => g.label));
    await pagina.selectOption('#onde', 'd:andar30');
    const noDesafio1 = await pagina.isVisible('#cartaoDesafio');
    await pagina.selectOption('#onde', 'p:oval');
    const naPista = await pagina.evaluate(() => ({cartao: !document.getElementById('cartaoDesafio').hidden,
                                                 pista: document.getElementById('pista').value, desafio: document.getElementById('desafio').value}));
    confere('"Pista ou desafio": grupos, entra no desafio e volta para uma pista',
            grupos.join('|') === 'Pistas para treinar|Arena da OBR|Feitas por você|Desafios' && noDesafio1
            && !naPista.cartao && naPista.pista === 'oval' && naPista.desafio === '', JSON.stringify({grupos, noDesafio1, naPista}));
    await pagina.click('#btOpcoes');
    const opcoes = await pagina.isVisible('#btZerar') && await pagina.isVisible('#somLigado');
    await pagina.keyboard.press('Escape');
    confere('menu Opções do simulador abre (som, ruído, projetor, progresso, professor) e fecha no Esc',
            opcoes && !(await pagina.isVisible('#btZerar')));

    await celular(navegador, base, erros);
    await roboNoUsb(navegador, base, erros);
  } catch (e) {
    confere('o teste chegou até o fim', false, e.message.split('\n').filter(l => l.trim()).slice(0, 3).join(' | '));
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
