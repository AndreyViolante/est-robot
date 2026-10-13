from robo import *

# Seguidor de linha com um sensor (S1) na borda esquerda da linha preta.
# Viu preto: puxa para a esquerda. Viu branco: puxa para a direita.
with para_sempre():
    with se_ver_cor(1, PRETO):
        motores(10, 30)
    with senao():
        motores(30, 10)
