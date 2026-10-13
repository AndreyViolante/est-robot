"""Compilador de programas EST (blocos.py) para o bytecode do robo, sem a IDE.

Reproduz o que a IDE EST gera, conferido byte a byte contra capturas do order_content.txt
(pasta gabaritos/). Estrutura do programa gerado:

  tabela de constantes   8 x (02 reg valor): 0..5 em float, 1 e 2 inteiros (ids 100..107)
  entradas com fio       02 reg FFFFFFFF, para cada parametro alimentado por fio
  thread principal       blocos da cadeia principal, termina em 24
  threads                corpo de cada loop e ramo de switch, cada uma termina em 21 tid 00

Registradores e codigo seguem a mesma ordem: cadeia principal inteira, depois cada thread
na ordem em que foi numerada.
"""
import struct

CONSTANTES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 1, 2]
C1 = 101                       # id da constante 1.0
FIO_VAZIO = b'\xff\xff\xff\xff'

# tipos de parametro: como inicializar o registrador
PORTA, FLOAT, FREIO, MASCARA, ZERO_F, ZERO_B, SAIDA = 'porta', 'float', 'freio', 'mascara', 'zero_f', 'zero_b', 'saida'
TAMANHO = {PORTA: 1, FLOAT: 4, FREIO: 1, MASCARA: 2, ZERO_F: 4, ZERO_B: 1}


class Modelo:
    """Como um bloco (tipo, modo) vira registradores e instrucoes.

    hw:       (id_hardware, tipo, tamanho_se_saida) na ordem de alocacao
    inicio:   ids inicializados antes dos passos (ordem da IDE)
    passos:   (opcode, operandos); operando = ('r', id) | ('c', id_constante) | ('b', byte)
    extra:    bytes reservados depois dos registradores (blocos de fluxo usam 3)
    """
    def __init__(self, hw, inicio, passos, extra=0, laco=None):
        self.hw, self.inicio, self.passos, self.extra = hw, inicio, passos, extra
        self.laco = laco       # loops: (ids iniciados dentro de cada volta, id_contador, id_condicao, id_flag)


def _tanque(modo, dados, ids_valor, tam):
    hw = [(0, PORTA, 0)] + [(i, FREIO if i == 3 else FLOAT, 0) for i in ids_valor]
    return Modelo(hw, [i for i, _, _ in hw],
                  [(0x31, [('b', 0), ('r', 0), ('b', 0x83), ('b', modo), ('b', tam), ('r', dados)])])


def _conta(op):
    return Modelo([(2, FLOAT, 0), (3, FLOAT, 0), (1, SAIDA, 4)], [2, 3],
                  [(op, [('r', 1), ('r', 2), ('r', 3)])])


MODELOS = {
    ('1004', '1'): _tanque(1, 3, [3], 1),
    ('1004', '2'): _tanque(2, 1, [1, 2], 8),
    ('1004', '3'): _tanque(3, 1, [1, 2, 4, 3], 13),
    ('1004', '4'): _tanque(4, 1, [1, 2, 5, 3], 13),
    ('1004', '5'): _tanque(5, 1, [1, 2, 6, 3], 13),
    ('1002', '4'): Modelo([(0, PORTA, 0), (1, FLOAT, 0), (4, FLOAT, 0), (2, FREIO, 0)], [0, 2, 4, 1],
                          [(0x31, [('b', 0), ('r', 0), ('b', 0x81), ('b', 4), ('b', 9), ('r', 1)])]),
    ('3002', '1'): Modelo([(0, PORTA, 0), (5, SAIDA, 4)], [0],
                          [(0x30, [('b', 0), ('r', 0), ('b', 1), ('b', 1), ('b', 4), ('r', 5)])]),
    ('3002', '2'): Modelo([(0, PORTA, 0), (7, SAIDA, 4)], [0],
                          [(0x30, [('b', 0), ('r', 0), ('b', 1), ('b', 2), ('b', 4), ('r', 7)])]),
    ('4005', '1'): _conta(0x09),
    ('4005', '2'): _conta(0x0A),
    ('4005', '3'): _conta(0x0B),
    ('4005', '4'): _conta(0x0C),     # divisao: ainda sem captura de gabarito
    ('2002', '67'): Modelo([(18, FLOAT, 0), (42, SAIDA, 4), (43, SAIDA, 1)], [18],
                           [(0x23, [('r', 18)]), (0x01, [('r', 43), ('b', 1)])], extra=3),
    ('2004', '4'): Modelo([(0, PORTA, 0), (3, MASCARA, 0), (13, SAIDA, 4), (14, SAIDA, 1)], [0, 3],
                          [(0x30, [('b', 0), ('r', 0), ('b', 1), ('b', 1), ('b', 4), ('r', 13)]),
                           (0x11, [('r', 14), ('r', 13), ('r', 3)])], extra=3),
    ('2003', '33'): Modelo([(15, ZERO_F, 0), (17, SAIDA, 4), (18, ZERO_B, 0)], [15, 18],
                           [(0x09, [('r', 15), ('r', 15), ('c', C1)]), (0x01, [('r', 17), ('b', 0)])],
                           extra=3, laco=([], 15, 17, 18)),
    ('2003', '34'): Modelo([(12, FLOAT, 0), (16, SAIDA, 4), (17, SAIDA, 4), (15, ZERO_F, 0), (18, ZERO_B, 0)],
                           [15, 18],
                           [(0x09, [('r', 15), ('r', 15), ('c', C1)]),
                            (0x10, [('b', 4), ('r', 17), ('r', 15), ('r', 12)])],
                           extra=3, laco=([12], 15, 17, 18)),
}


def porta_byte(porta):
    """Port_convertbyte da IDE: '1'..'4' -> 1..4, 'A'..'D' -> 5..8, 'X+Y' -> f(X)<<4 + f(Y)<<6."""
    p = str(porta).strip().upper()
    if len(p) == 3 and p[1] == '+':
        return ((ord(p[0]) - 65) << 4) + ((ord(p[2]) - 65) << 6)
    if p in ('A', 'B', 'C', 'D'):
        return ord(p) - 60
    return int(p)


def mascara_cores(campo):
    return sum(1 << int(d) for d in str(campo))


class _Programa:
    def __init__(self, cadeia, compat_ide_fios):
        self.reg = {}          # id(bloco) -> {id_hw: endereco}
        self.var = {}          # nome da variavel -> endereco
        self.tids = {}         # id(bloco) -> [tid por ramo]
        self.segmentos = []    # (tid, cadeia) na ordem da IDE; tid 0 = principal
        self.fios_de = {}      # id(origem) -> [(bloco_destino, entrada, saida)]
        self.ligados = set()   # (id(bloco), entrada) alimentadas por fio
        self._numerar(cadeia)
        self._fios(compat_ide_fios)
        self._alocar()

    def _numerar(self, cadeia):
        fila, proximo = [(0, cadeia)], 1
        while fila:
            tid, ch = fila.pop(0)
            self.segmentos.append((tid, ch))
            for b in ch:
                ramos = [b.b1, b.b2] if b.t == '2004' else [b.b1] if b.t == '2003' else []
                if ramos:
                    self.tids[id(b)] = list(range(proximo, proximo + len(ramos)))
                    fila += [(proximo + i, r) for i, r in enumerate(ramos)]
                    proximo += len(ramos)

    def blocos(self):
        return [b for _, ch in self.segmentos for b in ch if b.t != '2001']

    def _fios(self, compat_ide_fios):
        for b in self.blocos():
            for entrada, origem, saida in b.wires:
                self.fios_de.setdefault(id(origem), []).append((b, entrada, saida))
        if compat_ide_fios:
            # imita a IDE com um .est que grava um <line_info> por fio: so o ultimo de cada saida vale
            self.fios_de = {k: v[-1:] for k, v in self.fios_de.items()}
        for lista in self.fios_de.values():
            for b, entrada, _ in lista:
                self.ligados.add((id(b), entrada))

    def _alocar(self):
        end = 0
        for b in self.blocos():
            m = modelo(b)
            if b.t == '4001':
                if b.port not in self.var:
                    self.var[b.port] = end
                    end += 4
            regs = {}
            for hw, tipo, tam_saida in m.hw:
                regs[hw] = end
                end += tam_saida if tipo == SAIDA else TAMANHO[tipo]
            self.reg[id(b)] = regs
            end += m.extra
        self.base_const = end

    def const(self, cid):
        return self.base_const + 4 * (cid - 100)


def modelo(b):
    if b.t == '4001' and b.mode == '5':
        return Modelo([(7, FLOAT, 0)], [7], [])
    try:
        return MODELOS[(b.t, b.mode)]
    except KeyError:
        raise NotImplementedError(f'bloco {b.t} modo {b.mode} ainda nao suportado pelo compilador') from None


class _Montador:
    """Junta instrucoes com rotulos e resolve os enderecos (pc) no fim."""
    def __init__(self):
        self.itens, self.pos, self.rotulos = [], 0, {}

    def emite(self, dados):
        self.itens.append(dados); self.pos += len(dados)

    def pc(self, rotulo):
        self.itens.append(rotulo); self.pos += 4

    def rotulo(self, nome):
        self.rotulos[nome] = self.pos

    def bytes(self):
        return b''.join(struct.pack('>I', self.rotulos[i]) if isinstance(i, str) else i for i in self.itens)


def _r(end): return struct.pack('>I', end)


def compilar(cadeia, compat_ide_fios=False):
    """Compila uma lista de blocos (comecando por start()) para bytes prontos para o robo."""
    p = _Programa(cadeia, compat_ide_fios)
    a = _Montador()

    for i, v in enumerate(CONSTANTES):
        valor = struct.pack('<f', v) if isinstance(v, float) else struct.pack('<I', v)
        a.emite(b'\x02' + _r(p.const(100 + i)) + valor)
    vazios = sorted(p.reg[id(b)][entrada] for b in p.blocos() for entrada in
                    [e for e in p.reg[id(b)] if (id(b), e) in p.ligados])
    for end in vazios:
        a.emite(b'\x02' + _r(end) + FIO_VAZIO)

    def init(b, hw, tipo):
        end = p.reg[id(b)][hw]
        if tipo == PORTA:
            a.emite(b'\x01' + _r(end) + bytes([porta_byte(b.port)]))
        elif tipo == FLOAT:
            a.emite(b'\x02' + _r(end) + struct.pack('<f', float(b.param(hw))))
        elif tipo == FREIO:
            a.emite(b'\x01' + _r(end) + bytes([1 - int(b.param(hw))]))
        elif tipo == MASCARA:
            a.emite(b'\x2d' + _r(end) + struct.pack('<H', mascara_cores(b.param(hw))))
        elif tipo == ZERO_F:
            a.emite(b'\x02' + _r(end) + struct.pack('<f', 0.0))
        elif tipo == ZERO_B:
            a.emite(b'\x01' + _r(end) + b'\x00')

    def inicializa(b, m, ids):
        tipos = {hw: tipo for hw, tipo, _ in m.hw}
        for hw in ids:
            if (id(b), hw) not in p.ligados:
                init(b, hw, tipos[hw])

    def passos(b, m):
        regs = p.reg[id(b)]
        for op, operandos in m.passos:
            out = bytes([op])
            for tipo, v in operandos:
                out += bytes([v]) if tipo == 'b' else _r(regs[v] if tipo == 'r' else p.const(v))
            a.emite(out)
        if b.t == '4001':
            a.emite(b'\x04' + _r(p.var[b.port]) + _r(regs[7]))

    def fios(b):
        for destino, entrada, saida in p.fios_de.get(id(b), []):
            a.emite(b'\x04' + _r(p.reg[id(destino)][entrada]) + _r(p.reg[id(b)][saida]))

    def bloco(b, n):
        m = modelo(b)
        a.emite(b'\x48')
        if b.t == '2003':
            dentro, contador, condicao, flag = m.laco
            inicializa(b, m, m.inicio)
            tid = p.tids[id(b)][0]
            regs = p.reg[id(b)]
            a.rotulo(f'laco{n}')
            a.emite(b'\x1d'); a.pc(f't{tid}'); a.emite(bytes([tid, 0]))
            a.emite(bytes([0x20, tid, 0]))
            inicializa(b, m, dentro)
            passos(b, m)
            a.emite(b'\x1a'); a.pc(f'fim{n}'); a.emite(_r(regs[flag]))
            a.emite(b'\x1b'); a.pc(f'laco{n}'); a.emite(_r(regs[condicao]))
            a.emite(b'\x0a' + _r(regs[contador]) + _r(regs[contador]) + _r(p.const(C1)))
            a.rotulo(f'fim{n}')
        elif b.t == '2004':
            inicializa(b, m, m.inicio)
            passos(b, m)
            sim, nao = p.tids[id(b)]
            res = _r(p.reg[id(b)][14])
            a.emite(b'\x1f'); a.pc(f't{nao}'); a.emite(res + bytes([nao, 0]))
            a.emite(b'\x1e'); a.pc(f't{sim}'); a.emite(res + bytes([sim, 0]))
            a.emite(bytes([0x20, sim, 0, 0x20, nao, 0]))
        else:
            inicializa(b, m, m.inicio)
            passos(b, m)
        fios(b)

    n = 0
    for tid, ch in p.segmentos:
        a.rotulo(f't{tid}')
        for b in ch:
            if b.t != '2001':
                bloco(b, n); n += 1
        a.emite(b'\x24' if tid == 0 else bytes([0x21, tid, 0]))
    return a.bytes()
