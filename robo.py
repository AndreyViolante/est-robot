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
from __future__ import annotations

import importlib.util as _imp
import math as _m
import os as _os
from typing import Callable, Literal

import blocos as _b
from blocos import PRETO, AZUL, VERDE, AMARELO, VERMELHO, BRANCO, MARROM

__all__ = ['PRETO', 'AZUL', 'VERDE', 'AMARELO', 'VERMELHO', 'BRANCO', 'MARROM',
           'configurar', 'andar', 're', 'andar_cm', 'girar_direita', 'girar_esquerda', 'virar_direita',
           'virar_esquerda', 'motores', 'parar', 'motor', 'ligar_motor', 'desligar_motor', 'esperar',
           'luz_refletida', 'cor_vista', 'distancia', 'tocado', 'ler', 'guardar',
           'esperar_toque', 'esperar_distancia', 'esperar_luz', 'esperar_cor',
           'mostrar', 'tocar', 'bip', 'luz', 'apagar_luz',
           'para_sempre', 'repetir', 'repetir_ate', 'repetir_ate_luz', 'repetir_ate_cor',
           'se', 'se_ver_cor', 'se_tocado', 'se_distancia', 'se_luz', 'senao', 'limite',
           'melodia', 'botao_apertado', 'esperar_botao', 'ao_mesmo_tempo', 'tarefa', 'painel', 'ajustando',
           'ajustes', 'medir_laco', 'calibrar_na_largada', 'limite_medido',
           'BOTAO_CIMA', 'BOTAO_BAIXO', 'BOTAO_ESQUERDA', 'BOTAO_DIREITA', 'BOTAO_CENTRO',
           'novo_programa', 'programa']

# Tipos das opções: o VS Code mostra estes valores no autocompletar enquanto o aluno escreve
# (só ajudam a escrever; quem confere de verdade são os próprios comandos).
PortaSensor = Literal[1, 2, 3, 4]
PortaMotor = Literal['A', 'B', 'C', 'D']
Comparacao = Literal['<', '<=', '>', '>=', '=', '!=']
CorDaLuz = Literal['azul', 'roxo', 'vermelho']
Linha = Literal[1, 2, 3]

POTENCIA_PADRAO = 50
_config = {'esquerdo': 'B', 'direito': 'C', 'sentido': 1, 'roda_cm': 4.3, 'entre_rodas_cm': 12.0, 'pausa': 0.5}


# ---------------------------------------------------------------- programa em construcao

class _Trecho:
    def __init__(self, blocos):
        self.blocos = blocos
        self.ultimo_switch = None


_pilha = []


_MODO_COR = {('3002', '1'), ('2004', '4'), ('2003', '2'), ('2002', '3')}
_MODO_LUZ = {('3002', '2'), ('2004', '5'), ('2003', '3'), ('2002', '4')}


def avisos(blocos):
    """Problemas que não impedem o envio, mas atrapalham o robô."""
    modos = {}
    def percorre(lista):
        for b in lista:
            chave = (b.t, b.mode)
            if chave in _MODO_COR or chave in _MODO_LUZ:
                modos.setdefault(str(b.port).strip(), set()).add('cor' if chave in _MODO_COR else 'luz')
            percorre(b.b1); percorre(b.b2)
            for ramo in getattr(b, 'ramos', []):
                percorre(ramo)
    percorre(blocos)
    return [f'o sensor da porta {p} é usado no modo cor (cor_vista, se_ver_cor...) e no modo luz '
            f'(luz_refletida, se_luz...). Ele vai ficar trocando de modo, fica lento e erra leituras. '
            f'Use um modo só para cada sensor.' for p, m in sorted(modos.items()) if len(m) > 1]


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

def configurar(esquerdo: PortaMotor | None = None, direito: PortaMotor | None = None, invertido: bool | None = None,
               roda_cm: float | None = None, entre_rodas_cm: float | None = None, pausa: float | None = None):
    """Ajusta só este programa ao robô (o que não for informado fica como está no calibracao.py).

    esquerdo, direito   portas dos motores das rodas
    invertido           True se o robô anda de ré quando deveria ir para frente
    roda_cm             diâmetro efetivo da roda (para andar_cm); 4.3 medido no robô EST
    entre_rodas_cm      distância entre as duas rodas (para virar_direita / virar_esquerda)
    pausa               segundos parado depois de cada movimento que freia (0 = sem pausa);
                        sem ela o robô emenda um movimento no outro e erra a virada
    """
    if esquerdo is not None:
        _config['esquerdo'] = str(esquerdo).upper()
    if direito is not None:
        _config['direito'] = str(direito).upper()
    if invertido is not None:
        _config['sentido'] = -1 if invertido else 1
    for nome, valor in (('roda_cm', roda_cm), ('entre_rodas_cm', entre_rodas_cm), ('pausa', pausa)):
        if valor is not None:
            _config[nome] = valor


# luz refletida de cada sensor no preto e no branco, do calibracao.py (para limite())
_PRETO, _BRANCO = {}, {}
AVISO_DE_VERSAO = True        # calibracao.py: False desliga o aviso diário de versão nova (enviar.py)
# números dos botões no bloco "Botões da controladora" da IDE (como no EV3: 1 esquerda, 2 centro, 3 direita,
# 4 cima, 5 baixo). Ainda não conferidos no robô: a tarefa Teste geral descobre, e o calibracao.py pode trocar.
BOTAO_ESQUERDA, BOTAO_CENTRO, BOTAO_DIREITA, BOTAO_CIMA, BOTAO_BAIXO = 1, 2, 3, 4, 5
_BOTOES = ('BOTAO_ESQUERDA', 'BOTAO_CENTRO', 'BOTAO_DIREITA', 'BOTAO_CIMA', 'BOTAO_BAIXO')


def _carregar_calibracao():
    """Lê o calibracao.py da pasta do projeto, se existir: as medidas do robô valem para todos os programas."""
    arquivo = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'calibracao.py')
    if not _os.path.exists(arquivo):
        return
    try:
        spec = _imp.spec_from_file_location('calibracao', arquivo)
        cal = _imp.module_from_spec(spec)
        spec.loader.exec_module(cal)
    except SyntaxError as e:
        raise SyntaxError(f'erro no calibracao.py, linha {e.lineno}: confira o que foi mudado lá') from None
    configurar(esquerdo=getattr(cal, 'MOTOR_ESQUERDO', None), direito=getattr(cal, 'MOTOR_DIREITO', None),
               invertido=getattr(cal, 'INVERTIDO', None), roda_cm=getattr(cal, 'RODA_CM', None),
               entre_rodas_cm=getattr(cal, 'ENTRE_RODAS_CM', None), pausa=getattr(cal, 'PAUSA', None))
    global AVISO_DE_VERSAO
    AVISO_DE_VERSAO = bool(getattr(cal, 'AVISO_DE_VERSAO', True))
    _PRETO.update(getattr(cal, 'PRETO', {}))
    _BRANCO.update(getattr(cal, 'BRANCO', {}))
    for nome in _BOTOES:
        if isinstance(getattr(cal, nome, None), int):
            globals()[nome] = getattr(cal, nome)


_carregar_calibracao()


def _sensor(porta):
    """Confere a porta de um sensor (1 a 4). Devolve como veio, para o bloco sair igual ao da IDE."""
    if isinstance(porta, bool) or str(porta).strip() not in ('1', '2', '3', '4'):
        raise ValueError(f'a porta {porta!r} não é de sensor: os sensores vão nas portas 1, 2, 3 ou 4 '
                         '(os motores, nas letras "A" a "D")')
    return porta


def _motor(porta):
    """Confere a porta de um motor ('A' a 'D', maiúscula ou minúscula) e devolve em maiúscula."""
    p = str(porta).strip().upper()
    if p not in ('A', 'B', 'C', 'D'):
        raise ValueError(f'a porta {porta!r} não é de motor: os motores vão nas portas "A", "B", "C" ou "D", '
                         'com aspas (os sensores, nos números 1 a 4)')
    return p


def limite(porta: PortaSensor) -> float:
    """O meio do caminho entre o preto e o branco do sensor, medidos no calibracao.py.
    Ex.: with se_luz(1, '<', limite(1)):   ou   if luz_refletida(1) < limite(1):"""
    p = int(str(porta).strip())
    if p not in _PRETO or p not in _BRANCO:
        raise ValueError(f'meça o preto e o branco do sensor {p} e escreva no calibracao.py (PRETO e BRANCO)')
    return round((_PRETO[p] + _BRANCO[p]) / 2, 1)


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
        bloco = _tanque(_b.tank_rot, esq, dir_, rotacoes, brake=frear)
    elif graus is not None:
        bloco = _tanque(_b.tank_deg, esq, dir_, graus, brake=frear)
    else:
        bloco = _tanque(_b.tank_sec, esq, dir_, segundos, brake=frear)
    if frear and _config['pausa']:
        _adiciona(_b.wait_sec(_config['pausa']))   # testado no robô: sem a pausa a virada seguinte sai errada
    return bloco


# ---------------------------------------------------------------- movimento

def andar(rotacoes: float | None = None, graus: float | None = None, segundos: float | None = None,
          potencia: float = POTENCIA_PADRAO, frear: bool = True):
    """Anda para frente. Ex.: andar(rotacoes=2), andar(segundos=1.5, potencia=30)"""
    return _mover(potencia, potencia, rotacoes, graus, segundos, frear)


def re(rotacoes: float | None = None, graus: float | None = None, segundos: float | None = None,
       potencia: float = POTENCIA_PADRAO, frear: bool = True):
    """Anda de ré. Ex.: re(rotacoes=1)"""
    return _mover(-potencia, -potencia, rotacoes, graus, segundos, frear)


def andar_cm(cm: float, potencia: float = POTENCIA_PADRAO, frear: bool = True):
    """Anda cm centímetros (negativo = ré). Ajuste o tamanho da roda em configurar(roda_cm=...)."""
    graus = abs(cm) / (_m.pi * _config['roda_cm']) * 360
    p = potencia if cm >= 0 else -potencia
    return _mover(p, p, None, round(graus, 1), None, frear)


def girar_direita(rotacoes: float | None = None, graus: float | None = None, segundos: float | None = None,
                  potencia: float = POTENCIA_PADRAO, frear: bool = True):
    """Gira no lugar para a direita (as rodas giram em sentidos opostos).
    graus e rotações são das rodas; para virar o robô um angulo, use virar_direita."""
    return _mover(potencia, -potencia, rotacoes, graus, segundos, frear)


def girar_esquerda(rotacoes: float | None = None, graus: float | None = None, segundos: float | None = None,
                   potencia: float = POTENCIA_PADRAO, frear: bool = True):
    """Gira no lugar para a esquerda."""
    return _mover(-potencia, potencia, rotacoes, graus, segundos, frear)


def _graus_da_roda(angulo_robo):
    return round(angulo_robo * _config['entre_rodas_cm'] / _config['roda_cm'], 1)


def virar_direita(angulo: float = 90, potencia: float = 30):
    """Vira o robô angulo graus para a direita, no lugar. Calibre com configurar(entre_rodas_cm=...)."""
    return _mover(potencia, -potencia, None, _graus_da_roda(angulo), None, True)


def virar_esquerda(angulo: float = 90, potencia: float = 30):
    """Vira o robô angulo graus para a esquerda, no lugar."""
    return _mover(-potencia, potencia, None, _graus_da_roda(angulo), None, True)


def motores(esquerdo: float | Valor, direito: float | Valor):
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


def parar(frear: bool = True):
    """Desliga os dois motores."""
    return _tanque(lambda e, d, brake: _b.tank_off(brake), 0, 0, brake=frear)


def motor(porta: PortaMotor, potencia: float = POTENCIA_PADRAO, rotacoes: float | None = None,
          graus: float | None = None, segundos: float | None = None, frear: bool = True):
    """Gira um motor sozinho. Ex.: motor('A', 50, graus=180), motor('D', 30, segundos=2)"""
    dados = [v for v in (rotacoes, graus, segundos) if v is not None]
    if len(dados) > 1:
        raise ValueError('use só um: rotacoes=..., graus=... ou segundos=...')
    p = _motor(porta)
    if rotacoes is not None:
        return _adiciona(_b.motor_rot(p, potencia, rotacoes, frear))
    if segundos is not None:
        return _adiciona(_b.motor_sec(p, potencia, segundos, frear))
    return _adiciona(_b.motor_deg(p, potencia, 360 if graus is None else graus, frear))


def ligar_motor(porta: PortaMotor, potencia: float = POTENCIA_PADRAO):
    """Liga um motor e deixa ligado."""
    return _adiciona(_b.motor_on(_motor(porta), potencia))


def desligar_motor(porta: PortaMotor, frear: bool = True):
    """Desliga um motor."""
    return _adiciona(_b.motor_off(_motor(porta), frear))


def esperar(segundos: float):
    """Espera alguns segundos."""
    return _adiciona(_b.wait_sec(segundos))


# ---------------------------------------------------------------- valores e contas

def _const(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f'não sei fazer conta com {v!r}')
    return v


class Valor:
    """Um número que só existe no robô (leitura de sensor ou resultado de conta)."""
    def __init__(self, bloco, saida, byte=False, cor=False):
        self.bloco, self.saida, self.byte, self.cor = bloco, saida, byte, cor

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
        elif isinstance(outro, str):
            kw['cb'] = _numero_da_cor(outro, self)
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
        raise TypeError('esse valor do robô não funciona aqui: use ele num "if" ou num "while" '
                        '(o "x if ... else y" numa linha só ainda não funciona com o robô)')


# numero que cor_vista() devolve para cada cor. No robo (2026-10-16) o preto deu 1 e o branco oscilou entre 6 e 0:
# 0 = nenhuma cor, quando o sensor nao tem certeza (longe do chao, luz forte)
_NUMERO_DA_COR = {PRETO: 1, AZUL: 2, VERDE: 3, AMARELO: 4, VERMELHO: 5, BRANCO: 6, MARROM: 7}


def _numero_da_cor(cor, valor):
    if not valor.cor:
        raise TypeError('nomes de cor (PRETO, VERDE...) só podem ser comparados com cor_vista(...)')
    if cor not in _NUMERO_DA_COR:
        raise TypeError('compare uma cor por vez, ex.: se(cor_vista(1) == VERDE)')
    return _NUMERO_DA_COR[cor]


class Condicao:
    """Resultado de uma comparação feita no robô (ex.: distancia(4) < 20)."""
    def __init__(self, bloco):
        self.bloco, self.saida = bloco, 3

    def __bool__(self):
        raise TypeError('essa comparação do robô não funciona aqui: use ela num "if" ou num "while" '
                        '(o "x if ... else y" numa linha só ainda não funciona com o robô)')


def luz_refletida(porta: PortaSensor) -> Valor:
    """Lê a luz refletida (0 = escuro, 100 = claro) do sensor de cor na porta."""
    return Valor(_adiciona(_b.sensor_refl(_sensor(porta))), 7)


def cor_vista(porta: PortaSensor) -> Valor:
    """Lê a cor vista pelo sensor. Compare com os nomes: with se(cor_vista(1) == VERDE):
    Na tela aparece um número: PRETO = 1, AZUL = 2, VERDE = 3, AMARELO = 4, VERMELHO = 5, BRANCO = 6,
    e 0 quando o sensor não reconhece a cor (o branco às vezes dá 0).
    Para linha preta no chão branco, luz_refletida é mais confiável."""
    return Valor(_adiciona(_b.sensor_color_id(_sensor(porta))), 5, byte=True, cor=True)


def distancia(porta: PortaSensor) -> Valor:
    """Lê a distância em centímetros do sensor ultrassônico na porta."""
    return Valor(_adiciona(_b.ultrasonic_cm(_sensor(porta))), 4)


def tocado(porta: PortaSensor) -> Valor:
    """Lê o sensor de toque: 1 = apertado, 0 = solto."""
    return Valor(_adiciona(_b.touch_state(_sensor(porta))), 2, byte=True)


def botao_apertado() -> Valor:
    """Número do botão da controladora que está apertado (0 = nenhum). Ainda não conferido no robô."""
    return Valor(_adiciona(_b.Blk(3001, 1, '2|1|0|0', ' ')), 3, byte=True)


def ler(nome: str) -> Valor:
    """Lê o número guardado numa variável do robô. Ex.: ler('contador')"""
    return Valor(_adiciona(_b.var_rn(nome)), 2)


def guardar(nome: str, valor: float | Valor):
    """Guarda um número ou valor numa variável do robô. Ex.: guardar('erro', erro)"""
    if isinstance(valor, Valor):
        return _adiciona(_b.var_wn(nome, src=valor.bloco, out=valor.saida))
    return _adiciona(_b.var_wn(nome, _const(valor)))


# ---------------------------------------------------------------- esperas por sensor

def esperar_botao():
    """Espera apertar e soltar um botão da controladora (bom para largar o robô). Ainda não conferido no robô."""
    with repetir_ate(lambda: botao_apertado() != 0):
        pass
    with repetir_ate(lambda: botao_apertado() == 0):
        pass


def _cmp(comparacao):
    try:
        return _b.CMP_SENSOR[comparacao]
    except KeyError:
        raise ValueError(f'comparação {comparacao!r} invalida: use "<", "<=", ">", ">=", "=" ou "!="') from None


def esperar_toque(porta: PortaSensor):
    """Espera o sensor de toque ser apertado."""
    return _adiciona(_b.wait_touch(_sensor(porta)))


def esperar_distancia(porta: PortaSensor, comparacao: Comparacao, cm: float):
    """Espera a distância ficar menor/maior que cm. Ex.: esperar_distancia(4, '<', 20)"""
    return _adiciona(_b.wait_dist(_sensor(porta), _cmp(comparacao), cm))


def esperar_luz(porta: PortaSensor, comparacao: Comparacao, valor: float):
    """Espera a luz refletida passar de um valor. Ex.: esperar_luz(1, '<', 30)"""
    return _adiciona(_b.wait_refl(_sensor(porta), _cmp(comparacao), valor))


def esperar_cor(porta: PortaSensor, cor: int):
    """Espera o sensor ver a cor. Ex.: esperar_cor(1, VERDE)"""
    return _adiciona(_b.wait_color(_sensor(porta), cor))


# ---------------------------------------------------------------- tela, som e luz

def _ascii(texto):
    import unicodedata
    t = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in t if ord(c) < 128)


LINHAS_DA_TELA = {1: 0, 2: 20, 3: 40}     # conferido no robo em 2026-10-13: abaixo de y=40 o texto nao aparece


def mostrar(texto: str | float | Valor, linha: Linha = 1, x: int = 0, limpar: bool | None = None, y: int | None = None):
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


_NOTAS = {'do': 0, 'do#': 1, 're': 2, 're#': 3, 'mi': 4, 'fa': 5, 'fa#': 6, 'sol': 7, 'sol#': 8,
          'la': 9, 'la#': 10, 'si': 11}
_SEM_ACENTO = str.maketrans('óéíáú', 'oeiau')
_FREQ_MIN = 300                 # a IDE só aceita de 300 a 10000 Hz


def _frequencia(nota):
    """'la' -> 880 (oitava 5 se não disser), 'la4' -> 440, 'do#5' -> 554, 'ré' -> 587."""
    texto = str(nota).strip().lower().translate(_SEM_ACENTO)
    nome = texto.rstrip('0123456789')
    oitava = int(texto[len(nome):] or 5)
    if nome not in _NOTAS:
        raise ValueError(f'não conheço a nota {nota!r}: use do, re, mi, fa, sol, la, si '
                         f'(com # para sustenido e o número da oitava, ex.: "do#5")')
    freq = round(440 * 2 ** ((_NOTAS[nome] - 9) / 12 + oitava - 4))
    if freq < _FREQ_MIN:
        raise ValueError(f'a nota {nota!r} é grave demais para o robô ({freq} Hz): use uma oitava acima, '
                         f'ex.: "{nome}{oitava + 1}"')
    return freq


_X_DO_VALOR = 70              # um nome de até 6 letras cabe antes disso (8 letras já encostavam em x=80)


def painel(**valores: float | Valor):
    """Mostra até 3 valores na tela do robô, um por linha, com o nome na frente. Bom para ver o PID andando:
    painel(erro=ler('erro'), vel=ler('vel'), s1=luz_refletida(1))
    A controladora não manda as leituras para o computador, então a tela dela é o jeito de ver os números.
    Num laço muito rápido, a tela deixa o laço um pouco mais lento."""
    if not 1 <= len(valores) <= 3:
        raise ValueError('painel(...) mostra de 1 a 3 valores, um por linha, ex.: painel(erro=ler("erro"))')
    for linha, (nome, valor) in enumerate(valores.items(), 1):
        mostrar(f'{nome[:5]}:', linha=linha)
        mostrar(valor if isinstance(valor, Valor) else str(valor), linha=linha, x=_X_DO_VALOR, limpar=False)


def tocar(frequencia: float | str = 440, segundos: float = 1, volume: int = 100):
    """Toca um som e espera ele acabar. Ex.: tocar(440, 0.5) ou, pelo nome da nota, tocar('la', 0.5).
    Notas: do re mi fa sol la si (sustenido: 'do#'), na oitava 5 se não disser outra ('la4' = 440 Hz)."""
    if isinstance(frequencia, str):
        frequencia = _frequencia(frequencia)
    return _adiciona(_b.sound_tone(frequencia, segundos, volume))


def melodia(notas: str, tempo: float = 0.3, volume: int = 100):
    """Toca uma sequência de notas separadas por espaço. Cada nota dura tempo segundos;
    'nota:segundos' muda a duração de uma nota e '-' é uma pausa. Ex.: melodia('do re mi fa sol:0.6')"""
    for parte in str(notas).split():
        nota, _, duracao = parte.partition(':')
        segundos = float(duracao) if duracao else tempo
        if nota == '-':
            esperar(segundos)
        else:
            tocar(nota, segundos, volume)


def bip():
    """Um bip curto."""
    return tocar(880, 0.2)


_CORES_LUZ = {'azul': 0, 'roxo': 1, 'vermelho': 2}      # conferido no robo em 2026-10-13


def luz(cor: CorDaLuz = 'azul', piscar: bool = False):
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


def repetir(vezes: int):
    """Repete vezes vezes o que estiver dentro do with."""
    blk = _adiciona(_b.loop_count(vezes))
    return _Bloco(blk, blk.b1)


def repetir_ate(condicao: Callable[[], Condicao]):
    """Repete até a condição acontecer. A condição vai num lambda para ser medida a cada volta:
    with repetir_ate(lambda: distancia(4) < 20): ..."""
    if not callable(condicao):
        raise TypeError('use repetir_ate(lambda: ...), ex.: repetir_ate(lambda: distancia(4) < 20)')
    blk = _adiciona(_b.Blk(2003, 35, _b.LOOP_PARAMS, '', label='01'))
    return _Bloco(blk, blk.b1, condicao_no_fim=condicao)


def repetir_ate_luz(porta: PortaSensor, comparacao: Comparacao, valor: float):
    """Repete até a luz refletida passar de um valor. Ex.: repetir_ate_luz(1, '<', 30)"""
    blk = _adiciona(_b.loop_refl(_sensor(porta), _cmp(comparacao), valor))
    return _Bloco(blk, blk.b1)


def repetir_ate_cor(porta: PortaSensor, cor: int):
    """Repete até o sensor ver a cor."""
    blk = _adiciona(_b.loop_color(_sensor(porta), cor))
    return _Bloco(blk, blk.b1)


class _Paralelo(_Bloco):
    """O with ao_mesmo_tempo(): só aceita "with tarefa():" dentro."""
    def __enter__(self):
        super().__enter__()
        _pilha[-1].paralelo = self.bloco
        return self

    def __exit__(self, tipo_erro, *erro):
        if tipo_erro is None:
            if self.ramo:
                raise SyntaxError('dentro do "with ao_mesmo_tempo():" ponha cada parte num "with tarefa():"')
            if len(self.bloco.ramos) < 2:
                raise SyntaxError('"with ao_mesmo_tempo():" precisa de pelo menos duas "with tarefa():"')
        return super().__exit__(tipo_erro, *erro)


def ao_mesmo_tempo():
    """Faz várias partes do programa ao mesmo tempo, cada uma num "with tarefa():". Ex.:
        with ao_mesmo_tempo():
            with tarefa():
                andar_cm(30)
            with tarefa():
                melodia('do re mi')
    Continua depois que todas as tarefas acabarem. Ainda não conferido no robô (funciona no simulador)."""
    blk = _adiciona(_b.Blk(9001, 1, '', ' '))
    blk.ramos = []
    return _Paralelo(blk, [])


def tarefa():
    """Uma parte de um "with ao_mesmo_tempo():"."""
    paralelo = getattr(_pilha[-1], 'paralelo', None)
    if paralelo is None:
        raise SyntaxError('"with tarefa():" só funciona logo dentro de um "with ao_mesmo_tempo():"')
    ramo = []
    paralelo.ramos.append(ramo)
    return _Bloco(paralelo, ramo)


def _se(blk):
    return _Bloco(_adiciona(blk), blk.b1, abre_senao=True)


def se(condicao: Condicao):
    """Faz o que estiver dentro se a comparação for verdadeira. Ex.: with se(distancia(4) < 20):"""
    if not isinstance(condicao, Condicao):
        raise TypeError('se(...) precisa de uma comparação, ex.: se(distancia(4) < 20)')
    return _se(_b.switch_logic(condicao.bloco, condicao.saida))


def se_ver_cor(porta: PortaSensor, cor: int):
    """Faz o que estiver dentro se o sensor da porta ver a cor (ou uma das cores: PRETO + VERDE)."""
    return _se(_b.switch_color(_sensor(porta), cor))


def se_tocado(porta: PortaSensor):
    """Faz o que estiver dentro se o sensor de toque estiver apertado."""
    return _se(_b.switch_touch(_sensor(porta)))


def se_distancia(porta: PortaSensor, comparacao: Comparacao, cm: float):
    """Ex.: with se_distancia(4, '<', 20):"""
    return _se(_b.switch_dist(_sensor(porta), _cmp(comparacao), cm))


def se_luz(porta: PortaSensor, comparacao: Comparacao, valor: float):
    """Ex.: with se_luz(1, '<', 30):"""
    return _se(_b.switch_refl(_sensor(porta), _cmp(comparacao), valor))


def senao():
    """O que fazer quando a condição do "with se_..." logo acima não acontece."""
    sw = _pilha[-1].ultimo_switch
    if sw is None:
        raise SyntaxError('"with senao()" precisa vir logo depois de um "with se_..."')
    return _Bloco(sw, sw.b2)


# ---------------------------------------------------------------- if e while do Python
# enviar.py troca cada if/while do programa do aluno por estas peças: quando a condição é do robô
# (sensor, variável do robô), elas montam os blocos se/senão/repetir; quando é do Python, o if/while
# funciona como sempre.

_INVERSO = {'1': '2', '2': '1', '3': '6', '6': '3', '4': '5', '5': '4'}     # modos do Comparar: = != > >= < <=


def _nao(cond):
    """A comparação ao contrário (< vira >=, = vira !=). Se ela acabou de ser feita, só inverte o bloco;
    senão faz um bloco novo, para não mudar uma comparação guardada que o programa ainda usa."""
    velho = cond.bloco
    if _pilha[-1].blocos and _pilha[-1].blocos[-1] is velho:
        velho.mode = _INVERSO[velho.mode]
        return cond
    return Condicao(_adiciona(_b.Blk(velho.t, _INVERSO[velho.mode], velho.params, velho.port, velho.wires)))


def _como_condicao(valor, negar=False):
    """A comparação do robô que decide o if/while, ou None quando a condição é do Python."""
    if isinstance(valor, Valor):
        valor = (valor + 0 if valor.byte else valor) != 0      # "if tocado(4):" = "if tocado(4) != 0:"
    if isinstance(valor, Condicao):
        return _nao(valor) if negar else valor
    return None


class _Decisao:
    """Um if do aluno: se(...)/senao() quando a condição é do robô, if comum quando é do Python."""
    def __init__(self, valor, negar=False):
        self.cond = _como_condicao(valor, negar)
        self.python = None if self.cond is not None else (not valor if negar else bool(valor))
        self.trecho = None

    def _entra(self, bloco):
        self.trecho = bloco
        bloco.__enter__()
        return True

    def sim(self):
        return self._entra(se(self.cond)) if self.cond is not None else self.python

    def nao(self):
        return self._entra(senao()) if self.cond is not None else not self.python

    def fim(self):
        if self.trecho is not None:
            self.trecho.__exit__(None, None, None)
            self.trecho = None


class _Repeticao:
    """Um while do aluno. Com condição do robô vira se(cond) + repetir_ate(cond ao contrário)
    (o robô confere no fim de cada volta); com condição do Python, while comum."""
    def __init__(self, condicao, negar=False, tem_break=False):
        self.condicao, self.negar, self.tem_break = condicao, negar, tem_break
        self.robo = None            # None antes da 1a volta; depois True ou False
        self.trechos = []

    def volta(self):
        if self.robo is None:
            cond = _como_condicao(self.condicao(), self.negar)
            self.robo = cond is not None
            if not self.robo:
                return self._python()
            if self.tem_break:
                raise SyntaxError('"break" e "continue" ainda não funcionam num while com sensor: '
                                  'use a condição do próprio while para sair')
            for faz in (lambda: se(cond), lambda: repetir_ate(lambda: _como_condicao(self.condicao(), not self.negar))):
                bloco = faz()                   # um de cada vez: o repetir_ate fica dentro do se
                bloco.__enter__()
                self.trechos.append(bloco)
            return True
        return False if self.robo else self._python()

    def _python(self):
        valor = self.condicao()
        return not valor if self.negar else bool(valor)

    def fim(self):
        while self.trechos:
            self.trechos.pop().__exit__(None, None, None)


_contador_logica = [0]


def _variavel_logica():
    _contador_logica[0] += 1
    return f'_logica{_contador_logica[0]}'


def _e(*partes):
    """"a and b and ..." do aluno. Partes do Python funcionam como sempre; com partes do robô, o resultado
    vai para uma variável do robô (1 = verdadeiro) montada com um se dentro do outro."""
    valor = True
    for i, parte in enumerate(partes):
        valor = parte()
        cond = _como_condicao(valor)
        if cond is None:
            if not valor:
                return valor
            continue
        nome = _variavel_logica()
        guardar(nome, 0)

        def resto(j, cond):
            with se(cond):
                for k in range(j, len(partes)):
                    v = partes[k]()
                    c = _como_condicao(v)
                    if c is None:
                        if not v:
                            return
                        continue
                    return resto(k + 1, c)
                guardar(nome, 1)
        resto(i + 1, cond)
        return ler(nome) == 1
    return valor


def _ou(*partes):
    """"a or b or ..." do aluno, do mesmo jeito que o _e."""
    valor = False
    for i, parte in enumerate(partes):
        valor = parte()
        cond = _como_condicao(valor)
        if cond is None:
            if valor:
                return valor
            continue
        nome = _variavel_logica()
        guardar(nome, 0)

        def resto(j, cond):
            with se(cond):
                guardar(nome, 1)
            with senao():
                for k in range(j, len(partes)):
                    v = partes[k]()
                    c = _como_condicao(v)
                    if c is None:
                        if v:
                            guardar(nome, 1)
                            return
                        continue
                    return resto(k + 1, c)
        resto(i + 1, cond)
        return ler(nome) == 1
    return valor


def _nao_geral(valor):
    """"not x" do aluno: comparação do robô ao contrário, ou o not do Python."""
    cond = _como_condicao(valor, negar=True)
    return cond if cond is not None else not valor


def _vezes(n):
    """"for _ in range(n)" do aluno quando a variável do for não é usada: vira o repetir(n) do robô,
    para o programa não ficar n vezes maior. Se o corpo não tiver comandos do robô, repete no Python."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        yield from range(n)
        return
    bloco = repetir(n)
    bloco.__enter__()
    try:
        yield None
    except BaseException:
        bloco.__exit__(None, None, None)
        raise
    bloco.__exit__(None, None, None)
    if not bloco.bloco.b1:                          # só Python dentro: desfaz o bloco e repete do jeito normal
        _pilha[-1].blocos.remove(bloco.bloco)
        for _ in range(n - 1):
            yield None


# ---------------------------------------------------------------- ajustar um número pelos botões
# (os números dos botões ficam lá em cima, junto com a leitura do calibracao.py)


class _Ajustando:
    def __init__(self, nome, inicial, passo):
        self.nome, self.inicial, self.passo = nome, inicial, passo

    def __enter__(self):
        nome, passo = self.nome, self.passo
        guardar(nome, self.inicial)
        self.paralelo = ao_mesmo_tempo()
        self.paralelo.__enter__()
        with tarefa():                                      # os botões mudam o número, sem parar
            with para_sempre():
                for botao, conta in ((BOTAO_CIMA, passo), (BOTAO_BAIXO, -passo)):
                    with se(botao_apertado() == botao):
                        guardar(nome, ler(nome) + conta)
                        with repetir_ate(lambda: botao_apertado() == 0):     # espera soltar
                            pass
                mostrar(f'{nome[:5]}:', linha=3)
                mostrar(ler(nome), linha=3, x=_X_DO_VALOR, limpar=False)
                esperar(0.1)
        self.corpo = tarefa()
        self.corpo.__enter__()
        return self

    def __exit__(self, tipo_erro, *erro):
        self.corpo.__exit__(tipo_erro, *erro)
        return self.paralelo.__exit__(tipo_erro, *erro)


def ajustando(nome: str, inicial: float, passo: float):
    """Deixa ajustar um número com os botões da controladora enquanto o programa roda, sem reenviar:
    o botão de cima soma passo, o de baixo tira, e o valor aparece na linha 3 da tela. Ex.:
        with ajustando('kp', 0.4, 0.05):
            while True:
                ... motores(20 + erro * ler('kp'), 20 - erro * ler('kp'))
    Use ler('kp') no programa. Ainda não conferido no robô (os números dos botões podem ser outros)."""
    return _Ajustando(nome, inicial, passo)


class _Ajustes:
    def __init__(self, valores):
        if not 1 <= len(valores) <= 9:
            raise ValueError('ajustes(...) aceita de 1 a 9 números, ex.: ajustes(kp=(0.4, 0.05), vel=(25, 5))')
        self.valores = []
        for nome, par in valores.items():
            if not (isinstance(par, (tuple, list)) and len(par) == 2):
                raise ValueError(f'em ajustes(...), {nome} precisa de (valor inicial, passo), ex.: {nome}=(0.4, 0.05)')
            self.valores.append((nome, par[0], par[1]))

    def __enter__(self):
        n = len(self.valores)
        for nome, inicial, _ in self.valores:
            guardar(nome, inicial)
        guardar('ajsel', 0)                                 # qual número os botões de cima e de baixo mudam
        self.paralelo = ao_mesmo_tempo()
        self.paralelo.__enter__()
        with tarefa():
            with para_sempre():
                for botao, conta in ((BOTAO_DIREITA, 1), (BOTAO_ESQUERDA, n - 1)):     # n - 1: anda para trás
                    with se(botao_apertado() == botao):
                        guardar('ajsel', ler('ajsel') + conta)
                        with se(ler('ajsel') >= n):
                            guardar('ajsel', ler('ajsel') - n)
                        with repetir_ate(lambda: botao_apertado() == 0):
                            pass
                for i, (nome, _, passo) in enumerate(self.valores):
                    with se(ler('ajsel') == i):
                        for botao, conta in ((BOTAO_CIMA, passo), (BOTAO_BAIXO, -passo)):
                            with se(botao_apertado() == botao):
                                guardar(nome, ler(nome) + conta)
                                with repetir_ate(lambda: botao_apertado() == 0):
                                    pass
                        mostrar(f'{nome[:5]}:', linha=3)
                        mostrar(ler(nome), linha=3, x=_X_DO_VALOR, limpar=False)
                esperar(0.1)
        self.corpo = tarefa()
        self.corpo.__enter__()
        return self

    def __exit__(self, tipo_erro, *erro):
        self.corpo.__exit__(tipo_erro, *erro)
        return self.paralelo.__exit__(tipo_erro, *erro)


def ajustes(**valores: tuple):
    """Como o ajustando, mas para vários números: os botões da esquerda e da direita escolhem qual número
    mudar, e os de cima e de baixo mudam o escolhido. A linha 3 da tela mostra o nome e o valor. Ex.:
        with ajustes(kp=(0.4, 0.05), vel=(25, 5)):
            while True:
                erro = luz_refletida(1) - luz_refletida(2)
                motores(ler('vel') + erro * ler('kp'), ler('vel') - erro * ler('kp'))
    Bom para acertar o seguidor na arena entre uma rodada e outra, sem cabo. Os valores voltam ao inicial
    quando o programa recomeça: anote o que funcionou e passe para o programa.
    Ainda não conferido no robô (os números dos botões podem ser outros: veja a tarefa Teste geral)."""
    return _Ajustes(valores)


# ---------------------------------------------------------------- velocidade do laço

class _MedirLaco:
    def __init__(self, segundos):
        if not 1 <= segundos <= 60:
            raise ValueError('medir_laco(segundos) mede de 1 a 60 segundos, ex.: medir_laco(5)')
        self.segundos = segundos

    def __enter__(self):
        guardar('mvoltas', 0)
        guardar('mfim', 0)
        self.paralelo = ao_mesmo_tempo()
        self.paralelo.__enter__()
        with tarefa():                                      # o relógio: avisa o laço quando o tempo acaba
            esperar(self.segundos)
            guardar('mfim', 1)
        self.tarefa = tarefa()
        self.tarefa.__enter__()
        self.laco = repetir_ate(lambda: ler('mfim') == 1)
        self.laco.__enter__()
        return self

    def __exit__(self, tipo_erro, *erro):
        if tipo_erro is None:
            guardar('mvoltas', ler('mvoltas') + 1)
        self.laco.__exit__(tipo_erro, *erro)
        self.tarefa.__exit__(tipo_erro, *erro)
        resultado = self.paralelo.__exit__(tipo_erro, *erro)
        if tipo_erro is None:
            parar()
            mostrar('Voltas/s:')
            mostrar(ler('mvoltas') / self.segundos, linha=2)
            esperar(20)
        return resultado


def medir_laco(segundos: float = 5):
    """Repete o que estiver dentro durante alguns segundos e depois mostra na tela quantas voltas por segundo
    deu. Ponha dentro o corpo do seu laço (sem o while True) para saber se ele está rápido:
        with medir_laco():
            erro = luz_refletida(1) - luz_refletida(2)
            motores(25 + erro * 0.4, 25 - erro * 0.4)
    Mais voltas por segundo = o robô corrige mais vezes e pode andar mais rápido sem perder a linha.
    Compare: tire ou ponha uma leitura, um mostrar(...), um painel(...), e veja quanto cada coisa custa.
    A conta das voltas também gasta um pouquinho: o laço de verdade é um pouco mais rápido que o número.
    Usa o ao_mesmo_tempo (ainda não conferido no robô; funciona no simulador)."""
    return _MedirLaco(segundos)


# ---------------------------------------------------------------- calibração na largada

def calibrar_na_largada(*portas: PortaSensor, giro: float = 0.5, potencia: float = 20):
    """Mede o preto e o branco na própria pista, antes de sair: o robô gira devagar para um lado e para o
    outro sobre a linha, guarda a menor e a maior luz de cada sensor e calcula o limite (o meio entre as
    duas). A luz do lugar da prova nunca é a do laboratório: assim o robô se acerta sozinho. Ex.:
        calibrar_na_largada(1, 2)          # robô parado em cima da linha, sensores dos dois lados dela
        while True:
            if luz_refletida(1) < limite_medido(1): ...
    giro: quanto tempo gira para cada lado (aumente se os sensores não passarem pela linha).
    Se um sensor não viu diferença (não passou pela linha), fica o limite do calibracao.py.
    No fim mostra os limites na tela. Guarda nas variáveis min1, max1, lim1 (e min2...) do robô."""
    portas = portas or (1, 2)
    for p in portas:
        _sensor(p)
        guardar(f'min{p}', 100)
        guardar(f'max{p}', 0)
    voltas = max(1, round(giro / 0.02))
    for esq, dir_, vezes in ((-potencia, potencia, 1), (potencia, -potencia, 2), (-potencia, potencia, 1)):
        motores(esq, dir_)
        with repetir(voltas * vezes):
            for p in portas:
                luz = luz_refletida(p)
                with se(luz < ler(f'min{p}')):
                    guardar(f'min{p}', luz)
                with se(luz > ler(f'max{p}')):
                    guardar(f'max{p}', luz)
            esperar(0.02)
    parar()
    for p in portas:
        guardar(f'lim{p}', (ler(f'min{p}') + ler(f'max{p}')) / 2)
        if p in _PRETO and p in _BRANCO:
            with se(ler(f'max{p}') - ler(f'min{p}') < 20):         # não passou pela linha
                guardar(f'lim{p}', limite(p))
    painel(**{f'lim{p}': ler(f'lim{p}') for p in portas[:3]})
    bip()


def limite_medido(porta: PortaSensor) -> Valor:
    """O limite entre o preto e o branco que o calibrar_na_largada mediu para o sensor (variável lim1...)."""
    _sensor(porta)
    return ler(f'lim{porta}')
