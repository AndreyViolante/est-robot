"""
Teste isolado: motor C em loop infinito.
Se o motor C (direito) nao se mover, o marker 0x07 esta errado.
"""
from est import *

with repetir():
    motor(C, velocidade=50, direcao=FRENTE, rotacoes=1)
