"""Compila os programas de teste e compara byte a byte com o que a IDE EST gerou (gabaritos/).
Uso: python verificar_gabaritos.py
"""
import os, re, sys

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


def _em_portugues():
    """Programas escritos com robo.py e a referência que tem que dar os mesmos bytes: o que a IDE gerou
    (gabaritos/) ou o mesmo programa montado com os blocos."""
    from robo import (mostrar, tocar, luz, esperar, luz_refletida, apagar_luz, guardar, tocado, distancia,
                      esperar_toque, esperar_distancia, esperar_luz, esperar_cor, se_tocado, se_distancia,
                      se_luz, senao, motores, parar, repetir_ate_luz, repetir_ate_cor, se, ler, repetir_ate,
                      cor_vista, para_sempre, se_ver_cor)

    def liga_desliga():
        with para_sempre():
            with se_ver_cor(1, PRETO):
                motores(10, 30)
            with senao():
                motores(30, 10)

    def liga_desliga_blocos():
        borda = switch_color(1, PRETO)
        borda.b1 = [tank_on(10, 30)]
        borda.b2 = [tank_on(30, 10)]
        sempre = loop_forever()
        sempre.b1 = [borda]
        return [start(), sempre]

    def proporcional():
        with para_sempre():
            erro = luz_refletida(1) - luz_refletida(2)
            correcao = erro * 0.4
            motores(25 + correcao, 25 - correcao)

    def proporcional_blocos():
        s1, s2 = sensor_refl(1), sensor_refl(2)
        erro = math('-', a=(s1, 7), b=(s2, 7))
        correcao = math('*', a=(erro, 1), cb=0.4)
        pot_b = math('+', ca=25, b=(correcao, 1))
        pot_c = math('-', ca=25, b=(correcao, 1))
        sempre = loop_forever()
        sempre.b1 = [s1, s2, erro, correcao, pot_b, pot_c, tank_on(0, 0, wl=(pot_b, 1), wr=(pot_c, 1))]
        return [start(), sempre]

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
            ('l5_variaveis_logica (sem a divisao)', l5, l5_blocos),
            ('seguidor liga-desliga em blocos', liga_desliga, liga_desliga_blocos),
            ('seguidor proporcional em blocos', proporcional, proporcional_blocos)]


def verificar_robo():
    """A linguagem em portugues (robo.py) gera o mesmo que os blocos e avisa os erros comuns."""
    import robo
    falhas = 0
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
        robo.configurar(pausa=0.5)
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
        ('VEL = 30 if distancia(4) < 20 else 10', 3, 'não funciona aqui'),
        ('while distancia(4) > 10:\n    andar(rotacoes=1)\n    break', 3, '"break"'),
        ('if distancia(4) = 20:\n    bip()', 3, 'use "=="'),
        ('else:\n    bip()', 3, 'logo depois de um "if"'),
        ('esperar(0,5)', 3, 'use ponto'),
        ('mostrar(luz_refletida(9))', 3, 'não é de sensor'),
        ('motor(1, 50)', 3, 'não é de motor'),
        ("mostrar('Luz ' + 5)", 3, 'não dá para juntar um texto'),
        ("andar_cm('dez')", 3, 'precisa de um número'),
        ('x = 10 / 0', 3, 'divisão por zero'),
        ('for i in range(distancia(4)):\n    bip()', 3, 'só existe no robô'),
        ('robo.bip()', 3, 'sem "robo." na frente'),
        ('import robo\nrobo.bipp()', 4, 'Você quis dizer "bip"'),
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


# if/while do Python (enviar.py troca por se/senao/repetir_ate): cada par tem que dar os mesmos bytes
IF_WHILE = [
    ('if com sensor = se/senao',
     """with para_sempre():
    if luz_refletida(1) < 50:
        motores(10, 30)
    else:
        motores(30, 10)""",
     """with para_sempre():
    with se(luz_refletida(1) < 50):
        motores(10, 30)
    with senao():
        motores(30, 10)"""),
    ('if sem else',
     """if distancia(4) < 20:
    parar()
bip()""",
     """with se(distancia(4) < 20):
    parar()
bip()"""),
    ('elif = se dentro do senao',
     """with para_sempre():
    if cor_vista(1) == PRETO:
        motores(10, 30)
    elif cor_vista(2) == PRETO:
        motores(30, 10)
    else:
        motores(30, 30)""",
     """with para_sempre():
    with se(cor_vista(1) == PRETO):
        motores(10, 30)
    with senao():
        with se(cor_vista(2) == PRETO):
            motores(30, 10)
        with senao():
            motores(30, 30)"""),
    ('if not = comparação ao contrário',
     """if not luz_refletida(1) < 50:
    bip()""",
     """with se(luz_refletida(1) >= 50):
    bip()"""),
    ('while com sensor = se + repetir_ate',
     """while distancia(4) > 15:
    motores(30, 30)
parar()""",
     """with se(distancia(4) > 15):
    with repetir_ate(lambda: distancia(4) <= 15):
        motores(30, 30)
parar()"""),
    ('while True = para_sempre',
     """while True:
    mostrar(luz_refletida(1))""",
     """with para_sempre():
    mostrar(luz_refletida(1))"""),
    ('if e while do Python continuam do Python',
     """VELOCIDADE = 30
if VELOCIDADE > 20:
    andar(rotacoes=1, potencia=VELOCIDADE)
else:
    andar(rotacoes=1)
n = 0
while n < 2:
    bip()
    n += 1""",
     """andar(rotacoes=1, potencia=30)
bip()
bip()"""),
    ('and com sensores = se dentro do se',
     """if luz_refletida(1) < 50 and luz_refletida(2) < 50:
    parar()
else:
    bip()""",
     """c1 = luz_refletida(1) < 50
guardar('x', 0)
with se(c1):
    with se(luz_refletida(2) < 50):
        guardar('x', 1)
with se(ler('x') == 1):
    parar()
with senao():
    bip()"""),
    ('or com sensores = se e senao',
     """if distancia(4) < 10 or luz_refletida(1) < 30:
    parar()""",
     """c1 = distancia(4) < 10
guardar('x', 0)
with se(c1):
    guardar('x', 1)
with senao():
    with se(luz_refletida(1) < 30):
        guardar('x', 1)
with se(ler('x') == 1):
    parar()"""),
    ('and/or do Python continuam do Python',
     """VEL = 30
a = 0 or 5
b = 3 and 0
guardar('a', a)
guardar('b', b)
if VEL > 10 and VEL < 50 and not VEL == 40:
    bip()""",
     """guardar('a', 5)
guardar('b', 0)
bip()"""),
    ('for com range = repetir do robô',
     """for _ in range(4):
    andar_cm(30)
    virar_direita(90)
for i in range(2):
    bip()""",
     """with repetir(4):
    andar_cm(30)
    virar_direita(90)
with repetir(2):
    bip()"""),
    ('for que usa a variável continua repetindo no Python',
     """for i in range(3):
    tocar(400 + i * 100, 0.2)
t = 0
for _ in range(3):
    t += 1
guardar('t', t)""",
     """tocar(400, 0.2)
tocar(500, 0.2)
tocar(600, 0.2)
guardar('t', 3)"""),
    ('notas pelo nome e melodia',
     """tocar('la4', 0.5)
melodia('do re - mi:0.6')""",
     """tocar(440, 0.5)
tocar(523, 0.3)
tocar(587, 0.3)
esperar(0.3)
tocar(659, 0.6)"""),
]


def verificar_novidades():
    """Comandos novos sem referência da IDE: compilam e geram as instruções esperadas."""
    import tempfile
    from enviar import carregar, explicar
    casos = [
        ('ao_mesmo_tempo inicia as tarefas antes de esperar',
         """with ao_mesmo_tempo():
    with tarefa():
        andar_cm(30)
    with tarefa():
        melodia('do re mi')""",
         lambda d: re.search(rb'\x1d.{4}\x01\x00\x1d.{4}\x02\x00\x20\x01\x00\x20\x02\x00', d, re.S) is not None),
        ('botões da controladora (leitura interna 0x32)',
         """esperar_botao()
if botao_apertado() == 2:
    bip()""",
         lambda d: b'\x32\x03\x00\x01' in d),
        ('painel mostra nome e valor em cada linha',
         """painel(erro=luz_refletida(1) - luz_refletida(2), vel=20)""",
         lambda d: b'erro:' in d and b'vel:' in d),
        ('ajustando: botões em paralelo com o programa',
         """with ajustando('kp', 0.4, 0.05):
    while True:
        motores(20 + ler('kp'), 20 - ler('kp'))""",
         lambda d: b'\x32\x03\x00\x01' in d and re.search(rb'\x1d.{4}\x01\x00\x1d.{4}\x02\x00', d, re.S) is not None),
        ('while com and compila',
         """while luz_refletida(1) > 50 and distancia(4) > 10:
    motores(30, 30)
parar()""",
         lambda d: len(d) > 0),
        ('ajustes: vários números, botões em paralelo',
         """with ajustes(kp=(0.4, 0.05), vel=(25, 5)):
    while True:
        motores(ler('vel') + ler('kp'), ler('vel') - ler('kp'))""",
         lambda d: b'kp:' in d and b'vel:' in d
         and re.search(rb'\x1d.{4}\x01\x00\x1d.{4}\x02\x00', d, re.S) is not None),
        ('medir_laco: laço em paralelo com o relógio e mostra as voltas',
         """with medir_laco(5):
    erro = luz_refletida(1) - luz_refletida(2)
    motores(20 + erro * 0.3, 20 - erro * 0.3)""",
         lambda d: b'Voltas/s:' in d
         and re.search(rb'\x1d.{4}\x01\x00\x1d.{4}\x02\x00', d, re.S) is not None),
        ('calibrar_na_largada: mede e mostra o limite de cada sensor',
         """calibrar_na_largada(1, 2)
while True:
    if luz_refletida(1) < limite_medido(1):
        motores(10, 30)
    else:
        motores(30, 10)""",
         lambda d: b'lim1:' in d and b'lim2:' in d),
    ]
    erros = [
        ('ajustes sem o passo', 'with ajustes(kp=0.4):\n    bip()', '(valor inicial, passo)'),
        ('calibrar porta de motor', "calibrar_na_largada('B')", 'não é de sensor'),
        ('comando solto no ao_mesmo_tempo', 'with ao_mesmo_tempo():\n    bip()', 'cada parte num "with tarefa():"'),
        ('tarefa fora do ao_mesmo_tempo', 'with tarefa():\n    bip()', 'logo dentro de um "with ao_mesmo_tempo():"'),
        ('nota que não existe', "tocar('dó maior')", 'não conheço a nota'),
        ('nota grave demais', "tocar('do4')", 'grave demais'),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as pasta:
        arq = os.path.join(pasta, 'novo.py')
        for nome, codigo, confere in casos:
            with open(arq, 'w', encoding='utf-8') as f:
                f.write('from robo import *\n\n' + codigo + '\n')
            try:
                certo = confere(compilar(carregar(arq)))
            except Exception as e:
                certo = False
                nome += f' ({type(e).__name__}: {e})'
            ok &= certo
            print(f'  {"OK   " if certo else "FALHA"} {nome}')
        for nome, codigo, trecho in erros:
            with open(arq, 'w', encoding='utf-8') as f:
                f.write('from robo import *\n\n' + codigo + '\n')
            try:
                carregar(arq)
                texto = 'nenhum erro'
            except Exception as e:
                texto = explicar(e, arq)[2]
            certo = trecho in texto
            ok &= certo
            print(f'  {"OK   " if certo else "FALHA"} avisa: {nome} -> {texto}')
    return ok


def verificar_if_while():
    """O if/while normal do Python gera o mesmo programa que os with se(...)/repetir_ate equivalentes."""
    import tempfile
    from enviar import carregar
    ok = True
    with tempfile.TemporaryDirectory() as pasta:
        for nome, com_if, com_with in IF_WHILE:
            feitos = []
            for i, codigo in enumerate((com_if, com_with)):
                arq = os.path.join(pasta, f'p{i}.py')
                with open(arq, 'w', encoding='utf-8') as f:
                    f.write('from robo import *\n\n' + codigo + '\n')
                feitos.append(compilar(carregar(arq)))
            certo = feitos[0] == feitos[1]
            ok &= certo
            print(f'  {"OK   " if certo else "FALHA"} {nome}')
    return ok


def verificar_sintaxe():
    """Todos os .py do projeto compilam (um erro de escrita numa ferramenta passaria despercebido)."""
    raiz = os.path.dirname(os.path.abspath(__file__))
    ruins = []
    for pasta in ('', 'ferramentas', 'exemplos'):
        for nome in sorted(os.listdir(os.path.join(raiz, pasta))):
            if nome.endswith('.py'):
                arq = os.path.join(raiz, pasta, nome)
                try:
                    with open(arq, encoding='utf-8') as f:
                        compile(f.read(), arq, 'exec')
                except SyntaxError as e:
                    ruins.append(f'{os.path.join(pasta, nome)} linha {e.lineno}: {e.msg}')
    for r in ruins:
        print(f'  FALHA erro de escrita em {r}')
    print(f'  {"OK   " if not ruins else "FALHA"} todos os arquivos .py compilam')
    return not ruins


def expandir_atalho(corpo):
    """O texto que um atalho do VS Code (.vscode/robo.code-snippets) escreve, com os valores sugeridos.
    Onde o aluno ainda vai escrever ($0, $1...) entra um bip(), para o programa ficar completo."""
    texto = '\n'.join(corpo).replace('\t', '    ')
    texto = re.sub(r'\$\{\d+:([^}]*)\}', r'\1', texto)
    return re.sub(r'\$\{?\d+\}?', 'bip()', texto)


def verificar_atalhos():
    """Cada atalho do VS Code vira um programa que compila."""
    import json, tempfile
    from enviar import carregar
    raiz = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(raiz, '.vscode', 'robo.code-snippets'), encoding='utf-8') as f:
        atalhos = json.load(f)
    ok = True
    with tempfile.TemporaryDirectory() as pasta:
        for nome, atalho in atalhos.items():
            codigo = expandir_atalho(atalho['body'])
            if not codigo.startswith('from robo import'):
                codigo = 'from robo import *\n\n' + codigo
            arq = os.path.join(pasta, 'atalho.py')
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(codigo + '\n')
            try:
                compilar(carregar(arq))
                erro = ''
            except Exception as e:
                erro = f' -> {type(e).__name__}: {e}'
            ok &= not erro
            print(f'  {"OK   " if not erro else "FALHA"} atalho {atalho["prefix"]}{erro}')
    return ok


# traduções da IDE que não dão os mesmos bytes (o programa faz o mesmo): Mover com Direção com curva (l2),
# conta só com números (l5) e o fio duplicado que a IDE descarta (t9)
IMPORTAR_APROXIMADOS = {'l2_motores', 'l5_variaveis_logica', 't9_proporcional'}


def verificar_importar():
    """Os projetos da IDE (gabaritos/*.est): importados, compilam para os mesmos bytes que a IDE gerou
    (gabaritos/*.hex), e a tradução para Python também dá esses bytes (menos as aproximadas)."""
    import importar_est
    ok = True
    for arq in sorted(os.listdir(PASTA)):
        if not arq.endswith('.est'):
            continue
        nome = arq[:-4]
        with open(os.path.join(PASTA, arq), 'rb') as f:
            dados = f.read()
        try:
            programas, meus = importar_est.ler(dados)
            p = programas[0]
            ide = bytes.fromhex(open(os.path.join(PASTA, nome + '.hex')).read().strip())
            blocos_ok = compilar(p.blocos) == ide
            codigo, _ = importar_est.para_python(p, meus, arq)
            exata = importar_est.conferir(p, codigo, meus)
            certo = blocos_ok and (exata or nome in IMPORTAR_APROXIMADOS)
            detalhe = f'blocos iguais à IDE: {blocos_ok}; tradução exata: {exata}'
        except Exception as e:
            certo, detalhe = False, f'{type(e).__name__}: {e}'
        ok &= certo
        print(f'  {"OK   " if certo else "FALHA"} importar {arq} ({detalhe})')
    return ok


def verificar_guias():
    """Os programas dos guias (blocos ```python) compilam: um exemplo errado no guia confunde a turma."""
    import tempfile
    from enviar import carregar
    raiz = os.path.dirname(os.path.abspath(__file__))
    ok = True
    with tempfile.TemporaryDirectory() as pasta:
        for guia in ('guia-obr.md',):
            texto = open(os.path.join(raiz, 'docs', guia), encoding='utf-8').read()
            for n, codigo in enumerate(re.findall(r'```python\n(.*?)```', texto, re.S), 1):
                if 'from robo import' not in codigo:
                    continue
                arq = os.path.join(pasta, f'guia{n}.py')
                with open(arq, 'w', encoding='utf-8') as f:
                    f.write(codigo)
                try:
                    compilar(carregar(arq))
                    erro = ''
                except Exception as e:
                    erro = f' -> {type(e).__name__}: {e}'
                ok &= not erro
                print(f'  {"OK   " if not erro else "FALHA"} programa {n} do docs/{guia}{erro}')
    return ok


def verificar_offline():
    """O sw.js da página de programar (modo sem internet) guarda as mesmas versões de bibliotecas que a página
    usa, e a lista de arquivos dela (projeto/arquivos.json) tem todos os arquivos da página."""
    import json
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'programar')
    ler = lambda nome: open(os.path.join(pasta, nome), encoding='utf-8').read()
    sw, falhas = ler('sw.js'), []
    usadas = {'compilador.js': re.findall(r"https://cdn\.jsdelivr\.net/pyodide/[^'\"]+", ler('compilador.js')),
              'modo_blocos.js': [f'https://cdn.jsdelivr.net/npm/blockly@{v}/'
                                 for v in re.findall(r"const VERSAO = '([^']+)'", ler('modo_blocos.js'))],
              'index.html': re.findall(r'https://cdnjs\.cloudflare\.com/ajax/libs/codemirror/[\d.]+/', ler('index.html'))}
    for arquivo, urls in usadas.items():
        if not urls:
            falhas.append(f'não achei a biblioteca do {arquivo}')
        falhas += [f'o sw.js não guarda {u} (usado no {arquivo})' for u in set(urls) if u not in sw]
    lista = json.loads(ler(os.path.join('projeto', 'arquivos.json'))).get('offline', [])
    na_pasta = sorted(os.path.relpath(os.path.join(r, a), pasta).replace(os.sep, '/')
                      for r, subpastas, arquivos in os.walk(pasta) if '__pycache__' not in r for a in arquivos)
    faltam = [a for a in na_pasta if a not in lista and a != 'sw.js']
    sobram = [a for a in lista if a not in na_pasta]
    if faltam or sobram:
        falhas.append(f'a lista do modo sem internet está velha (faltam {faltam}, sobram {sobram}): '
                      'rode python ferramentas/publicar_programar.py')
    for f in falhas:
        print(f'  FALHA {f}')
    print(f'  {"OK   " if not falhas else "FALHA"} página de programar sem internet (sw.js)')
    return not falhas


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
    robo_ok &= verificar_if_while()
    robo_ok &= verificar_novidades()
    robo_ok &= verificar_sintaxe()
    robo_ok &= verificar_atalhos()
    robo_ok &= verificar_offline()
    robo_ok &= verificar_guias()
    robo_ok &= verificar_importar()
    print('\nlinguagem em portugues: ' + ('OK' if robo_ok else 'COM FALHAS'))
    sys.exit(0 if ok == len(TESTES) and robo_ok else 1)


if __name__ == '__main__':
    main()
