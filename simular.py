"""Simula um programa no navegador, sem o robô.

Compila igual ao enviar.py e abre o simulador (pasta simulador/), que executa os mesmos bytes que
iriam para o robô: dá para ver o caminho, os sensores, a tela, a luz e o som.
Uso:  python simular.py meu_programa.py
      python simular.py meu_programa.py --sem-abrir    só prepara o simulador
"""
import json, os, sys, time, webbrowser
from pathlib import Path

import blocos
from enviar import anotar_linhas as _anotar_linhas, avisos_do_codigo, carregar, mostrar_aviso, _mostrar_erro
from estc import compilar, _Programa

PASTA = Path(__file__).resolve().parent / 'simulador'


def _ler_fonte(arquivo):
    try:
        with open(arquivo, encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(arquivo, encoding='latin-1') as f:
            return f.read()


def montar(arquivo):
    """Compila o arquivo e devolve o programa no formato que o simulador lê (um dicionário).
    Erros do aluno: mostra e sai, como o enviar.py. carregar() marca a linha de cada bloco (.linha)."""
    try:
        programa = carregar(arquivo)
        codigo = compilar(programa)
    except Exception as e:                      # o programa do aluno pode ter qualquer erro
        _mostrar_erro(e, arquivo)
        sys.exit(1)

    import avisos as _avisos, robo
    avisos = robo.avisos(programa)
    for aviso in avisos:
        print()
        print(f'AVISO: {aviso}')
        print()
    do_codigo = avisos_do_codigo(arquivo, programa)
    for aviso in do_codigo:
        mostrar_aviso(aviso, arquivo)
    avisos += [_avisos.como_texto(a) for a in do_codigo]

    import estc
    ocupa = estc.espaco(programa, codigo)
    if estc.aviso_do_espaco(ocupa):
        print(f'\nAVISO: {estc.aviso_do_espaco(ocupa)}\n')
        avisos.append(estc.aviso_do_espaco(ocupa))

    p = _Programa(programa, False)              # a mesma alocação que o compilar acabou de fazer
    return {
        'espaco': estc.texto_do_espaco(ocupa),
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


def montar_dbf(arquivo):
    """Um programa baixado do robô (.dbf, os bytes que estão gravados nele) no formato do simulador: roda igual,
    só sem o código Python ao lado (vale também para programa feito na IDE EST)."""
    with open(arquivo, 'rb') as f:
        codigo = f.read()
    return {'nome': os.path.basename(arquivo), 'gerado': time.strftime('%d/%m/%Y %H:%M:%S'), 'bytes': codigo.hex(),
            'fonte': '', 'linhas': [], 'variaveis': {}, 'avisos': []}


def preparar(arquivo):
    """Compila o arquivo (ou lê o .dbf baixado do robô) e grava simulador/programa.js. Devolve o programa
    (dicionário de montar)."""
    dados = montar_dbf(arquivo) if arquivo.lower().endswith('.dbf') else montar(arquivo)
    gravar(dados)
    return dados


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arquivo = sys.argv[1]
    if not arquivo.lower().endswith(('.py', '.dbf')):
        sys.exit('ERRO: abra um arquivo de programa (.py, ou um .dbf baixado do robô) antes de simular.')
    dados = preparar(arquivo)
    print(f'[OK] {os.path.basename(arquivo)}: {len(dados["bytes"]) // 2} bytes')
    if dados.get('espaco'):
        print(f'     {dados["espaco"]}')
    if '--sem-abrir' in sys.argv:
        return
    pagina = (PASTA / 'index.html').as_uri()
    if webbrowser.open(pagina):
        print('Simulador aberto no navegador: arraste o robô para a largada e aperte Executar.')
    else:
        print(f'Abra no navegador: {pagina}')


if __name__ == '__main__':
    main()
