"""Simula um programa no navegador, sem o robô.

Compila igual ao enviar.py e abre o simulador (pasta simulador/), que executa os mesmos bytes que
iriam para o robô: dá para ver o caminho, os sensores, a tela, a luz e o som.
Uso:  python simular.py exemplos/2_quadrado.py
      python simular.py exemplos/2_quadrado.py --sem-abrir    só prepara o simulador
"""
import json, os, sys, time, webbrowser
from pathlib import Path

import blocos
from enviar import carregar, _mostrar_erro
from estc import compilar, _Programa

PASTA = Path(__file__).resolve().parent / 'simulador'


def _anotar_linhas(arquivo):
    """Faz cada bloco criado guardar a linha do arquivo do aluno que o criou. Devolve o __init__ original."""
    alvo = os.path.normcase(os.path.abspath(arquivo))
    original = blocos.Blk.__init__

    def __init__(self, *args, **kw):
        original(self, *args, **kw)
        quadro = sys._getframe(1)
        while quadro is not None:
            if os.path.normcase(os.path.abspath(quadro.f_code.co_filename)) == alvo:
                self.linha = quadro.f_lineno
                break
            quadro = quadro.f_back

    blocos.Blk.__init__ = __init__
    return original


def _ler_fonte(arquivo):
    try:
        with open(arquivo, encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(arquivo, encoding='latin-1') as f:
            return f.read()


def montar(arquivo):
    """Compila o arquivo e devolve o programa no formato que o simulador lê (um dicionário).
    Erros do aluno: mostra e sai, como o enviar.py."""
    original = _anotar_linhas(arquivo)
    try:
        programa = carregar(arquivo)
        codigo = compilar(programa)
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        _mostrar_erro(e, arquivo)
        sys.exit(1)
    finally:
        blocos.Blk.__init__ = original

    import robo
    avisos = robo.avisos(programa)
    for aviso in avisos:
        print()
        print(f'AVISO: {aviso}')
        print()

    p = _Programa(programa, False)              # a mesma alocação que o compilar acabou de fazer
    return {
        'nome': os.path.basename(arquivo),
        'gerado': time.strftime('%d/%m/%Y %H:%M:%S'),
        'bytes': codigo.hex(),
        'fonte': _ler_fonte(arquivo),
        'linhas': [getattr(b, 'linha', 0) for b in p.blocos()],     # linha de cada bloco, na ordem dos marcadores 48
        'variaveis': p.var,                                         # nome -> registrador
        'avisos': avisos,
    }


def gravar(dados, destino=PASTA / 'programa.js'):
    """Grava o programa (dicionário) ou uma lista de programas no arquivo que a página do simulador carrega."""
    lista = isinstance(dados, list)
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(f'// Gerado por simular.py: {"os programas compilados" if lista else "o programa compilado"}'
                ' (os mesmos bytes que vão para o robô).\n')
        f.write(f'window.{"PROGRAMAS" if lista else "PROGRAMA"} = ' + json.dumps(dados, indent=1) + ';\n')


def preparar(arquivo):
    """Compila o arquivo e grava simulador/programa.js. Devolve os bytes compilados."""
    dados = montar(arquivo)
    gravar(dados)
    return bytes.fromhex(dados['bytes'])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arquivo = sys.argv[1]
    if not arquivo.endswith('.py'):
        sys.exit('ERRO: abra um arquivo de programa (.py) antes de simular.')
    codigo = preparar(arquivo)
    print(f'[OK] {os.path.basename(arquivo)}: {len(codigo)} bytes')
    if '--sem-abrir' in sys.argv:
        return
    pagina = (PASTA / 'index.html').as_uri()
    if webbrowser.open(pagina):
        print('Simulador aberto no navegador: arraste o robô para a largada e aperte Executar.')
    else:
        print(f'Abra no navegador: {pagina}')


if __name__ == '__main__':
    main()
