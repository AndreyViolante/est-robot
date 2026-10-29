"""Blocos de programa do robo EST (a linguagem em que os programas sao escritos).

Cada funcao devolve um Blk. Um programa e uma lista de blocos comecando por start();
loops e switches guardam os blocos de dentro em .b1 (e .b2 no ramo "nao" do switch).
Os campos de params seguem o paramvalues da IDE: o campo N e o parametro de hardware N.
"""

DISPLAY_PARAMS = '0|0|0|0|0|0|0|50|20|130|100|40|80|80|0|1|2'
WAIT_PARAMS = '1|1|1|1|1|20|0|5|1|1|0|0|0|0|1|1|1|1|0|0|0|1|1|1|1|0|0|1|0|0|0|0|0|0|0|0|1|1|1|0|1|1'
LOOP_PARAMS = '1|0|1|1|1|1|0|1|1|1|1|1|1|1|0|0|0|0|0|0|0'
SWITCH_PARAMS = '1|0|1|1|1|1|1|1|1|1|1|1|0|0|0|0'
MOTORS = 'B+C'      # motores do Mover Tanque: B = esquerdo, C = direito

PRETO, AZUL, VERDE, AMARELO, VERMELHO, BRANCO, MARROM = '1', '2', '3', '4', '5', '6', '7'


class Blk:
    def __init__(self, t, mode, params='', port=' ', wires=(), label=None):
        self.t = str(t); self.mode = str(mode); self.params = params; self.port = port
        self.wires = list(wires)          # (parametro_de_entrada, bloco_origem, parametro_de_saida)
        self.b1 = []; self.b2 = []        # blocos de dentro (loop: b1; switch: b1 = sim, b2 = nao)
        self.label = label

    def param(self, hw_id):
        campos = self.params.split('|')
        return campos[hw_id - 1] if 0 < hw_id <= len(campos) else ''

    def __repr__(self):
        return f'Blk({self.t}, modo {self.mode}, porta {self.port!r})'


def start(): return Blk(2001, 0, '', ' ')

# ---- motores ----
def tank_on(l, r, wl=None, wr=None):                                   # Mover Tanque - Ligado
    b = Blk(1004, 2, f'{l}|{r}|0|1|1|1', MOTORS)
    if wl: b.wires.append((1,) + wl)
    if wr: b.wires.append((2,) + wr)
    return b
def tank_rot(l, r, rot, brake=True):                                   # Mover Tanque - Rotacoes
    return Blk(1004, 5, f'{l}|{r}|{0 if brake else 1}|1|1|{rot}', MOTORS)
def tank_deg(l, r, deg, brake=True):                                   # Mover Tanque - Graus
    return Blk(1004, 4, f'{l}|{r}|{0 if brake else 1}|1|{deg}|1', MOTORS)
def tank_sec(l, r, sec, brake=True):                                   # Mover Tanque - Segundos
    return Blk(1004, 3, f'{l}|{r}|{0 if brake else 1}|{sec}|1|1', MOTORS)
def tank_off(brake=True):                                              # Mover Tanque - Desligado
    return Blk(1004, 1, f'50|50|{0 if brake else 1}|1|1|1', MOTORS)
def motor_deg(port, power, deg, brake=True):                           # Motor Grande - Graus
    return Blk(1002, 4, f'{power}|{0 if brake else 1}|1|{deg}|1', port)
def motor_rot(port, power, rot, brake=True):                           # Motor Grande - Rotacoes
    return Blk(1002, 5, f'{power}|{0 if brake else 1}|1|360|{rot}', port)
def motor_sec(port, power, sec, brake=True):                           # Motor Grande - Segundos
    return Blk(1002, 3, f'{power}|{0 if brake else 1}|{sec}|360|1', port)
def motor_on(port, power):                                             # Motor Grande - Ligado
    return Blk(1002, 2, f'{power}|0|1|360|1', port)
def motor_off(port, brake=True):                                       # Motor Grande - Desligado
    return Blk(1002, 1, f'50|{0 if brake else 1}|1|360|1', port)
def steer_on(power, steering):                                         # Mover com Direcao - Ligado
    return Blk(1003, 2, f'{power}|{steering}|0|1|360|1', MOTORS)
def steer_rot(power, rot, steering=0, brake=True):                     # Mover com Direcao - Rotacoes
    return Blk(1003, 5, f'{power}|{steering}|{0 if brake else 1}|1|360|{rot}', MOTORS)
def motors_off(brake=True):                                            # Mover com Direcao - Desligado
    return Blk(1003, 1, f'50|0|{0 if brake else 1}|1|360|1', MOTORS)

# ---- tela, som e luz ----
def display(text, x=0, y=0, clear=True):                               # Tela - texto
    p = DISPLAY_PARAMS.split('|'); p[0] = '0' if clear else '1'; p[5] = str(x); p[6] = str(y)
    return Blk(1005, 1, '|'.join(p), text)
def display_val(src, out, x=0, y=0, clear=True):                       # Tela - valor ligado por fio
    b = display('0', x, y, clear); b.wires.append((0, src, out)); return b
def sound_tone(freq=440, sec=1, volume=100):                           # Som - tocar tom
    return Blk(1006, 3, f'0|0|{freq}|{sec}|{volume}|0', ' ')
def light_on(color=2, pulse=False):                                    # Luz do bloco - ligar
    return Blk(1007, 2, f'{color}|{1 if pulse else 0}', ' ')
def light_off(): return Blk(1007, 1, '1|1', ' ')                       # Luz do bloco - desligar

# ---- sensores ----
def sensor_refl(port): return Blk(3002, 2, '5|4|0|50|0|0|0', str(port))          # saida 7 = luz refletida
def sensor_color_id(port): return Blk(3002, 1, '5|4|0|50|0|0|0', str(port))      # saida 5 = numero da cor
def touch_state(port): return Blk(3008, 1, '1|0|0|0', str(port))                  # saida 2 = estado (1 = apertado)
# da tabela de compilação da IDE (compileconfig_file/compile_xml), ainda não conferidos no robô nem contra captura
def motor_rotation(port, mode): return Blk(3005, mode, '2|90|0|1|0|0', str(port))  # 1 graus (saida 3), 2 rotacoes (4), 3 potencia (5), 7 zera
def gyro(port, mode): return Blk(3003, mode, '4|90|0|0|0', str(port))             # 1 angulo (saida 3), 2 graus/s (4), 6 zera
def timer(n, mode): return Blk(3007, mode, f'{n}|2|5|0|0', ' ')                   # 1 segundos (saida 4), 3 zera; n = cronometro 1..8
def round_num(mode=1, src=None, out=None):                             # Arredondar: 1 mais perto, 2 para cima, 3 para baixo
    b = Blk(4006, mode, '0|1|0', ' ')
    if src: b.wires.append((1, src, out))
    return b                                                            # saida 3
def random_num(lo, hi): return Blk(4010, 1, f'{lo}|{hi}|50|0|0', ' ')            # Aleatorio entre lo e hi, saida 5
def ultrasonic_cm(port): return Blk(3009, 3, '4|50|0|0|0|0|0', str(port))         # saida 4 = distancia em cm

# ---- variaveis e contas ----
def var_wn(name, value=1, src=None, out=None):                         # Escrever variavel numerica
    b = Blk(4001, 5, f'2|0|0|0|0|0|{value}|1|1|1', name)
    if src: b.wires.append((7, src, out))
    return b
def var_rn(name): return Blk(4001, 2, '2|0|0|0|0|0|1|1|1|1', name)    # Ler variavel numerica, saida 2
CMP = {'=': 1, '!=': 2, '>': 3, '>=': 4, '<': 5, '<=': 6}
def compare(op, a=None, b=None, ca=1, cb=1):                           # Comparar, saida 3 (logico)
    blk = Blk(4007, CMP[op], f'{ca}|{cb}|0', ' ')
    if a: blk.wires.append((1,) + a)
    if b: blk.wires.append((2,) + b)
    return blk
MATH = {'+': 1, '-': 2, '*': 3, '/': 4}
def math(op, a=None, b=None, ca=1, cb=1):                             # saida 1 = resultado
    blk = Blk(4005, MATH[op], f'0|{ca}|{cb}|1|0|1', ' ')
    if a: blk.wires.append((2,) + a)
    if b: blk.wires.append((3,) + b)
    return blk

# ---- fluxo ----
def switch_color(port, colors):                                        # Switch - Sensor de Cor - Cor
    return Blk(2004, 4, f'1|0|{colors}|1|1|1|1|1|1|1|1|1|0|0|0|0', str(port))
def loop_forever(label='01'):                                          # Loop ilimitado
    return Blk(2003, 33, LOOP_PARAMS, '', label=label)
def loop_count(n, label='01'):                                         # Loop N vezes
    p = LOOP_PARAMS.split('|'); p[11] = str(n)
    return Blk(2003, 34, '|'.join(p), '', label=label)
def wait_sec(s):                                                       # Esperar N segundos
    p = WAIT_PARAMS.split('|'); p[7] = '4'; p[17] = str(s); p[5] = '1'
    return Blk(2002, 67, '|'.join(p), ' ')

# comparacao dos blocos de sensor (Esperar, Switch, Loop): 0 =, 1 !=, 2 >, 3 >=, 4 <, 5 <=
CMP_SENSOR = {'=': 0, '!=': 1, '>': 2, '>=': 3, '<': 4, '<=': 5}

def _wait(mode, port, **campos):
    p = WAIT_PARAMS.split('|')
    for hw, v in campos.items():
        p[int(hw[1:]) - 1] = str(v)
    return Blk(2002, mode, '|'.join(p), str(port))
def wait_touch(port): return _wait(33, port)                           # Esperar toque
def wait_dist(port, cmp, thr): return _wait(35, port, p8=cmp, p6=thr)  # Esperar distancia (cm)
def wait_refl(port, cmp, thr): return _wait(4, port, p8=cmp, p6=thr)   # Esperar luz refletida
def wait_color(port, colors): return _wait(3, port, p5=colors)         # Esperar cor

def switch_touch(port): return Blk(2004, 20, SWITCH_PARAMS, str(port))  # Switch - toque
def switch_refl(port, cmp, thr):                                       # Switch - luz refletida
    return Blk(2004, 5, f'1|0|1|{thr}|{cmp}|1|1|1|1|1|1|1|0|0|0|0', str(port))
def switch_dist(port, cmp, thr):                                       # Switch - ultrassom cm
    return Blk(2004, 21, f'1|0|1|{thr}|{cmp}|1|1|1|1|1|1|1|0|0|0|0', str(port))
def switch_logic(src, out=3):                                          # Switch - logico (fio)
    b = Blk(2004, 37, SWITCH_PARAMS, ''); b.wires.append((11, src, out)); return b

def loop_refl(port, cmp, thr, label='01'):                             # Loop ate luz refletida
    p = LOOP_PARAMS.split('|'); p[3] = str(thr); p[4] = str(cmp)
    return Blk(2003, 3, '|'.join(p), str(port), label=label)
def loop_color(port, colors, label='01'):                              # Loop ate ver a cor
    p = LOOP_PARAMS.split('|'); p[2] = str(colors)
    return Blk(2003, 2, '|'.join(p), str(port), label=label)
def loop_until(src, out=3, label='01'):                                # Loop ate logico (fio)
    b = Blk(2003, 35, LOOP_PARAMS, '', label=label); b.wires.append((13, src, out)); return b
