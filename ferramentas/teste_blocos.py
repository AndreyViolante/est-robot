"""Ida e volta da aba Blocos da página de programar: o programa em Python vira blocos (docs/programar/para_blocos.py),
os blocos geram Python de novo (o gerador do modo_blocos.js, rodando no node com o Blockly) e os dois têm que
compilar para os mesmos bytes. Roda no GitHub a cada mudança.
Uso: python ferramentas/teste_blocos.py      (precisa do node e do Blockly: veja ferramentas/blocos_para_python.js)
"""
import json, os, re, subprocess, sys, tempfile

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, 'docs', 'programar'))

from enviar import carregar
from estc import compilar
import para_blocos

# usa todos os blocos da página: tem que virar só blocos (nenhum bloco "Python")
TODOS_OS_BLOCOS = """from robo import *

# todos os blocos da página
VEL = 30
andar(rotacoes=2)
andar(segundos=1, potencia=30)
andar(graus=360)
andar_cm(20)
re(rotacoes=1)
andar_cm(-15, potencia=40)
virar_direita(90)
virar_esquerda(45)
motores(VEL, -30)   # gira no lugar
parar()
esperar(0.5)
mostrar('Oi')
mostrar(distancia(4), linha=2)
tocar('la', 0.5)
tocar('do#6', 0.25)
tocar(880, 0.5)
melodia('do re mi', tempo=0.2)
bip()
luz('roxo', piscar=True)
apagar_luz()
guardar('contador', 0)
guardar('contador', ler('contador') + 1)
zerar_motor('B')
zerar_giroscopio(2)
zerar_cronometro()
erro = luz_refletida(1) - luz_refletida(2)
erro += 1
while True:
    # segue a linha
    if cor_vista(1) == VERDE and not tocado(4) == 1:
        motores(10, 30)
    elif graus_do_motor('B') > 360 or giroscopio(2) >= 90:
        parar()
    else:
        motores(25 + erro * 0.4, 25 - erro / 2)
    for _ in range(3):
        bip()
    while distancia(4) < 20:
        motores(-20, -20)
    while not luz_refletida(3) < 40:
        mostrar(cronometro())
    with se_ver_cor(1, PRETO):
        motores(10, 30)
    with senao():
        with se_luz(2, '<', 40):
            bip()
    with se_distancia(4, '<=', 20):
        parar()
    with se_tocado(4):
        bip()
    with senao():
        apagar_luz()
"""

# o que ainda não tem bloco vira blocos "Python", e o programa continua o mesmo
SEM_BLOCO = """from robo import *

def curva():
    # vira com a roda de dentro parada
    mover(30, 0, graus=200)

with ao_mesmo_tempo():
    with tarefa():
        andar_cm(30)
    with tarefa():
        melodia('do re mi')
curva()
esperar_toque(4)   # espera o toque
if luz_refletida(1) < 50:
    curva()
    # comentário no fim do if
x = aleatorio(1, 6)
mostrar(x)
"""


def casos():
    """(nome, programa, quantos blocos "Python" pode ter: None = tanto faz)."""
    lista = [('todos os blocos da página', TODOS_OS_BLOCOS, 0), ('o que não tem bloco', SEM_BLOCO, None)]
    lista.append(('exemplo 11', open(os.path.join(RAIZ, 'exemplos', '11_seguidor_dois_sensores.py'), encoding='utf-8').read(), 0))
    lista.append(('meu_programa.py', open(os.path.join(RAIZ, 'meu_programa.py'), encoding='utf-8').read(), 0))
    for guia in ('guia-obr.md', 'guia-do-professor.md'):
        texto = open(os.path.join(RAIZ, 'docs', guia), encoding='utf-8').read()
        for n, codigo in enumerate(re.findall(r'```python\n(.*?)```', texto, re.S), 1):
            if 'from robo import' in codigo:
                lista.append((f'{guia}, programa {n}', codigo, None))
    import verificar_gabaritos as vg
    with open(os.path.join(RAIZ, '.vscode', 'robo.code-snippets'), encoding='utf-8') as f:
        for atalho in json.load(f).values():
            codigo = vg.expandir_atalho(atalho['body'])
            lista.append((f'atalho {atalho["prefix"]}', codigo if codigo.startswith('from robo') else 'from robo import *\n\n' + codigo, None))
    for nome, com_if, com_with in vg.IF_WHILE:
        lista.append((f'if/while: {nome}', 'from robo import *\n\n' + com_if, None))
        lista.append((f'with: {nome}', 'from robo import *\n\n' + com_with, None))
    return lista


def main():
    lista, falhas = casos(), 0
    with tempfile.TemporaryDirectory() as pasta:
        arq = os.path.join(pasta, 'p.py')

        def bytes_de(codigo):
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(codigo)
            return compilar(carregar(arq))

        areas, originais = [], {}
        for nome, codigo, _ in lista:
            try:
                originais[nome] = bytes_de(codigo)
            except Exception as e:                  # o programa do guia/atalho não compila sozinho: fora do teste
                print(f'  ----  {nome}: não compila sozinho ({type(e).__name__}), fica fora')
                continue
            r = para_blocos.para_blocos(codigo)
            areas.append({'nome': nome, 'estado': r['estado'], 'python': r['python']})
        entrada, saida = os.path.join(pasta, 'areas.json'), os.path.join(pasta, 'codigos.json')
        with open(entrada, 'w', encoding='utf-8') as f:
            json.dump(areas, f, ensure_ascii=False)
        rodou = subprocess.run(['node', os.path.join(RAIZ, 'ferramentas', 'blocos_para_python.js'), entrada, saida])
        if rodou.returncode:
            sys.exit(rodou.returncode)
        with open(saida, encoding='utf-8') as f:
            gerados = {g['nome']: g for g in json.load(f)}
        maximo = {nome: m for nome, _, m in lista}
        for area in areas:
            nome, g = area['nome'], gerados[area['nome']]
            if g.get('erro'):
                certo, detalhe = False, f"os blocos não carregaram: {g['erro']}"
            else:
                try:
                    igual = bytes_de(g['codigo']) == originais[nome]
                    detalhe = '' if igual else 'o Python dos blocos compila diferente'
                except Exception as e:
                    igual, detalhe = False, f'o Python dos blocos não compila ({type(e).__name__}: {e})'
                cru_ok = maximo[nome] is None or area['python'] <= maximo[nome]
                if not cru_ok:
                    detalhe += f' {area["python"]} linha(s) viraram bloco "Python" (esperado: {maximo[nome]})'
                certo = igual and cru_ok
                if not certo:
                    detalhe += '\n' + '\n'.join('        | ' + l for l in g['codigo'].splitlines())
            falhas += not certo
            cru = f' ({area["python"]} bloco(s) "Python")' if area['python'] else ''
            print(f'  {"OK   " if certo else "FALHA"} {nome}{cru}' + (f' -> {detalhe}' if detalhe else ''))
    print(f'\nida e volta dos blocos: {"OK" if not falhas else f"{falhas} FALHA(S)"}')
    sys.exit(1 if falhas else 0)


if __name__ == '__main__':
    main()
