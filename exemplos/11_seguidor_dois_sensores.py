from robo import *

# Seguidor de linha básico com dois sensores: S1 à esquerda e S2 à direita da linha preta.
#   S1 viu preto: a linha foi para a esquerda, vira para a esquerda.
#   Senão, S2 viu preto: a linha foi para a direita, vira para a direita.
#   Senão (os dois no branco): a linha está no meio, anda reto.
# Na virada a roda de dentro anda um pouco de ré: assim ele faz até a curva de 90 graus.

RETO = 30            # potência dos dois motores na reta
FORA = 30            # roda de fora da curva
DENTRO = -15         # roda de dentro da curva (negativo = de ré)

with para_sempre():
    with se_ver_cor(1, PRETO):
        motores(DENTRO, FORA)           # vira para a esquerda
    with senao():
        with se_ver_cor(2, PRETO):
            motores(FORA, DENTRO)       # vira para a direita
        with senao():
            motores(RETO, RETO)         # anda reto
