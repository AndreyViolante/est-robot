"""Compila um programa e envia ao robo (Ctrl+Shift+B no VS Code).

O programa pode ser escrito com robo.py (comandos em portugues, ex.: andar(rotacoes=2))
ou com blocos.py, definindo  PROGRAMA = [start(), ...]
Uso:  python enviar.py quadrado.py                 compila, envia e já executa
      python enviar.py quadrado.py --so-gravar     envia sem executar (iniciar pelo menu do robô)
      python enviar.py quadrado.py --so-compilar   só compila (não precisa do robô)
"""
import ast, difflib, inspect, os, re, subprocess, sys, tokenize, traceback, types

from estc import compilar


class _IfWhileDoRobo(ast.NodeTransformer):
    """Troca cada if/while do programa por robo._Decisao/_Repeticao, que montam os blocos se/senão/repetir
    quando a condição vem do robô (sensor, variável) e deixam o if/while normal quando ela é do Python.

        if T: A else: B          _rb1 = __robo__._Decisao(T)
                                 if _rb1.sim(): A
                                 _rb1.fim()
                                 if _rb1.nao(): B
                                 _rb1.fim()

        while T: A               _rb2 = __robo__._Repeticao(lambda: T)
                                 while _rb2.volta(): A
                                 _rb2.fim()

    E também: a and b -> __robo__._e(lambda: a, lambda: b); a or b -> __robo__._ou(...);
    not a -> __robo__._nao_geral(a); for _ in range(n) (variável sem uso) -> for _rb3 in __robo__._vezes(n).
    """
    def __init__(self, arvore):
        self.n = 0
        self.usados = {no.id for no in ast.walk(arvore) if isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load)}

    def _nome(self):
        self.n += 1
        return f'_rb{self.n}'

    @staticmethod
    def _chama(var, metodo):
        return ast.Call(ast.Attribute(ast.Name(var, ast.Load()), metodo, ast.Load()), [], [])

    @staticmethod
    def _teste(no):
        if isinstance(no.test, ast.UnaryOp) and isinstance(no.test.op, ast.Not):
            return no.test.operand, True
        return no.test, False

    def _cria(self, var, classe, argumentos, negar, extras=()):
        robo_ = ast.Attribute(ast.Name('__robo__', ast.Load()), classe, ast.Load())
        palavras = [ast.keyword('negar', ast.Constant(negar))] + list(extras)
        return ast.Assign([ast.Name(var, ast.Store())], ast.Call(robo_, argumentos, palavras))

    @staticmethod
    def _robo(funcao, argumentos):
        return ast.Call(ast.Attribute(ast.Name('__robo__', ast.Load()), funcao, ast.Load()), argumentos, [])

    def visit_BoolOp(self, no):
        self.generic_visit(no)
        if any(isinstance(n, (ast.NamedExpr, ast.Yield, ast.YieldFrom, ast.Await))
               for v in no.values for n in ast.walk(v)):
            return no                                   # := e yield não cabem num lambda
        partes = [ast.Lambda(ast.arguments([], [], None, [], [], None, []), v) for v in no.values]
        return _na_linha(self._robo('_e' if isinstance(no.op, ast.And) else '_ou', partes), no)

    def visit_UnaryOp(self, no):
        self.generic_visit(no)
        if not isinstance(no.op, ast.Not):
            return no
        return _na_linha(self._robo('_nao_geral', [no.operand]), no)

    def visit_For(self, no):
        self.generic_visit(no)
        it = no.iter
        if (isinstance(no.target, ast.Name) and no.target.id not in self.usados and not no.orelse
                and isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'range'
                and len(it.args) == 1 and not it.keywords
                and not any(isinstance(n, (ast.Break, ast.Continue)) for n in _sem_lacos_internos(no.body))):
            no.target = ast.Name(self._nome(), ast.Store())
            no.iter = self._robo('_vezes', it.args)
            _na_linha(no, no)
        return no

    def visit_If(self, no):
        self.generic_visit(no)
        teste, negar = self._teste(no)
        var = self._nome()
        novos = [self._cria(var, '_Decisao', [teste], negar),
                 ast.If(self._chama(var, 'sim'), no.body, []),
                 ast.Expr(self._chama(var, 'fim'))]
        if no.orelse:
            novos += [ast.If(self._chama(var, 'nao'), no.orelse, []), ast.Expr(self._chama(var, 'fim'))]
        return [_na_linha(n, no) for n in novos]

    def visit_While(self, no):
        self.generic_visit(no)
        if no.orelse:
            return no                                   # while ... else: fica do jeito do Python
        tem_break = any(isinstance(n, (ast.Break, ast.Continue)) for n in _sem_lacos_internos(no.body))
        if isinstance(no.test, ast.Constant) and no.test.value is True:
            if tem_break:
                return no                               # while True com break: lógica do Python
            sempre = ast.Call(ast.Attribute(ast.Name('__robo__', ast.Load()), 'para_sempre', ast.Load()), [], [])
            return ast.copy_location(ast.With([ast.withitem(sempre)], no.body), no)
        teste, negar = self._teste(no)
        var = self._nome()
        condicao = ast.Lambda(ast.arguments([], [], None, [], [], None, []), teste)
        novos = [self._cria(var, '_Repeticao', [condicao], negar, [ast.keyword('tem_break', ast.Constant(tem_break))]),
                 ast.While(self._chama(var, 'volta'), no.body, []),
                 ast.Expr(self._chama(var, 'fim'))]
        return [_na_linha(n, no) for n in novos]


def _na_linha(novo, original):
    """Os pedaços criados ficam na linha do if/while original: um erro neles aponta para essa linha."""
    for no in ast.walk(novo):
        if isinstance(no, (ast.stmt, ast.expr)) and getattr(no, 'lineno', None) is None:
            no.lineno = no.end_lineno = original.lineno
            no.col_offset = no.end_col_offset = original.col_offset
    return novo


def _sem_lacos_internos(corpo):
    """Os comandos de um laço, sem entrar em laços e funções de dentro (o break deles é deles)."""
    for no in corpo:
        yield no
        if not isinstance(no, (ast.For, ast.While, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for campo in ('body', 'orelse', 'finalbody', 'handlers'):
                yield from _sem_lacos_internos(getattr(no, campo, []) or [])


def carregar(arquivo):
    pasta = os.path.dirname(os.path.abspath(arquivo))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    import robo
    robo.novo_programa()
    with tokenize.open(arquivo) as f:
        arvore = ast.parse(f.read(), filename=arquivo)
    arvore = ast.fix_missing_locations(_IfWhileDoRobo(arvore).visit(arvore))
    mod = types.ModuleType('programa_usuario')
    mod.__file__ = arquivo
    mod.__robo__ = robo
    exec(compile(arvore, arquivo, 'exec'), mod.__dict__)
    if hasattr(mod, 'PROGRAMA'):
        return mod.PROGRAMA
    feito = robo.programa()
    if len(feito) > 1:
        return feito
    raise ValueError('o programa não tem nenhum comando para o robô (comece com: from robo import *)')


# ---------------------------------------------------------------- mensagens de erro para alunos

_SINTAXE = [
    ("expected ':'", 'faltou o ":" no fim da linha'),
    ('expected an indented block', 'as linhas de dentro de um "with ...:" precisam começar com espaços (4 espaços ou Tab)'),
    ('unexpected indent', 'tem espaço a mais no começo desta linha'),
    ('unindent does not match', 'os espaços no começo desta linha não batem com os das linhas de cima'),
    ('was never closed', 'faltou fechar um parêntese "(" ou colchete "["'),
    ('unterminated string', 'faltou fechar as aspas do texto'),
    ("unmatched ')'", 'tem um parêntese ")" sobrando'),
    ('positional argument follows keyword', 'número com vírgula? use ponto: 0.5 (e não 0,5)'),
    ('Perhaps you forgot a comma', 'parece que faltou uma vírgula entre dois valores'),
    ('invalid decimal literal', 'número escrito errado (use ponto: 0.5, e não 0,5)'),
    ('invalid character', 'tem um caractere estranho nesta linha (aspas curvas copiadas de outro lugar?)'),
    ('invalid syntax', 'tem algo escrito errado nesta linha'),
]


def _comandos():
    import robo
    return list(robo.__all__)


def _sugestao(nome, opcoes):
    perto = difflib.get_close_matches(nome, opcoes, n=1, cutoff=0.6)
    if not perto:
        perto = [o for o in opcoes if o.lower() == nome.lower()]
    return f' Você quis dizer "{perto[0]}"?' if perto else ''


def _parametros(funcao):
    import robo
    f = getattr(robo, funcao, None)
    return list(inspect.signature(f).parameters) if callable(f) else []


def explicar(erro, arquivo):
    """Transforma um erro do programa do aluno numa mensagem curta em portugues: (linha, texto, mensagem)."""
    linha, codigo = None, ''
    if isinstance(erro, SyntaxError) and erro.lineno is not None:      # erro de digitação (o robo.py levanta sem linha)
        linha, codigo = erro.lineno, (erro.text or '').rstrip()
        texto = next((pt for en, pt in _SINTAXE if en in str(erro.msg)), f'erro de escrita: {erro.msg}')
        return linha, codigo, texto

    alvo = os.path.normcase(os.path.abspath(arquivo))
    for quadro in traceback.extract_tb(erro.__traceback__):
        if os.path.normcase(os.path.abspath(quadro.filename)) == alvo:
            linha, codigo = quadro.lineno, (quadro.line or '').rstrip()
    msg = str(erro)

    if isinstance(erro, NameError):
        nome = getattr(erro, 'name', None) or re.findall(r"'(\w+)'", msg)[0]
        if nome in _comandos():
            return linha, codigo, f'"{nome}" só funciona se a primeira linha do programa for:  from robo import *'
        texto = f'não conheço "{nome}".' + _sugestao(nome, _comandos())
        if not _sugestao(nome, _comandos()):
            texto += ' Confira se escreveu certo e se a primeira linha é:  from robo import *'
        return linha, codigo, texto

    if isinstance(erro, TypeError):
        m = re.match(r"(\w+)\(\) got an unexpected keyword argument '(\w+)'", msg)
        if m:
            opcoes = _parametros(m[1])
            return linha, codigo, (f'o comando {m[1]} não tem a opção "{m[2]}".' + _sugestao(m[2], opcoes)
                                   + (f' Opções: {", ".join(opcoes)}.' if opcoes else ''))
        m = re.match(r"(\w+)\(\) missing \d+ required positional arguments?: (.+)", msg)
        if m:
            return linha, codigo, f'faltou informar {m[2].replace(chr(39), "")} no comando {m[1]}(...)'
        m = re.match(r"(\w+)\(\) takes .* but \d+ (were|was) given", msg)
        if m:
            return linha, codigo, f'o comando {m[1]}(...) recebeu valores demais'

    if isinstance(erro, (TypeError, ValueError, SyntaxError, RuntimeError, NotImplementedError)):
        return linha, codigo, msg
    return linha, codigo, f'{type(erro).__name__}: {msg}'


def _mostrar_erro(erro, arquivo):
    linha, codigo, texto = explicar(erro, arquivo)
    onde = f' na linha {linha}' if linha else ''
    print(f'\nERRO{onde} de {os.path.basename(arquivo)}:')
    if codigo:
        print(f'    {codigo.strip()}')
    print(f'  {texto}\n')


def ide_est_aberta():
    """True se a IDE EST (maintest.exe) estiver aberta: ela conversa com o robô junto e atrapalha o envio."""
    if os.name != 'nt':
        return False
    try:
        saida = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq maintest.exe', '/NH'],
                               capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return 'maintest.exe' in saida.lower()


_SENSORES = {'3002', '3008', '3009', '2002', '2003', '2004'}      # blocos que leem um sensor numa porta
_MOTORES = {'1001', '1002', '1003', '1004'}


def portas_usadas(programa):
    """{porta: 'sensor' | 'motor'} das portas que os blocos do programa usam."""
    usadas = {}

    def percorre(blocos):
        for b in blocos:
            porta = str(b.port).strip().upper()
            if b.t in _SENSORES and porta in ('1', '2', '3', '4'):
                usadas[porta] = 'sensor'
            elif b.t in _MOTORES:
                for p in porta.split('+'):
                    if p in ('A', 'B', 'C', 'D'):
                        usadas[p] = 'motor'
            percorre(b.b1); percorre(b.b2)
            for ramo in getattr(b, 'ramos', []):
                percorre(ramo)
    percorre(programa)
    return usadas


def avisos_de_portas(programa, ligadas):
    """Avisa quando o programa usa uma porta em que o robô diz não ter nada ligado."""
    avisos = []
    for porta, coisa in sorted(portas_usadas(programa).items()):
        if porta not in ligadas:
            if coisa == 'sensor':
                avisos.append(f'o programa usa o sensor da porta {porta}, mas o robô não tem nada ligado nela. '
                              f'Confira o cabo e a porta.')
            else:
                avisos.append(f'o programa usa o motor da porta {porta}, mas o robô não tem motor ligado nela. '
                              f'Confira o cabo, ou as portas MOTOR_ESQUERDO e MOTOR_DIREITO no calibracao.py.')
    return avisos


AVISO_IDE = ('AVISO: a IDE EST está aberta. Ela fica conversando com o robô ao mesmo tempo e pode '
             'atrapalhar o envio. Feche a IDE se o programa não começar.')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arquivo = sys.argv[1]
    if not arquivo.endswith('.py'):
        sys.exit('ERRO: abra um arquivo de programa (.py) antes de enviar.')
    nome = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(arquivo))[0])[:20] or 'programa'

    try:
        programa = carregar(arquivo)
        dados = compilar(programa)
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        _mostrar_erro(e, arquivo)
        sys.exit(1)
    import robo
    for aviso in robo.avisos(programa):
        print()
        print(f'AVISO: {aviso}')
        print()
    print(f'[OK] {os.path.basename(arquivo)}: {len(dados)} bytes')

    if '--so-compilar' in sys.argv:
        return
    from est_protocol import portas_ligadas, upload
    if ide_est_aberta():
        print(f'\n{AVISO_IDE}\n')
    ligadas = portas_ligadas()
    if ligadas is not None:
        for aviso in avisos_de_portas(programa, ligadas):
            print(f'\nAVISO: {aviso}\n')
    so_gravar = '--so-gravar' in sys.argv
    try:
        upload(dados, prog_path=f'/vscode/{nome}', executar=not so_gravar)
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    if so_gravar:
        print(f'Gravado no robô como vscode/{nome}: inicie pelo menu do robô.')


if __name__ == '__main__':
    main()
