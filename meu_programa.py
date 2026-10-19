from robo import *

# Primeiro programa: com o robô ligado no USB, aperte Ctrl+Shift+B.
# Se a luz acender, o robô apitar e aparecer "Funcionou!" na tela,
# o computador está conversando com a controladora.
# Depois apague as linhas abaixo e escreva o seu programa aqui.

luz('azul')
tocar(440, 0.5)
mostrar('Funcionou!')
esperar(3)
apagar_luz()
