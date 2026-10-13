from robo import *

# Anda ate chegar perto de um obstaculo (sensor ultrassonico na porta 4), da re e vira.
with para_sempre():
    with se_distancia(4, '<', 15):
        re(rotacoes=0.5)
        virar_direita(90)
    with senao():
        motores(30, 30)
