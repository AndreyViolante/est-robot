from blocos import *

# Seguidor de linha proporcional com S1 (esquerda) e S2 (direita) em luz refletida.
# Linha embaixo do S1 -> S1 le mais escuro -> erro negativo -> motor esquerdo desacelera -> vira para a linha.
BASE = 25      # potencia dos dois motores com a linha centralizada (positiva = para frente)
KP = 0.4       # ganho: quanto corrige para cada ponto de diferenca entre os sensores

s1 = sensor_refl(1)
s2 = sensor_refl(2)
erro = math('-', a=(s1, 7), b=(s2, 7))        # S1 - S2
correcao = math('*', a=(erro, 1), cb=KP)
pot_b = math('+', ca=BASE, b=(correcao, 1))   # motor B (esquerdo)
pot_c = math('-', ca=BASE, b=(correcao, 1))   # motor C (direito)
motores = tank_on(0, 0, wl=(pot_b, 1), wr=(pot_c, 1))

sempre = loop_forever()
sempre.b1 = [s1, s2, erro, correcao, pot_b, pot_c, motores]

PROGRAMA = [start(), sempre]
