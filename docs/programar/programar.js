'use strict';
/* Página de programar o robô EST pelo navegador: editor (aba Python) ou blocos (aba Blocos, modo_blocos.js),
   compilação com o Python do navegador (compilador.js + ponte.py, os mesmos arquivos do projeto),
   simulador (pasta simulador/) e envio pelo USB com WebHID (protocolo.js). */
(function () {
const P = globalThis.ESTProtocolo;
const CHAVE = 'est-programar-v1';
const LIMITE_MS = 20000;          // compilação mais longa que isso: laço do Python sem fim no programa

const INICIAL = `from robo import *

# Primeiro programa: ligue o robô no USB e clique em "Enviar ao robô".
# Se a luz acender, o robô apitar e aparecer "Funcionou!" na tela,
# o navegador está conversando com a controladora.
# Sem o robô, clique em "Simular" para ver o programa rodando aqui.
# Depois apague as linhas abaixo e escreva o seu programa aqui.

luz('azul')
tocar(440, 0.5)
mostrar('Funcionou!')
esperar(3)
apagar_luz()
`;

const $ = id => document.getElementById(id);
const escapar = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const temUsb = P.temWebHID();

// ---------------------------------------------------------------- o que fica guardado no navegador

function lerSalvo() {
  try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; } catch (e) { return {}; }
}
function salvar() {
  try {
    localStorage.setItem(CHAVE, JSON.stringify({fonte: editor.valor(), nome: $('nome').value, modo}));
    return true;
  } catch (e) { return false; }        // navegador sem armazenamento: só não guarda
}

// ---------------------------------------------------------------- editor (CodeMirror, ou a caixa de texto se ele não carregar)

function criarEditor(caixa, somenteLeitura = false) {
  if (!globalThis.CodeMirror) {
    caixa.readOnly = somenteLeitura;
    caixa.addEventListener('keydown', e => {           // Tab escreve 4 espaços, como no VS Code
      if (e.key !== 'Tab' || e.ctrlKey || e.altKey || e.metaKey) return;
      e.preventDefault();
      document.execCommand('insertText', false, '    ');
    });
    return {
      valor: () => caixa.value,
      trocar: t => { caixa.value = t; },
      aoMudar: f => caixa.addEventListener('input', f),
      marcarErro: n => {
        const linhas = caixa.value.split('\n');
        const ini = linhas.slice(0, n - 1).join('\n').length + (n > 1 ? 1 : 0);
        caixa.focus();
        caixa.setSelectionRange(ini, ini + (linhas[n - 1] || '').length);
      },
      limparErro: () => {},
      focar: () => caixa.focus(),
      atualizar: () => {},
    };
  }
  const cm = CodeMirror.fromTextArea(caixa, {
    mode: {name: 'python', version: 3}, lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
    matchBrackets: true, lineWrapping: window.matchMedia('(max-width: 600px)').matches, readOnly: somenteLeitura,
    extraKeys: {
      Tab: c => c.somethingSelected() ? c.indentSelection('add') : c.replaceSelection('    ', 'end'),
      'Shift-Tab': c => c.indentSelection('subtract'),
    },
  });
  let marcada = null;
  const limparErro = () => {
    if (marcada === null) return;
    cm.removeLineClass(marcada, 'background', 'linha-erro');
    cm.removeLineClass(marcada, 'gutter', 'linha-erro-num');
    marcada = null;
  };
  return {
    valor: () => cm.getValue(),
    trocar: t => { limparErro(); cm.setValue(t); cm.clearHistory(); },
    aoMudar: f => cm.on('change', f),
    marcarErro: n => {
      limparErro();
      const i = Math.min(Math.max(n - 1, 0), cm.lineCount() - 1);
      marcada = cm.getLineHandle(i);
      cm.addLineClass(marcada, 'background', 'linha-erro');
      cm.addLineClass(marcada, 'gutter', 'linha-erro-num');
      cm.scrollIntoView({line: i, ch: 0}, 80);
      cm.setCursor({line: i, ch: cm.getLine(i).length});
      cm.focus();
    },
    limparErro,
    focar: () => cm.focus(),
    atualizar: () => cm.refresh(),
  };
}

const salvo = lerSalvo();
let modo = 'python';                    // aba aberta: 'python' ou 'blocos'
const editor = criarEditor($('codigo'));
editor.trocar(typeof salvo.fonte === 'string' ? salvo.fonte : INICIAL);
if (typeof salvo.nome === 'string' && salvo.nome) $('nome').value = salvo.nome;

let espera = null;
editor.aoMudar(() => {
  editor.limparErro();
  clearTimeout(espera);
  espera = setTimeout(salvar, 400);
});

// o nome vira o nome do arquivo no robô (vscode/<nome>): só letras, números e _, até 20, como no enviar.py
const limparNome = t => t.replace(/\.py$/i, '').replace(/[^A-Za-z0-9_]/gu, '_').slice(0, 20) || 'meu_programa';
$('nome').addEventListener('change', () => { $('nome').value = limparNome($('nome').value); salvar(); });
const nomeDoArquivo = () => `${limparNome($('nome').value)}.py`;

// ---------------------------------------------------------------- mensagens

const caixaMsg = $('mensagens');
function limparMensagens() { caixaMsg.innerHTML = ''; }
function mensagem(tipo, titulo, corpo = '') {
  const div = document.createElement('div');
  div.className = `msg ${tipo}`;
  div.innerHTML = `<b>${titulo}</b>${corpo}`;
  caixaMsg.append(div);
  return div;
}
function mostrarSaida(texto) {
  if (texto && texto.trim()) mensagem('info', 'O programa imprimiu', `<pre>${escapar(texto.replace(/\s+$/, ''))}</pre>`);
}
function mostrarErro(r, arquivo) {
  const {linha, codigo, texto} = r.erro;
  const onde = linha ? ` na linha ${linha}` : '';
  const dosBlocos = r.modo === 'blocos' && blocos;
  const div = mensagem('erro', `ERRO${onde} de ${escapar(arquivo)}`,
    (codigo && codigo.trim() ? `<pre>${escapar(codigo.trim())}</pre>` : '') + `<p>${escapar(texto)}</p>` +
    (linha ? `<button class="bt pequeno" type="button">${dosBlocos ? 'Mostrar o bloco' : `Ir para a linha ${linha}`}</button>` : ''));
  if (linha) {
    const ir = dosBlocos ? () => { espelho.marcarErro(linha); blocos.mostrarLinha(linha, texto); }
                         : () => editor.marcarErro(linha);
    div.querySelector('button').addEventListener('click', ir);
    ir();
  }
  div.scrollIntoView({block: 'nearest'});
}

// ---------------------------------------------------------------- compilador (Python do navegador num worker)

let worker = null, workerPronto = null, pythonPronto = false, proximoId = 1;
const pedidos = new Map();

function estadoPython(classe, texto) {
  const p = $('estadoPython');
  p.className = `python ${classe}`;
  p.textContent = texto;
}

function iniciarCompilador() {
  pythonPronto = false;
  estadoPython('carregando', 'Preparando o Python do navegador… (na primeira vez demora um pouco)');
  const w = worker = new Worker('compilador.js');
  workerPronto = new Promise((ok, falha) => {
    w.onmessage = ({data}) => {
      if (data.pronto) {
        pythonPronto = true;
        estadoPython('pronto', 'Python pronto: compila aqui mesmo, sem instalar nada.');
        ok();
      } else if (data.falhaCarga) {
        falha(new Error(data.falhaCarga));
      } else {
        const pedido = pedidos.get(data.id);
        if (!pedido) return;
        pedidos.delete(data.id);
        clearTimeout(pedido.relogio);
        if (data.falha) pedido.falha(new Error(data.falha)); else pedido.ok(data.resultado);
      }
    };
    w.onerror = e => {
      e.preventDefault();
      falha(new Error(e.message || 'o Python do navegador parou'));
      pararCompilador(e.message || 'o Python do navegador parou');
      estadoPython('falhou', 'O Python do navegador parou: ele recomeça quando você compilar de novo.');
    };
  });
  workerPronto.catch(e => {
    estadoPython('falhou', 'Não consegui carregar o Python do navegador. Confira a internet e recarregue a página.');
    console.error(e);
    if (worker === w) { w.terminate(); worker = null; }
  });
}

function pararCompilador(motivo) {
  if (worker) worker.terminate();
  worker = null;
  pythonPronto = false;
  for (const [, pedido] of pedidos) { clearTimeout(pedido.relogio); pedido.falha(new Error(motivo)); }
  pedidos.clear();
}

/** Compila o programa do editor. Devolve o resultado de ponte.compilar (com erro ou com bytes). */
async function compilar() {
  if (!worker) iniciarCompilador();
  const fonte = fonteAtual(), nome = nomeDoArquivo(), daAba = modo;
  if (!pythonPronto) mensagem('info', 'Preparando o Python do navegador…', '<p>Na primeira vez demora alguns segundos.</p>');
  try {
    await workerPronto;
  } catch (e) {
    throw new Error('não consegui carregar o Python do navegador (precisa de internet). Confira a conexão e recarregue a página.');
  }
  return new Promise((ok, falha) => {
    const id = proximoId++;
    const relogio = setTimeout(() => {
      pedidos.delete(id);
      falha(Object.assign(new Error('demorou'), {demorou: true}));
      pararCompilador('o Python do navegador recomeçou');
      iniciarCompilador();
    }, LIMITE_MS);
    pedidos.set(id, {ok: r => ok(Object.assign(r, {fonte, nome, modo: daAba})), falha, relogio});
    worker.postMessage({id, fonte, nome});
  });
}

/** Os avisos do enviar.py para as portas sem nada ligado (do último programa compilado). [] se não der. */
function avisosDePortas(ligadas) {
  if (!worker || !pythonPronto) return Promise.resolve([]);
  return new Promise(ok => {
    const id = proximoId++;
    const relogio = setTimeout(() => { pedidos.delete(id); ok([]); }, 5000);
    pedidos.set(id, {ok, falha: () => ok([]), relogio});
    worker.postMessage({id, ligadas});
  });
}

/** Compila e mostra erros, avisos e o tamanho, como o enviar.py no terminal. Devolve o resultado ou null. */
async function compilarComMensagens() {
  if (modo === 'blocos') {
    try {
      await abrirBlocos();
    } catch (e) {
      limparMensagens();
      mensagem('erro', 'Os blocos não carregaram', '<p>Confira a internet e clique de novo na aba Blocos.</p>');
      return null;
    }
    blocos.limparAvisos();
    const falta = blocos.faltando();
    if (falta) {
      limparMensagens();
      mensagem('erro', 'Falta encaixar um bloco',
        `<p>O bloco <b>"${escapar(falta.texto)}"</b> tem um encaixe vazio. Encaixe uma comparação ou um valor nele.</p>`);
      blocos.mostrarBloco(falta.id, 'Falta encaixar um bloco aqui');
      return null;
    }
  }
  let r;
  try {
    r = await compilar();
  } catch (e) {
    limparMensagens();
    if (e.demorou) {
      mensagem('erro', 'O programa demorou demais para compilar',
        '<p>Ele tem um laço do Python que não termina (<code>while</code> ou <code>for</code>)? Para repetir no robô, use ' +
        '<code>with para_sempre():</code> ou <code>with repetir(4):</code>.</p>');
    } else {
      mensagem('erro', 'Não deu para compilar', `<p>${escapar(e.message)}</p>`);
    }
    return null;
  }
  limparMensagens();
  mostrarSaida(r.saida);
  if (r.erro) {
    mostrarErro(r, r.nome);
    return null;
  }
  editor.limparErro();
  if (espelho) espelho.limparErro();
  for (const aviso of r.avisos || []) mensagem('aviso', 'AVISO', `<p>${escapar(aviso)}</p>`);
  mensagem('ok', `${escapar(r.nome)}: ${r.bytes.length / 2} bytes`);
  return r;
}

// ---------------------------------------------------------------- simulador (pasta simulador/ num quadro)

const doisDigitos = n => String(n).padStart(2, '0');
function agora() {        // como o time.strftime('%d/%m/%Y %H:%M:%S') do simular.py
  const d = new Date();
  return `${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}/${d.getFullYear()} ` +
         `${doisDigitos(d.getHours())}:${doisDigitos(d.getMinutes())}:${doisDigitos(d.getSeconds())}`;
}

const quadro = $('quadroSim');
quadro.addEventListener('load', () => {
  let doc = null;
  try { doc = quadro.contentDocument; } catch (e) { /* outra origem */ }
  if (!doc || quadro.src === 'about:blank') return;
  for (const a of doc.querySelectorAll('a[href]')) a.target = '_top';     // links do simulador abrem fora do quadro
  quadro.focus();
});

function abrirSimulador(r) {
  window.ESTPROGRAMA = {nome: r.nome, gerado: agora(), bytes: r.bytes, fonte: r.fonte, linhas: r.linhas,
                        variaveis: r.variaveis, avisos: r.avisos};
  $('sim').hidden = false;
  document.documentElement.classList.add('travado');
  quadro.src = `simulador/index.html?${Date.now()}`;     // carrega de novo: o programa.js lê o ESTPROGRAMA
}

function fecharSimulador() {
  $('sim').hidden = true;
  document.documentElement.classList.remove('travado');
  quadro.src = 'about:blank';                             // para a simulação e o som
  $('btSimular').focus();
}
$('btFecharSim').addEventListener('click', fecharSimulador);
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('sim').hidden) fecharSimulador(); });

// ---------------------------------------------------------------- envio pelo USB (WebHID)

let ocupado = false;
function travar(sim) {
  ocupado = sim;
  for (const id of ['btSimular', 'btEnviar', 'btGravar']) $(id).disabled = sim;
}

async function atualizarRobo() {
  if (!temUsb) return;
  const p = $('estadoRobo');
  let d = null;
  try { d = await P.roboPermitido(); } catch (e) { /* sem permissão para listar */ }
  p.className = d ? 'robo ligado' : 'robo';
  p.textContent = d ? `Robô no USB${d.productName ? `: ${d.productName}` : ''}.`
                    : 'Na primeira vez o navegador pergunta qual é o robô.';
}

const ehLinux = () => /Linux/.test(navigator.userAgent) && !/CrOS|Android/.test(navigator.userAgent);

function explicarErroUsb(e) {
  const linux = ehLinux() ? ' No Linux, confira se o sistema libera o USB para o navegador (regra do udev para 0483:5750).' : '';
  if (e.name === 'SecurityError') return 'o navegador não deixou abrir a lista de dispositivos. Clique de novo em Enviar ao robô.';
  if (e.name === 'NotFoundError') return 'nenhum robô escolhido. Ligue o robô no USB, clique de novo e escolha o robô na lista.';
  if (e.etapa === 'abrir') {
    return 'não consegui abrir a conexão com o robô. Feche a IDE EST e outras abas que estejam usando o robô, ' +
           'tire e ponha o cabo USB e tente de novo.' + linux;
  }
  return `a conexão com o robô falhou (${e.message}). Confira o cabo e se o robô está ligado, e tente de novo.` + linux;
}

async function enviarAoRobo(executar) {
  if (ocupado) return;
  travar(true);
  try {
    limparMensagens();
    let r = null;
    if (pythonPronto) {          // compila antes de abrir a lista do navegador (ela precisa vir logo depois do clique)
      r = await compilarComMensagens();
      if (!r) return;
    }
    let robo = await P.roboPermitido();
    if (!robo) {
      const pedido = mensagem('info', 'Escolha o robô na janela do navegador', '<p>Depois clique em <b>Conectar</b>.</p>');
      try {
        robo = await P.escolherRobo();
        pedido.remove();
      } catch (e) {
        pedido.remove();
        mensagem('erro', 'Não enviei', `<p>${escapar(explicarErroUsb(e))}</p>`);
        return;
      }
      if (!robo) {
        mensagem('erro', 'Não enviei', '<p>Nenhum robô escolhido. Ligue o robô no USB, clique de novo e escolha o robô na lista.</p>');
        return;
      }
      atualizarRobo();
    }
    if (!r) {
      r = await compilarComMensagens();
      if (!r) return;
    }

    const bytes = Uint8Array.from(r.bytes.match(/../g) || [], h => parseInt(h, 16));
    const caminho = `/vscode/${r.nome_no_robo}`;
    const caixa = mensagem('info', 'Enviando ao robô…', '<div class="progresso"><i></i></div>');
    const barra = caixa.querySelector('.progresso i');
    const log = [];
    let respostas;
    try {
      if (!robo.opened) {
        try { await robo.open(); } catch (e) { e.etapa = 'abrir'; throw e; }
      }
      // como o enviar.py: avisa se o programa usa uma porta em que o robô não tem nada ligado
      let ligadas = null;
      try { ligadas = await P.portasLigadas(robo); } catch (e) { console.warn(e); }
      for (const aviso of ligadas ? await avisosDePortas(ligadas) : []) {
        caixa.before(mensagem('aviso', 'AVISO', `<p>${escapar(aviso)}</p>`));
      }
      respostas = await P.enviar(robo, bytes, caminho, executar, passo => {
        barra.style.width = `${Math.round(100 * passo.passo / passo.total)}%`;
        log.push(`${passo.nome.padEnd(20)} tx=${passo.tx}...  rx=${passo.rx || '(sem resposta)'}`);
      });
    } catch (e) {
      caixa.remove();
      mensagem('erro', 'O envio não terminou', `<p>${escapar(explicarErroUsb(e))}</p>`);
      console.error(e);
      return;
    }
    caixa.remove();
    const detalhes = `<details class="detalhes"><summary>Detalhes do envio</summary><pre>${escapar(log.join('\n'))}</pre></details>`;
    if (!respostas) {
      mensagem('aviso', 'O robô não respondeu',
        '<p>Os pacotes foram enviados, mas o robô não respondeu nenhum. Confira se ele está ligado e se a IDE EST está ' +
        'fechada, e tente de novo.</p>' + detalhes);
    } else if (executar) {
      mensagem('ok', 'Enviado!', '<p>O programa já está rodando no robô.</p>' + detalhes);
    } else {
      mensagem('ok', 'Gravado no robô', `<p>Gravado como <code>vscode/${escapar(r.nome_no_robo)}</code>: inicie pelo menu do robô.</p>` + detalhes);
    }
  } catch (e) {
    mensagem('erro', 'Não enviei', `<p>${escapar(explicarErroUsb(e))}</p>`);
    console.error(e);
  } finally {
    travar(false);
  }
}

// ---------------------------------------------------------------- botões e atalhos

async function simular() {
  if (ocupado) return;
  travar(true);
  try {
    const r = await compilarComMensagens();
    if (r) abrirSimulador(r);
  } finally {
    travar(false);
  }
}

$('btSimular').addEventListener('click', simular);
if (temUsb) {
  $('btEnviar').addEventListener('click', () => enviarAoRobo(true));
  $('btGravar').addEventListener('click', () => enviarAoRobo(false));
  navigator.hid.addEventListener('connect', atualizarRobo);
  navigator.hid.addEventListener('disconnect', atualizarRobo);
  atualizarRobo();
} else {
  $('blocoEnvio').hidden = true;
  $('semUsb').hidden = false;
}

function guardarAgora() {
  if (blocos) blocos.salvar();
  $('guardado').textContent = salvar() ? 'Guardado neste navegador.' : 'Este navegador não deixa guardar: use Baixar .py.';
}
document.addEventListener('keydown', e => {           // Ctrl+S guarda; Ctrl+Shift+B envia, como no VS Code
  if (!(e.ctrlKey || e.metaKey) || e.altKey || !$('sim').hidden) return;
  const tecla = e.key.toLowerCase();
  if (tecla === 's' && !e.shiftKey) { e.preventDefault(); guardarAgora(); }
  if (tecla === 'b' && e.shiftKey) { e.preventDefault(); temUsb ? enviarAoRobo(true) : simular(); }
});

// arquivos: baixar e abrir
$('btBaixar').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([fonteAtual()], {type: 'text/x-python'}));
  const a = Object.assign(document.createElement('a'), {href: url, download: nomeDoArquivo()});
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$('btAbrir').addEventListener('click', () => $('arquivo').click());
$('arquivo').addEventListener('change', async () => {
  const arq = $('arquivo').files[0];
  $('arquivo').value = '';
  if (!arq) return;
  trocarPrograma(await arq.text(), arq.name);
});

function trocarPrograma(texto, nome) {
  editor.trocar(texto.replace(/\r\n?/g, '\n'));
  $('nome').value = limparNome(nome);
  trocarModo('python');
  editor.focar();
}

// exemplos (lista gravada por ferramentas/publicar_programar.py)
const exemplos = [{arquivo: '', titulo: 'Primeiro programa (luz, som e Funcionou!)', nome: 'meu_programa'}];
fetch('projeto/arquivos.json', {cache: 'no-cache'}).then(r => r.json()).then(lista => {
  exemplos.push(...(lista.exemplos || []));
}).catch(() => { /* sem a lista: fica só o primeiro programa */ }).finally(() => {
  $('exemplo').innerHTML = '<option value="">Escolha…</option>' +
    exemplos.map((e, i) => `<option value="${i}">${escapar(e.titulo)}</option>`).join('');
});
$('exemplo').addEventListener('change', async () => {
  const e = exemplos[$('exemplo').value];
  $('exemplo').value = '';
  if (!e) return;
  const atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() &&
      !confirm(`Trocar o programa do editor por "${e.titulo}"? O que está escrito agora some (use Baixar .py para guardar).`)) return;
  if (!e.arquivo) { trocarPrograma(INICIAL, e.nome); return; }
  try {
    const r = await fetch(`exemplos/${e.arquivo}`, {cache: 'no-cache'});
    if (!r.ok) throw new Error(r.status);
    trocarPrograma(await r.text(), e.arquivo);
  } catch (erro) {
    limparMensagens();
    mensagem('erro', 'Não consegui abrir o exemplo', '<p>Confira a internet e tente de novo.</p>');
  }
});

// ---------------------------------------------------------------- abas Python | Blocos

let blocos = null, espelho = null, abrindo = null;

/** Baixa o Blockly (só na primeira vez) e monta a área de blocos, com o Python gerado ao lado. */
function abrirBlocos() {
  if (!abrindo) {
    espelho = espelho || criarEditor($('pythonBlocos'), true);
    $('blockly').innerHTML = '<p class="carregando">Carregando os blocos…</p>';
    abrindo = globalThis.ESTBlocos.criar($('blockly'), codigo => espelho.trocar(codigo)).then(api => { blocos = api; });
    abrindo.catch(e => {
      console.error(e);
      abrindo = null;
      $('blockly').innerHTML = '<p class="carregando">Não consegui carregar os blocos. Confira a internet e clique de novo na aba Blocos.</p>';
    });
  }
  return abrindo;
}

const fonteAtual = () => (modo === 'blocos' && blocos ? blocos.codigo() : editor.valor());

async function trocarModo(novo) {
  modo = novo;
  for (const [aba, area, m] of [['abaPython', 'areaPython', 'python'], ['abaBlocos', 'areaBlocos', 'blocos']]) {
    $(aba).setAttribute('aria-selected', String(m === novo));
    $(area).hidden = m !== novo;
  }
  salvar();
  if (novo === 'python') { editor.atualizar(); return; }
  try {
    await abrirBlocos();
    espelho.atualizar();
    blocos.redimensionar();
  } catch (e) { /* a mensagem já está na área de blocos */ }
}
$('abaPython').addEventListener('click', () => trocarModo('python'));
$('abaBlocos').addEventListener('click', () => trocarModo('blocos'));

$('btLevar').addEventListener('click', () => {
  if (!blocos) return;
  const codigo = blocos.codigo(), atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() && atual !== codigo.trim() &&
      !confirm('O programa da aba Python vai ser trocado pelo Python dos blocos. Continuar?')) return;
  editor.trocar(codigo);
  trocarModo('python');
  editor.focar();
});

if (salvo.modo === 'blocos') trocarModo('blocos');

// o link "Como enviar" (#ajuda) abre a caixa de ajuda
for (const a of document.querySelectorAll('a[href="#ajuda"]')) a.addEventListener('click', () => { $('ajuda').open = true; });
if (location.hash === '#ajuda') $('ajuda').open = true;

iniciarCompilador();
})();
