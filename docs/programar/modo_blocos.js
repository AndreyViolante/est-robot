'use strict';
/* Modo Blocos da página de programar: o aluno monta o programa com blocos (Blockly) e a página gera o
   Python que um aluno escreveria à mão, com as mesmas palavras do robo.py (andar, virar_direita,
   luz_refletida, if/elif/else, while, for _ in range(...)). Quem compila é sempre esse Python.
   O Blockly só é baixado quando o aluno abre a aba Blocos. */
(function () {
const VERSAO = '12.3.1';
const BASE = `https://cdn.jsdelivr.net/npm/blockly@${VERSAO}/`;
const ARQUIVOS = [
  ['blockly_compressed.js', 'sha384-w9GrXFbJ0m5jp7LitYG28h2U4fuRumUxQhvHTnGWdxFMT43YFG24NyAcZzpw8LQR'],
  ['blocks_compressed.js', 'sha384-1tCYtBLLOtsQKC3GDkQezPTGKc2ct7vKrpO/DLk8LMLRq2/Z0mSUG6IdZ2X9q+Vp'],
  ['msg/pt-br.js', 'sha384-QFAKMfz5sL/OTCNPCF/ckL7PhrVKgXiy4miBqyEyDOzz8CnVqDssGAnlAero1Rpt'],
];
const CHAVE = 'est-programar-blocos-v1';
const INICIO = '\u0001', FIM = '\u0002';      // marcas das linhas de cada bloco no código gerado (saem antes de mostrar)

const CORES = {inicio: '#d9a400', movimento: '#4c97ff', tela: '#9966ff', sensores: '#2b9fc4', decidir: '#e6900a',
               repetir: '#cf7c00', contas: '#40a640', variaveis: '#ff7a1a'};

// ---------------------------------------------------------------- baixar o Blockly

function carregarScript(url, integridade) {
  return new Promise((ok, falha) => {
    const s = document.createElement('script');
    Object.assign(s, {src: url, integrity: integridade, crossOrigin: 'anonymous'});
    s.onload = ok;
    s.onerror = () => { s.remove(); falha(new Error(`não consegui baixar ${url}`)); };
    document.head.append(s);
  });
}

let carga = null;
function carregarBlockly() {
  if (!carga) {
    carga = ARQUIVOS.reduce((antes, [arq, sri]) => antes.then(() => carregarScript(BASE + arq, sri)), Promise.resolve())
      .then(definir);
    carga.catch(() => { carga = null; });           // sem internet: tenta de novo na próxima vez
  }
  return carga;
}

// ---------------------------------------------------------------- blocos

const portas = (nome = 'PORTA') => ({type: 'field_dropdown', name: nome, options: [['1', '1'], ['2', '2'], ['3', '3'], ['4', '4']]});
const motores = (nome = 'MOTOR') => ({type: 'field_dropdown', name: nome, options: [['B', 'B'], ['C', 'C'], ['A', 'A'], ['D', 'D']]});
const numero = (nome, valor, extra = {}) => ({type: 'field_number', name: nome, value: valor, ...extra});
const NOTAS = [['dó', 'do'], ['dó#', 'do#'], ['ré', 're'], ['ré#', 're#'], ['mi', 'mi'], ['fá', 'fa'], ['fá#', 'fa#'],
               ['sol', 'sol'], ['sol#', 'sol#'], ['lá', 'la'], ['lá#', 'la#'], ['si', 'si']];
const CORES_ROBO = [['preto', 'PRETO'], ['azul', 'AZUL'], ['verde', 'VERDE'], ['amarelo', 'AMARELO'],
                    ['vermelho', 'VERMELHO'], ['branco', 'BRANCO'], ['marrom', 'MARROM']];
const comando = (tipo, cor, mensagem, args, dica, extra = {}) => ({type: tipo, message0: mensagem, args0: args,
  previousStatement: null, nextStatement: null, colour: cor, tooltip: dica, ...extra});
const leitura = (tipo, cor, mensagem, args, saida, dica) => ({type: tipo, message0: mensagem, args0: args,
  output: saida, colour: cor, tooltip: dica});

function nomeDeVariavel(texto) {      // as variáveis do robô: letras sem acento, números e _
  const limpo = String(texto).normalize('NFKD').replace(/[^\w]/g, '_').replace(/^(\d)/, '_$1');
  return limpo || null;
}

function definir() {
  const B = Blockly;
  B.Blocks.robo_inicio = {
    init() {
      this.jsonInit({message0: 'programa do robô', nextStatement: null, colour: CORES.inicio,
        tooltip: 'Encaixe os blocos aqui embaixo. Em Python o programa começa com: from robo import *'});
      this.hat = 'cap';
      this.setDeletable(false);
    },
  };
  const unidades = [['rotações', 'rotacoes'], ['segundos', 'segundos'], ['graus', 'graus'], ['cm', 'cm']];
  B.common.defineBlocksWithJsonArray([
    comando('robo_andar', CORES.movimento, 'andar %1 %2 potência %3',
      [numero('QUANTO', 2, {min: 0}), {type: 'field_dropdown', name: 'UNIDADE', options: unidades},
       numero('POTENCIA', 50, {min: -100, max: 100})],
      'andar(rotacoes=2), andar(segundos=1), andar_cm(20)'),
    comando('robo_re', CORES.movimento, 'ré %1 %2 potência %3',
      [numero('QUANTO', 1, {min: 0}), {type: 'field_dropdown', name: 'UNIDADE', options: unidades},
       numero('POTENCIA', 50, {min: -100, max: 100})],
      're(rotacoes=1); em cm: andar_cm(-20)'),
    comando('robo_virar', CORES.movimento, 'virar %1 %2 graus',
      [{type: 'field_dropdown', name: 'LADO', options: [['à direita', 'direita'], ['à esquerda', 'esquerda']]},
       numero('GRAUS', 90)],
      'virar_direita(90): vira o robô no lugar'),
    comando('robo_motores', CORES.movimento, 'motores esquerdo %1 direito %2',
      [{type: 'input_value', name: 'ESQ', check: 'Number'}, {type: 'input_value', name: 'DIR', check: 'Number'}],
      'motores(30, 30): liga os dois motores e deixa ligados', {inputsInline: true}),
    comando('robo_parar', CORES.movimento, 'parar', [], 'parar(): desliga os motores'),
    comando('robo_esperar', CORES.repetir, 'esperar %1 segundos', [numero('SEGUNDOS', 1, {min: 0})], 'esperar(1)'),

    comando('robo_mostrar', CORES.tela, 'mostrar %1 na linha %2',
      [{type: 'input_value', name: 'TEXTO'},
       {type: 'field_dropdown', name: 'LINHA', options: [['1', '1'], ['2', '2'], ['3', '3']]}],
      "mostrar('Oi') ou mostrar(luz_refletida(1), linha=2). A linha 1 apaga a tela antes", {inputsInline: true}),
    comando('robo_tocar_nota', CORES.tela, 'tocar nota %1 oitava %2 por %3 segundos',
      [{type: 'field_dropdown', name: 'NOTA', options: NOTAS},
       {type: 'field_dropdown', name: 'OITAVA', options: [['5', '5'], ['6', '6'], ['7', '7'], ['4', '4']]},
       numero('SEGUNDOS', 0.5, {min: 0})],
      "tocar('la', 0.5)"),
    comando('robo_tocar', CORES.tela, 'tocar %1 Hz por %2 segundos',
      [numero('FREQ', 440, {min: 300, max: 10000}), numero('SEGUNDOS', 0.5, {min: 0})], 'tocar(440, 0.5)'),
    comando('robo_melodia', CORES.tela, 'melodia %1 cada nota %2 s',
      [{type: 'field_input', name: 'NOTAS', text: 'do re mi fa sol'}, numero('TEMPO', 0.3, {min: 0})],
      "melodia('do re mi fa sol'): notas separadas por espaço, '-' é pausa, 'sol:0.6' muda a duração"),
    comando('robo_bip', CORES.tela, 'bip', [], 'bip(): um bip curto'),
    comando('robo_luz', CORES.tela, 'luz %1 piscar %2',
      [{type: 'field_dropdown', name: 'COR', options: [['azul', 'azul'], ['roxo', 'roxo'], ['vermelho', 'vermelho']]},
       {type: 'field_checkbox', name: 'PISCAR', checked: false}],
      "luz('azul')"),
    comando('robo_apagar_luz', CORES.tela, 'apagar luz', [], 'apagar_luz()'),

    leitura('robo_luz_refletida', CORES.sensores, 'luz refletida porta %1', [portas()], 'Number',
      'luz_refletida(1): 0 (escuro) a 100 (claro)'),
    leitura('robo_cor_vista', CORES.sensores, 'cor vista porta %1', [portas()], 'Cor',
      'cor_vista(1): compare com uma cor, ex.: cor_vista(1) == VERDE'),
    leitura('robo_cor', CORES.sensores, '%1', [{type: 'field_dropdown', name: 'COR', options: CORES_ROBO}], 'Cor',
      'Uma cor para comparar com a cor vista'),
    leitura('robo_distancia', CORES.sensores, 'distância porta %1', [portas()], 'Number',
      'distancia(4): em centímetros (ultrassom)'),
    leitura('robo_tocado', CORES.sensores, 'tocado porta %1', [portas()], null,
      'tocado(4): 1 se o toque estiver apertado, 0 se não'),
    leitura('robo_limite', CORES.sensores, 'limite porta %1', [portas()], 'Number',
      'limite(1): o meio entre o preto e o branco do sensor, medidos no calibracao.py'),
    // rotação do motor, giroscópio e cronômetro: da tabela de compilação da IDE, ainda não conferidos no robô
    leitura('robo_graus_motor', CORES.sensores, 'graus do motor %1', [motores()], 'Number',
      "graus_do_motor('B'): quanto o motor girou desde o começo ou o último zerar (ainda não conferido no robô)"),
    leitura('robo_giroscopio', CORES.sensores, 'giroscópio porta %1', [portas()], 'Number',
      'giroscopio(2): o ângulo do robô em graus, pelo sensor giroscópio (ainda não conferido no robô)'),
    leitura('robo_cronometro', CORES.sensores, 'cronômetro', [], 'Number',
      'cronometro(): segundos desde o começo do programa ou o último zerar (ainda não conferido no robô)'),
    comando('robo_zerar_motor', CORES.sensores, 'zerar graus do motor %1', [motores()],
      "zerar_motor('B') (ainda não conferido no robô)"),
    comando('robo_zerar_giroscopio', CORES.sensores, 'zerar giroscópio porta %1', [portas()],
      'zerar_giroscopio(2): deixe o robô parado (ainda não conferido no robô)'),
    comando('robo_zerar_cronometro', CORES.sensores, 'zerar cronômetro', [],
      'zerar_cronometro() (ainda não conferido no robô)'),

    comando('robo_para_sempre', CORES.repetir, 'repetir para sempre %1 %2',
      [{type: 'input_dummy'}, {type: 'input_statement', name: 'FAZER'}], 'while True:', {nextStatement: undefined}),
    comando('robo_repetir', CORES.repetir, 'repetir %1 vezes %2 %3',
      [numero('VEZES', 4, {min: 0, precision: 1}), {type: 'input_dummy'}, {type: 'input_statement', name: 'FAZER'}],
      'for _ in range(4):'),
    comando('robo_enquanto', CORES.repetir, 'repetir %1 %2 %3',
      [{type: 'field_dropdown', name: 'MODO', options: [['enquanto', 'enquanto'], ['até', 'ate']]},
       {type: 'input_value', name: 'COND', check: 'Boolean'}, {type: 'input_statement', name: 'FAZER'}],
      'while distancia(4) > 20:   (até: while not ...)'),

    leitura('robo_conta', CORES.contas, '%1 %2 %3',
      [{type: 'input_value', name: 'A', check: 'Number'},
       {type: 'field_dropdown', name: 'OP', options: [['+', '+'], ['-', '-'], ['×', '*'], ['÷', '/']]},
       {type: 'input_value', name: 'B', check: 'Number'}], 'Number', 'Conta: + - * /'),

    comando('robo_guardar', CORES.variaveis, 'guardar %1 = %2',
      [{type: 'field_input', name: 'NOME', text: 'contador'}, {type: 'input_value', name: 'VALOR', check: 'Number'}],
      "guardar('contador', 0): guarda um número numa variável do robô", {inputsInline: true}),
    leitura('robo_ler', CORES.variaveis, 'ler %1', [{type: 'field_input', name: 'NOME', text: 'contador'}], 'Number',
      "ler('contador'): o número guardado na variável do robô"),
  ]);
  for (const tipo of ['robo_guardar', 'robo_ler']) {
    const init = B.Blocks[tipo].init;
    B.Blocks[tipo].init = function () {
      init.call(this);
      this.getField('NOME').setValidator(nomeDeVariavel);
    };
  }
  B.Blocks.robo_conta.init = (init => function () { init.call(this); this.setInputsInline(true); })(B.Blocks.robo_conta.init);
}

// ---------------------------------------------------------------- gerador de Python

const ORDEM = {ATOMO: 0, SINAL: 4, VEZES: 5, MAIS: 6, COMPARA: 11, NAO: 12, E: 13, OU: 14, NADA: 99};

const texto = s => `'${String(s).replace(/[\u0000-\u001f]/g, '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
const num = (b, campo) => String(Number(b.getFieldValue(campo)));

function criarGerador() {
  const G = new Blockly.CodeGenerator('Robo');
  G.INDENT = '    ';
  G.init = function () { this.isInitialized = true; };
  G.finish = codigo => codigo;
  G.scrub_ = function (bloco, codigo, soEste) {
    const proximo = bloco.nextConnection && bloco.nextConnection.targetBlock();
    const resto = proximo && !soEste ? this.blockToCode(proximo) : '';
    if (bloco.outputConnection) return codigo;
    const comentario = (bloco.getCommentText && bloco.getCommentText()) || '';
    const nota = comentario.trim() ? comentario.trim().split('\n').map(l => `# ${l.trim()}\n`).join('') : '';
    return `${INICIO}${bloco.id}\n${nota}${codigo}${FIM}\n${resto}`;
  };
  const valor = (b, nome, ordem) => G.valueToCode(b, nome, ordem) || 'None';
  const corpo = (b, nome) => G.statementToCode(b, nome) || `${G.INDENT}pass\n`;
  const potencia = b => (num(b, 'POTENCIA') === '50' ? '' : `, potencia=${num(b, 'POTENCIA')}`);
  const f = G.forBlock;

  f.robo_inicio = () => 'from robo import *\n\n';
  f.robo_andar = b => (b.getFieldValue('UNIDADE') === 'cm' ? `andar_cm(${num(b, 'QUANTO')}${potencia(b)})\n`
    : `andar(${b.getFieldValue('UNIDADE')}=${num(b, 'QUANTO')}${potencia(b)})\n`);
  f.robo_re = b => (b.getFieldValue('UNIDADE') === 'cm' ? `andar_cm(-${num(b, 'QUANTO')}${potencia(b)})\n`
    : `re(${b.getFieldValue('UNIDADE')}=${num(b, 'QUANTO')}${potencia(b)})\n`);
  f.robo_virar = b => `virar_${b.getFieldValue('LADO')}(${num(b, 'GRAUS')})\n`;
  f.robo_motores = b => `motores(${valor(b, 'ESQ', ORDEM.NADA)}, ${valor(b, 'DIR', ORDEM.NADA)})\n`;
  f.robo_parar = () => 'parar()\n';
  f.robo_esperar = b => `esperar(${num(b, 'SEGUNDOS')})\n`;
  f.robo_mostrar = b => {
    const linha = b.getFieldValue('LINHA');
    return `mostrar(${valor(b, 'TEXTO', ORDEM.NADA)}${linha === '1' ? '' : `, linha=${linha}`})\n`;
  };
  f.robo_tocar_nota = b => {
    const oitava = b.getFieldValue('OITAVA');
    return `tocar(${texto(b.getFieldValue('NOTA') + (oitava === '5' ? '' : oitava))}, ${num(b, 'SEGUNDOS')})\n`;
  };
  f.robo_tocar = b => `tocar(${num(b, 'FREQ')}, ${num(b, 'SEGUNDOS')})\n`;
  f.robo_melodia = b => {
    const tempo = num(b, 'TEMPO');
    return `melodia(${texto(b.getFieldValue('NOTAS'))}${tempo === '0.3' ? '' : `, tempo=${tempo}`})\n`;
  };
  f.robo_bip = () => 'bip()\n';
  f.robo_luz = b => `luz(${texto(b.getFieldValue('COR'))}${b.getFieldValue('PISCAR') === 'TRUE' ? ', piscar=True' : ''})\n`;
  f.robo_apagar_luz = () => 'apagar_luz()\n';
  f.robo_guardar = b => `guardar(${texto(b.getFieldValue('NOME'))}, ${valor(b, 'VALOR', ORDEM.NADA)})\n`;

  f.robo_luz_refletida = b => [`luz_refletida(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_cor_vista = b => [`cor_vista(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_cor = b => [b.getFieldValue('COR'), ORDEM.ATOMO];
  f.robo_distancia = b => [`distancia(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_tocado = b => [`tocado(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_limite = b => [`limite(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_graus_motor = b => [`graus_do_motor(${texto(b.getFieldValue('MOTOR'))})`, ORDEM.ATOMO];
  f.robo_giroscopio = b => [`giroscopio(${b.getFieldValue('PORTA')})`, ORDEM.ATOMO];
  f.robo_cronometro = () => ['cronometro()', ORDEM.ATOMO];
  f.robo_zerar_motor = b => `zerar_motor(${texto(b.getFieldValue('MOTOR'))})\n`;
  f.robo_zerar_giroscopio = b => `zerar_giroscopio(${b.getFieldValue('PORTA')})\n`;
  f.robo_zerar_cronometro = () => 'zerar_cronometro()\n';
  f.robo_ler = b => [`ler(${texto(b.getFieldValue('NOME'))})`, ORDEM.ATOMO];

  f.robo_para_sempre = b => `while True:\n${corpo(b, 'FAZER')}`;
  f.robo_repetir = b => `for _ in range(${Math.max(0, Math.round(Number(b.getFieldValue('VEZES'))))}):\n${corpo(b, 'FAZER')}`;
  f.robo_enquanto = b => (b.getFieldValue('MODO') === 'ate'
    ? `while not ${valor(b, 'COND', ORDEM.COMPARA)}:\n${corpo(b, 'FAZER')}`
    : `while ${valor(b, 'COND', ORDEM.NADA)}:\n${corpo(b, 'FAZER')}`);
  f.controls_if = b => {
    let codigo = '', n = 0;
    do {
      codigo += `${n ? 'elif' : 'if'} ${valor(b, `IF${n}`, ORDEM.NADA)}:\n${corpo(b, `DO${n}`)}`;
      n++;
    } while (b.getInput(`IF${n}`));
    if (b.getInput('ELSE')) codigo += `else:\n${corpo(b, 'ELSE')}`;
    return codigo;
  };

  // contas e comparações: só os parênteses que o Python precisa (à esquerda, a mesma ordem não precisa)
  f.robo_conta = b => {
    const op = b.getFieldValue('OP'), ordem = op === '+' || op === '-' ? ORDEM.MAIS : ORDEM.VEZES;
    return [`${valor(b, 'A', ordem + 0.5)} ${op} ${valor(b, 'B', ordem)}`, ordem];
  };
  const COMPARA = {EQ: '==', NEQ: '!=', LT: '<', LTE: '<=', GT: '>', GTE: '>='};
  f.logic_compare = b => [`${valor(b, 'A', ORDEM.COMPARA)} ${COMPARA[b.getFieldValue('OP')]} ${valor(b, 'B', ORDEM.COMPARA)}`,
                          ORDEM.COMPARA];
  f.logic_operation = b => {
    const e = b.getFieldValue('OP') === 'AND', ordem = e ? ORDEM.E : ORDEM.OU;
    return [`${valor(b, 'A', ordem + 0.5)} ${e ? 'and' : 'or'} ${valor(b, 'B', ordem + 0.5)}`, ordem];
  };
  f.logic_negate = b => [`not ${valor(b, 'BOOL', ORDEM.COMPARA)}`, ORDEM.NAO];
  f.logic_boolean = b => [b.getFieldValue('BOOL') === 'TRUE' ? 'True' : 'False', ORDEM.ATOMO];
  f.math_number = b => {
    const n = Number(b.getFieldValue('NUM'));
    return [String(n), n < 0 ? ORDEM.SINAL : ORDEM.ATOMO];
  };
  f.text = b => [texto(b.getFieldValue('TEXT')), ORDEM.ATOMO];
  return G;
}

/** Tira as marcas do código gerado. Devolve o Python e, para cada linha, o id do bloco que a gerou. */
function limpar(bruto) {
  const linhas = [], blocos = [], pilha = [];
  for (const linha of bruto.split('\n')) {
    const t = linha.trim();
    if (t[0] === INICIO) { pilha.push(t.slice(1)); continue; }
    if (t === FIM) { pilha.pop(); continue; }
    linhas.push(linha);
    blocos.push(pilha[pilha.length - 1] || null);
  }
  while (linhas.length && !linhas[linhas.length - 1].trim()) { linhas.pop(); blocos.pop(); }
  return {codigo: linhas.join('\n') + '\n', blocos};
}

// ---------------------------------------------------------------- caixa de blocos

const sombra = (tipo, campos) => ({shadow: {type: tipo, fields: campos}});
const n = v => sombra('math_number', {NUM: v});
const CAIXA = {
  kind: 'categoryToolbox',
  contents: [
    {kind: 'category', name: 'Movimento', colour: CORES.movimento, contents: [
      {kind: 'block', type: 'robo_andar'},
      {kind: 'block', type: 'robo_andar', fields: {QUANTO: 20, UNIDADE: 'cm'}},
      {kind: 'block', type: 'robo_re'},
      {kind: 'block', type: 'robo_virar'},
      {kind: 'block', type: 'robo_virar', fields: {LADO: 'esquerda'}},
      {kind: 'block', type: 'robo_motores', inputs: {ESQ: n(30), DIR: n(30)}},
      {kind: 'block', type: 'robo_parar'},
      {kind: 'block', type: 'robo_esperar'},
    ]},
    {kind: 'category', name: 'Sensores', colour: CORES.sensores, contents: [
      {kind: 'block', type: 'robo_luz_refletida'},
      {kind: 'block', type: 'robo_cor_vista'},
      {kind: 'block', type: 'robo_cor', fields: {COR: 'VERDE'}},
      {kind: 'block', type: 'robo_distancia', fields: {PORTA: '4'}},
      {kind: 'block', type: 'robo_tocado', fields: {PORTA: '4'}},
      {kind: 'block', type: 'robo_limite'},
      {kind: 'block', type: 'robo_zerar_motor'},
      {kind: 'block', type: 'robo_graus_motor'},
      {kind: 'block', type: 'robo_zerar_giroscopio', fields: {PORTA: '2'}},
      {kind: 'block', type: 'robo_giroscopio', fields: {PORTA: '2'}},
      {kind: 'block', type: 'robo_zerar_cronometro'},
      {kind: 'block', type: 'robo_cronometro'},
    ]},
    {kind: 'category', name: 'Decidir', colour: CORES.decidir, contents: [
      {kind: 'block', type: 'controls_if'},
      {kind: 'block', type: 'controls_if', extraState: {hasElse: true}},
      {kind: 'block', type: 'controls_if', extraState: {elseIfCount: 1, hasElse: true}},
      {kind: 'block', type: 'logic_compare', fields: {OP: 'LT'},
       inputs: {A: {block: {type: 'robo_luz_refletida'}}, B: {block: {type: 'robo_limite'}}}},
      {kind: 'block', type: 'logic_compare', fields: {OP: 'LT'},
       inputs: {A: {block: {type: 'robo_distancia', fields: {PORTA: '4'}}}, B: n(20)}},
      {kind: 'block', type: 'logic_compare', fields: {OP: 'EQ'},
       inputs: {A: {block: {type: 'robo_cor_vista'}}, B: {block: {type: 'robo_cor', fields: {COR: 'VERDE'}}}}},
      {kind: 'block', type: 'logic_compare', fields: {OP: 'GT'}, inputs: {A: n(0), B: n(0)}},
      {kind: 'block', type: 'logic_operation', fields: {OP: 'AND'}},
      {kind: 'block', type: 'logic_operation', fields: {OP: 'OR'}},
      {kind: 'block', type: 'logic_negate'},
    ]},
    {kind: 'category', name: 'Repetir', colour: CORES.repetir, contents: [
      {kind: 'block', type: 'robo_para_sempre'},
      {kind: 'block', type: 'robo_repetir'},
      {kind: 'block', type: 'robo_enquanto'},
      {kind: 'block', type: 'robo_enquanto', fields: {MODO: 'ate'}},
      {kind: 'block', type: 'robo_esperar'},
    ]},
    {kind: 'category', name: 'Tela e som', colour: CORES.tela, contents: [
      {kind: 'block', type: 'robo_mostrar', inputs: {TEXTO: sombra('text', {TEXT: 'Oi!'})}},
      {kind: 'block', type: 'robo_mostrar', fields: {LINHA: '2'}, inputs: {TEXTO: {block: {type: 'robo_luz_refletida'}}}},
      {kind: 'block', type: 'robo_tocar_nota', fields: {NOTA: 'la'}},
      {kind: 'block', type: 'robo_tocar'},
      {kind: 'block', type: 'robo_melodia'},
      {kind: 'block', type: 'robo_bip'},
      {kind: 'block', type: 'robo_luz'},
      {kind: 'block', type: 'robo_apagar_luz'},
    ]},
    {kind: 'category', name: 'Contas', colour: CORES.contas, contents: [
      {kind: 'block', type: 'math_number', fields: {NUM: 0}},
      {kind: 'block', type: 'robo_conta', fields: {OP: '+'}, inputs: {A: n(30), B: n(10)}},
      {kind: 'block', type: 'robo_conta', fields: {OP: '-'},
       inputs: {A: {block: {type: 'robo_luz_refletida'}}, B: {block: {type: 'robo_luz_refletida', fields: {PORTA: '2'}}}}},
      {kind: 'block', type: 'robo_conta', fields: {OP: '*'}, inputs: {A: n(0), B: n(0.5)}},
      {kind: 'block', type: 'robo_conta', fields: {OP: '/'}, inputs: {A: n(0), B: n(2)}},
    ]},
    {kind: 'category', name: 'Variáveis', colour: CORES.variaveis, contents: [
      {kind: 'block', type: 'robo_guardar', inputs: {VALOR: n(0)}},
      {kind: 'block', type: 'robo_guardar',
       inputs: {VALOR: {block: {type: 'robo_conta', fields: {OP: '+'}, inputs: {A: {block: {type: 'robo_ler'}}, B: n(1)}}}}},
      {kind: 'block', type: 'robo_ler'},
    ]},
  ],
};

// o primeiro programa, igual ao da aba Python: luz, som e "Funcionou!"
const INICIAL = {blocks: {languageVersion: 0, blocks: [{type: 'robo_inicio', x: 24, y: 24, next: {block:
  {type: 'robo_luz', fields: {COR: 'azul'}, next: {block:
  {type: 'robo_tocar', fields: {FREQ: 440, SEGUNDOS: 0.5}, next: {block:
  {type: 'robo_mostrar', inputs: {TEXTO: sombra('text', {TEXT: 'Funcionou!'})}, next: {block:
  {type: 'robo_esperar', fields: {SEGUNDOS: 3}, next: {block:
  {type: 'robo_apagar_luz'}}}}}}}}}}}]}};

function tema(nome, escuro) {
  const estilo = cor => ({colourPrimary: cor});
  return Blockly.Theme.defineTheme(nome, {
    base: Blockly.Themes.Classic,
    blockStyles: {logic_blocks: estilo(CORES.decidir), loop_blocks: estilo(CORES.repetir),
                  math_blocks: estilo(CORES.contas), text_blocks: estilo(CORES.tela)},
    componentStyles: escuro ? {
      workspaceBackgroundColour: '#0f1424', toolboxBackgroundColour: '#121727', toolboxForegroundColour: '#e7ebf6',
      flyoutBackgroundColour: '#1a2033', flyoutForegroundColour: '#e7ebf6', flyoutOpacity: 0.96,
      scrollbarColour: '#3a4360', insertionMarkerColour: '#ffffff', insertionMarkerOpacity: 0.3,
    } : {
      workspaceBackgroundColour: '#f7f8fb', toolboxBackgroundColour: '#ffffff', toolboxForegroundColour: '#0d1222',
      flyoutBackgroundColour: '#e9edf5', flyoutForegroundColour: '#0d1222', flyoutOpacity: 0.96,
      scrollbarColour: '#c3c9d6',
    },
    fontStyle: {family: '"Segoe UI", system-ui, -apple-system, sans-serif', weight: '600', size: 11},
  });
}

// ---------------------------------------------------------------- área de blocos

/** Abre a área de blocos dentro de div. aoMudar(codigo) é chamado a cada mudança. Devolve a API do modo. */
async function criar(div, aoMudar) {
  await carregarBlockly();
  const escuroMQ = window.matchMedia('(prefers-color-scheme: dark)');
  const escuro = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : escuroMQ.matches;
  const temas = {claro: tema('est-claro', false), escuro: tema('est-escuro', true)};
  div.textContent = '';
  const ws = Blockly.inject(div, {
    toolbox: CAIXA, renderer: 'zelos', theme: escuro() ? temas.escuro : temas.claro,
    media: BASE + 'media/', sounds: false, trashcan: true,
    zoom: {controls: true, wheel: false, startScale: window.matchMedia('(max-width: 600px)').matches ? 0.62 : 0.8,
           maxScale: 2, minScale: 0.4, scaleSpeed: 1.15},
    move: {scrollbars: true, drag: true, wheel: true},
  });
  escuroMQ.addEventListener('change', () => ws.setTheme(escuro() ? temas.escuro : temas.claro));
  const G = criarGerador();

  let carregou = false;
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE));
    if (salvo) { Blockly.serialization.workspaces.load(salvo, ws); carregou = true; }
  } catch (e) {
    ws.clear();                     // guardado estragado: começa do primeiro programa
  }
  if (!carregou) Blockly.serialization.workspaces.load(INICIAL, ws);
  if (!ws.getTopBlocks(false).some(b => b.type === 'robo_inicio')) {
    const inicio = ws.newBlock('robo_inicio');
    inicio.initSvg();
    inicio.render();
    inicio.moveBy(24, 24);
  }
  // bloco solto (fora do "programa do robô") fica apagado e não entra no Python
  ws.addChangeListener(Blockly.Events.disableOrphans);
  function apagarSoltos() {
    for (const topo of ws.getTopBlocks(false)) {
      if (topo.type === 'robo_inicio') continue;
      for (let b = topo; b; b = b.getNextBlock()) b.setDisabledReason(true, 'ORPHANED_BLOCK');
    }
  }
  apagarSoltos();

  let atual = {codigo: '', blocos: []};
  const avisados = new Set();
  function gerar() {
    G.init(ws);
    const inicio = ws.getTopBlocks(true).find(b => b.type === 'robo_inicio');
    atual = limpar(G.finish(inicio ? G.blockToCode(inicio) : 'from robo import *\n'));
    return atual.codigo;
  }
  function salvar() {
    try { localStorage.setItem(CHAVE, JSON.stringify(Blockly.serialization.workspaces.save(ws))); } catch (e) { /* sem armazenamento */ }
  }
  function limparAvisos() {
    for (const id of avisados) { const b = ws.getBlockById(id); if (b) b.setWarningText(null); }
    avisados.clear();
  }
  function mostrarBloco(id, aviso) {
    const b = ws.getBlockById(id);
    if (!b) return false;
    limparAvisos();
    if (aviso) { b.setWarningText(aviso); avisados.add(id); }
    ws.centerOnBlock(id);
    if (Blockly.common.setSelected) Blockly.common.setSelected(b); else b.select();
    return true;
  }

  let espera = null;
  ws.addChangeListener(e => {
    if (e.type === (Blockly.Events.EventType || Blockly.Events).FINISHED_LOADING) apagarSoltos();
    if (e.isUiEvent || ws.isDragging()) return;
    clearTimeout(espera);
    espera = setTimeout(() => { aoMudar(gerar()); salvar(); }, 120);
  });
  new ResizeObserver(() => Blockly.svgResize(ws)).observe(div);
  aoMudar(gerar());

  return {
    codigo: gerar,
    /** O bloco de um comando com encaixe vazio (ex.: um "se" sem condição), para avisar antes de compilar. */
    faltando() {
      for (const b of ws.getAllBlocks(false)) {
        if (!b.isEnabled() || b.getRootBlock().type !== 'robo_inicio') continue;
        if (b.inputList.some(i => i.connection && i.connection.type === Blockly.ConnectionType.INPUT_VALUE &&
                                  !i.connection.targetBlock())) {
          return {id: b.id, texto: b.toString().split('?')[0].trim() || b.toString()};
        }
      }
      return null;
    },
    /** Mostra o bloco que gerou a linha (de um erro) e põe o aviso nele. */
    mostrarLinha: (linha, aviso) => mostrarBloco(atual.blocos[linha - 1], aviso),
    mostrarBloco,
    limparAvisos,
    redimensionar: () => Blockly.svgResize(ws),
    salvar,
    area: ws,
  };
}

globalThis.ESTBlocos = {criar, carregarBlockly};
})();
