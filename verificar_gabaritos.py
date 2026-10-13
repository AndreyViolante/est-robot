"""Compila os programas de teste e compara byte a byte com o que a IDE EST gerou (gabaritos/).
Uso: python verificar_gabaritos.py
"""
import os, sys

import blocos
from blocos import *
from estc import compilar

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gabaritos')


def teste1_switch_cor_preto():
    sw = switch_color(1, PRETO)
    sw.b1 = [motor_deg('B', 50, 360)]
    sw.b2 = [motor_deg('C', 50, 360)]
    return [start(), sw]


def teste2_move_tank_bc():
    return [start(), tank_rot(50, 50, 1)]


def t4_loop_inf():
    lp = loop_forever(); lp.b1 = [wait_sec(1)]
    return [start(), lp]


def t5_loop_cont():
    lp = loop_count(3); lp.b1 = [motor_deg('B', 20, 90)]
    return [start(), lp]


def t6_switch_depois():
    sw = switch_color(1, PRETO)
    sw.b1 = [motor_deg('B', 20, 90)]
    sw.b2 = [motor_deg('C', 20, 90)]
    return [start(), sw, tank_rot(20, 20, 1)]


def t7_loop_switch():
    sw = switch_color(2, BRANCO)
    sw.b1 = [tank_on(20, 20)]
    sw.b2 = [tank_off()]
    lp = loop_count(2); lp.b1 = [sw]
    return [start(), lp]


def t8_tank_modos():
    return [start(), tank_on(20, -20), wait_sec(1), tank_sec(20, 20, 1),
            tank_deg(20, 20, 90), tank_off()]


def t9_proporcional():
    s = sensor_refl(1)
    erro = math('-', a=(s, 7), cb=50)
    corr = math('*', a=(erro, 1), cb=0.5)
    esq = math('+', ca=30, b=(corr, 1))
    dir_ = math('-', ca=30, b=(corr, 1))
    lp = loop_count(2)
    lp.b1 = [s, erro, corr, esq, dir_, tank_on(0, 0, wl=(esq, 1), wr=(dir_, 1)),
             var_wn('erro', src=erro, out=1)]
    return [start(), lp, tank_off()]


TESTES = [teste1_switch_cor_preto, teste2_move_tank_bc, t4_loop_inf, t5_loop_cont,
          t6_switch_depois, t7_loop_switch, t8_tank_modos, t9_proporcional]
# no t9 a IDE manteve so o ultimo fio de cada saida ligada a duas entradas: reproduz isso so aqui
COMPAT_FIOS = {'t9_proporcional'}


def comparar(nome, nosso, ide):
    if nosso == ide:
        print(f'  OK    {nome:26s} {len(ide)} bytes identicos')
        return True
    i = next((k for k in range(min(len(nosso), len(ide))) if nosso[k] != ide[k]), min(len(nosso), len(ide)))
    print(f'  FALHA {nome:26s} nosso {len(nosso)} B, IDE {len(ide)} B, primeira diferenca no byte {i}')
    print(f'        IDE:   {ide[max(0, i - 8):i + 24].hex(" ")}')
    print(f'        nosso: {nosso[max(0, i - 8):i + 24].hex(" ")}')
    return False


def main():
    blocos.MOTORS = 'B+C'
    ok = 0
    for fn in TESTES:
        ide = bytes.fromhex(open(os.path.join(PASTA, fn.__name__ + '.hex')).read().strip())
        try:
            nosso = compilar(fn(), compat_ide_fios=fn.__name__ in COMPAT_FIOS)
        except Exception as e:
            print(f'  ERRO  {fn.__name__:26s} {type(e).__name__}: {e}')
            continue
        ok += comparar(fn.__name__, nosso, ide)
    print(f'\n{ok}/{len(TESTES)} gabaritos identicos')
    sys.exit(0 if ok == len(TESTES) else 1)


if __name__ == '__main__':
    main()
