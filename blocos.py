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

# ---- sensores ----
def sensor_refl(port): return Blk(3002, 2, '5|4|0|50|0|0|0', str(port))          # saida 7 = luz refletida
def sensor_color_id(port): return Blk(3002, 1, '5|4|0|50|0|0|0', str(port))      # saida 5 = numero da cor

# ---- variaveis e contas ----
def var_wn(name, value=1, src=None, out=None):                         # Escrever variavel numerica
    b = Blk(4001, 5, f'2|0|0|0|0|0|{value}|1|1|1', name)
    if src: b.wires.append((7, src, out))
    return b
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
