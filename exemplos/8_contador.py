from robo import *

# Conta de 1 ate 10 na tela, com um bip a cada numero. A variavel fica guardada no robo.
guardar('contador', 0)

with repetir(10):
    guardar('contador', ler('contador') + 1)
    mostrar(ler('contador'), x=10, y=50)
    bip()
    esperar(1)
