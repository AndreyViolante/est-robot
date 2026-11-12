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

/** Um trecho do teclado de programação, pronto para inserir: a quebra de linha ganha o recuo da linha atual e
    o que está entre « » fica selecionado (para o aluno já digitar por cima). */
function prepararTrecho(modelo, recuo) {
  const texto = modelo.replace(/\n/g, '\n' + recuo);
  const ini = texto.indexOf('«'), fim = texto.indexOf('»');
  return {texto: texto.replace(/[«»]/g, ''), selecao: ini >= 0 && fim > ini ? [ini, fim - 1] : null};
}

function criarEditor(caixa, somenteLeitura = false) {
  if (!globalThis.CodeMirror) {
    const inserir = modelo => {
      const v = caixa.value, a = caixa.selectionStart, b = caixa.selectionEnd;
      const inicioDaLinha = v.lastIndexOf('\n', a - 1) + 1;
      const {texto, selecao} = prepararTrecho(modelo, v.slice(inicioDaLinha).match(/^[ \t]*/)[0]);
      caixa.setRangeText(texto, a, b, 'end');
      if (selecao) caixa.setSelectionRange(a + selecao[0], a + selecao[1]);
      caixa.dispatchEvent(new Event('input'));
      caixa.focus();
    };
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
      irPara: n => {
        const linhas = caixa.value.split('\n');
        const ini = linhas.slice(0, n - 1).join('\n').length + (n > 1 ? 1 : 0);
        caixa.focus();
        caixa.setSelectionRange(ini, ini + (linhas[n - 1] || '').length);
      },
      focar: () => caixa.focus(),
      atualizar: () => {},
      inserir,
      comando: nome => {
        if (nome === 'desfazer' || nome === 'refazer') document.execCommand(nome === 'desfazer' ? 'undo' : 'redo');
        else if (nome === 'indentar') inserir('    ');
        caixa.focus();
      },
      aoFocar: f => caixa.addEventListener('focus', f),
      aoSair: f => caixa.addEventListener('blur', f),
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
    irPara: n => {                      // leva o cursor para a linha (de um aviso), sem marcar como erro
      const i = Math.min(Math.max(n - 1, 0), cm.lineCount() - 1);
      cm.scrollIntoView({line: i, ch: 0}, 80);
      cm.setSelection({line: i, ch: cm.getLine(i).match(/^\s*/)[0].length}, {line: i, ch: cm.getLine(i).length});
      cm.focus();
    },
    focar: () => cm.focus(),
    atualizar: () => cm.refresh(),
    inserir: modelo => {
      const de = cm.getCursor('from');
      const {texto, selecao} = prepararTrecho(modelo, cm.getLine(de.line).match(/^\s*/)[0]);
      cm.replaceSelection(texto);
      if (selecao) {
        const pos = i => cm.posFromIndex(cm.indexFromPos(de) + i);
        cm.setSelection(pos(selecao[0]), pos(selecao[1]));
      }
      cm.focus();
    },
    comando: nome => {
      cm.execCommand({indentar: 'indentMore', desindentar: 'indentLess', desfazer: 'undo', refazer: 'redo'}[nome]);
      cm.focus();
    },
    aoFocar: f => cm.on('focus', f),
    aoSair: f => cm.on('blur', f),
  };
}

const salvo = lerSalvo();
const versoes = globalThis.ESTVersoes.criar();          // versões do programa (versoes.js, mais abaixo)
let modo = 'python';                    // aba aberta: 'python' ou 'blocos'
const editor = criarEditor($('codigo'));
editor.trocar(typeof salvo.fonte === 'string' ? salvo.fonte : INICIAL);
if (typeof salvo.nome === 'string' && salvo.nome) $('nome').value = salvo.nome;

let espera = null;
editor.aoMudar(() => {
  editor.limparErro();
  clearTimeout(espera);
  espera = setTimeout(() => { salvar(); versaoEnquantoEscreve(); }, 400);
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
/** Um aviso do avisos.py (variável sem uso, laço sem espera, motor ligado no fim): não impede de enviar. */
function mostrarAviso(a, r) {
  const dosBlocos = r.modo === 'blocos' && blocos;
  const div = mensagem('aviso', `AVISO${a.linha ? ` na linha ${a.linha}` : ''}`,
    (a.codigo ? `<pre>${escapar(a.codigo)}</pre>` : '') + `<p>${escapar(a.texto)}</p>` +
    `<p><b>Como arrumar:</b> ${escapar(a.arrumar)}</p>` +
    (a.linha ? `<button class="bt pequeno" type="button">${dosBlocos ? 'Mostrar o bloco' : `Ir para a linha ${a.linha}`}</button>` : ''));
  if (a.linha) {
    div.querySelector('button').addEventListener('click', dosBlocos
      ? () => blocos.mostrarLinha(a.linha, a.texto) : () => editor.irPara(a.linha));
  }
}
/** Os avisos numa linha de texto cada um, como o simulador mostra (avisos.como_texto). */
const avisosEmTexto = r => [...(r.avisos || []), ...(r.avisos_do_codigo || []).map(a =>
  `${a.linha ? `linha ${a.linha}: ` : ''}${a.texto} Como arrumar: ${a.arrumar}`)];

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
async function compilarComMensagens(motivo = 'compilou') {
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
  for (const aviso of r.avisos_do_codigo || []) mostrarAviso(aviso, r);
  guardarVersao(motivo, {fonte: r.fonte, nome: limparNome(r.nome), modo: r.modo,
                         blocos: r.modo === 'blocos' && blocos ? blocos.estado() : null});
  mensagem('ok', `${escapar(r.nome)}: ${r.bytes.length / 2} bytes`, r.espaco ? `<p>${escapar(r.espaco)}</p>` : '');
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
                        variaveis: r.variaveis, avisos: avisosEmTexto(r)};
  mostrarTeclado(false);
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

// "Levar para o código" do Dirigir, no simulador: o caminho feito com as setas vira o programa do editor
window.ESTDoSimulador = codigo => {
  const atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() && atual !== codigo.trim() &&
      !confirm('Trocar o programa do editor pelo caminho que você fez dirigindo o robô? O que está escrito agora some ' +
               '(clique em Cancelar e use Baixar .py antes, se quiser guardar).')) return;
  fecharSimulador();
  trocarPrograma(codigo, $('nome').value);
  salvar();
  limparMensagens();
  mensagem('ok', 'Programa escrito dirigindo o robô',
    '<p>Aperte <b>Simular</b> para ver o robô fazer o mesmo caminho sozinho. Depois é só mudar os números.</p>');
};
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('sim').hidden) fecharSimulador(); });

// ---------------------------------------------------------------- envio pelo USB (WebHID)

let ocupado = false;
function travar(sim) {
  ocupado = sim;
  for (const id of ['btSimular', 'btEnviar', 'btGravar', 'btBluetooth', 'btGravarBluetooth']) $(id).disabled = sim;
}

const bytesDoPrograma = r => Uint8Array.from(r.bytes.match(/../g) || [], h => parseInt(h, 16));
const detalhesDoEnvio = log => `<details class="detalhes"><summary>Detalhes do envio</summary><pre>${escapar(log.join('\n'))}</pre></details>`;

/** Como o enviar.py termina: diz se o robô respondeu, se já está rodando ou onde ficou gravado. */
function mostrarResultado(respostas, executar, r, log, via) {
  const detalhes = detalhesDoEnvio(log);
  if (!respostas) {
    mensagem('aviso', 'O robô não respondeu',
      `<p>Os pacotes foram enviados ${via}, mas o robô não respondeu nenhum. Confira se ele está ligado e se a IDE EST ` +
      'está fechada, e tente de novo.</p>' + detalhes);
  } else if (executar) {
    mensagem('ok', 'Enviado!', '<p>O programa já está rodando no robô.</p>' + detalhes);
  } else {
    mensagem('ok', 'Gravado no robô', `<p>Gravado como <code>vscode/${escapar(r.nome_no_robo)}</code>: inicie pelo menu do robô.</p>` + detalhes);
  }
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
      r = await compilarComMensagens(executar ? 'enviou ao robô' : 'gravou no robô');
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
      r = await compilarComMensagens(executar ? 'enviou ao robô' : 'gravou no robô');
      if (!r) return;
    }

    const bytes = bytesDoPrograma(r);
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
    mostrarResultado(respostas, executar, r, log, 'pelo USB');
  } catch (e) {
    mensagem('erro', 'Não enviei', `<p>${escapar(explicarErroUsb(e))}</p>`);
    console.error(e);
  } finally {
    travar(false);
  }
}

// ---------------------------------------------------------------- envio pelo Bluetooth (Web Serial: Chrome do Android)

const temBluetooth = P.temWebSerial();

function explicarErroBluetooth(e) {
  if (e.name === 'NotFoundError') {
    return 'nenhum robô escolhido. Pareie o robô nas configurações de Bluetooth do aparelho (a senha costuma ser 1234), ' +
           'clique de novo e escolha o robô na lista.';
  }
  if (e.name === 'SecurityError') return 'o navegador não deixou abrir a lista do Bluetooth. Clique de novo em Enviar por Bluetooth.';
  if (e.etapa === 'abrir' || e.name === 'NetworkError') {
    return 'não consegui conectar ao robô pelo Bluetooth. Confira se ele está ligado e perto, com o Bluetooth ligado e ' +
           'pareado com este aparelho, e se nenhum outro aparelho está conectado a ele.';
  }
  return `a conexão pelo Bluetooth caiu (${e.message}). Chegue mais perto do robô e tente de novo.`;
}

async function enviarPorBluetooth(executar) {
  if (ocupado) return;
  travar(true);
  let canal = null;
  try {
    limparMensagens();
    let r = null;
    if (pythonPronto) {          // compila antes de abrir a lista do navegador (ela precisa vir logo depois do clique)
      r = await compilarComMensagens(executar ? 'enviou pelo Bluetooth' : 'gravou pelo Bluetooth');
      if (!r) return;
    }
    let porta = await P.portaBluetoothPermitida();
    if (!porta) {
      const pedido = mensagem('info', 'Escolha o robô na janela do navegador', '<p>Só aparecem os aparelhos já pareados.</p>');
      try {
        porta = await P.escolherPortaBluetooth();
      } catch (e) {
        mensagem('erro', 'Não enviei', `<p>${escapar(explicarErroBluetooth(e))}</p>`);
        return;
      } finally {
        pedido.remove();
      }
    }
    if (!r) {
      r = await compilarComMensagens(executar ? 'enviou pelo Bluetooth' : 'gravou pelo Bluetooth');
      if (!r) return;
    }
    const caixa = mensagem('info', 'Conectando pelo Bluetooth…', '<div class="progresso"><i></i></div>');
    const barra = caixa.querySelector('.progresso i');
    const log = [];
    let respostas;
    try {
      try { canal = await P.abrirCanalBluetooth(porta); } catch (e) { e.etapa = 'abrir'; throw e; }
      log.push(`${'APRESENTAÇÃO'.padEnd(20)} rx=${canal.apresentacao || '(sem resposta)'}`);
      caixa.querySelector('b').textContent = 'Enviando pelo Bluetooth…';
      let ligadas = null;
      try { ligadas = await P.consultarPortas(canal); } catch (e) { console.warn(e); }
      for (const aviso of ligadas ? await avisosDePortas(ligadas) : []) {
        caixa.before(mensagem('aviso', 'AVISO', `<p>${escapar(aviso)}</p>`));
      }
      respostas = await P.enviarPorCanal(canal, bytesDoPrograma(r), `/vscode/${r.nome_no_robo}`, executar, passo => {
        barra.style.width = `${Math.round(100 * passo.passo / passo.total)}%`;
        log.push(`${passo.nome.padEnd(20)} tx=${passo.tx}...  rx=${passo.rx || '(sem resposta)'}`);
      });
    } catch (e) {
      caixa.remove();
      mensagem('erro', 'O envio pelo Bluetooth não terminou',
        `<p>${escapar(explicarErroBluetooth(e))}</p>` + (log.length ? detalhesDoEnvio(log) : ''));
      console.error(e);
      return;
    }
    caixa.remove();
    mostrarResultado(respostas, executar, r, log, 'pelo Bluetooth');
    $('estadoBluetooth').className = respostas ? 'robo ligado' : 'robo';
    $('estadoBluetooth').textContent = respostas ? 'O robô respondeu pelo Bluetooth.' : 'O robô não respondeu pelo Bluetooth.';
  } catch (e) {
    mensagem('erro', 'Não enviei', `<p>${escapar(explicarErroBluetooth(e))}</p>`);
    console.error(e);
  } finally {
    if (canal) await canal.fechar().catch(() => {});
    travar(false);
  }
}

// ---------------------------------------------------------------- botões e atalhos

async function simular() {
  if (ocupado) return;
  travar(true);
  try {
    const r = await compilarComMensagens('simulou');
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
}
if (temBluetooth) {
  $('blocoBluetooth').hidden = false;
  $('btBluetooth').addEventListener('click', () => enviarPorBluetooth(true));
  $('btGravarBluetooth').addEventListener('click', () => enviarPorBluetooth(false));
  if (temUsb) {          // no computador o USB vem primeiro: o Bluetooth fica como segunda opção, mais discreto
    $('btBluetooth').classList.remove('principal', 'azul', 'grande');
    $('btBluetooth').textContent = 'ᛒ Enviar';
    $('blocoBluetooth').classList.add('secundario');
  }
}
if (!temUsb && !temBluetooth) $('semUsb').hidden = false;

function guardarAgora() {
  if (blocos) blocos.salvar();
  guardarVersao('Ctrl+S');
  $('guardado').textContent = salvar() ? 'Guardado neste navegador.' : 'Este navegador não deixa guardar: use Baixar .py.';
}
document.addEventListener('keydown', e => {           // Ctrl+S guarda; Ctrl+Shift+B envia, como no VS Code
  if (!(e.ctrlKey || e.metaKey) || e.altKey || !$('sim').hidden) return;
  const tecla = e.key.toLowerCase();
  if (tecla === 's' && !e.shiftKey) { e.preventDefault(); guardarAgora(); }
  if (tecla === 'b' && e.shiftKey) { e.preventDefault(); temUsb ? enviarAoRobo(true) : temBluetooth ? enviarPorBluetooth(true) : simular(); }
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
  if (/\.est$/i.test(arq.name)) { abrirEst(arq); return; }
  trocarPrograma(await arq.text(), arq.name);
});

/** Um pedido ao Python do navegador (o worker do compilador.js) que não é a compilação de sempre. */
async function pedirAoPython(mensagemDoPedido) {
  if (!worker) iniciarCompilador();
  if (!pythonPronto) mensagem('info', 'Preparando o Python do navegador…', '<p>Na primeira vez demora alguns segundos.</p>');
  await workerPronto;
  return new Promise((ok, falha) => {
    const id = proximoId++;
    const relogio = setTimeout(() => { pedidos.delete(id); falha(new Error('o Python do navegador demorou demais')); }, LIMITE_MS);
    pedidos.set(id, {ok, falha, relogio});
    worker.postMessage(Object.assign({id}, mensagemDoPedido));
  });
}

/** Traduz um projeto da IDE EST (.est) para Python, com o Python do navegador (importar_est.py). */
const importarEst = (texto, nome) => pedirAoPython({est: texto, nome});

// o programa no formato da IDE EST (exportar_est.py): baixa um .est para abrir na IDE
$('btSalvarEst').addEventListener('click', async () => {
  limparMensagens();
  let r;
  try {
    r = await pedirAoPython({paraEst: fonteAtual(), nome: nomeDoArquivo()});
  } catch (e) {
    r = {erro: e.message};
  }
  if (r.erro) {
    mensagem('erro', `Não deu para salvar para a IDE${r.linha ? ` (linha ${r.linha})` : ''}`,
      (r.codigo && r.codigo.trim() ? `<pre>${escapar(r.codigo.trim())}</pre>` : '') + `<p>${escapar(r.erro)}</p>`);
    return;
  }
  const nome = nomeDoArquivo().replace(/\.py$/, '.est');
  const url = URL.createObjectURL(new Blob([r.est], {type: 'application/octet-stream'}));
  const a = Object.assign(document.createElement('a'), {href: url, download: nome});
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  mensagem(r.iguais ? 'ok' : 'aviso', `Salvo para a IDE EST: ${escapar(nome)}`,
    (r.iguais ? '<p>Lido de volta, o .est tem os mesmos blocos e dá os mesmos bytes que o EST-LAB manda para o robô.</p>'
              : '<p>Lido de volta, o .est não deu os mesmos bytes: confira o programa na IDE antes de enviar.</p>') +
    '<p>Na IDE EST: Arquivo → Abrir e escolha o arquivo. Ao enviar, a IDE grava por cima do arquivo aberto.</p>');
});

async function abrirEst(arq) {
  limparMensagens();
  let r;
  try {
    r = await importarEst(await arq.text(), arq.name);
  } catch (e) {
    r = {erro: e.message};
  }
  if (r.erro) {
    mensagem('erro', 'Não consegui abrir o projeto da IDE', `<p>${escapar(r.erro)}</p>`);
    return;
  }
  const p = r.programas[0], atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() &&
      !confirm(`Trocar o programa do editor pelo "${p.nome}" do projeto da IDE? O que está escrito agora some ` +
               '(clique em Cancelar e use Baixar .py antes, se quiser guardar).')) return;
  trocarPrograma(p.codigo, p.nome);
  salvar();
  limparMensagens();
  const estado = p.exata ? 'Tradução exata: o Python gera os mesmos bytes que a IDE manda para o robô.'
    : p.exata === null ? 'Traduzido, mas algum bloco deste programa ainda não tem comando no EST-LAB (veja os comentários no código).'
      : 'Tradução aproximada: faz o mesmo, com alguns blocos diferentes.';
  mensagem(p.exata ? 'ok' : 'aviso', `Programa "${escapar(p.nome)}" da IDE, agora em Python`,
    `<p>${estado}</p>` + (p.avisos.length ? `<ul>${p.avisos.map(a => `<li>${escapar(a)}</li>`).join('')}</ul>` : '') +
    (r.programas.length > 1 ? `<p>O projeto tem mais ${r.programas.length - 1} programa(s): abri o primeiro.</p>` : '') +
    '<p>Aperte <b>Simular</b> para ver rodando.</p>');
}

function trocarPrograma(texto, nome) {
  guardarVersao('antes de abrir outro programa', {fonte: editor.valor(), nome: limparNome($('nome').value), modo: 'python'});
  editor.trocar(texto.replace(/\r\n?/g, '\n'));
  $('nome').value = limparNome(nome);
  trocarModo('python');
  editor.focar();
}

// ---------------------------------------------------------------- compartilhar por link
// O programa vai comprimido dentro do próprio link, depois do # (essa parte nunca vai para o servidor):
// #programa=<z ou t><base64url>&nome=<nome>. z = comprimido (deflate), t = texto puro (navegador sem compressão).

function paraBase64url(bytes) {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const deBase64url = t => Uint8Array.from(atob(t.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
const passarPor = async (bytes, fluxo) =>
  new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(fluxo)).arrayBuffer());

async function linkDoPrograma(fonte, nome) {
  let dados = new TextEncoder().encode(fonte), tipo = 't';
  if (globalThis.CompressionStream) { dados = await passarPor(dados, new CompressionStream('deflate-raw')); tipo = 'z'; }
  const url = new URL(location.href);
  url.hash = `programa=${tipo}${paraBase64url(dados)}&nome=${encodeURIComponent(nome)}`;
  return url.href;
}

async function programaDoLink(hash) {
  const p = new URLSearchParams(hash.replace(/^#/, ''));
  const valor = p.get('programa') || '';
  let dados = deBase64url(valor.slice(1));
  if (valor[0] === 'z') dados = await passarPor(dados, new DecompressionStream('deflate-raw'));
  else if (valor[0] !== 't') throw new Error('link sem programa');
  return {fonte: new TextDecoder('utf-8', {fatal: true}).decode(dados), nome: p.get('nome') || 'meu_programa'};
}

$('btLink').addEventListener('click', async () => {
  limparMensagens();
  let link;
  try {
    link = await linkDoPrograma(fonteAtual(), limparNome($('nome').value));
  } catch (e) {
    mensagem('erro', 'Não consegui criar o link', '<p>Use <b>Baixar .py</b> e mande o arquivo.</p>');
    return;
  }
  let copiou = false;
  try { await navigator.clipboard.writeText(link); copiou = true; } catch (e) { /* sem permissão: o link fica na caixa */ }
  const div = mensagem('ok', copiou ? 'Link copiado!' : 'Link do programa',
    `<p>${copiou ? 'Cole no WhatsApp ou no e-mail.' : 'Copie o link abaixo.'} Quem abrir vê este programa e o simulador.
     O programa vai dentro do próprio link: não fica guardado em nenhum servidor.</p>
     <input class="link" type="text" readonly aria-label="Link do programa" value="${escapar(link)}">` +
    (link.length > 8000 ? '<p>O programa é grande: se o link não abrir do outro lado, use <b>Baixar .py</b>.</p>' : ''));
  const caixa = div.querySelector('input');
  caixa.addEventListener('focus', () => caixa.select());
});

async function abrirDoLink() {
  if (!location.hash.startsWith('#programa=')) return;
  let veio;
  try {
    veio = await programaDoLink(location.hash);
  } catch (e) {
    limparMensagens();
    mensagem('erro', 'O link do programa veio cortado', '<p>Peça para mandarem de novo (o link inteiro) ou o arquivo .py.</p>');
    return;
  } finally {
    history.replaceState(null, '', location.pathname + location.search);     // recarregar não abre de novo
  }
  const atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() && atual !== veio.fonte.trim() &&
      !confirm(`Abrir o programa "${limparNome(veio.nome)}" que veio no link? O que está no editor agora some ` +
               '(clique em Cancelar e use Baixar .py antes, se quiser guardar).')) return;
  trocarPrograma(veio.fonte, veio.nome);
  salvar();
  limparMensagens();
  mensagem('info', `Programa "${escapar(limparNome(veio.nome))}" aberto do link`, '<p>Abrindo o simulador…</p>');
  simular();
}
window.addEventListener('hashchange', abrirDoLink);       // link colado com a página já aberta

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
    abrindo = globalThis.ESTBlocos.criar($('blockly'), codigo => {
      espelho.trocar(codigo);
      if (blocos && modo === 'blocos') versaoEnquantoEscreve();
    }).then(api => { blocos = api; });
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

/** O Python como área de blocos, com o Python do navegador (para_blocos.py). */
async function blocosDoPython(fonte) {
  if (!worker) iniciarCompilador();
  if (!pythonPronto) mensagem('info', 'Preparando o Python do navegador…', '<p>Na primeira vez demora alguns segundos.</p>');
  await workerPronto;
  return new Promise((ok, falha) => {
    const id = proximoId++;
    const relogio = setTimeout(() => { pedidos.delete(id); falha(new Error('o Python do navegador demorou demais')); }, LIMITE_MS);
    pedidos.set(id, {ok, falha, relogio});
    worker.postMessage({id, blocosDe: fonte});
  });
}

$('btTrazer').addEventListener('click', async () => {
  try {
    await abrirBlocos();
  } catch (e) {
    return;                       // a mensagem já está na área de blocos
  }
  limparMensagens();
  let r;
  try {
    r = await blocosDoPython(editor.valor());
  } catch (e) {
    r = {erro: e.message};
  }
  limparMensagens();
  if (r.erro) {
    mensagem('erro', 'Não deu para trazer o Python', `<p>${escapar(r.erro)}</p>`);
    return;
  }
  const atual = blocos.codigo().trim();
  if (atual !== 'from robo import *' && atual !== editor.valor().trim() &&
      !confirm('Os blocos vão ser trocados pelo programa da aba Python. Continuar?')) return;
  guardarVersao('antes de trazer do Python', {fonte: blocos.codigo(), nome: limparNome($('nome').value), modo: 'blocos',
                                               blocos: blocos.estado()});
  blocos.carregar(r.estado);
  mensagem(r.python ? 'aviso' : 'ok', 'O programa da aba Python agora está em blocos',
    r.python ? `<p>${r.python === 1 ? '1 linha ainda não tem bloco e ficou' : `${r.python} linhas ainda não têm bloco e ficaram`} ` +
               'num bloco cinza "Python", com o texto como está: o programa faz o mesmo.</p>'
             : '<p>Todas as linhas viraram blocos.</p>');
});

$('btLevar').addEventListener('click', () => {
  if (!blocos) return;
  const codigo = blocos.codigo(), atual = editor.valor().trim();
  if (atual && atual !== INICIAL.trim() && atual !== codigo.trim() &&
      !confirm('O programa da aba Python vai ser trocado pelo Python dos blocos. Continuar?')) return;
  guardarVersao('antes de levar os blocos para o Python', {fonte: editor.valor(), nome: limparNome($('nome').value),
                                                         modo: 'python'});
  editor.trocar(codigo);
  trocarModo('python');
  editor.focar();
});

// no celular, quem abre a página pela primeira vez começa nos blocos (digitar Python na tela pequena é difícil)
const telaPequena = () => window.matchMedia('(max-width: 600px)').matches;
if (salvo.modo === 'blocos' || (!salvo.modo && typeof salvo.fonte !== 'string' && telaPequena())) trocarModo('blocos');

// ---------------------------------------------------------------- versões do programa (versoes.js)
// Guardadas neste navegador: quando simula ou envia, no Ctrl+S, antes de abrir outro programa e, enquanto o aluno
// escreve, de tempos em tempos. A lista deixa ver cada uma e voltar para ela.

const ENQUANTO_ESCREVE_MS = 5 * 60 * 1000;      // escrevendo: uma versão nova a cada 5 minutos, no máximo
const NOMES_MOTIVO = {'Ctrl+S': 'guardou (Ctrl+S)'};

/** O programa de agora: o Python do editor, ou os blocos (com o Python deles) na aba Blocos. */
function estadoAtual() {
  const nome = limparNome($('nome').value);
  if (modo === 'blocos' && blocos) return {fonte: blocos.codigo(), nome, modo: 'blocos', blocos: blocos.estado()};
  return {fonte: editor.valor(), nome, modo: 'python'};
}

function guardarVersao(motivo, estado = estadoAtual()) {
  try { return versoes.guardar(Object.assign({motivo}, estado)); } catch (e) { return null; }
}

/** Escrevendo: guarda uma versão se a mais nova já tem mais de 5 minutos. */
function versaoEnquantoEscreve() {
  if (versoes.idadeDaMaisNova() > ENQUANTO_ESCREVE_MS) guardarVersao('enquanto escrevia');
}

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

function montarVersoes() {
  const lista = $('listaVersoes'), agora = estadoAtual(), todas = versoes.lista();
  lista.textContent = '';
  $('semVersoes').hidden = todas.length > 0;
  for (const v of todas) {
    const li = document.createElement('li');
    const topo = document.createElement('div');
    topo.className = 'v-topo';
    const quando = document.createElement('b');
    quando.textContent = globalThis.ESTVersoes.quando(v.quando);
    const motivo = document.createElement('span');
    motivo.className = 'v-motivo';
    motivo.textContent = NOMES_MOTIVO[v.motivo] || v.motivo || '';
    topo.append(quando, motivo);
    const {mais, menos} = globalThis.ESTVersoes.diferenca(v.fonte, agora.fonte);
    const linhas = v.fonte.replace(/\n+$/, '').split('\n').length;
    const igual = !mais && !menos;
    const info = document.createElement('div');
    info.className = 'v-info';
    info.textContent = [`${v.nome || 'programa'}.py`, v.modo === 'blocos' ? 'blocos' : 'Python', plural(linhas, 'linha', 'linhas'),
      igual ? 'igual ao programa de agora'
            : `${plural(Math.max(mais, menos), 'linha diferente', 'linhas diferentes')} do programa de agora`].join(' · ');
    if (igual) li.classList.add('igual');
    const ver = document.createElement('details');
    const resumo = document.createElement('summary');
    resumo.textContent = 'Ver o programa';
    const codigo = document.createElement('pre');
    codigo.textContent = v.fonte;
    ver.append(resumo, codigo);
    const voltar = document.createElement('button');
    voltar.className = 'bt pequeno';
    voltar.type = 'button';
    voltar.textContent = 'Voltar para esta versão';
    voltar.disabled = igual && v.modo === agora.modo;
    voltar.addEventListener('click', () => voltarPara(v.id));
    li.append(topo, info, ver, voltar);
    lista.append(li);
  }
}

function abrirVersoes() {
  montarVersoes();
  const caixa = $('versoes');
  if (caixa.showModal) caixa.showModal(); else caixa.setAttribute('open', '');
}
function fecharVersoes() {
  const caixa = $('versoes');
  if (caixa.close) caixa.close(); else caixa.removeAttribute('open');
}

async function voltarPara(id) {
  const v = versoes.achar(id);
  if (!v) return;
  guardarVersao('antes de voltar para uma versão');      // o programa de agora não se perde
  fecharVersoes();
  if (v.modo === 'blocos' && v.blocos) {
    $('nome').value = limparNome(v.nome || $('nome').value);
    await trocarModo('blocos');
    if (!blocos) return;
    blocos.carregar(v.blocos);
  } else {
    trocarPrograma(v.fonte, v.nome || $('nome').value);
  }
  salvar();
  limparMensagens();
  mensagem('ok', `Voltou para a versão guardada ${escapar(globalThis.ESTVersoes.quando(v.quando))}`,
    '<p>O programa que estava antes também ficou guardado nas versões.</p>');
}

$('btVersoes').addEventListener('click', abrirVersoes);
$('btFecharVersoes').addEventListener('click', fecharVersoes);
$('versoes').addEventListener('click', e => { if (e.target === $('versoes')) fecharVersoes(); });    // clique fora
$('btGuardarVersao').addEventListener('click', () => {
  const v = guardarVersao('guardou nas versões');
  montarVersoes();
  $('avisoVersoes').textContent = v ? 'Versão guardada.' : 'Nada mudou desde a última versão guardada.';
});

// o programa que estava na página quando ela abriu também vira uma versão (se mudou desde a última)
guardarVersao('ao abrir a página', {fonte: editor.valor(), nome: limparNome($('nome').value), modo: 'python'});

// ---------------------------------------------------------------- celular: arquivos e Python dos blocos recolhidos

// menu Arquivo: abre e fecha no botão; fecha ao escolher, ao clicar fora e no Esc
function menuArquivo(abrir) {
  $('extras').classList.toggle('aberto', abrir);
  $('btExtras').setAttribute('aria-expanded', String(abrir));
  $('btExtras').textContent = abrir ? 'Arquivo ▴' : 'Arquivo ▾';
}
$('btExtras').addEventListener('click', () => {
  const abrir = !$('extras').classList.contains('aberto');
  menuArquivo(abrir);
  if (abrir) ($('extras').querySelector('select, button') || $('extras')).focus();
});
for (const item of $('extras').querySelectorAll('button')) item.addEventListener('click', () => menuArquivo(false));
$('exemplo').addEventListener('change', () => menuArquivo(false));
document.addEventListener('click', e => {
  if ($('extras').classList.contains('aberto') && !e.target.closest('.menu-arquivo')) menuArquivo(false);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && $('extras').classList.contains('aberto')) { menuArquivo(false); $('btExtras').focus(); }
});
$('btVerPython').addEventListener('click', () => {
  const aberto = $('btVerPython').closest('.espelho').classList.toggle('aberto');
  $('btVerPython').setAttribute('aria-expanded', String(aberto));
  $('btVerPython').textContent = aberto ? 'Esconder' : 'Ver';
  if (aberto && espelho) espelho.atualizar();
});

// ---------------------------------------------------------------- teclado de programação (celular e tablet)
// Os símbolos que dão trabalho no teclado do celular e os comandos mais usados. Nos trechos, o que está entre « »
// fica selecionado para o aluno digitar por cima; as teclas com nome de comando (indentar...) mexem no editor.

const SIMBOLOS = [
  ['⇥', 'indentar', 'Recuar a linha (4 espaços)'], ['⇤', 'desindentar', 'Desfazer o recuo da linha'],
  [':', ':'], ['( )', '(«»)'], [')', ')'], ["' '", "'«»'"], ['=', ' = '], ['==', ' == '], ['<', ' < '], ['>', ' > '],
  [',', ', '], ['.', '.'], ['_', '_'], ['+', ' + '], ['-', ' - '], ['*', ' * '], ['/', ' / '], ['#', '# '],
  ['↶', 'desfazer', 'Desfazer'], ['↷', 'refazer', 'Refazer'],
];
const COMANDOS_DO_TECLADO = [
  ['andar', 'andar(rotacoes=«1»)'], ['ré', 're(rotacoes=«1»)'], ['andar_cm', 'andar_cm(«20»)'],
  ['virar →', 'virar_direita(«90»)'], ['virar ←', 'virar_esquerda(«90»)'], ['motores', 'motores(«30», 30)'],
  ['parar', 'parar()'], ['esperar', 'esperar(«1»)'],
  ['if', 'if «luz_refletida(1) < 50»:\n    '], ['else', 'else:\n    '], ['while', 'while «True»:\n    '],
  ['for', 'for _ in range(«4»):\n    '],
  ['luz', 'luz_refletida(«1»)'], ['cor', 'cor_vista(«1»)'], ['distância', 'distancia(«4»)'],
  ['mostrar', "mostrar(«'Oi'»)"], ['bip', 'bip()'], ['guardar', "guardar('«x»', 0)"], ['ler', "ler('«x»')"],
];
const EDICAO = new Set(['indentar', 'desindentar', 'desfazer', 'refazer']);

function montarTeclas(caixa, lista) {
  for (const [rotulo, acao, dica] of lista) {
    const b = Object.assign(document.createElement('button'), {type: 'button', textContent: rotulo, title: dica || acao});
    // sem o pointerdown padrão o editor não perde o foco, e o teclado do aparelho continua aberto
    b.addEventListener('pointerdown', e => e.preventDefault());
    b.addEventListener('click', () => (EDICAO.has(acao) ? editor.comando(acao) : editor.inserir(acao)));
    caixa.append(b);
  }
}
montarTeclas($('teclasSimbolos'), SIMBOLOS);
montarTeclas($('teclasComandos'), COMANDOS_DO_TECLADO);

const usaToque = () => window.matchMedia('(pointer: coarse)').matches;
let saiuDoEditor = null;
function mostrarTeclado(sim) {
  $('teclado').hidden = !sim;
  document.body.classList.toggle('com-teclado', sim);
}
editor.aoFocar(() => {
  clearTimeout(saiuDoEditor);
  if (usaToque() && modo === 'python' && $('sim').hidden) mostrarTeclado(true);
});
editor.aoSair(() => { saiuDoEditor = setTimeout(() => mostrarTeclado(false), 150); });
// no iPhone o teclado não diminui a página (o resizes-content do index.html é do Chrome): a barra sobe junto com ele
if (window.visualViewport) {
  const acompanhar = () => {
    const vv = window.visualViewport;
    $('teclado').style.bottom = `${Math.max(0, window.innerHeight - vv.height - vv.offsetTop)}px`;
  };
  window.visualViewport.addEventListener('resize', acompanhar);
  window.visualViewport.addEventListener('scroll', acompanhar);
}

// ---------------------------------------------------------------- instalar (página na tela inicial, como aplicativo)

let pedidoDeInstalar = null;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();                  // o botão da página pergunta na hora certa, em vez da faixa do navegador
  pedidoDeInstalar = e;
  $('btInstalar').hidden = false;
});
$('btInstalar').addEventListener('click', async () => {
  if (!pedidoDeInstalar) return;
  pedidoDeInstalar.prompt();
  try { await pedidoDeInstalar.userChoice; } catch (e) { /* o navegador fechou a pergunta */ }
  pedidoDeInstalar = null;
  $('btInstalar').hidden = true;
});
window.addEventListener('appinstalled', () => { $('btInstalar').hidden = true; });

// o link "Como enviar" (#ajuda) abre a caixa de ajuda
for (const a of document.querySelectorAll('a[href="#ajuda"]')) a.addEventListener('click', () => { $('ajuda').open = true; });
if (location.hash === '#ajuda') $('ajuda').open = true;

iniciarCompilador();
abrirDoLink();

// sem internet: o sw.js guarda a página e o Python do navegador depois da primeira visita
if ('serviceWorker' in navigator && isSecureContext) {
  navigator.serviceWorker.register('sw.js').catch(e => console.warn('sem modo offline:', e));
  if (!navigator.onLine && navigator.serviceWorker.controller) {
    mensagem('info', 'Sem internet', '<p>Usando a cópia desta página guardada no navegador: dá para escrever, ' +
             'simular e enviar ao robô normalmente.</p>');
  }
}
})();
