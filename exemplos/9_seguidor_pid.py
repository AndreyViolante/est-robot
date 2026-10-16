from robo import *

# Seguidor de linha PID com dois sensores de luz: S1 (esquerda) e S2 (direita).
#
#   erro      = S1 - S2       negativo: a linha está embaixo do S1; positivo: embaixo do S2
#   P         = KP * erro     corrige mais quanto mais longe da linha
#   I         = KI * soma     corrige um desvio que dura (curva longa, robô puxando para um lado)
#   D         = KD * mudança  freia a correção quando o erro já está diminuindo (menos balanço)
#   correção  = P + I + D     um motor ganha a correção e o outro perde

VELOCIDADE = 15      # lento, para observar; o exemplo 4 usa 25
KP = 0.3
KI = 0.001
KD = 1.5
LIMITE_I = 2000      # teto da soma dos erros, para o I não crescer sem fim

guardar('erro_anterior', 0)
guardar('soma', 0)

with para_sempre():
    guardar('erro', luz_refletida(1) - luz_refletida(2))

    # I: soma dos erros, presa entre -LIMITE_I e LIMITE_I
    guardar('soma', ler('soma') + ler('erro'))
    with se(ler('soma') > LIMITE_I):
        guardar('soma', LIMITE_I)
    with se(ler('soma') < -LIMITE_I):
        guardar('soma', -LIMITE_I)

    # D: quanto o erro mudou desde a última volta
    guardar('mudanca', ler('erro') - ler('erro_anterior'))
    guardar('erro_anterior', ler('erro'))

    guardar('correcao', KP * ler('erro') + KI * ler('soma') + KD * ler('mudanca'))
    motores(VELOCIDADE + ler('correcao'), VELOCIDADE - ler('correcao'))
    esperar(0.01)    # sem esta espera o laço é tão rápido que a mudança do erro fica quase sempre 0
