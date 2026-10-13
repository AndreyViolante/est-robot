from robo import *

# Seguidor de linha proporcional com dois sensores: S1 (esquerda) e S2 (direita).
# Quanto mais a linha puxa para um lado, mais forte o robo corrige.
VELOCIDADE = 25
GANHO = 0.4

with para_sempre():
    erro = luz_refletida(1) - luz_refletida(2)
    correcao = erro * GANHO
    motores(VELOCIDADE + correcao, VELOCIDADE - correcao)
