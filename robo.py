"""Linguagem em português para programar o robô EST (pensada para aulas).

Cada comando entra no programa na ordem em que aparece. Exemplo:

    from robo import *

    andar(rotacoes=2)
    girar_direita(rotacoes=0.5)

    with para_sempre():
        with se_ver_cor(1, PRETO):
            motores(10, 30)
        with senao():
            motores(30, 10)

Leituras de sensor podem entrar em contas: erro = luz_refletida(1) - luz_refletida(2)
O resultado vira um valor que pode ir para os motores: motores(25 + erro * 0.4, 25 - erro * 0.4)
"""
import math as _m

import blocos as _b
from blocos import PRETO, AZUL, VERDE, AMARELO, VERMELHO, BRANCO, MARROM

__all__ = ['PRETO', 'AZUL', 'VERDE', 'AMARELO', 'VERMELHO', 'BRANCO', 'MARROM',
           'configurar', 'andar', 're', 'andar_cm', 'girar_direita', 'girar_esquerda', 'virar_direita',
           'virar_esquerda', 'motores', 'parar', 'motor', 'ligar_motor', 'desligar_motor', 'esperar',
           'luz_refletida', 'cor_vista', 'distancia', 'tocado', 'ler', 'guardar',
           'esperar_toque', 'esperar_distancia', 'esperar_luz', 'esperar_cor',
           'mostrar', 'tocar', 'bip', 'luz', 'apagar_luz',
           'para_sempre', 'repetir', 'repetir_ate', 'repetir_ate_luz', 'repetir_ate_cor',
           'se', 'se_ver_cor', 'se_tocado', 'se_distancia', 'se_luz', 'senao', 'novo_programa', 'programa']

POTENCIA_PADRAO = 50
_config = {'esquerdo': 'B', 'direito': 'C', 'sentido': 1, 'roda_cm': 5.6, 'entre_rodas_cm': 12.0}


# ---------------------------------------------------------------- programa em construcao

class _Trecho:
    def __init__(self, blocos):
        self.blocos = blocos
        self.ultimo_switch = None


_pilha = []


def novo_programa():
    """Começa um programa vazio (o arquivo do aluno não precisa chamar)."""
    _pilha.clear()
    _pilha.append(_Trecho([_b.start()]))


def programa():
    """Lista de blocos do programa escrito até aqui (usada por enviar.py)."""
    if len(_pilha) != 1:
        raise RuntimeError('algum "with" não foi fechado')
    return _pilha[0].blocos


def _adiciona(bloco):
    _pilha[-1].blocos.append(bloco)
    _pilha[-1].ultimo_switch = None
    return bloco


novo_programa()


# ---------------------------------------------------------------- configuracao

def configurar(esquerdo='B', direito='C', invertido=False, roda_cm=5.6, entre_rodas_cm=12.0):
    """Ajusta o programa ao robo.

    esquerdo, direito   portas dos motores das rodas
    invertido           True se o robô anda de ré quando deveria ir para frente
    roda_cm             diâmetro da roda (para andar_cm)
    entre_rodas_cm      distância entre as duas rodas (para virar_direita / virar_esquerda)
    """
    _config.update(esquerdo=esquerdo.upper(), direito=direito.upper(), sentido=-1 if invertido else 1,
                   roda_cm=roda_cm, entre_rodas_cm=entre_rodas_cm)


def _tanque(construtor, esq, dir_, *extra, **kw):
    e, d = _config['esquerdo'], _config['direito']
    _b.MOTORS = f'{min(e, d)}+{max(e, d)}'
    if e > d:
        esq, dir_ = dir_, esq
    return _adiciona(construtor(esq, dir_, *extra, **kw))


def _pot(p):
    if isinstance(p, Valor):
        return p if _config['sentido'] == 1 else -p
    return _config['sentido'] * p


def _mover(esq, dir_, rotacoes, graus, segundos, frear):
    dados = [v for v in (rotacoes, graus, segundos) if v is not None]
    if len(dados) != 1:
        raise ValueError('diga quanto andar: rotacoes=..., graus=... ou segundos=...')
    esq, dir_ = _pot(esq), _pot(dir_)
    if rotacoes is not None:
        return _tanque(_b.tank_rot, esq, dir_, rotacoes, brake=frear)
    if graus is not None:
        return _tanque(_b.tank_deg, esq, dir_, graus, brake=frear)
    return _tanque(_b.tank_sec, esq, dir_, segundos, brake=frear)


# ---------------------------------------------------------------- movimento

def andar(rotacoes=None, graus=None, segundos=None, potencia=POTENCIA_PADRAO, frear=True):
    """Anda para frente. Ex.: andar(rotacoes=2), andar(segundos=1.5, potencia=30)"""
    return _mover(potencia, potencia, rotacoes, graus, segundos, frear)


def re(rotacoes=None, graus=None, segundos=None, potencia=POTENCIA_PADRAO, frear=True):
    """Anda de ré. Ex.: re(rotacoes=1)"""
    return _mover(-potencia, -potencia, rotacoes, graus, segundos, frear)


def andar_cm(cm, potencia=POTENCIA_PADRAO, frear=True):
    """Anda cm centímetros (negativo = ré). Ajuste o tamanho da roda em configurar(roda_cm=...)."""
    graus = abs(cm) / (_m.pi * _config['roda_cm']) * 360
    p = potencia if cm >= 0 else -potencia
    return _mover(p, p, None, round(graus, 1), None, frear)


def girar_direita(rotacoes=None, graus=None, segundos=None, potencia=POTENCIA_PADRAO, frear=True):
    """Gira no lugar para a direita (as rodas giram em sentidos opostos).
    graus e rotações são das rodas; para virar o robô um angulo, use virar_direita."""
    return _mover(potencia, -potencia, rotacoes, graus, segundos, frear)


def girar_esquerda(rotacoes=None, graus=None, segundos=None, potencia=POTENCIA_PADRAO, frear=True):
    """Gira no lugar para a esquerda."""
    return _mover(-potencia, potencia, rotacoes, graus, segundos, frear)


def _graus_da_roda(angulo_robo):
    return round(angulo_robo * _config['entre_rodas_cm'] / _config['roda_cm'], 1)


def virar_direita(angulo=90, potencia=30):
    """Vira o robô angulo graus para a direita, no lugar. Calibre com configurar(entre_rodas_cm=...)."""
    return _mover(potencia, -potencia, None, _graus_da_roda(angulo), None, True)


def virar_esquerda(angulo=90, potencia=30):
    """Vira o robô angulo graus para a esquerda, no lugar."""
    return _mover(-potencia, potencia, None, _graus_da_roda(angulo), None, True)


def motores(esquerdo, direito):
    """Liga os dois motores e deixa ligados. Aceita números ou valores de sensor/contas."""
    esq, dir_ = _pot(esquerdo), _pot(direito)
    ce = 0 if isinstance(esq, Valor) else esq
    cd = 0 if isinstance(dir_, Valor) else dir_
    blk = _tanque(_b.tank_on, ce, cd)
    e, d = _config['esquerdo'], _config['direito']
    lados = [(1, esq), (2, dir_)] if e < d else [(1, dir_), (2, esq)]
    for entrada, v in lados:
        if isinstance(v, Valor):
            blk.wires.append((entrada, v.bloco, v.saida))
    return blk


def parar(frear=True):
    """Desliga os dois motores."""
    return _tanque(lambda e, d, brake: _b.tank_off(brake), 0, 0, brake=frear)


def motor(porta, potencia=POTENCIA_PADRAO, rotacoes=None, graus=None, segundos=None, frear=True):
    """Gira um motor sozinho. Ex.: motor('A', 50, graus=180), motor('D', 30, segundos=2)"""
    dados = [v for v in (rotacoes, graus, segundos) if v is not None]
    if len(dados) > 1:
        raise ValueError('use só um: rotacoes=..., graus=... ou segundos=...')
    p = porta.upper()
    if rotacoes is not None:
        return _adiciona(_b.motor_rot(p, potencia, rotacoes, frear))
    if segundos is not None:
        return _adiciona(_b.motor_sec(p, potencia, segundos, frear))
    return _adiciona(_b.motor_deg(p, potencia, 360 if graus is None else graus, frear))


def ligar_motor(porta, potencia=POTENCIA_PADRAO):
    """Liga um motor e deixa ligado."""
    return _adiciona(_b.motor_on(porta.upper(), potencia))


def desligar_motor(porta, frear=True):
    """Desliga um motor."""
    return _adiciona(_b.motor_off(porta.upper(), frear))


def esperar(segundos):
    """Espera alguns segundos."""
    return _adiciona(_b.wait_sec(segundos))


# ---------------------------------------------------------------- valores e contas

def _const(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f'não sei fazer conta com {v!r}')
    return v


class Valor:
    """Um número que só existe no robô (leitura de sensor ou resultado de conta)."""
    def __init__(self, bloco, saida, byte=False):
        self.bloco, self.saida, self.byte = bloco, saida, byte

    def _conta(self, op, outro, invertido=False):
        a, b = (outro, self) if invertido else (self, outro)
        kw = {}
        for nome, lado in (('a', a), ('b', b)):
            if isinstance(lado, Valor):
                kw[nome] = (lado.bloco, lado.saida)
            else:
                kw['c' + nome] = _const(lado)
        return Valor(_adiciona(_b.math(op, **kw)), 1)

    def __add__(self, o): return self._conta('+', o)
    def __radd__(self, o): return self._conta('+', o, True)
    def __sub__(self, o): return self._conta('-', o)
    def __rsub__(self, o): return self._conta('-', o, True)
    def __mul__(self, o): return self._conta('*', o)
    def __rmul__(self, o): return self._conta('*', o, True)
    def __truediv__(self, o): return self._conta('/', o)
    def __rtruediv__(self, o): return self._conta('/', o, True)
    def __neg__(self): return self._conta('-', 0, True)

    def _compara(self, op, outro):
        kw = {'a': (self.bloco, self.saida)}
        if isinstance(outro, Valor):
            kw['b'] = (outro.bloco, outro.saida)
        else:
            kw['cb'] = _const(outro)
        return Condicao(_adiciona(_b.compare(op, **kw)))

    def __lt__(self, o): return self._compara('<', o)
    def __le__(self, o): return self._compara('<=', o)
    def __gt__(self, o): return self._compara('>', o)
    def __ge__(self, o): return self._compara('>=', o)
    def __eq__(self, o): return self._compara('=', o)
    def __ne__(self, o): return self._compara('!=', o)
    __hash__ = object.__hash__

    def __bool__(self):
        raise TypeError('valores do robô não funcionam com "if" do Python: use "with se(...)"')


class Condicao:
    """Resultado de uma comparação feita no robô (ex.: distancia(4) < 20)."""
    def __init__(self, bloco):
        self.bloco, self.saida = bloco, 3

    def __bool__(self):
        raise TypeError('comparações do robô não funcionam com "if" do Python: use "with se(...)"')


def luz_refletida(porta):
    """Lê a luz refletida (0 = escuro, 100 = claro) do sensor de cor na porta."""
    return Valor(_adiciona(_b.sensor_refl(porta)), 7)


def cor_vista(porta):
    """Lê o número da cor vista pelo sensor (PRETO = 1, VERDE = 3, BRANCO = 6...)."""
    return Valor(_adiciona(_b.sensor_color_id(porta)), 5, byte=True)


def distancia(porta):
    """Lê a distância em centímetros do sensor ultrassônico na porta."""
    return Valor(_adiciona(_b.ultrasonic_cm(porta)), 4)


def tocado(porta):
    """Lê o sensor de toque: 1 = apertado, 0 = solto."""
    return Valor(_adiciona(_b.touch_state(porta)), 2, byte=True)


def ler(nome):
    """Lê o número guardado numa variável do robô. Ex.: ler('contador')"""
    return Valor(_adiciona(_b.var_rn(nome)), 2)


def guardar(nome, valor):
    """Guarda um número ou valor numa variável do robô. Ex.: guardar('erro', erro)"""
    if isinstance(valor, Valor):
        return _adiciona(_b.var_wn(nome, src=valor.bloco, out=valor.saida))
    return _adiciona(_b.var_wn(nome, _const(valor)))


# ---------------------------------------------------------------- esperas por sensor

def _cmp(comparacao):
    try:
        return _b.CMP_SENSOR[comparacao]
    except KeyError:
        raise ValueError(f'comparação {comparacao!r} invalida: use "<", "<=", ">", ">=", "=" ou "!="') from None


def esperar_toque(porta):
    """Espera o sensor de toque ser apertado."""
    return _adiciona(_b.wait_touch(porta))


def esperar_distancia(porta, comparacao, cm):
    """Espera a distância ficar menor/maior que cm. Ex.: esperar_distancia(4, '<', 20)"""
    return _adiciona(_b.wait_dist(porta, _cmp(comparacao), cm))


def esperar_luz(porta, comparacao, valor):
    """Espera a luz refletida passar de um valor. Ex.: esperar_luz(1, '<', 30)"""
    return _adiciona(_b.wait_refl(porta, _cmp(comparacao), valor))


def esperar_cor(porta, cor):
    """Espera o sensor ver a cor. Ex.: esperar_cor(1, VERDE)"""
    return _adiciona(_b.wait_color(porta, cor))


# ---------------------------------------------------------------- tela, som e luz

def _ascii(texto):
    import unicodedata
    t = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in t if ord(c) < 128)


LINHAS_DA_TELA = {1: 0, 2: 20, 3: 40}     # conferido no robo em 2026-10-13: abaixo de y=40 o texto nao aparece


def mostrar(texto, linha=1, x=0, limpar=None, y=None):
    """Escreve um texto ou um valor na tela do robô, que tem 3 linhas.
    Ex.: mostrar('Luz:'), mostrar(luz_refletida(1), linha=2)
    Escrever na linha 1 apaga a tela antes; nas linhas 2 e 3 escreve sem apagar."""
    if y is None:
        if linha not in LINHAS_DA_TELA:
            raise ValueError('a tela tem 3 linhas: use linha=1, linha=2 ou linha=3')
        y = LINHAS_DA_TELA[linha]
    elif not 0 <= y <= 40:
        raise ValueError(f'y={y} não cabe na tela: use y de 0 a 40 (ou linha=1, 2, 3)')
    if limpar is None:
        limpar = y == 0
    if isinstance(texto, Valor):
        if texto.byte:
            texto = texto + 0        # a tela converte numero de 4 bytes em texto; leituras de 1 byte passam por uma conta
        return _adiciona(_b.display_val(texto.bloco, texto.saida, x, y, limpar))
    return _adiciona(_b.display(_ascii(texto), x, y, limpar))


def tocar(frequencia=440, segundos=1, volume=100):
    """Toca um som. Ex.: tocar(440, 0.5)"""
    return _adiciona(_b.sound_tone(frequencia, segundos, volume))


def bip():
    """Um bip curto."""
    return tocar(880, 0.2)


_CORES_LUZ = {'azul': 0, 'roxo': 1, 'vermelho': 2}      # conferido no robo em 2026-10-13


def luz(cor='azul', piscar=False):
    """Acende a luz do robô: 'azul', 'roxo' ou 'vermelho'."""
    try:
        return _adiciona(_b.light_on(_CORES_LUZ[cor.lower()], piscar))
    except KeyError:
        raise ValueError('cores da luz: "azul", "roxo" ou "vermelho"') from None


def apagar_luz():
    """Apaga a luz do robo."""
    return _adiciona(_b.light_off())


# ---------------------------------------------------------------- loops e decisoes

class _Bloco:
    def __init__(self, bloco, ramo, abre_senao=False, condicao_no_fim=None):
        self.bloco, self.ramo, self.abre_senao = bloco, ramo, abre_senao
        self.condicao_no_fim = condicao_no_fim

    def __enter__(self):
        _pilha.append(_Trecho(self.ramo))
        return self

    def __exit__(self, tipo_erro, *erro):
        if self.condicao_no_fim and tipo_erro is None:
            cond = self.condicao_no_fim()
            if not isinstance(cond, Condicao):
                raise TypeError('repetir_ate precisa de uma comparação, ex.: repetir_ate(lambda: distancia(4) < 20)')
            self.bloco.wires.append((13, cond.bloco, cond.saida))
        _pilha.pop()
        _pilha[-1].ultimo_switch = self.bloco if self.abre_senao else None
        return False


def para_sempre():
    """Repete para sempre o que estiver dentro do with."""
    blk = _adiciona(_b.loop_forever())
    return _Bloco(blk, blk.b1)


def repetir(vezes):
    """Repete vezes vezes o que estiver dentro do with."""
    blk = _adiciona(_b.loop_count(vezes))
    return _Bloco(blk, blk.b1)


def repetir_ate(condicao):
    """Repete até a condição acontecer. A condição vai num lambda para ser medida a cada volta:
    with repetir_ate(lambda: distancia(4) < 20): ..."""
    if not callable(condicao):
        raise TypeError('use repetir_ate(lambda: ...), ex.: repetir_ate(lambda: distancia(4) < 20)')
    blk = _adiciona(_b.Blk(2003, 35, _b.LOOP_PARAMS, '', label='01'))
    return _Bloco(blk, blk.b1, condicao_no_fim=condicao)


def repetir_ate_luz(porta, comparacao, valor):
    """Repete até a luz refletida passar de um valor. Ex.: repetir_ate_luz(1, '<', 30)"""
    blk = _adiciona(_b.loop_refl(porta, _cmp(comparacao), valor))
    return _Bloco(blk, blk.b1)


def repetir_ate_cor(porta, cor):
    """Repete até o sensor ver a cor."""
    blk = _adiciona(_b.loop_color(porta, cor))
    return _Bloco(blk, blk.b1)


def _se(blk):
    return _Bloco(_adiciona(blk), blk.b1, abre_senao=True)


def se(condicao):
    """Faz o que estiver dentro se a comparação for verdadeira. Ex.: with se(distancia(4) < 20):"""
    if not isinstance(condicao, Condicao):
        raise TypeError('se(...) precisa de uma comparação, ex.: se(distancia(4) < 20)')
    return _se(_b.switch_logic(condicao.bloco, condicao.saida))


def se_ver_cor(porta, cor):
    """Faz o que estiver dentro se o sensor da porta ver a cor (ou uma das cores: PRETO + VERDE)."""
    return _se(_b.switch_color(porta, cor))


def se_tocado(porta):
    """Faz o que estiver dentro se o sensor de toque estiver apertado."""
    return _se(_b.switch_touch(porta))


def se_distancia(porta, comparacao, cm):
    """Ex.: with se_distancia(4, '<', 20):"""
    return _se(_b.switch_dist(porta, _cmp(comparacao), cm))


def se_luz(porta, comparacao, valor):
    """Ex.: with se_luz(1, '<', 30):"""
    return _se(_b.switch_refl(porta, _cmp(comparacao), valor))


def senao():
    """O que fazer quando a condição do "with se_..." logo acima não acontece."""
    sw = _pilha[-1].ultimo_switch
    if sw is None:
        raise SyntaxError('"with senao()" precisa vir logo depois de um "with se_..."')
    return _Bloco(sw, sw.b2)
