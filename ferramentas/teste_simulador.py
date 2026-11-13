"""Testes do simulador: compila programas com os comandos do robo.py, roda no simulador (ferramentas/simulacao.js,
com o node) e confere como o robô terminou: ângulo do giroscópio, graus do motor, cronômetro, mensagens, o caminho
que o Dirigir escreve e o seguidor do exemplo. Roda no GitHub a cada mudança.
Uso: python ferramentas/teste_simulador.py      (precisa do node)
"""
import json, os, subprocess, sys, tempfile

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)

from enviar import carregar
from estc import compilar


def perto(valor, alvo, folga):
    return valor is not None and abs(float(str(valor).replace(',', '.')) - alvo) <= folga


# (nome, programa, segundos, pista, confere(resultado) -> True/False[, mais campos do caso, ex.: {'botao': 2}])
CASOS = [
    ('giroscópio: vira até 90 graus', """zerar_giroscopio(2)
while giroscopio(2) < 90:
    motores(20, -20)
parar()
mostrar(giroscopio(2))""", 10, 'livre', lambda r: perto(r['giro'], 90, 3) and perto(r['tela'][-1], 90, 3)),
    ('graus do motor: uma volta = 360', """zerar_motor('B')
motor('B', 50, graus=360)
mostrar(graus_do_motor('B'))""", 5, 'livre', lambda r: perto(r['tela'][-1], 360, 3)),
    ('rotações do motor: andar 2 rotações', """andar(rotacoes=2)
mostrar(rotacoes_do_motor('C'))""", 6, 'livre', lambda r: perto(r['tela'][-1], 2, 0.05)),
    ('zerar o motor no meio do caminho', """andar(rotacoes=1)
zerar_motor('B')
andar(rotacoes=0.5)
mostrar(graus_do_motor('B'))""", 8, 'livre', lambda r: perto(r['tela'][-1], 180, 3)),
    ('cronômetro: zerar e contar', """esperar(0.5)
zerar_cronometro(2)
esperar(1.5)
mostrar(cronometro(2))
mostrar(cronometro(1), linha=2, limpar=False)""", 5, 'livre',
     lambda r: perto(r['tela'][0], 1.5, 0.05) and perto(r['tela'][1], 2.0, 0.05)),
    ('aleatório e arredondar dão um inteiro de 1 a 3', """mostrar(arredondar(aleatorio(1, 6) / 2))""", 2, 'livre',
     lambda r: r['tela'][-1] in ('1', '2', '3')),
    ('mensagens: o simulador guarda o último valor de cada título', """ligar_bluetooth()
enviar_mensagem('tempo', 2.5)
enviar_mensagem('oi', 'ola', para='robo2')
enviar_mensagem('pronto', True)
enviar_mensagem('dobro', luz_refletida(1) * 2)""", 2, 'livre',
     lambda r: r['mensagens'] == {'tempo': {'para': 'EST-LAB', 'valor': 2.5}, 'oi': {'para': 'robo2', 'valor': 'ola'},
                                  'pronto': {'para': 'EST-LAB', 'valor': True},
                                  'dobro': {'para': 'EST-LAB', 'valor': 200}}),
    # o Dirigir do simulador escreve andar_cm e virar_*: o programa tem que refazer o mesmo caminho
    ('caminho do Dirigir: 20 cm e vira 90 à direita', """andar_cm(20)
virar_direita(90)""", 8, 'livre',
     lambda r: perto(r['x'], 20, 1.5) and perto(r['y'], 0, 1.5) and perto(r['ang'], 90, 3)),
    ('seguidor do exemplo 11 anda pela pista', open(os.path.join(RAIZ, 'exemplos', '11_seguidor_dois_sensores.py'),
                                                    encoding='utf-8').read(), 10, 'quadrado',
     lambda r: r['andou'] > 100),
    # o gráfico dos sensores no tempo: anota 50 vezes por segundo a leitura de cada sensor enquanto o robô anda; o
    # seguidor passa os sensores 1 e 2 pela borda da linha (escuro) e pelo chão (claro); o desenho reduzido não perde picos
    ('gráfico dos sensores: o seguidor vê a linha e o chão', open(os.path.join(RAIZ, 'exemplos', '11_seguidor_dois_sensores.py'),
                                                               encoding='utf-8').read(), 10, 'quadrado',
     lambda r: (abs(r['grafico']['anotacoes'] - 10 / 0.02) <= 2 and perto(r['grafico']['fim'], 10, 0.03)
                and all(r['grafico']['portas'][p]['min'] < 50 and r['grafico']['portas'][p]['max'] > 90 for p in '12')
                and set(r['grafico']['portas']) == {'1', '2', '3', '4'} and r['grafico']['reduzidoOk']
                and r['grafico']['maiorReduzido'] <= 4 * 150)),
    # botões da controladora: o simulador enche os 5 bytes da leitura como o robô do lab (13/11/2026)
    ('botão da controladora: nenhum apertado dá 0', """mostrar(botao_apertado())""", 1, 'livre',
     lambda r: r['tela'][-1] == '0'),
    ('botão da controladora: o de baixo dá BOTAO_BAIXO (5)', """mostrar(botao_apertado())
if botao_apertado() == BOTAO_BAIXO:
    mostrar('baixo', linha=2)""", 1, 'livre', lambda r: r['tela'] == ['5', 'baixo'], {'botao': 5}),
]


def main():
    entrada = []
    with tempfile.TemporaryDirectory() as pasta:
        arq = os.path.join(pasta, 'caso.py')
        for nome, codigo, segundos, pista, _, *mais in CASOS:
            if not codigo.startswith('from robo import'):
                codigo = 'from robo import *\n\n' + codigo
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(codigo + '\n')
            entrada.append({'nome': nome, 'hex': compilar(carregar(arq)).hex(), 'segundos': segundos, 'pista': pista,
                            **(mais[0] if mais else {})})
        casos, saida = os.path.join(pasta, 'casos.json'), os.path.join(pasta, 'resultado.json')
        with open(casos, 'w', encoding='utf-8') as f:
            json.dump(entrada, f)
        subprocess.run(['node', os.path.join(RAIZ, 'ferramentas', 'simulacao.js'), casos, saida], check=True)
        with open(saida, encoding='utf-8') as f:
            resultados = json.load(f)
    falhas = 0
    for (nome, _, _, _, confere, *_), r in zip(CASOS, resultados):
        nao_simulado = [a for a in r.get('avisos', []) if 'ainda não simulad' in a]
        try:
            certo = not r.get('erro') and not nao_simulado and confere(r)
        except (KeyError, IndexError, TypeError, ValueError):
            certo = False
        falhas += not certo
        n = lambda v: f'{v:.1f}' if isinstance(v, (int, float)) else str(v)
        detalhe = '' if certo else (f" -> erro: {r.get('erro')}; tela: {r.get('tela')}; x={n(r.get('x'))} "
                                    f"y={n(r.get('y'))} ângulo={n(r.get('ang'))} giro={n(r.get('giro'))}; "
                                    f"{nao_simulado or ''}")
        print(f'  {"OK   " if certo else "FALHA"} {nome}{detalhe}')
    print(f'\nsimulador: {"OK" if not falhas else f"{falhas} FALHA(S)"}')
    sys.exit(1 if falhas else 0)


if __name__ == '__main__':
    main()
