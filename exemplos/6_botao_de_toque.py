from robo import *

# Espera apertar o sensor de toque (porta 4) para comecar.
mostrar('Aperte o botao')
esperar_toque(4)
bip()
luz('verde')
andar(rotacoes=2)
apagar_luz()
