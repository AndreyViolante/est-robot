from robo import *

# Seguidor PID (exemplo 9) que também faz curvas de 90 graus, com a função seguir_linha().
#
# Sensores, todos no modo luz:
#   S1 esquerda e S2 direita, um de cada lado da linha (são eles que o PID usa);
#   S3 no meio e mais à frente, em cima da linha.
#
# Na curva de 90, o S3 chega à esquina primeiro e sai da linha. Nessa hora o robô ainda não
# sabe para que lado é a curva, então anda reto devagar até o S1 ou o S2 passar por cima da
# linha nova, e gira para esse lado até o S3 achar a linha. Se nenhum dos dois achar linha,
# é uma falha na linha: ele segue reto.
#
# Confirmação: um evento só vale depois de CONFIRMA leituras seguidas iguais, para uma
# leitura errada (sujeira, reflexo) não disparar uma curva que não existe.
#
# Velocidade adaptativa: quanto mais longe da linha, mais devagar (VEL_RETA na reta,
# VEL_CURVA no mínimo).
#
# Funções: "def nome():" dá um nome a um grupo de comandos. O robô não guarda a função: cada
# vez que o programa chama seguir_linha(), os comandos dela entram ali, como se tivessem sido
# copiados naquele lugar.
#
# Medido neste robô: branco 100 nos três; preto S1 18, S2 21, S3 10.

VEL_RETA = 20
VEL_CURVA = 13
FREIO = 0.2          # quanto a velocidade cai por ponto de erro (erro 35 já dá VEL_CURVA)
KP = 0.3
KI = 0.001
KD = 1.5
LIMITE_I = 2000

PERDEU = 60          # S3 acima disto: saiu da linha
ACHOU = 40           # S3 abaixo disto: achou a linha de novo
ESCURO = 40          # S1 ou S2 abaixo disto: está em cima de uma linha
CONFIRMA = 3         # leituras seguidas para um evento valer
AVANCO = 15          # potência andando reto até achar a curva
GIRO = 20            # potência do giro para a curva
ATE_AS_RODAS = 7     # cm do S1/S2 até o eixo das rodas (meça no robô): anda isso antes de girar
PASSOS_MAX = 100     # voltas andando reto (cerca de 1 s) antes de concluir que é falha na linha


def corrigir_pid():
    """Uma correção do PID com S1 e S2, igual ao exemplo 9, mais a velocidade adaptativa."""
    guardar('erro', luz_refletida(1) - luz_refletida(2))

    guardar('soma', ler('soma') + ler('erro'))
    with se(ler('soma') > LIMITE_I):
        guardar('soma', LIMITE_I)
    with se(ler('soma') < -LIMITE_I):
        guardar('soma', -LIMITE_I)

    guardar('mudanca', ler('erro') - ler('erro_anterior'))
    guardar('erro_anterior', ler('erro'))

    guardar('correcao', KP * ler('erro') + KI * ler('soma') + KD * ler('mudanca'))

    # velocidade adaptativa: tamanho do erro (sem sinal) tira velocidade, até VEL_CURVA
    guardar('tamanho_erro', ler('erro'))
    with se(ler('tamanho_erro') < 0):
        guardar('tamanho_erro', -ler('tamanho_erro'))
    guardar('vel', VEL_RETA - FREIO * ler('tamanho_erro'))
    with se(ler('vel') < VEL_CURVA):
        guardar('vel', VEL_CURVA)

    motores(ler('vel') + ler('correcao'), ler('vel') - ler('correcao'))
    esperar(0.01)


def fazer_curva():
    """O S3 saiu da linha: faz a curva de 90 graus, ou segue reto se for uma falha na linha."""
    # Anda reto até um sensor do lado ficar CONFIRMA leituras em cima da linha da curva.
    guardar('lado', 0)           # -1 = esquerda, 1 = direita, 2 = falha na linha
    guardar('passos', 0)
    guardar('esq', 0)
    guardar('dir', 0)
    with repetir_ate(lambda: ler('lado') != 0):
        motores(AVANCO, AVANCO)
        with se_luz(1, '<', ESCURO):
            guardar('esq', ler('esq') + 1)
        with senao():
            guardar('esq', 0)
        with se_luz(2, '<', ESCURO):
            guardar('dir', ler('dir') + 1)
        with senao():
            guardar('dir', 0)
        with se(ler('esq') >= CONFIRMA):
            guardar('lado', -1)
        with se(ler('dir') >= CONFIRMA):
            guardar('lado', 1)
        guardar('passos', ler('passos') + 1)
        with se(ler('passos') > PASSOS_MAX):
            guardar('lado', 2)
        esperar(0.01)

    # Anda até as rodas ficarem em cima da esquina, gira para o lado da curva até o S3 achar a
    # linha nova e freia. Girando antes da esquina, o S3 acha a linha com o robô torto; sem
    # frear, ele passa da linha. Nos dois casos o robô se perde.
    with se(ler('lado') < 2):
        andar_cm(ATE_AS_RODAS, potencia=AVANCO)
        with repetir_ate_luz(3, '<', ACHOU):
            motores(ler('lado') * GIRO, ler('lado') * -GIRO)
        parar()
    guardar('soma', 0)
    guardar('erro_anterior', 0)


def seguir_linha():
    """Uma leitura do seguidor: PID nas retas e curvas suaves; curva de 90 graus (ou falha na
    linha) quando o S3 fica CONFIRMA leituras seguidas no branco. Chame dentro de um laço."""
    with se_luz(3, '>', PERDEU):
        guardar('branco', ler('branco') + 1)
    with senao():
        guardar('branco', 0)

    with se(ler('branco') >= CONFIRMA):
        fazer_curva()
    with senao():
        corrigir_pid()


# Programa: zera as variáveis do seguidor e segue a linha para sempre.
# Para seguir a linha até ver um obstáculo, troque o para_sempre() por
#     with repetir_ate(lambda: distancia(4) < 10):
guardar('erro_anterior', 0)
guardar('soma', 0)
guardar('branco', 0)

with para_sempre():
    seguir_linha()
