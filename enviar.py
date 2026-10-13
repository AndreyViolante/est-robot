"""Compila um programa e envia ao robo (Ctrl+Shift+B no VS Code).

O programa pode ser escrito com robo.py (comandos em portugues, ex.: andar(rotacoes=2))
ou com blocos.py, definindo  PROGRAMA = [start(), ...]
Uso:  python enviar.py quadrado.py                 compila e envia
      python enviar.py quadrado.py --so-compilar   só compila (não precisa do robô)
"""
import difflib, importlib.util, inspect, os, re, sys, traceback

from estc import compilar


def carregar(arquivo):
    pasta = os.path.dirname(os.path.abspath(arquivo))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    import robo
    robo.novo_programa()
    spec = importlib.util.spec_from_file_location('programa_usuario', arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
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
    if isinstance(erro, SyntaxError):
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


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arquivo = sys.argv[1]
    if not arquivo.endswith('.py'):
        sys.exit('ERRO: abra um arquivo de programa (.py) antes de enviar.')
    nome = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(arquivo))[0])[:20] or 'programa'

    try:
        dados = compilar(carregar(arquivo))
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        _mostrar_erro(e, arquivo)
        sys.exit(1)
    print(f'[OK] {os.path.basename(arquivo)}: {len(dados)} bytes')

    if '--so-compilar' in sys.argv:
        return
    from est_protocol import upload
    try:
        upload(dados, prog_path=f'/vscode/{nome}')
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')


if __name__ == '__main__':
    main()
