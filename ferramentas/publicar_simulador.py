"""Publica a demonstração do simulador na página do projeto (GitHub Pages, pasta docs/).

Copia a página do simulador (pasta simulador/) para docs/simulador/ e grava lá, em programa.js,
os exemplos já compilados por simular.py, cada um com a pista em que ele faz sentido.
Rode de novo sempre que mudar o simulador ou um exemplo; docs/simulador/ não se edita à mão.
Uso:  python ferramentas/publicar_simulador.py
"""
import shutil, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import robo
import simular

ORIGEM = RAIZ / 'simulador'
DESTINO = RAIZ / 'docs' / 'simulador'

# arquivo em exemplos/, nome no seletor, pista escolhida ao abrir (ids em simulador/mundo.js)
EXEMPLOS = [
    ('1_andar_e_virar.py',          'Andar e virar',                  'livre'),
    ('2_quadrado.py',               'Quadrado',                       'livre'),
    ('3_seguidor_liga_desliga.py',  'Seguidor liga-desliga',          'oval'),
    ('4_seguidor_proporcional.py',  'Seguidor proporcional',          'oval'),
    ('5_desviar_obstaculo.py',      'Desviar do obstáculo',           'arena'),
    ('6_botao_de_toque.py',         'Botão de toque',                 'livre'),
    ('7_mostrar_sensor.py',         'Mostrar o sensor na tela',       'oval'),
    ('8_contador.py',               'Contador',                       'livre'),
    ('9_seguidor_pid.py',           'Seguidor PID',                   'oval'),
    ('10_seguidor_pid_90.py',       'Seguidor PID com curvas de 90°', 'curvas90'),
    ('11_seguidor_dois_sensores.py', 'Seguidor básico com dois sensores', 'quadrado'),
]
INICIAL = '11_seguidor_dois_sensores.py'      # o exemplo que a demonstração mostra ao abrir


def main():
    configuracao = dict(robo._config)
    programas = []
    for arquivo, titulo, pista in EXEMPLOS:
        robo._config.update(configuracao)           # o configurar() de um exemplo não passa para o próximo
        dados = simular.montar(str(RAIZ / 'exemplos' / arquivo))
        del dados['gerado']                         # sem data: o arquivo só muda quando um programa muda
        dados.update(titulo=titulo, pista=pista)
        if arquivo == INICIAL:
            dados['inicial'] = True
        programas.append(dados)
        print(f'[OK] {arquivo}: {len(dados["bytes"]) // 2} bytes, pista {pista}')

    listados = {e[0] for e in EXEMPLOS}
    for arq in sorted((RAIZ / 'exemplos').glob('*.py')):
        if arq.name not in listados:
            print(f'(fora da demonstração: exemplos/{arq.name}; para incluir, ponha na lista EXEMPLOS)')

    # a página é cópia da pasta simulador/, menos o programa.js de lá (o do aluno)
    DESTINO.mkdir(parents=True, exist_ok=True)
    copiar = [a for a in ORIGEM.iterdir() if a.is_file() and a.name != 'programa.js']
    for velho in DESTINO.iterdir():
        if velho.is_file() and velho.name != 'programa.js' and velho.name not in {a.name for a in copiar}:
            velho.unlink()
    for arq in copiar:
        shutil.copyfile(arq, DESTINO / arq.name)
    simular.gravar(programas, DESTINO / 'programa.js')
    print(f'[OK] {len(programas)} exemplos em docs/simulador/ (abra docs/simulador/index.html para conferir)')


if __name__ == '__main__':
    main()
