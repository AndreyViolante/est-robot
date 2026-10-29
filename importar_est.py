"""Abre um projeto da IDE EST (.est) e escreve o mesmo programa em Python, com os comandos do robo.py.

O .est é o arquivo que a IDE grava: um XML (em base64) em que cada bloco tem o tipo, o modo, os parâmetros
e a porta, e a ordem dos blocos e os fios de dados ficam em listas à parte. Este arquivo remonta os mesmos
blocos que o compilador do EST-ROBOT usa (blocos.py) e escreve o Python que gera esses blocos. Depois
confere: se o Python compila para os mesmos bytes que os blocos da IDE, a tradução é exata.

Uso:  python importar_est.py projeto.est                um .py por programa do projeto, na pasta da_ide/
      python importar_est.py projeto.est --saida pasta  em outra pasta
      python importar_est.py                            (Windows) abre a janela para escolher o .est
"""
import base64, html, json, keyword, os, re, subprocess, sys, tempfile, unicodedata

import blocos as _b
from blocos import Blk

CMP_SENSOR = ['==', '!=', '>', '>=', '<', '<=']        # campo de comparação dos blocos de sensor (0 a 5)
CMP_TEXTO = {'==': '=', '!=': '!=', '>': '>', '>=': '>=', '<': '<', '<=': '<='}     # como o robo.py escreve
CMP_BLOCO = {'1': '==', '2': '!=', '3': '>', '4': '>=', '5': '<', '6': '<='}       # bloco Comparar
CONTA = {'1': '+', '2': '-', '3': '*', '4': '/'}
CORES = {'1': 'PRETO', '2': 'AZUL', '3': 'VERDE', '4': 'AMARELO', '5': 'VERMELHO', '6': 'BRANCO', '7': 'MARROM'}
CORES_LUZ = {'0': 'azul', '1': 'roxo', '2': 'vermelho'}
SAIDA_DE_1_BYTE = {('3002', '1'), ('3008', '1'), ('3001', '1')}       # a tela mostra com uma conta a mais
NOMES_DE_BLOCO = {'1002': 'Motor Grande', '1003': 'Mover com Direção', '1004': 'Mover Tanque', '1005': 'Tela',
                  '1006': 'Som', '1007': 'Luz', '2002': 'Esperar', '2003': 'Repetir', '2004': 'Decisão (Switch)',
                  '3002': 'Sensor de Cor', '3003': 'Giroscópio', '3005': 'Rotação do Motor', '3007': 'Cronômetro',
                  '4001': 'Variável', '4004': 'Lógica', '4005': 'Matemática', '4006': 'Arredondar',
                  '4007': 'Comparar', '4010': 'Aleatório', '5005': 'Inverter Motor'}

COMO_USAR = ('Para ver rodando: abra o .py no VS Code e use Terminal > Executar Tarefa > Simular no computador '
             '(ou Ctrl+Shift+B para mandar ao robô).')


class Programa:
    """Um programa do projeto da IDE: o nome, a lista de blocos (começa pelo bloco de início) e os avisos."""
    def __init__(self, nome, blocos, avisos):
        self.nome, self.blocos, self.avisos = nome, blocos, avisos


# ---------------------------------------------------------------- ler o .est

def decodificar(dados):
    """Conteúdo do .est (bytes) -> texto do XML. O .est é base64; aceita também o XML direto."""
    bruto = dados.strip() if isinstance(dados, bytes) else dados.strip().encode('utf-8')
    if bruto.startswith(b'<'):
        texto = bruto.decode('utf-8', 'replace')
    else:
        try:
            texto = base64.b64decode(bruto).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            texto = ''
    if '<project' not in texto:
        raise ValueError('o arquivo não parece um projeto da IDE EST (.est)')
    return texto


def _atributos(texto):
    return {k: html.unescape(v) for k, v in re.findall(r'(\w+)="([^"]*)"', texto)}


def ler(dados):
    """Os programas principais do projeto [Programa] e os Meus Blocos {id: Programa} (o bloco 6001 chama o
    primeiro Meu Bloco, o 6002 o segundo...)."""
    xml = decodificar(dados)
    projeto = re.search(r'<project ([^>]*)>', xml)
    info = _atributos(projeto.group(1)).get('info', '') if projeto else ''
    ids = {n: int(i) for i, n in re.findall(r'myModuleId(\d+)myModuleName(.*?)myModuleInfo', info)}
    programas, meus = [], {}
    for topo in re.finditer(r'<top ([^>]*)>(.*?)</top>', xml, re.S):
        a = _atributos(topo.group(1))
        nome = a.get('name') or 'programa'
        if a.get('type') == '1':
            programas.append(_programa(nome, topo.group(2)))
        elif a.get('type') == '2' and nome in ids:                # o programa de um Meu Bloco
            meus[ids[nome]] = _programa(nome, topo.group(2), com_inicio=False)
    if not programas:
        raise ValueError('o projeto não tem nenhum programa')
    return programas, meus


def _programa(nome, corpo, com_inicio=True):
    m = re.search(r'<modulesInfos info="([^"]*)"', corpo)
    info = json.loads(html.unescape(m.group(1))) if m else {}
    blocos = {}
    for k, v in info.items():
        if not (k.isdigit() and isinstance(v, dict)):
            continue
        b = Blk(v.get('moduletype', '0'), v.get('modulestate', '0'), v.get('paramvalues', ''), v.get('portvalue', ' '))
        b.id_ide, b.pai = int(k), str(v.get('parentid', '0'))
        if b.t == '2003':
            b.label = (v.get('str5') or '01|').split('|')[0] or '01'
        blocos[int(k)] = b
    seguintes, anterior = {}, {}
    for r in re.finditer(r'<head_relation ([^/]*)/>', corpo):
        a = _atributos(r.group(1))
        pre, post = int(a.get('pre', -1)), int(a.get('post', -1))
        anterior[post] = pre
        seguintes.setdefault(pre, []).append(post)
    avisos = []
    fios = []
    for li in re.finditer(r'<line_info ([^>]*)>(.*?)</line_info>', corpo, re.S):
        origem = int(_atributos(li.group(1)).get('out_module_id', -1))
        for o in re.finditer(r'<line_info_other ([^/]*)/>', li.group(2)):
            a = _atributos(o.group(1))
            fios.append((origem, int(a['out_para_id']), int(a['in_module_id']), int(a['in_para_id'])))
    # como a IDE: de cada bloco, só o último fio gravado no .est vale (estc.compilar(compat_ide_fios=True))
    ultimo = {f[0]: i for i, f in enumerate(fios)}
    for i, (om, op, im, ip) in enumerate(fios):
        if om not in blocos or im not in blocos:
            continue
        if ultimo[om] != i:
            avisos.append(f'um bloco {NOMES_DE_BLOCO.get(blocos[om].t, blocos[om].t)} tinha mais de um fio saindo; '
                          'a IDE só usa o último, e a tradução faz igual')
            continue
        blocos[im].wires.append((ip, blocos[om], op))

    filhos = {}
    for i in sorted(blocos):
        filhos.setdefault(blocos[i].pai, []).append(i)
    vistos = set()

    def seguir(i, grupo):
        lista = []
        while i is not None and i not in vistos and i in grupo:
            vistos.add(i)
            b = blocos[i]
            lista.append(b)
            if b.t in ('2003', '2004'):
                b.b1 = ramo(i, 1)
                b.b2 = ramo(i, 2) if b.t == '2004' else []
            prox = [p for p in seguintes.get(i, []) if p in grupo]
            if len(prox) > 1:                      # a sequência se divide: partes ao mesmo tempo
                par = Blk(9001, 1, '', ' ')
                par.ramos = [seguir(p, grupo) for p in prox]
                lista.append(par)
                return lista
            i = prox[0] if prox else None
        return lista

    def ramo(i, n):
        grupo = set(filhos.get(str(i * 32768 + n), []))
        cabecas = [k for k in sorted(grupo) if anterior.get(k, -1) not in grupo]
        return seguir(cabecas[0], grupo) if cabecas else []

    grupo = set(filhos.get('0', []))
    inicio = next((i for i in sorted(grupo) if blocos[i].t == '2001'), None)
    if inicio is None and not com_inicio:                         # Meu Bloco: a primeira sequência
        inicio = next((i for i in sorted(grupo) if anterior.get(i, -1) not in grupo), None)
        if inicio is None:
            return Programa(nome, [], [])
    if inicio is None:
        raise ValueError(f'o programa "{nome}" não tem o bloco de início')
    lista = seguir(inicio, grupo)
    soltos = len(blocos) - len(vistos)
    if soltos:
        avisos.append(f'{soltos} bloco(s) soltos, sem ligação com o início, ficaram de fora (a IDE também não executa)')
    return Programa(nome, lista, avisos)


# ---------------------------------------------------------------- escrever em Python

def _numero(texto):
    try:
        v = float(str(texto).strip())
    except ValueError:
        return '0'
    return str(int(v)) if v.is_integer() and '.' not in str(texto) else repr(v)


def _porta(b):
    p = str(b.port).strip()
    return p if p in ('1', '2', '3', '4') else repr(p)


def _cores(campo):
    nomes = [CORES.get(d) for d in str(campo).strip()]
    return ' + '.join(n for n in nomes if n) or 'PRETO'


def _identificador(texto):
    t = unicodedata.normalize('NFKD', str(texto))
    t = re.sub(r'[^A-Za-z0-9_]', '_', ''.join(c for c in t if ord(c) < 128)).strip('_') or 'valor'
    return ('v_' + t) if t[0].isdigit() or keyword.iskeyword(t) else t


class _Tradutor:
    def __init__(self, funcoes):
        import robo
        self.funcoes = funcoes     # id do Meu Bloco (6001...) -> nome da função Python
        self.linhas = []
        self.nomes = {}            # id(bloco de dado) -> nome da variável Python
        self.juntos = {}           # id(bloco lógico E/OU) -> expressão (vai direto no if)
        self.usados = set(robo.__all__) | set(dir(__builtins__)) | {'robo'}
        self.aproximado = []       # por que a tradução não dá os mesmos bytes
        self.portas_tanque = []

    def aviso(self, texto):
        if texto not in self.aproximado:
            self.aproximado.append(texto)

    def nome(self, base):
        base = _identificador(base)
        nome, n = base, 2
        while nome in self.usados:
            nome, n = f'{base}_{n}', n + 1
        self.usados.add(nome)
        return nome

    def emitir(self, texto, nivel):
        self.linhas.append('    ' * nivel + texto)

    def fio(self, b, entrada):
        for ip, origem, _ in b.wires:
            if ip == entrada:
                return origem
        return None

    def valor(self, b, entrada, campo):
        """O que entra no bloco: o nome do valor ligado por fio ou o número do parâmetro."""
        origem = self.fio(b, entrada)
        if origem is None:
            return _numero(b.param(campo))
        if id(origem) in self.juntos:
            return self.juntos[id(origem)]
        if id(origem) in self.nomes:
            return self.nomes[id(origem)]
        self.aviso('um fio vem de um bloco que não foi traduzido')
        return '0'

    def dado(self, b, base, expr, nivel):
        nome = self.nome(base)
        self.nomes[id(b)] = nome
        self.emitir(f'{nome} = {expr}', nivel)

    def sem_comando(self, b, nivel, explicacao=''):
        nome = NOMES_DE_BLOCO.get(b.t, f'tipo {b.t}')
        self.emitir(f'# bloco {nome} (modo {b.mode}) da IDE: {explicacao or "ainda sem comando no EST-ROBOT"}', nivel)
        self.aviso(f'bloco {nome} (modo {b.mode}) sem comando no EST-ROBOT')

    def cadeia(self, lista, nivel):
        antes = sum(1 for linha in self.linhas if not linha.lstrip().startswith('#'))
        for b in lista:
            self.bloco(b, nivel)
        if sum(1 for linha in self.linhas if not linha.lstrip().startswith('#')) == antes:
            self.emitir('pass', nivel)

    # ---- cada bloco
    def bloco(self, b, nivel):
        t, m = b.t, b.mode
        metodo = getattr(self, f'_b{t}', None)
        if t == '2001':
            return
        if t == '9001':
            self.emitir('with ao_mesmo_tempo():', nivel)
            for ramo in b.ramos:
                self.emitir('with tarefa():', nivel + 1)
                self.cadeia(ramo, nivel + 2)
            self.aviso('a sequência dividida da IDE vira um "ao_mesmo_tempo" (que espera todas as partes acabarem)')
            return
        if t.startswith('6') and t.isdigit():
            funcao = self.funcoes.get(int(t))
            if funcao:
                self.emitir(f'{funcao}()', nivel)
                self.aviso('os Meus Blocos viram funções do Python (o mesmo movimento; no EST-ROBOT os blocos '
                           'da função entram no lugar de cada chamada)')
            else:
                self.emitir(f'# Meu Bloco {t} da IDE: não está neste projeto', nivel)
                self.aviso(f'o Meu Bloco {t} não está no projeto')
            return
        if metodo is None or metodo(b, m, nivel) is False:
            self.sem_comando(b, nivel)

    def _b3002(self, b, m, nivel):                    # sensor de cor
        if m == '2':
            return self.dado(b, f'luz{b.port}'.strip(), f'luz_refletida({_porta(b)})', nivel)
        if m == '1':
            return self.dado(b, f'cor{b.port}'.strip(), f'cor_vista({_porta(b)})', nivel)
        return False

    def _b3008(self, b, m, nivel):
        if m != '1':
            return False
        self.dado(b, f'toque{b.port}'.strip(), f'tocado({_porta(b)})', nivel)

    def _b3009(self, b, m, nivel):
        if m != '3':
            return False
        self.dado(b, f'dist{b.port}'.strip(), f'distancia({_porta(b)})', nivel)

    def _b3001(self, b, m, nivel):
        if m != '1':
            return False
        self.dado(b, 'botao', 'botao_apertado()', nivel)

    def _b3005(self, b, m, nivel):                    # rotação do motor
        leitura = {'1': ('graus', 'graus_do_motor'), '2': ('voltas', 'rotacoes_do_motor'),
                   '3': ('pot', 'potencia_do_motor')}
        if m == '7':
            return self.emitir(f'zerar_motor({_porta(b)})', nivel)
        if m not in leitura:
            return False
        base, funcao = leitura[m]
        self.dado(b, f'{base}{b.port}'.strip(), f'{funcao}({_porta(b)})', nivel)

    def _b3003(self, b, m, nivel):                    # giroscópio
        if m == '6':
            return self.emitir(f'zerar_giroscopio({_porta(b)})', nivel)
        if m not in ('1', '2'):
            return False
        funcao = 'giroscopio' if m == '1' else 'velocidade_do_giro'
        self.dado(b, f'giro{b.port}'.strip(), f'{funcao}({_porta(b)})', nivel)

    def _b3007(self, b, m, nivel):                    # cronômetro
        n = _numero(b.param(1))
        if m == '3':
            return self.emitir(f'zerar_cronometro({n})', nivel)
        if m != '1':
            return False
        self.dado(b, f'tempo{n}', f'cronometro({n})', nivel)

    def _b4006(self, b, m, nivel):                    # arredondar (só o "mais perto" tem comando)
        if m != '1':
            return False
        if self.fio(b, 1) is None:
            self.aviso('um arredondar só com número: o Python já arredonda (não precisa do bloco)')
        self.dado(b, 'arredondado', f'arredondar({self.valor(b, 1, 1)})', nivel)

    def _b4010(self, b, m, nivel):                    # aleatório (com os limites escritos no bloco)
        if m != '1' or self.fio(b, 1) is not None or self.fio(b, 2) is not None:
            return False
        self.dado(b, 'sorteio', f'aleatorio({_numero(b.param(1))}, {_numero(b.param(2))})', nivel)

    def _b4001(self, b, m, nivel):                    # variável numérica
        if m == '2':
            return self.dado(b, b.port, f'ler({str(b.port)!r})', nivel)
        if m == '5':
            return self.emitir(f'guardar({str(b.port)!r}, {self.valor(b, 7, 7)})', nivel)
        return False

    def _b4005(self, b, m, nivel):                    # matemática
        if m not in CONTA:
            return False
        if self.fio(b, 2) is None and self.fio(b, 3) is None:
            self.aviso('uma conta só com números: o Python já faz a conta (não precisa do bloco)')
        self.dado(b, 'conta', f'{self.valor(b, 2, 2)} {CONTA[m]} {self.valor(b, 3, 3)}', nivel)

    def _b4007(self, b, m, nivel):                    # comparar
        if m not in CMP_BLOCO:
            return False
        if self.fio(b, 1) is None and self.fio(b, 2) is not None:
            self.aviso('uma comparação com o número na frente fica invertida no Python (mesmo resultado)')
        self.dado(b, 'condicao', f'{self.valor(b, 1, 1)} {CMP_BLOCO[m]} {self.valor(b, 2, 2)}', nivel)

    def _b4004(self, b, m, nivel):                    # lógica E / OU: vai direto no if
        if m not in ('1', '2'):
            return False
        a, c = self.valor(b, 1, 1), self.valor(b, 2, 2)
        self.juntos[id(b)] = f'({a} {"and" if m == "1" else "or"} {c})'
        self.aviso('o E/OU lógico vira um "if" dentro do outro (mesmo resultado)')

    def _b1005(self, b, m, nivel):                    # tela
        if m != '1':
            return False
        if not 0 <= float(b.param(7) or 0) <= 40:
            self.emitir(f'# a IDE escrevia {str(b.port)!r} em y={_numero(b.param(7))}, abaixo da tela do robô '
                        '(não aparece): ficou de fora', nivel)
            self.aviso('um texto da tela estava abaixo da parte que o robô mostra e ficou de fora')
            return
        origem = self.fio(b, 0)
        if origem is not None:
            arg = self.valor(b, 0, 0)
            if (origem.t, origem.mode) in SAIDA_DE_1_BYTE:
                self.aviso('a tela mostra leituras de 1 byte com uma conta a mais (para o número aparecer certo)')
        else:
            texto = str(b.port)
            if texto != ''.join(c for c in unicodedata.normalize('NFKD', texto) if ord(c) < 128):
                self.aviso('a tela não mostra acentos: o texto vai sem eles')
            arg = repr(texto)
        y = float(b.param(7) or 0)
        x = _numero(b.param(6))
        limpar = b.param(1) == '0'
        linha = {0.0: 1, 20.0: 2, 40.0: 3}.get(y)
        partes = [arg]
        if linha and linha > 1:
            partes.append(f'linha={linha}')
        elif not linha:
            partes.append(f'y={_numero(b.param(7))}')
        if x != '0':
            partes.append(f'x={x}')
        if limpar != (y == 0):
            partes.append(f'limpar={limpar}')
        self.emitir(f'mostrar({", ".join(partes)})', nivel)

    def _b1006(self, b, m, nivel):                    # som
        if m != '3':
            return False
        vol = _numero(b.param(5))
        self.emitir(f'tocar({_numero(b.param(3))}, {_numero(b.param(4))}' + (f', {vol})' if vol != '100' else ')'), nivel)

    def _b1007(self, b, m, nivel):                    # luz
        if m == '1':
            return self.emitir('apagar_luz()', nivel)
        if m == '2':
            cor = CORES_LUZ.get(b.param(1).strip(), 'azul')
            return self.emitir(f"luz('{cor}'" + (', piscar=True)' if b.param(2).strip() == '1' else ')'), nivel)
        return False

    def _b2002(self, b, m, nivel):                    # esperar
        p = _porta(b)
        comparacao = lambda: CMP_TEXTO[CMP_SENSOR[int(_numero(b.param(8))) % 6]]
        if m == '67':
            return self.emitir(f'esperar({_numero(b.param(18))})', nivel)
        if m == '33':
            return self.emitir(f'esperar_toque({p})', nivel)
        if m == '35':
            return self.emitir(f"esperar_distancia({p}, '{comparacao()}', {_numero(b.param(6))})", nivel)
        if m == '4':
            return self.emitir(f"esperar_luz({p}, '{comparacao()}', {_numero(b.param(6))})", nivel)
        if m == '3':
            return self.emitir(f'esperar_cor({p}, {_cores(b.param(5))})', nivel)
        return False

    def _b1004(self, b, m, nivel):                    # Mover Tanque
        self.portas_tanque.append(str(b.port).strip().upper())
        frear = '' if b.param(3).strip() == '0' else ', frear=False'
        if m == '1':
            return self.emitir(f'parar({frear[2:]})', nivel)
        if m == '2':
            return self.emitir(f'motores({self.valor(b, 1, 1)}, {self.valor(b, 2, 2)})', nivel)
        quanto = {'3': ('segundos', 4), '4': ('graus', 5), '5': ('rotacoes', 6)}.get(m)
        if not quanto:
            return False
        if b.wires:
            return self.sem_comando(b, nivel, 'com valor ligado por fio, ainda sem comando no EST-ROBOT')
        self.emitir(f'mover({_numero(b.param(1))}, {_numero(b.param(2))}, {quanto[0]}={_numero(b.param(quanto[1]))}{frear})', nivel)

    def _b1002(self, b, m, nivel):                    # Motor Grande
        p = repr(str(b.port).strip().upper())
        frear = '' if b.param(2).strip() == '0' else ', frear=False'
        if b.wires:
            return self.sem_comando(b, nivel, 'com valor ligado por fio, ainda sem comando no EST-ROBOT')
        if m == '1':
            return self.emitir(f'desligar_motor({p}{frear})', nivel)
        if m == '2':
            return self.emitir(f'ligar_motor({p}, {_numero(b.param(1))})', nivel)
        quanto = {'3': ('segundos', 3), '4': ('graus', 4), '5': ('rotacoes', 5)}.get(m)
        if not quanto:
            return False
        self.emitir(f'motor({p}, {_numero(b.param(1))}, {quanto[0]}={_numero(b.param(quanto[1]))}{frear})', nivel)

    def _b1003(self, b, m, nivel):                    # Mover com Direção: só sem curva, com o Mover Tanque
        direcao = _numero(b.param(2))
        self.portas_tanque.append(str(b.port).strip().upper())
        if m == '1':
            self.aviso('o "Mover com Direção" virou o "Mover Tanque" (mesmo movimento)')
            return self.emitir('parar()' if b.param(3).strip() == '0' else 'parar(frear=False)', nivel)
        if direcao != '0' or b.wires:
            return self.sem_comando(b, nivel, 'com curva, ainda sem comando no EST-ROBOT')
        self.aviso('o "Mover com Direção" virou o "Mover Tanque" (mesmo movimento)')
        if m == '2':
            pot = _numero(b.param(1))
            return self.emitir(f'motores({pot}, {pot})', nivel)
        if m == '5':
            frear = '' if b.param(3).strip() == '0' else ', frear=False'
            return self.emitir(f'andar(rotacoes={_numero(b.param(6))}, potencia={_numero(b.param(1))}{frear})', nivel)
        return False

    def _b5005(self, b, m, nivel):                    # Inverter Motor
        porta = str(b.port).strip()
        if b.param(1).strip() == '0':
            self.emitir(f'# a IDE deixa o motor {porta} no sentido normal (não muda o movimento)', nivel)
            self.aviso('o bloco Inverter Motor no sentido normal ficou como comentário (não muda o movimento)')
            return
        self.emitir(f'# a IDE inverte o motor {porta} aqui: se forem os dois motores do robô, use '
                    'configurar(invertido=True)', nivel)
        self.aviso(f'o bloco Inverter Motor ({porta}) não foi traduzido: veja o comentário no programa')

    def _b2004(self, b, m, nivel):                    # decisão (Switch)
        p = _porta(b)
        if m == '37':
            origem = self.fio(b, 11)
            if origem is None:
                return self.sem_comando(b, nivel, 'decisão sem a condição ligada')
            cabeca = f'if {self.valor(b, 11, 11)}:'
            self.emitir(cabeca, nivel)
            self.cadeia(b.b1, nivel + 1)
            if b.b2:
                self.emitir('else:', nivel)
                self.cadeia(b.b2, nivel + 1)
            return
        if m == '4':
            cabeca = f'with se_ver_cor({p}, {_cores(b.param(3))}):'
        elif m == '5':
            cabeca = f"with se_luz({p}, '{CMP_TEXTO[CMP_SENSOR[int(_numero(b.param(5))) % 6]]}', {_numero(b.param(4))}):"
        elif m == '21':
            cabeca = f"with se_distancia({p}, '{CMP_TEXTO[CMP_SENSOR[int(_numero(b.param(5))) % 6]]}', {_numero(b.param(4))}):"
        elif m == '20':
            cabeca = f'with se_tocado({p}):'
        else:
            return False
        self.emitir(cabeca, nivel)
        self.cadeia(b.b1, nivel + 1)
        if b.b2:
            self.emitir('with senao():', nivel)
            self.cadeia(b.b2, nivel + 1)

    def _b2003(self, b, m, nivel):                    # repetir
        p = _porta(b)
        if m == '33':
            cabeca = 'while True:'
        elif m == '34':
            cabeca = f'for _ in range({_numero(b.param(12))}):'
        elif m == '35':
            if self.fio(b, 13) is None:
                return self.sem_comando(b, nivel, '"repetir até" sem a condição ligada')
            # a condição é medida no fim de cada volta: ela fica dentro do laço e o lambda a lê lá
            self.emitir('with repetir_ate(lambda: CONDICAO):', nivel)
            marca = len(self.linhas) - 1
            self.cadeia(b.b1, nivel + 1)
            condicao = self.valor(b, 13, 13)
            if condicao.startswith('('):
                self.aviso('um "repetir até" com E/OU lógico ainda não é traduzido (ficou só a primeira parte)')
                condicao = condicao[1:].split(' ')[0]
            self.linhas[marca] = self.linhas[marca].replace('CONDICAO', condicao)
            return
        elif m == '3':
            cabeca = f"with repetir_ate_luz({p}, '{CMP_TEXTO[CMP_SENSOR[int(_numero(b.param(5))) % 6]]}', {_numero(b.param(4))}):"
        elif m == '2':
            cabeca = f'with repetir_ate_cor({p}, {_cores(b.param(3))}):'
        else:
            return False
        if getattr(b, 'label', '01') != '01':
            self.aviso('o nome do laço na IDE não é 01 (só muda o lugar na memória)')
        self.emitir(cabeca, nivel)
        self.cadeia(b.b1, nivel + 1)


def para_python(programa, meus=None, arquivo=''):
    """O programa da IDE escrito em Python (texto) e a lista do que ficou aproximado. meus: os Meus Blocos
    {id: Programa}, que viram funções antes do programa."""
    meus = meus or {}
    funcoes = {}
    tr = _Tradutor(funcoes)
    for i in sorted(meus):
        funcoes[i] = tr.nome(meus[i].nome)
    usados = _meus_usados(programa.blocos, meus)
    for i in sorted(meus):
        if i not in usados:
            continue
        tr.emitir(f'def {funcoes[i]}():', 0)
        tr.emitir(f'"""Meu Bloco "{meus[i].nome}" da IDE."""', 1)
        corpo = [b for b in meus[i].blocos if b.t != '2001']
        tr.cadeia(corpo, 1)
        tr.emitir('', 0)
        tr.emitir('', 0)
    if usados:
        tr.emitir('# ---- o programa', 0)
    tr.cadeia(programa.blocos[1:], 0)
    cabeca = ['from robo import *', '']
    origem = f' do projeto "{os.path.basename(arquivo)}"' if arquivo else ''
    cabeca.append(f'# Programa "{programa.nome}"{origem} da IDE EST, traduzido pelo EST-ROBOT.')
    portas = sorted(set(tr.portas_tanque))
    if portas:
        p = portas[0] if len(portas[0]) == 3 and portas[0][1] == '+' else 'B+C'
        if len(portas) > 1:
            tr.aviso('blocos de movimento com motores diferentes: valem os do primeiro')
        cabeca.append('# Como na IDE: motores de cada lado e sem a pausa automática depois de cada movimento.')
        cabeca.append(f"configurar(esquerdo='{p[0]}', direito='{p[2]}', invertido=False, pausa=0)")
    cabeca.append('')
    return '\n'.join(cabeca + tr.linhas) + '\n', tr.aproximado


def _meus_usados(lista, meus, achados=None):
    """Os Meus Blocos chamados pelo programa (e pelos Meus Blocos que ele chama)."""
    achados = set() if achados is None else achados
    def percorre(blocos):
        for b in blocos:
            if b.t.isdigit() and b.t.startswith('6') and int(b.t) in meus and int(b.t) not in achados:
                achados.add(int(b.t))
                percorre(meus[int(b.t)].blocos)
            percorre(b.b1)
            percorre(b.b2)
            for ramo in getattr(b, 'ramos', []):
                percorre(ramo)
    percorre(lista)
    return achados


def _expandir(lista, meus, fundo=0):
    """Os blocos com uma cópia de cada Meu Bloco no lugar de cada chamada (como as funções no EST-ROBOT)."""
    import copy
    if fundo > 20:
        raise RecursionError('Meu Bloco chamando a si mesmo')
    saida = []
    for b in lista:
        if b.t.isdigit() and b.t.startswith('6') and int(b.t) in meus:
            corpo = copy.deepcopy([x for x in meus[int(b.t)].blocos if x.t != '2001'])
            saida.extend(_expandir(corpo, meus, fundo + 1))
            continue
        b.b1 = _expandir(b.b1, meus, fundo)
        b.b2 = _expandir(b.b2, meus, fundo)
        if hasattr(b, 'ramos'):
            b.ramos = [_expandir(r, meus, fundo) for r in b.ramos]
        saida.append(b)
    return saida


def conferir(programa, codigo, meus=None):
    """True se o Python compila para os mesmos bytes que os blocos da IDE (com os Meus Blocos no lugar de cada
    chamada); None se o compilador do EST-ROBOT ainda não sabe compilar algum bloco do programa da IDE."""
    import copy, estc, enviar, robo
    try:
        esperado = estc.compilar(_expandir(copy.deepcopy(programa.blocos), meus or {}))
    except (NotImplementedError, RecursionError):
        return None
    config, motores = dict(robo._config), _b.MOTORS
    pasta = tempfile.mkdtemp(prefix='est_importar_')
    arquivo = os.path.join(pasta, 'traduzido.py')
    try:
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(codigo)
        obtido = estc.compilar(enviar.carregar(arquivo))
    except Exception:
        return False
    finally:
        robo._config.clear()
        robo._config.update(config)
        _b.MOTORS = motores
        try:
            os.remove(arquivo)
            os.rmdir(pasta)
        except OSError:
            pass
    return obtido == esperado


def traduzir(dados, arquivo=''):
    """Lê o .est e traduz cada programa: [{nome, codigo, exata (True/False/None), avisos}] e os Meus Blocos."""
    programas, meus = ler(dados)
    saida = []
    for p in programas:
        codigo, aproximado = para_python(p, meus, arquivo)
        exata = conferir(p, codigo, meus)
        avisos = list(dict.fromkeys(p.avisos + [a for m in meus.values() for a in m.avisos] + aproximado))
        saida.append({'nome': p.nome, 'codigo': codigo, 'exata': exata, 'avisos': avisos})
    return saida, [meus[i].nome for i in sorted(meus)]


def traduzir_json(texto, arquivo=''):
    """Para a página de programar (Pyodide): o .est em texto -> JSON com os programas ou {erro}."""
    try:
        programas, meus = traduzir(texto, arquivo)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return json.dumps({'erro': str(e)}, ensure_ascii=False)
    return json.dumps({'programas': programas, 'meus_blocos': meus}, ensure_ascii=False)


# ---------------------------------------------------------------- linha de comando

def _escolher_arquivo():
    """A janela do Windows para escolher o .est (None se cancelar ou não der)."""
    if sys.platform != 'win32':
        return None
    script = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; "
              "$d.Title = 'Escolha o projeto da IDE EST'; $d.Filter = 'Projeto da IDE EST (*.est)|*.est'; "
              "if ($d.ShowDialog() -eq 'OK') { [Console]::OutputEncoding = [Text.Encoding]::UTF8; $d.FileName }")
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-STA', '-Command', script], capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None
    caminho = r.stdout.decode('utf-8', 'replace').strip()
    return caminho or None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    saida = sys.argv[sys.argv.index('--saida') + 1] if '--saida' in sys.argv[:-1] else 'da_ide'
    if '--saida' in sys.argv[:-1]:
        args = [a for a in args if a != saida]
    arquivo = args[0] if args else _escolher_arquivo()
    if not arquivo:
        sys.exit('Diga qual projeto abrir: python importar_est.py projeto.est')
    try:
        with open(arquivo, 'rb') as f:
            programas, meus = traduzir(f.read(), arquivo)
    except OSError:
        sys.exit(f'ERRO: não achei o arquivo {arquivo}')
    except ValueError as e:
        sys.exit(f'ERRO: {e}')
    os.makedirs(saida, exist_ok=True)
    print(f'Projeto da IDE: {os.path.basename(arquivo)}\n')
    for p in programas:
        destino = os.path.join(saida, f'{_identificador(p["nome"])}.py')
        with open(destino, 'w', encoding='utf-8') as f:
            f.write(p['codigo'])
        if p['exata']:
            estado = 'tradução exata: o Python gera os mesmos bytes que a IDE manda para o robô'
        elif p['exata'] is None:
            estado = 'traduzido, mas o EST-ROBOT ainda não compila algum bloco deste programa da IDE'
        else:
            estado = 'tradução aproximada: faz o mesmo, com alguns blocos diferentes'
        print(f'  "{p["nome"]}" -> {os.path.normpath(destino)}\n    {estado}')
        for a in p['avisos']:
            print(f'    - {a}')
    if meus:
        print(f'\nMeus Blocos do projeto (viram funções no .py): {", ".join(meus)}')
    print(f'\n{COMO_USAR}')


if __name__ == '__main__':
    main()
