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


def l1_tela_som_luz():
    s = sensor_refl(1)
    return [start(), display('Ola'), sound_tone(440, 1, 100), light_on(2), wait_sec(1),
            s, display_val(s, 7, x=10, y=20), light_off()]


def l2_motores():
    return [start(), motor_on('B', 30), wait_sec(1), motor_off('B'), motor_rot('C', 30, 2),
            motor_sec('B', 30, 1.5), steer_on(30, 20), wait_sec(1), steer_rot(30, 1), motors_off()]


def l3_toque_ultra():
    toque, ultra = touch_state(4), ultrasonic_cm(4)
    sw_t = switch_touch(4)
    sw_t.b1 = [tank_on(10, 10)]; sw_t.b2 = [tank_off()]
    sw_d = switch_dist(4, 4, 20)
    sw_d.b1 = [tank_on(10, -10)]; sw_d.b2 = [tank_off()]
    return [start(), toque, var_wn('toque', src=toque, out=2), ultra, var_wn('dist', src=ultra, out=4),
            wait_touch(4), wait_dist(4, 4, 20), sw_t, sw_d]


def l4_espera_cor():
    sw = switch_refl(1, 4, 30)
    sw.b1 = [tank_on(10, 20)]; sw.b2 = [tank_on(20, 10)]
    lr = loop_refl(1, 4, 30); lr.b1 = [tank_on(15, 15)]
    lc = loop_color(2, PRETO); lc.b1 = [tank_on(15, 15)]
    return [start(), wait_refl(1, 4, 30), wait_color(2, PRETO), sw, lr, lc, tank_off()]


def l5_variaveis_logica():
    rx = var_rn('x')
    menor = compare('<', a=(rx, 2), cb=10)
    sw = switch_logic(menor)
    sw.b1 = [tank_on(10, 10)]; sw.b2 = [tank_off()]
    r2 = var_rn('x')
    soma = math('+', a=(r2, 2), cb=1)
    r3 = var_rn('x')
    chegou = compare('>=', a=(r3, 2), cb=10)
    lp = loop_until(chegou)
    lp.b1 = [r2, soma, var_wn('x', src=soma, out=1), r3, chegou]
    cor = sensor_color_id(3)
    div = math('/', ca=10, cb=4)
    return [start(), var_wn('x', 7), rx, menor, sw, lp,
            cor, var_wn('cor', src=cor, out=5), div, var_wn('metade', src=div, out=1)]


TESTES = [teste1_switch_cor_preto, teste2_move_tank_bc, t4_loop_inf, t5_loop_cont,
          t6_switch_depois, t7_loop_switch, t8_tank_modos, t9_proporcional,
          l1_tela_som_luz, l2_motores, l3_toque_ultra, l4_espera_cor, l5_variaveis_logica]
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


RAIZ = os.path.dirname(os.path.abspath(__file__))
EQUIVALENTES = [('exemplos/3_seguidor_liga_desliga.py', 'exemplos/blocos/seguidor_linha.py'),
                ('exemplos/4_seguidor_proporcional.py', 'exemplos/blocos/seguidor_proporcional.py')]


def _em_portugues():
    """Os programas do lote 3 escritos com robo.py: tem que dar os mesmos bytes que a IDE gerou."""
    from robo import (mostrar, tocar, luz, esperar, luz_refletida, apagar_luz, guardar, tocado, distancia,
                      esperar_toque, esperar_distancia, esperar_luz, esperar_cor, se_tocado, se_distancia,
                      se_luz, senao, motores, parar, repetir_ate_luz, repetir_ate_cor, se, ler, repetir_ate,
                      cor_vista)

    def l1():
        mostrar('Ola'); tocar(440, 1, 100); luz('vermelho'); esperar(1)
        mostrar(luz_refletida(1), x=10, y=20, limpar=True); apagar_luz()

    def l3():
        guardar('toque', tocado(4)); guardar('dist', distancia(4))
        esperar_toque(4); esperar_distancia(4, '<', 20)
        with se_tocado(4): motores(10, 10)
        with senao(): parar()
        with se_distancia(4, '<', 20): motores(10, -10)
        with senao(): parar()

    def l4():
        esperar_luz(1, '<', 30); esperar_cor(2, PRETO)
        with se_luz(1, '<', 30): motores(10, 20)
        with senao(): motores(20, 10)
        with repetir_ate_luz(1, '<', 30): motores(15, 15)
        with repetir_ate_cor(2, PRETO): motores(15, 15)
        parar()

    def l5():
        guardar('x', 7)
        with se(ler('x') < 10): motores(10, 10)
        with senao(): parar()
        with repetir_ate(lambda: ler('x') >= 10):
            guardar('x', ler('x') + 1)
        guardar('cor', cor_vista(3))

    def l5_blocos():
        return l5_variaveis_logica()[:-2]           # o mesmo, sem a divisao do final

    return [('l1_tela_som_luz', l1, None), ('l3_toque_ultra', l3, None), ('l4_espera_cor', l4, None),
            ('l5_variaveis_logica (sem a divisao)', l5, l5_blocos)]


def verificar_robo():
    """A linguagem em portugues (robo.py) gera o mesmo que os blocos e avisa os erros comuns."""
    import robo
    from enviar import carregar
    falhas = 0
    for pt, bl in EQUIVALENTES:
        iguais = compilar(carregar(os.path.join(RAIZ, pt))) == compilar(carregar(os.path.join(RAIZ, bl)))
        print(f'  {"OK   " if iguais else "FALHA"} {pt} = {bl}')
        falhas += not iguais
    for nome, escrever, referencia in _em_portugues():
        robo.novo_programa()
        escrever()
        nosso = compilar(robo.programa())
        if referencia:
            esperado = compilar(referencia())
        else:
            esperado = bytes.fromhex(open(os.path.join(PASTA, nome + '.hex')).read().strip())
        iguais = nosso == esperado
        print(f'  {"OK   " if iguais else "FALHA"} em portugues = {nome}')
        falhas += not iguais

    def espera_erro(nome, tipo, acao):
        nonlocal falhas
        robo.novo_programa()
        try:
            acao()
        except tipo:
            print(f'  OK    avisa: {nome}')
            return
        print(f'  FALHA nao avisou: {nome}')
        falhas += 1

    def senao_solto():
        robo.andar(rotacoes=1)
        with robo.senao():
            pass

    def senao_depois_de_outro_comando():
        with robo.se_ver_cor(1, robo.PRETO):
            robo.parar()
        robo.esperar(1)
        with robo.senao():
            pass

    def if_com_sensor():
        if robo.luz_refletida(1):
            pass

    def quadrado(pausa_a_mao):
        robo.novo_programa()
        robo.configurar(pausa=0 if pausa_a_mao else 0.5)
        with robo.repetir(4):
            robo.andar_cm(30)
            if pausa_a_mao: robo.esperar(0.5)
            robo.virar_direita(90)
            if pausa_a_mao: robo.esperar(0.5)
        feito = compilar(robo.programa())
        robo.configurar()
        return feito
    iguais = quadrado(False) == quadrado(True)
    print(f'  {"OK   " if iguais else "FALHA"} pausa depois de cada movimento = esperar(0.5) testado no robô')
    falhas += not iguais

    espera_erro('senao sem se', SyntaxError, senao_solto)
    espera_erro('senao separado do se', SyntaxError, senao_depois_de_outro_comando)
    espera_erro('if do Python com sensor', TypeError, if_com_sensor)
    espera_erro('andar sem dizer quanto', ValueError, lambda: robo.andar())
    falhas += not verificar_mensagens()

    robo.novo_programa()
    with robo.se(robo.cor_vista(1) == robo.VERDE):
        robo.bip()
    comparou = robo.programa()[2].params.startswith('1|3|')          # bloco Comparar com B = 3 (verde)
    robo.novo_programa()
    robo.mostrar(robo.cor_vista(1)); robo.mostrar(robo.luz_refletida(1), linha=2)
    avisou = len(robo.avisos(robo.programa())) == 1
    robo.novo_programa()
    robo.mostrar(robo.cor_vista(1)); robo.mostrar(robo.luz_refletida(2), linha=2)
    calado = robo.avisos(robo.programa()) == []
    for ok, nome in ((comparou, 'cor_vista(1) == VERDE compara com 3'),
                     (avisou, 'avisa sensor usado nos modos cor e luz'),
                     (calado, 'não avisa quando cada sensor tem um modo')):
        print(f'  {"OK   " if ok else "FALHA"} {nome}')
        falhas += not ok
    robo.novo_programa()
    blocos.MOTORS = 'B+C'
    return falhas == 0


def verificar_mensagens():
    """Erros tipicos de aluno viram mensagens em portugues com a linha certa."""
    import tempfile
    from enviar import carregar, explicar
    casos = [
        ('andr(rotacoes=2)', 3, 'Você quis dizer "andar"'),
        ('with repetir(4)\n    andar_cm(30)', 3, 'faltou o ":"'),
        ('with repetir(4):\nandar_cm(30)', 4, 'precisam começar com espaços'),
        ('andar(rotacao=2)', 3, 'Você quis dizer "rotacoes"'),
        ('andar(rotacoes=0,5)', 3, 'use ponto'),
        ('mostrar("Ola)', 3, 'faltou fechar as aspas'),
        ('esperar()', 3, 'faltou informar segundos'),
        ('if distancia(4) < 20:\n    parar()', 3, 'use "with se(...)"'),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as pasta:
        for i, (codigo, linha_esperada, trecho) in enumerate(casos):
            arq = os.path.join(pasta, f'aluno{i}.py')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write('from robo import *\n\n' + codigo + '\n')
            try:
                carregar(arq)
                linha, texto = None, 'nenhum erro'
            except Exception as e:
                linha, _, texto = explicar(e, arq)
            certo = linha == linha_esperada and trecho in texto
            ok &= certo
            print(f'  {"OK   " if certo else "FALHA"} mensagem: {codigo.splitlines()[0]!r} -> linha {linha}: {texto}')
        arq = os.path.join(pasta, 'sem_import.py')
        with open(arq, 'w', encoding='utf-8') as f:
            f.write('andar(rotacoes=2)\n')
        try:
            carregar(arq)
            texto = 'nenhum erro'
        except Exception as e:
            texto = explicar(e, arq)[2]
        certo = 'from robo import *' in texto
        ok &= certo
        print(f'  {"OK   " if certo else "FALHA"} mensagem: esqueceu o import -> {texto}')
    return ok


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
    print(f'\n{ok}/{len(TESTES)} gabaritos identicos\n')
    robo_ok = verificar_robo()
    print('\nlinguagem em portugues: ' + ('OK' if robo_ok else 'COM FALHAS'))
    sys.exit(0 if ok == len(TESTES) and robo_ok else 1)


if __name__ == '__main__':
    main()
