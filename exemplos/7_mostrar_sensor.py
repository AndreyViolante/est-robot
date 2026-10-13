from robo import *

# Mostra na tela, sem parar, quanta luz o sensor S1 esta vendo (0 = escuro, 100 = claro).
# Bom para descobrir os valores da linha preta e do chao branco antes de programar o seguidor.
with para_sempre():
    mostrar(luz_refletida(1), x=10, y=50)
    esperar(0.2)
