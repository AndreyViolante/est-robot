from robo import *

# Mostra na tela, sem parar, quanta luz o sensor S1 esta vendo (0 = escuro, 100 = claro).
# Bom para descobrir os valores da linha preta e do chao branco antes de programar o seguidor.
with para_sempre():
    mostrar('Luz:')
    mostrar(luz_refletida(1), linha=2)
    esperar(0.2)
