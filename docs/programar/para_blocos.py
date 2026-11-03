"""Do Python para os blocos da página de programar (modo_blocos.js): lê o programa com o ast do Python e monta a
área de blocos no formato de serialização do Blockly. É o caminho de volta do gerador de Python do modo_blocos.js:
o Python que os blocos geram de novo compila para os mesmos bytes (ferramentas/teste_blocos.js confere).

O que ainda não tem bloco não se perde: vira um bloco "Python" com a linha como está (uma instrução de várias
linhas vira um bloco por linha, com o recuo dentro do texto). Comentários vão para o balão de comentário do bloco
seguinte, como o gerador escreve; comentários no fim de um trecho viram uma linha "Python".
Se mudar os blocos ou o gerador do modo_blocos.js, mude aqui também.
"""
import ast, io, json, re, tokenize

CORES = {'PRETO', 'AZUL', 'VERDE', 'AMARELO', 'VERMELHO', 'BRANCO', 'MARROM'}
NOTAS = {'do', 'do#', 're', 're#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si'}
COMPARA = {ast.Eq: 'EQ', ast.NotEq: 'NEQ', ast.Lt: 'LT', ast.LtE: 'LTE', ast.Gt: 'GT', ast.GtE: 'GTE'}
CONTA = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}
SENSORES = {'luz_refletida': 'robo_luz_refletida', 'cor_vista': 'robo_cor_vista', 'distancia': 'robo_distancia',
            'tocado': 'robo_tocado', 'limite': 'robo_limite', 'giroscopio': 'robo_giroscopio'}
SIMPLES = {'parar': 'robo_parar', 'bip': 'robo_bip', 'apagar_luz': 'robo_apagar_luz',
           'zerar_cronometro': 'robo_zerar_cronometro'}
UNIDADES = ('rotacoes', 'segundos', 'graus')
SE_SENSOR = {'se_ver_cor': 'robo_se_cor', 'se_luz': 'robo_se_luz', 'se_distancia': 'robo_se_distancia',
             'se_tocado': 'robo_se_tocado'}
# o tipo do que cada bloco de valor devolve (os encaixes com tipo, como a condição do "se", só aceitam o tipo certo);
# o que não está aqui (variável, tocado, valor em Python) encaixa em qualquer lugar
SAIDA = {'math_number': 'Number', 'text': 'String', 'logic_boolean': 'Boolean', 'logic_compare': 'Boolean',
         'logic_operation': 'Boolean', 'logic_negate': 'Boolean', 'robo_conta': 'Number', 'robo_luz_refletida': 'Number',
         'robo_distancia': 'Number', 'robo_limite': 'Number', 'robo_graus_motor': 'Number', 'robo_giroscopio': 'Number',
         'robo_cronometro': 'Number', 'robo_ler': 'Number', 'robo_cor_vista': 'Cor', 'robo_cor': 'Cor'}


class NaoTemBloco(Exception):
    """Este pedaço do programa vira um bloco "Python" (com o texto como está)."""


def _numero(no):
    """O número de um nó (com o sinal de menos, se tiver), ou NaoTemBloco."""
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        return -_numero(no.operand)
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)) and not isinstance(no.value, bool):
        return no.value
    raise NaoTemBloco


def _texto(no):
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    raise NaoTemBloco


def _porta(no, portas=('1', '2', '3', '4')):
    if isinstance(no, ast.Constant) and not isinstance(no.value, bool) and str(no.value).upper() in portas:
        return str(no.value).upper()
    raise NaoTemBloco


def _faixa(valor, minimo=None, maximo=None):
    """Os campos de número dos blocos têm limites: fora deles o Blockly mudaria o número."""
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise NaoTemBloco
    return valor


def _argumentos(chamada, nomes, padroes=None):
    """{nome: nó} dos argumentos da chamada, pela posição ou pelo nome. Argumento desconhecido: NaoTemBloco."""
    if any(isinstance(a, ast.Starred) for a in chamada.args) or len(chamada.args) > len(nomes):
        raise NaoTemBloco
    valores = dict(zip(nomes, chamada.args))
    for k in chamada.keywords:
        if k.arg not in nomes or k.arg in valores:
            raise NaoTemBloco
        valores[k.arg] = k.value
    for nome, padrao in (padroes or {}).items():
        valores.setdefault(nome, padrao)
    return valores


def _sombra_numero(v):
    return {'shadow': {'type': 'math_number', 'fields': {'NUM': v}}}


class Tradutor:
    def __init__(self, fonte):
        self.fonte = fonte
        self.linhas = fonte.splitlines()
        self.variaveis = {}                    # nome -> id da variável do Blockly
        self.python = 0                        # quantos blocos "Python" (linhas sem bloco)
        self.comentarios = {}                  # linha -> texto do comentário (sem o #)
        self.so_comentario = set()             # linhas que só têm comentário
        try:
            for t in tokenize.generate_tokens(io.StringIO(fonte).readline):
                if t.type == tokenize.COMMENT:
                    self.comentarios[t.start[0]] = t.string[1:].strip()
                    if not self.linhas[t.start[0] - 1][:t.start[1]].strip():
                        self.so_comentario.add(t.start[0])
        except (tokenize.TokenError, IndentationError):
            pass
        self.usados = set()                    # comentários já postos em algum bloco

    # ---- blocos "Python": o texto como está
    def _bloco_python(self, texto):
        self.python += 1
        return {'type': 'robo_python', 'fields': {'CODIGO': texto}}

    def _linhas_cruas(self, no):
        """Uma instrução sem bloco: um bloco "Python" por linha, com o recuo relativo dentro do texto."""
        trecho = self.linhas[no.lineno - 1:no.end_lineno]
        corte = no.col_offset
        return [self._bloco_python(l[corte:] if l[:corte].strip() == '' else l.lstrip()) for l in trecho]

    def _valor_python(self, no):
        self.python += 1
        return {'type': 'robo_python_valor', 'fields': {'CODIGO': ast.get_source_segment(self.fonte, no) or ast.unparse(no)}}

    # ---- valores (o que entra nos encaixes)
    def valor(self, no, tipo=None):
        """O bloco do valor; tipo: o que o encaixe aceita ('Number', 'Boolean'), se ele tiver tipo."""
        try:
            bloco = self._valor(no)
        except NaoTemBloco:
            return self._valor_python(no)
        if tipo and SAIDA.get(bloco['type'], tipo) != tipo:
            self.python += self._contar_python(bloco) * -1        # os de dentro deixam de existir
            return self._valor_python(no)
        return bloco

    def _contar_python(self, bloco):
        """Quantos blocos "Python" há dentro de um bloco (para descontar quando ele vira um valor em Python só)."""
        n = bloco['type'] in ('robo_python', 'robo_python_valor')
        for entrada in bloco.get('inputs', {}).values():
            n += self._contar_python(entrada['block'])
        return n

    def _valor(self, no):
        if isinstance(no, ast.Constant):
            if isinstance(no.value, bool):
                return {'type': 'logic_boolean', 'fields': {'BOOL': 'TRUE' if no.value else 'FALSE'}}
            if isinstance(no.value, (int, float)):
                return {'type': 'math_number', 'fields': {'NUM': no.value}}
            if isinstance(no.value, str):
                return {'type': 'text', 'fields': {'TEXT': no.value}}
            raise NaoTemBloco
        if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
            return {'type': 'math_number', 'fields': {'NUM': _numero(no)}}
        if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.Not):
            return {'type': 'logic_negate', 'inputs': {'BOOL': {'block': self.valor(no.operand, 'Boolean')}}}
        if isinstance(no, ast.Name):
            if no.id in CORES:
                return {'type': 'robo_cor', 'fields': {'COR': no.id}}
            if no.id in self.variaveis:
                return {'type': 'variables_get', 'fields': {'VAR': {'id': self.variaveis[no.id]}}}
            raise NaoTemBloco
        if isinstance(no, ast.BinOp) and type(no.op) in CONTA:
            return {'type': 'robo_conta', 'fields': {'OP': CONTA[type(no.op)]},
                    'inputs': {'A': {'block': self.valor(no.left, 'Number')}, 'B': {'block': self.valor(no.right, 'Number')}}}
        if isinstance(no, ast.Compare) and len(no.ops) == 1 and type(no.ops[0]) in COMPARA:
            return {'type': 'logic_compare', 'fields': {'OP': COMPARA[type(no.ops[0])]},
                    'inputs': {'A': {'block': self.valor(no.left)}, 'B': {'block': self.valor(no.comparators[0])}}}
        if isinstance(no, ast.BoolOp):
            op = 'AND' if isinstance(no.op, ast.And) else 'OR'
            bloco = self.valor(no.values[0], 'Boolean')
            for proximo in no.values[1:]:           # a and b and c = (a and b) and c, como o gerador escreve
                bloco = {'type': 'logic_operation', 'fields': {'OP': op},
                         'inputs': {'A': {'block': bloco}, 'B': {'block': self.valor(proximo, 'Boolean')}}}
            return bloco
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            return self._leitura(no.func.id, no)
        raise NaoTemBloco

    def _leitura(self, nome, chamada):
        if nome in SENSORES:
            a = _argumentos(chamada, ['porta'])
            if 'porta' not in a:
                raise NaoTemBloco
            return {'type': SENSORES[nome], 'fields': {'PORTA': _porta(a['porta'])}}
        if nome == 'graus_do_motor':
            a = _argumentos(chamada, ['porta'])
            if 'porta' not in a:
                raise NaoTemBloco
            return {'type': 'robo_graus_motor', 'fields': {'MOTOR': _porta(a['porta'], ('A', 'B', 'C', 'D'))}}
        if nome == 'cronometro' and not chamada.args and not chamada.keywords:
            return {'type': 'robo_cronometro'}
        if nome == 'ler':
            a = _argumentos(chamada, ['nome'])
            texto = _texto(a.get('nome'))
            if not re.fullmatch(r'[A-Za-z_]\w*', texto, re.ASCII):
                raise NaoTemBloco
            return {'type': 'robo_ler', 'fields': {'NOME': texto}}
        raise NaoTemBloco

    # ---- comandos
    def _comando(self, nome, chamada):
        """Um comando (andar, motores...) como bloco, ou NaoTemBloco."""
        if nome in SIMPLES:
            if chamada.args or chamada.keywords:
                raise NaoTemBloco
            return {'type': SIMPLES[nome]}
        if nome in ('andar', 're'):
            a = _argumentos(chamada, ['rotacoes', 'graus', 'segundos', 'potencia'])
            unidades = [u for u in UNIDADES if u in a]
            if len(unidades) != 1:
                raise NaoTemBloco
            pot = _faixa(_numero(a['potencia']), -100, 100) if 'potencia' in a else 50
            return {'type': 'robo_andar' if nome == 'andar' else 'robo_re',
                    'fields': {'QUANTO': _faixa(_numero(a[unidades[0]]), 0), 'UNIDADE': unidades[0], 'POTENCIA': pot}}
        if nome == 'andar_cm':
            a = _argumentos(chamada, ['cm', 'potencia'])
            cm = _numero(a['cm']) if 'cm' in a else _numero(None)
            pot = _faixa(_numero(a['potencia']), -100, 100) if 'potencia' in a else 50
            return {'type': 'robo_andar' if cm >= 0 else 'robo_re',
                    'fields': {'QUANTO': abs(cm), 'UNIDADE': 'cm', 'POTENCIA': pot}}
        if nome in ('virar_direita', 'virar_esquerda'):
            a = _argumentos(chamada, ['angulo'], {'angulo': ast.Constant(90)})
            return {'type': 'robo_virar', 'fields': {'LADO': nome.split('_')[1], 'GRAUS': _numero(a['angulo'])}}
        if nome == 'motores':
            a = _argumentos(chamada, ['esquerdo', 'direito'])
            if len(a) != 2:
                raise NaoTemBloco
            return {'type': 'robo_motores', 'inputs': {'ESQ': {'block': self.valor(a['esquerdo'], 'Number')},
                                                       'DIR': {'block': self.valor(a['direito'], 'Number')}}}
        if nome == 'esperar':
            a = _argumentos(chamada, ['segundos'])
            return {'type': 'robo_esperar', 'fields': {'SEGUNDOS': _faixa(_numero(a.get('segundos')), 0)}}
        if nome == 'mostrar':
            a = _argumentos(chamada, ['texto', 'linha'])
            if 'texto' not in a:
                raise NaoTemBloco
            linha = str(_numero(a['linha'])) if 'linha' in a else '1'
            if linha not in ('1', '2', '3'):
                raise NaoTemBloco
            return {'type': 'robo_mostrar', 'fields': {'LINHA': linha}, 'inputs': {'TEXTO': {'block': self.valor(a['texto'])}}}
        if nome == 'tocar':
            a = _argumentos(chamada, ['frequencia', 'segundos'],
                            {'frequencia': ast.Constant(440), 'segundos': ast.Constant(1)})
            segundos = _faixa(_numero(a['segundos']), 0)
            if isinstance(a['frequencia'], ast.Constant) and isinstance(a['frequencia'].value, str):
                m = re.fullmatch(r'([a-z]+#?)([4-7]?)', a['frequencia'].value)
                if not m or m.group(1) not in NOTAS:
                    raise NaoTemBloco
                return {'type': 'robo_tocar_nota', 'fields': {'NOTA': m.group(1), 'OITAVA': m.group(2) or '5',
                                                             'SEGUNDOS': segundos}}
            return {'type': 'robo_tocar', 'fields': {'FREQ': _faixa(_numero(a['frequencia']), 300, 10000), 'SEGUNDOS': segundos}}
        if nome == 'melodia':
            a = _argumentos(chamada, ['notas', 'tempo'], {'tempo': ast.Constant(0.3)})
            return {'type': 'robo_melodia', 'fields': {'NOTAS': _texto(a.get('notas')), 'TEMPO': _faixa(_numero(a['tempo']), 0)}}
        if nome == 'luz':
            a = _argumentos(chamada, ['cor', 'piscar'], {'cor': ast.Constant('azul'), 'piscar': ast.Constant(False)})
            cor, piscar = _texto(a['cor']), a['piscar']
            if cor not in ('azul', 'roxo', 'vermelho') or not (isinstance(piscar, ast.Constant) and isinstance(piscar.value, bool)):
                raise NaoTemBloco
            return {'type': 'robo_luz', 'fields': {'COR': cor, 'PISCAR': 'TRUE' if piscar.value else 'FALSE'}}
        if nome == 'guardar':
            a = _argumentos(chamada, ['nome', 'valor'])
            texto = _texto(a.get('nome'))
            if 'valor' not in a or not re.fullmatch(r'[A-Za-z_]\w*', texto, re.ASCII):
                raise NaoTemBloco
            return {'type': 'robo_guardar', 'fields': {'NOME': texto}, 'inputs': {'VALOR': {'block': self.valor(a['valor'], 'Number')}}}
        if nome == 'zerar_motor':
            a = _argumentos(chamada, ['porta'])
            return {'type': 'robo_zerar_motor', 'fields': {'MOTOR': _porta(a.get('porta'), ('A', 'B', 'C', 'D'))}}
        if nome == 'zerar_giroscopio':
            a = _argumentos(chamada, ['porta'])
            return {'type': 'robo_zerar_giroscopio', 'fields': {'PORTA': _porta(a.get('porta'))}}
        raise NaoTemBloco

    def _variavel(self, nome):
        if nome not in self.variaveis:
            self.variaveis[nome] = f'var_{len(self.variaveis) + 1}'
        return self.variaveis[nome]

    def _se(self, testes_e_corpos, senao):
        """[(condição, corpo)] e o corpo do senão (ou None) -> bloco "se" com os "senão se"."""
        bloco = {'type': 'controls_if', 'inputs': {}}
        estado = {}
        if len(testes_e_corpos) > 1:
            estado['elseIfCount'] = len(testes_e_corpos) - 1
        if senao is not None:
            estado['hasElse'] = True
        if estado:
            bloco['extraState'] = estado
        for n, (teste, corpo) in enumerate(testes_e_corpos):
            bloco['inputs'][f'IF{n}'] = {'block': self.valor(teste, 'Boolean')}
            dentro = self.cadeia(corpo, teste.lineno + 1)
            if dentro:
                bloco['inputs'][f'DO{n}'] = {'block': dentro}
        if senao:
            dentro = self.cadeia(senao, testes_e_corpos[-1][1][-1].end_lineno + 1)
            if dentro:
                bloco['inputs']['ELSE'] = {'block': dentro}
        return bloco

    @staticmethod
    def _com_chamada(no, nome):
        """O nó da chamada de um "with nome(...):" (um só item, sem "as"), ou None."""
        if not isinstance(no, ast.With) or len(no.items) != 1 or no.items[0].optional_vars is not None:
            return None
        e = no.items[0].context_expr
        return e if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == nome else None

    def _instrucao(self, no, seguinte):
        """A instrução como lista de blocos (normalmente um só). Devolve (blocos, usou_o_seguinte)."""
        if isinstance(no, ast.ImportFrom) and no.module == 'robo' and [a.name for a in no.names] == ['*']:
            return [], False
        if isinstance(no, ast.Pass):
            return [], False
        if isinstance(no, ast.Expr) and isinstance(no.value, ast.Call) and isinstance(no.value.func, ast.Name):
            return [self._comando(no.value.func.id, no.value)], False
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            valor = self.valor(no.value)            # antes de criar a variável: "x = x + 1" lê a de antes
            nome = no.targets[0].id
            return [{'type': 'variables_set', 'fields': {'VAR': {'id': self._variavel(nome)}},
                     'inputs': {'VALUE': {'block': valor}}}], False
        if isinstance(no, ast.AugAssign) and isinstance(no.op, ast.Add) and isinstance(no.target, ast.Name) \
                and no.target.id in self.variaveis:
            return [{'type': 'math_change', 'fields': {'VAR': {'id': self.variaveis[no.target.id]}},
                     'inputs': {'DELTA': {'block': self.valor(no.value, 'Number')}}}], False
        if isinstance(no, ast.While) and not no.orelse:
            corpo = self.cadeia(no.body, no.lineno + 1)
            if isinstance(no.test, ast.Constant) and no.test.value is True:
                bloco = {'type': 'robo_para_sempre', 'inputs': {}}
            else:
                ate = isinstance(no.test, ast.UnaryOp) and isinstance(no.test.op, ast.Not)
                cond = no.test.operand if ate else no.test
                bloco = {'type': 'robo_enquanto', 'fields': {'MODO': 'ate' if ate else 'enquanto'},
                         'inputs': {'COND': {'block': self.valor(cond, 'Boolean')}}}
            if corpo:
                bloco['inputs']['FAZER'] = {'block': corpo}
            return [bloco], False
        # for com uma variável que o corpo não usa é o "repetir N vezes" (o gerador escreve for _ in range(N))
        if isinstance(no, ast.For) and not no.orelse and isinstance(no.target, ast.Name) \
                and not any(isinstance(n, ast.Name) and n.id == no.target.id for c in no.body for n in ast.walk(c)) \
                and isinstance(no.iter, ast.Call) and isinstance(no.iter.func, ast.Name) and no.iter.func.id == 'range' \
                and len(no.iter.args) == 1 and not no.iter.keywords:
            vezes = _numero(no.iter.args[0])
            if not isinstance(vezes, int) or vezes < 0:
                raise NaoTemBloco
            return [self._laco('robo_repetir', no, {'VEZES': vezes})], False
        if isinstance(no, ast.If):
            casos, resto = [(no.test, no.body)], no.orelse
            while len(resto) == 1 and isinstance(resto[0], ast.If):        # elif
                casos.append((resto[0].test, resto[0].body))
                resto = resto[0].orelse
            return [self._se(casos, resto or None)], False
        if self._com_chamada(no, 'para_sempre') and not self._com_chamada(no, 'para_sempre').args:
            return [self._laco('robo_para_sempre', no)], False
        chamada = self._com_chamada(no, 'repetir')
        if chamada and len(chamada.args) == 1 and not chamada.keywords:
            vezes = _numero(chamada.args[0])
            if isinstance(vezes, int) and vezes >= 0:
                return [self._laco('robo_repetir', no, {'VEZES': vezes})], False
        # with repetir_ate(...) fica em Python: o "while not" dos blocos confere a condição antes de começar
        for nome, tipo in SE_SENSOR.items():                # with se_ver_cor(1, PRETO): ... with senao(): ...
            chamada = self._com_chamada(no, nome)
            if chamada:
                bloco = {'type': tipo, 'fields': self._campos_do_se(nome, chamada), 'inputs': {}}
                senao = self._com_chamada(seguinte, 'senao') if seguinte is not None else None
                senao = senao if senao is not None and not senao.args and not senao.keywords else None
                for entrada, parte in (('FAZER', no), ('SENAO', seguinte if senao else None)):
                    dentro = self.cadeia(parte.body, parte.lineno + 1) if parte else None
                    if dentro:
                        bloco['inputs'][entrada] = {'block': dentro}
                return [bloco], senao is not None
        chamada = self._com_chamada(no, 'se')
        if chamada and len(chamada.args) == 1 and not chamada.keywords:
            senao = self._com_chamada(seguinte, 'senao') if seguinte is not None else None
            return [self._se([(chamada.args[0], no.body)], seguinte.body if senao else None)], bool(senao)
        raise NaoTemBloco

    @staticmethod
    def _campos_do_se(nome, chamada):
        """Os campos do bloco "se o sensor..." (porta, cor ou comparação e valor), ou NaoTemBloco."""
        if nome == 'se_ver_cor':
            a = _argumentos(chamada, ['porta', 'cor'])
            cor = a.get('cor')
            if not (isinstance(cor, ast.Name) and cor.id in CORES):
                raise NaoTemBloco
            return {'PORTA': _porta(a.get('porta')), 'COR': cor.id}
        if nome == 'se_tocado':
            return {'PORTA': _porta(_argumentos(chamada, ['porta']).get('porta'))}
        a = _argumentos(chamada, ['porta', 'comparacao', 'valor' if nome == 'se_luz' else 'cm'])
        comparacao = _texto(a.get('comparacao'))
        if comparacao not in ('<', '<=', '>', '>=', '=', '!='):
            raise NaoTemBloco
        return {'PORTA': _porta(a.get('porta')), 'OP': comparacao,
                'VALOR': _numero(a.get('valor' if nome == 'se_luz' else 'cm'))}

    def _laco(self, tipo, no, campos=None):
        bloco = {'type': tipo, 'inputs': {}}
        if campos:
            bloco['fields'] = campos
        dentro = self.cadeia(no.body, no.lineno + 1)
        if dentro:
            bloco['inputs']['FAZER'] = {'block': dentro}
        return bloco

    def _comentario_antes(self, no, desde):
        """O texto dos comentários entre a linha desde e a instrução (e o do fim da linha dela)."""
        linhas = [n for n in range(desde, no.lineno) if n in self.so_comentario and n not in self.usados]
        if no.lineno in self.comentarios and no.lineno not in self.so_comentario:
            linhas.append(no.lineno)
        self.usados.update(linhas)
        return '\n'.join(self.comentarios[n] for n in linhas if self.comentarios[n])

    def cadeia(self, corpo, desde=1):
        """Os blocos de uma lista de instruções, encadeados (o primeiro, com os outros em next).
        desde: a primeira linha do trecho (os comentários a partir dela vão para o primeiro bloco)."""
        lista, i = [], 0
        while i < len(corpo):
            no = corpo[i]
            seguinte = corpo[i + 1] if i + 1 < len(corpo) else None
            comentario = self._comentario_antes(no, desde)
            try:
                blocos, pulou = self._instrucao(no, seguinte)
            except NaoTemBloco:
                blocos, pulou = self._linhas_cruas(no), False
                self.usados.update(range(no.lineno, no.end_lineno + 1))     # os comentários de dentro vão no texto
            if comentario and blocos:
                blocos[0]['icons'] = {'comment': {'text': comentario, 'pinned': False, 'height': 80, 'width': 160}}
            elif comentario:            # comentário antes de um "from robo import *" ou "pass": linha "Python"
                lista.extend(self._bloco_python('# ' + c) for c in comentario.split('\n'))
            lista.extend(blocos)
            fim = (seguinte if pulou else no).end_lineno
            i += 2 if pulou else 1
            desde = fim + 1
        # comentários depois da última instrução do trecho (até o fim dele)
        if corpo:
            ultimo = max(n.end_lineno for n in corpo)
            limite = len(self.linhas) if corpo is self.arvore.body else ultimo + self._fim_do_trecho(ultimo, corpo[0].col_offset)
            for n in range(ultimo + 1, limite + 1):
                if n in self.so_comentario and n not in self.usados:
                    self.usados.add(n)
                    lista.append(self._bloco_python('# ' + self.comentarios[n]))
        for a, b in zip(lista, lista[1:]):
            a['next'] = {'block': b}
        return lista[0] if lista else None

    def _fim_do_trecho(self, ultimo, recuo):
        """Quantas linhas logo depois da linha ultimo ainda são do trecho (as com recuo igual ou maior)."""
        n = 0
        for linha in self.linhas[ultimo:]:
            if linha.strip() and (len(linha) - len(linha.lstrip())) < recuo:
                break
            n += 1
        return n

    def traduzir(self):
        self.arvore = ast.parse(self.fonte)
        corpo = self.cadeia(self.arvore.body)
        inicio = {'type': 'robo_inicio', 'x': 24, 'y': 24}
        if corpo:
            inicio['next'] = {'block': corpo}
        estado = {'blocks': {'languageVersion': 0, 'blocks': [inicio]}}
        if self.variaveis:
            estado['variables'] = [{'name': nome, 'id': i} for nome, i in self.variaveis.items()]
        return estado


def para_blocos(fonte):
    """{'estado': área de blocos do Blockly, 'python': quantas linhas ficaram sem bloco} ou {'erro': texto}."""
    try:
        t = Tradutor(fonte.replace('\r\n', '\n'))
        return {'estado': t.traduzir(), 'python': t.python}
    except SyntaxError as e:
        return {'erro': f'o programa tem um erro de escrita na linha {e.lineno}: corrija na aba Python antes '
                        '(o botão Simular mostra o que é)'}


def para_blocos_json(fonte):
    return json.dumps(para_blocos(fonte), ensure_ascii=False)


if __name__ == '__main__':                     # python para_blocos.py programa.py: mostra a área de blocos
    import sys
    with open(sys.argv[1], encoding='utf-8') as f:
        print(json.dumps(para_blocos(f.read()), ensure_ascii=False, indent=1))
