"""
EST Robot - API Python para programar o robo Dr. Luck EST.

Uso:
    from est import *
    motor(A, velocidade=50, direcao=FRENTE)
    esperar(1.0)
    with repetir(3):
        motor(A, velocidade=50, direcao=FRENTE)
"""

# ── Constantes públicas ───────────────────────────────────────────────────────

# Portas de motor
A = 'A'
B = 'B'
C = 'C'
D = 'D'

# Direções
FRENTE   = 'frente'
TRAS     = 'tras'
PARAR    = 'parar'

# Sensores (portas)
S1 = 1
S2 = 2
S3 = 3
S4 = 4

# Cores do sensor RGB
PRETO    = 1
VERDE    = 3
VERMELHO = 5
BRANCO   = 6

# ── Registro de instruções do programa ───────────────────────────────────────

_program_instructions = []
_context_stack = []     # pilha de contextos para instrucoes aninhadas

def _reset():
    global _program_instructions, _context_stack
    _program_instructions = []
    _context_stack = []

def _add(instr_type, **kwargs):
    instr = {'tipo': instr_type, **kwargs}
    if _context_stack:
        _context_stack[-1].append(instr)
    else:
        _program_instructions.append(instr)

def _push_context(lst):
    _context_stack.append(lst)

def _pop_context():
    if _context_stack:
        _context_stack.pop()

# ── Contexto de loop (para uso com 'with') ────────────────────────────────────

class _LoopContext:
    """
    Contexto gerado por repetir().  Use com 'with':

        with repetir(3):
            motor(A, velocidade=50, direcao=FRENTE)
    """
    def __init__(self, vezes: int):
        self.vezes = vezes
        self.instrucoes = []

    def __enter__(self):
        _push_context(self.instrucoes)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _pop_context()
        _add('loop', vezes=self.vezes, instrucoes=list(self.instrucoes))
        return False   # nao suprime excecoes

# ── API pública ───────────────────────────────────────────────────────────────

def motor(porta, velocidade=50, direcao=FRENTE, rotacoes=0):
    """
    Controla um motor.

    Args:
        porta:      A, B, C ou D
        velocidade: 0 a 100
        direcao:    FRENTE, TRAS ou PARAR
        rotacoes:   numero de rotacoes (0 = modo ON continuo; >0 = para apos N rotacoes)
                    Suportado apenas para porta B por enquanto.

    Exemplos:
        motor(B, velocidade=50, direcao=FRENTE, rotacoes=1)   # 1 rotacao
        motor(B, velocidade=75, direcao=TRAS,   rotacoes=3)   # 3 rotacoes para tras
    """
    velocidade = max(0, min(100, int(velocidade)))
    _add('motor', porta=porta, velocidade=velocidade, direcao=direcao,
         rotacoes=int(rotacoes))


def esperar(segundos):
    """
    Pausa a execução por N segundos.

    Args:
        segundos: tempo de espera (float)
    """
    _add('esperar', segundos=float(segundos))


def repetir(vezes=0):
    """
    Repete um bloco N vezes (ou infinitamente se vezes=0).

    Use com 'with' para incluir instruções dentro do loop:

        with repetir(3):
            motor(A, velocidade=50, direcao=FRENTE)

        with repetir():          # loop infinito
            motor(A, velocidade=50, direcao=FRENTE)

    Para loop vazio (sem bloco interno):

        with repetir(3):
            pass

    Args:
        vezes: numero de repeticoes (0 = infinito)

    Returns:
        _LoopContext (use com 'with')
    """
    n = 0 if (vezes is None or vezes == 0) else int(vezes)
    return _LoopContext(n)


def se_sensor_cor(porta, cor, se_motor_args, senao_motor_args):
    """
    Condicional: se sensor(porta) == cor entao motor_A, senao motor_B.

    se_motor_args e senao_motor_args sao tuplas/listas:
        (velocidade, direcao, rotacoes)

    Exemplo:
        se_sensor_cor(S3, PRETO,
            se_motor_args   = (50,  FRENTE, 1),
            senao_motor_args= (50,  TRAS,   1))
    """
    def _parse(args):
        if isinstance(args, dict):
            return args
        return {'velocidade': args[0], 'direcao': args[1], 'rotacoes': args[2]}

    _add('se_sensor_cor',
         porta=porta,
         cor=cor,
         se_motor=_parse(se_motor_args),
         senao_motor=_parse(senao_motor_args))


def se_sensor_cor_2motores(porta, cor,
                            se_motor_B_args, se_motor_C_args,
                            senao_motor_B_args, senao_motor_C_args):
    """
    Condicional com 2 motores: se sensor(porta) == cor entao B+C, senao B+C.

    Cada argumento e uma tupla (velocidade, direcao, rotacoes).
    Deve ser usado dentro de 'with repetir()' (loop infinito).

    Motor B = esquerda, Motor C = direita.
    Positivo = FRENTE, negativo = TRAS.

    Exemplo (seguidor de linha simples, sensor S1 esquerdo):
        with repetir():
            se_sensor_cor_2motores(
                S1, PRETO,
                se_motor_B_args   = (50, FRENTE, 1),   # if: B frente
                se_motor_C_args   = (50, FRENTE, 1),   # if: C frente
                senao_motor_B_args= (50, FRENTE, 1),   # else: B frente
                senao_motor_C_args= (50, TRAS,   1),   # else: C tras
            )
    """
    def _parse(args):
        if isinstance(args, dict):
            return args
        return {'velocidade': args[0], 'direcao': args[1], 'rotacoes': args[2]}

    _add('se_sensor_cor',
         porta=porta,
         cor=cor,
         se_motor_B=_parse(se_motor_B_args),
         se_motor_C=_parse(se_motor_C_args),
         senao_motor_B=_parse(senao_motor_B_args),
         senao_motor_C=_parse(senao_motor_C_args))


def sensor_cor(porta, cor, tipo='rgbcores'):
    """
    Configura um bloco de deteccao de cor do sensor RGB.

    Args:
        porta: S1, S2, S3 ou S4 (porta do sensor)
        cor:   PRETO, VERDE, VERMELHO ou BRANCO
        tipo:  'rgbcores' (padrao, bloco 40B) ou 'cores' (bloco 64B)

    Exemplos:
        sensor_cor(S3, PRETO)
        sensor_cor(S3, VERMELHO, tipo='cores')

    Use multiplos sensor_cor() para configurar varias cores.
    Todos devem usar o mesmo tipo e o mesmo porta no mesmo programa.
    """
    _add('sensor_cor', porta=porta, cor=cor, sensor_tipo=tipo)


def ler_sensor(porta):
    """
    Le o valor de um sensor.

    Args:
        porta: S1, S2, S3 ou S4

    Returns:
        valor do sensor (0-100)
    """
    _add('ler_sensor', porta=porta)
    return 0  # placeholder - valor real vem do robo


def parar_tudo():
    """Para todos os motores."""
    _add('parar_tudo')
