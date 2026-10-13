from robo import *

# Espera apertar o sensor de toque (porta 4) para comecar.
mostrar('Aperte')
mostrar('o botao', linha=2)
esperar_toque(4)
bip()
luz('azul')
andar(rotacoes=2)
apagar_luz()
