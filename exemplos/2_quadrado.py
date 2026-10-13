from robo import *

# Um quadrado e andar e virar 90 graus, 4 vezes.
# Se o robo virar mais ou menos que 90 graus, ajuste entre_rodas_cm.
configurar(roda_cm=5.6, entre_rodas_cm=12)

with repetir(4):
    andar_cm(30)
    virar_direita(90)
