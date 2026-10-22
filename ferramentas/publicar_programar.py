"""Publica a página de programar pelo navegador (GitHub Pages, pasta docs/programar/).

A página compila no navegador, com o Python do Pyodide, usando os arquivos de verdade do projeto.
Este script copia para docs/programar/:
  projeto/     enviar.py, simular.py, robo.py e os arquivos do projeto que eles importam (blocos.py,
               estc.py...), o calibracao.py, mais arquivos.json, a lista que a página carrega
  exemplos/    os programas de exemplos/
  simulador/   a página do simulador (pasta simulador/), com um programa.js que pega o programa
               da página de programar
No fim, compila meu_programa.py e os exemplos pela ponte.py da página e confere que dão os mesmos bytes
do enviar.py. Rode de novo sempre que mudar o compilador, a linguagem, o simulador ou um exemplo. Essas
três pastas não se editam à mão; o resto de docs/programar/ (index.html, programar.js, ponte.py...) é a página.
Uso:  python ferramentas/publicar_programar.py
"""
import ast, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'ferramentas'))
import publicar_simulador

DESTINO = RAIZ / 'docs' / 'programar'
ENTRADAS = ['enviar', 'simular', 'robo']        # o que a ponte.py da página importa
NAO_COPIAR = {'est_protocol'}                   # no navegador o envio é o protocolo.js (WebHID)
EXTRAS = ['calibracao.py']                      # o robo.py lê da pasta dele (não é import)

# conferido junto com os exemplos: if/elif/else, while, and/or/not e for com sensores, como o aluno escreve
TESTE = """from robo import *

luz('roxo')
tocar('la', 0.3)
melodia('do re mi - sol:0.6')
for _ in range(3):
    andar_cm(10)
    virar_direita(90)
while distancia(4) > 20 and not tocado(3):
    if luz_refletida(1) < limite(1):
        motores(10, 40)
    elif luz_refletida(2) < limite(2) or cor_vista(3) == VERDE:
        motores(40, 10)
    else:
        motores(30, 30)
parar()
guardar('voltas', 0)
while True:
    guardar('voltas', ler('voltas') + 1)
    mostrar(ler('voltas'), linha=2)
    esperar(1)
"""

PROGRAMA_JS = """\
// Gerado por ferramentas/publicar_programar.py: este simulador mostra o programa que a página de
// programar (../index.html) acabou de compilar e guardou em window.ESTPROGRAMA.
try { window.PROGRAMA = (window.parent !== window && window.parent.ESTPROGRAMA) || null; }
catch (e) { window.PROGRAMA = null; }
"""


def modulos_do_projeto():
    """Os módulos do projeto que as ENTRADAS importam, direta ou indiretamente (olhando os import do código)."""
    achados, fila = [], list(ENTRADAS)
    while fila:
        nome = fila.pop(0)
        if nome in achados or nome in NAO_COPIAR or not (RAIZ / f'{nome}.py').is_file():
            continue
        achados.append(nome)
        arvore = ast.parse((RAIZ / f'{nome}.py').read_text(encoding='utf-8'))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                fila += [a.name.split('.')[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
                fila.append(no.module.split('.')[0])
    return sorted(achados)


def espelhar(origem, destino, arquivos):
    """Copia os arquivos para destino e apaga de lá os que não estão mais na lista."""
    destino.mkdir(parents=True, exist_ok=True)
    nomes = {a.name for a in arquivos}
    for velho in destino.iterdir():
        if velho.is_file() and velho.name not in nomes:
            velho.unlink()
    for arq in arquivos:
        shutil.copyfile(arq, destino / arq.name)


def conferir(arquivos):
    """Compila cada programa com a ponte.py da página e os arquivos copiados, e compara com o que o
    enviar.py gera num processo novo (enviar.carregar + estc.compilar, como no --so-compilar).
    Também confere o programa TESTE, com if/while/and/or/not/for."""
    sys.path[:0] = [str(DESTINO), str(DESTINO / 'projeto')]
    sys.dont_write_bytecode = True              # nada de __pycache__ dentro de docs/
    import ponte
    gerar = ('import sys; sys.path.insert(0, sys.argv[1]); import enviar, estc; '
             'sys.stdout.write(estc.compilar(enviar.carregar(sys.argv[2])).hex())')
    with tempfile.TemporaryDirectory() as pasta:
        teste = Path(pasta) / 'teste_if_while.py'
        teste.write_text(TESTE, encoding='utf-8')
        aluno = Path(pasta) / 'aluno'
        aluno.mkdir()
        ponte.PASTA_ALUNO, ponte.ARQUIVO = str(aluno), str(aluno / 'programa_do_aluno.py')
        for arq in arquivos + [teste]:
            r = ponte.compilar(arq.read_text(encoding='utf-8'), arq.name)
            if 'erro' in r:
                sys.exit(f'ERRO: a página não compila {arq.name}: {r["erro"]}')
            esperado = subprocess.run([sys.executable, '-c', gerar, str(RAIZ), str(arq)], capture_output=True,
                                      text=True, check=True).stdout
            if r['bytes'] != esperado:
                sys.exit(f'ERRO: na página {arq.name} dá bytes diferentes do enviar.py')
            nome = arq.relative_to(RAIZ).as_posix() if arq.is_relative_to(RAIZ) else f'{arq.name} (TESTE)'
            print(f'[OK] {nome}: {len(esperado) // 2} bytes, iguais aos do enviar.py')


def main():
    modulos = modulos_do_projeto()
    extras = [e for e in EXTRAS if (RAIZ / e).is_file()]
    espelhar(RAIZ, DESTINO / 'projeto', [RAIZ / f'{m}.py' for m in modulos] + [RAIZ / e for e in extras])

    titulos = {arq: titulo for arq, titulo, _ in publicar_simulador.EXEMPLOS}
    exemplos = sorted((RAIZ / 'exemplos').glob('*.py'))
    espelhar(RAIZ / 'exemplos', DESTINO / 'exemplos', exemplos)
    lista = {
        'arquivos': [f'{m}.py' for m in modulos] + extras,
        'exemplos': [{'arquivo': a.name, 'titulo': titulos.get(a.name, a.stem.replace('_', ' '))} for a in exemplos],
    }
    with open(DESTINO / 'projeto' / 'arquivos.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
        f.write('\n')

    origem = RAIZ / 'simulador'
    espelhar(origem, DESTINO / 'simulador', [a for a in origem.iterdir() if a.is_file() and a.name != 'programa.js'])
    with open(DESTINO / 'simulador' / 'programa.js', 'w', encoding='utf-8', newline='\n') as f:
        f.write(PROGRAMA_JS)

    print(f'[OK] docs/programar/projeto/: {", ".join(lista["arquivos"])}')
    print(f'[OK] docs/programar/simulador/: cópia de simulador/')
    conferir([a for a in [RAIZ / 'meu_programa.py'] if a.is_file()] + exemplos)
    print('Para conferir, sirva a pasta docs/ (python -m http.server --directory docs) e abra /programar/')


if __name__ == '__main__':
    main()
