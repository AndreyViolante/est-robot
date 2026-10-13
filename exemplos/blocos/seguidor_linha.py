from blocos import *

# Seguidor de linha com o sensor S1 na borda esquerda da linha preta.
# Neste robo, potencia positiva = para frente. B = motor esquerdo, C = direito.
RAPIDO, DEVAGAR = 30, 10

borda = switch_color(1, PRETO)
borda.b1 = [tank_on(DEVAGAR, RAPIDO)]   # S1 viu preto: puxa para a esquerda
borda.b2 = [tank_on(RAPIDO, DEVAGAR)]   # S1 viu branco: puxa para a direita

sempre = loop_forever()
sempre.b1 = [borda]

PROGRAMA = [start(), sempre]
