"""Compila no navegador (Pyodide) o programa escrito na página programar/, com os arquivos do projeto.

Faz o mesmo que o computador faz: enviar.carregar + estc.compilar, os erros em português de
enviar.explicar, os avisos de robo.avisos e o programa no formato do simulador, como simular.montar.
robo.py, blocos.py, estc.py, enviar.py e simular.py são cópias feitas por ferramentas/publicar_programar.py.
"""
import contextlib, importlib.util, io, json, os, re, sys

sys.dont_write_bytecode = True          # o arquivo do aluno muda a cada compilação: nada de .pyc velho

PASTA_ALUNO = '/home/pyodide/aluno'
ARQUIVO = PASTA_ALUNO + '/programa_do_aluno.py'     # nome fixo: não esconde nenhum módulo do projeto
_ultimo = None          # (enviar, programa) da última compilação, para os avisos de portas antes do envio


def nome_no_robo(nome):
    """O nome com que o programa é gravado no robô (vscode/<nome>), com a mesma regra do enviar.py."""
    return re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(nome))[0])[:20] or 'programa'


def _esquecer_projeto():
    """Tira do sys.modules os módulos da pasta do projeto (robo, blocos, estc...): cada compilação começa
    do zero, como um "python enviar.py" novo, e o configurar() de um programa não passa para o próximo."""
    pasta = os.path.dirname(os.path.abspath(importlib.util.find_spec('robo').origin))
    for nome, modulo in list(sys.modules.items()):
        arquivo = getattr(modulo, '__file__', None)
        if nome != __name__ and arquivo and os.path.dirname(os.path.abspath(arquivo)) == pasta:
            del sys.modules[nome]


def compilar(fonte, nome='meu_programa.py'):
    """Devolve um dicionário: bytes (hex), linhas, variaveis, avisos e saida (o que o programa imprimiu),
    ou erro = {linha, codigo, texto}."""
    _esquecer_projeto()
    import enviar, estc, simular

    os.makedirs(PASTA_ALUNO, exist_ok=True)
    with open(ARQUIVO, 'w', encoding='utf-8') as f:
        f.write(fonte)

    saida = io.StringIO()
    original = simular._anotar_linhas(ARQUIVO)
    try:
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
            programa = enviar.carregar(ARQUIVO)
            codigo = estc.compilar(programa)
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        linha, trecho, texto = enviar.explicar(e, ARQUIVO)
        return {'erro': {'linha': linha, 'codigo': trecho, 'texto': texto}, 'saida': saida.getvalue()}
    finally:
        simular.blocos.Blk.__init__ = original

    global _ultimo
    _ultimo = (enviar, programa)
    import robo
    p = estc._Programa(programa, False)         # a mesma alocação que o compilar acabou de fazer
    return {
        'nome': nome,
        'nome_no_robo': nome_no_robo(nome),
        'bytes': codigo.hex(),
        'linhas': [getattr(b, 'linha', 0) for b in p.blocos()],
        'variaveis': p.var,
        'avisos': robo.avisos(programa),
        'saida': saida.getvalue(),
    }


def compilar_json(fonte, nome='meu_programa.py'):
    return json.dumps(compilar(fonte, nome), ensure_ascii=False)


def importar_est_json(texto, arquivo=''):
    """Um projeto da IDE EST (.est) traduzido para Python, como o importar_est.py do computador."""
    _esquecer_projeto()
    import importar_est
    return importar_est.traduzir_json(texto, arquivo)


def avisos_de_portas_json(ligadas_json):
    """Os avisos do enviar.py para as portas que o último programa usa e em que o robô não tem nada ligado."""
    if _ultimo is None or not hasattr(_ultimo[0], 'avisos_de_portas'):
        return '[]'
    enviar, programa = _ultimo
    return json.dumps(enviar.avisos_de_portas(programa, json.loads(ligadas_json)), ensure_ascii=False)
