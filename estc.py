"""Compilador de programas EST (blocos.py) para o bytecode do robo, sem a IDE.

Reproduz o que a IDE EST gera, conferido byte a byte contra capturas do order_content.txt
(pasta gabaritos/). Estrutura do programa gerado:

  tabela de constantes   8 x (02 reg valor): 0..5 em float, 1 e 2 inteiros (ids 100..107)
  entradas com fio       02 reg FFFFFFFF por parametro numerico ligado; 2F txt 03 0D0D00 por texto ligado
  thread principal       blocos da cadeia principal, termina em 24
  threads                corpo de cada loop e ramo de switch, cada uma termina em 21 tid 00

Registradores e codigo seguem a mesma ordem: cadeia principal inteira, depois cada thread
na ordem em que foi numerada.
"""
import struct

CONSTANTES = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 1, 2]
C1 = 101                       # id da constante 1.0
FIO_VAZIO = b'\xff\xff\xff\xff'
TEXTO_BASE, TEXTO_PASSO = 0xD7FF, 50       # area de textos: uma vaga de 50 bytes por parametro de texto
TEXTO_VAZIO = b'\x0d\x0d\x00'

# tipos de registrador: (tamanho, tipo do dado) e como inicializar
PORTA, FLOAT, BYTE, LOGICO, MASCARA, TEXTO, ZERO_F, ZERO_B = (
    'porta', 'float', 'byte', 'logico', 'mascara', 'texto', 'zero_f', 'zero_b')
SAIDA_F, SAIDA_B = 'saida_f', 'saida_b'
TAMANHO = {PORTA: 1, FLOAT: 4, BYTE: 1, LOGICO: 1, MASCARA: 2, TEXTO: 4, ZERO_F: 4, ZERO_B: 1}
DADO = {PORTA: 'b', FLOAT: 'f', BYTE: 'b', LOGICO: 'b', MASCARA: 'b', TEXTO: 't', ZERO_F: 'f', ZERO_B: 'b',
        SAIDA_F: 'f', SAIDA_B: 'b'}
# copia de um fio: (dado da saida, dado da entrada) -> opcode
COPIA = {('f', 'f'): 0x04, ('b', 'b'): 0x03, ('b', 'f'): 0x08, ('f', 'b'): 0x07}


class Modelo:
    """Como um bloco (tipo, modo) vira registradores e instrucoes.

    hw:      (id_hardware, tipo) ou (id_hardware, SAIDA_x, tamanho), na ordem de alocacao
    inicio:  ids inicializados antes dos passos, na ordem da IDE
    passos:  (opcode, operandos); operando = ('r', id) | ('c', id_constante) | ('b', byte)
             | ('p+1', id) byte = parametro + 1 | ('raw', bytes)
    extra:   bytes reservados depois dos registradores
    laco:    loops: (ids iniciados a cada volta, id_contador, id_condicao, id_flag)
    espera:  esperas por sensor: (passos repetidos ate a condicao, id_condicao, passos depois)
    """
    def __init__(self, hw, inicio, passos, extra=0, laco=None, espera=None):
        self.hw, self.inicio, self.passos, self.extra = hw, inicio, passos, extra
        self.laco, self.espera = laco, espera

    def tipo(self, hw_id):
        return next(h[1] for h in self.hw if h[0] == hw_id)


def _r(hw): return ('r', hw)
def _b(v): return ('b', v)


def _disp(op, tipo, modo, tam, dados):
    return (op, [_b(0), _r(0), _b(tipo), _b(modo), _b(tam), _r(dados)])


def _interno(tipo, modo, tam, dados):
    return (0x33, [_b(tipo), _b(modo), _b(tam), _r(dados)])


def _motor(tipo, modo, tam, dados, hw, inicio=None):
    return Modelo(hw, inicio or [h[0] for h in hw], [_disp(0x31, tipo, modo, tam, dados)])


def _conta(op):
    return Modelo([(2, FLOAT), (3, FLOAT), (1, SAIDA_F, 4)], [2, 3], [(op, [_r(1), _r(2), _r(3)])])


def _laco(hw, dentro, passos):
    return Modelo(hw, [15, 18], passos + [(0x09, [_r(15), _r(15), ('c', C1)])], extra=3,
                  laco=(dentro, 15, 17, 18))


_P, _F, _L = (0, PORTA), FLOAT, LOGICO
MODELOS = {
    # ---- motores (tipo 0x81 grande, 0x82 com direcao, 0x83 tanque) ----
    ('1002', '1'): _motor(0x81, 1, 1, 2, [_P, (2, _L)]),
    ('1002', '2'): _motor(0x81, 2, 4, 1, [_P, (1, _F)]),
    ('1002', '3'): _motor(0x81, 3, 9, 1, [_P, (1, _F), (3, _F), (2, _L)], [0, 2, 3, 1]),
    ('1002', '4'): _motor(0x81, 4, 9, 1, [_P, (1, _F), (4, _F), (2, _L)], [0, 2, 4, 1]),
    ('1002', '5'): _motor(0x81, 5, 9, 1, [_P, (1, _F), (5, _F), (2, _L)], [0, 2, 5, 1]),
    ('1003', '1'): _motor(0x82, 1, 1, 3, [_P, (3, _L)]),
    ('1003', '2'): _motor(0x82, 2, 8, 2, [_P, (2, _F), (1, _F)]),
    ('1003', '5'): _motor(0x82, 5, 13, 2, [_P, (2, _F), (1, _F), (6, _F), (3, _L)]),
    ('1004', '1'): _motor(0x83, 1, 1, 3, [_P, (3, _L)]),
    ('1004', '2'): _motor(0x83, 2, 8, 1, [_P, (1, _F), (2, _F)]),
    ('1004', '3'): _motor(0x83, 3, 13, 1, [_P, (1, _F), (2, _F), (4, _F), (3, _L)]),
    ('1004', '4'): _motor(0x83, 4, 13, 1, [_P, (1, _F), (2, _F), (5, _F), (3, _L)]),
    ('1004', '5'): _motor(0x83, 5, 13, 1, [_P, (1, _F), (2, _F), (6, _F), (3, _L)]),
    # ---- tela, som e luz (escrita interna 0x33: 1 tela, 2 som, 4 luz) ----
    ('1005', '1'): Modelo([(0, TEXTO), (18, SAIDA_B, 1), (1, _L), (6, BYTE), (7, BYTE), (16, _L), (17, BYTE)],
                          [0, 1, 6, 7, 16, 17], [_interno(1, 1, 10, 0)]),
    ('1006', '3'): Modelo([(3, _F), (4, _F), (5, _F), (6, _L)], [3, 4, 5, 6], [_interno(2, 1, 13, 3)]),
    ('1007', '1'): Modelo([], [], [(0x33, [_b(4), _b(0), _b(0), ('raw', FIO_VAZIO)])]),
    ('1007', '2'): Modelo([(1, BYTE), (2, _L)], [1, 2], [_interno(4, 1, 2, 1)]),
    # ---- sensores (leitura 0x30: 1 cor, 7 toque, 8 ultrassom) ----
    ('3002', '1'): Modelo([_P, (5, SAIDA_B, 2)], [0],
                          [_disp(0x30, 1, 1, 1, 5), (0x0D, [_b(0x15), _r(5), _r(5)])]),
    ('3002', '2'): Modelo([_P, (7, SAIDA_F, 4)], [0], [_disp(0x30, 1, 2, 4, 7)]),
    ('3008', '1'): Modelo([_P, (2, SAIDA_B, 1)], [0], [_disp(0x30, 7, 1, 1, 2)]),
    ('3009', '3'): Modelo([_P, (4, SAIDA_F, 4)], [0], [_disp(0x30, 8, 3, 4, 4)]),
    # ---- contas e comparacoes ----
    ('4005', '1'): _conta(0x09),
    ('4005', '2'): _conta(0x0A),
    ('4005', '3'): _conta(0x0B),
    ('4005', '4'): _conta(0x0C),
    **{('4007', str(m)): Modelo([(1, _F), (2, _F), (3, SAIDA_B, 1)], [1, 2],
                                [(0x10, [_b(m), _r(3), _r(1), _r(2)])]) for m in range(1, 7)},
    # ---- esperas ----
    ('2002', '67'): Modelo([(18, _F), (42, SAIDA_F, 4), (43, SAIDA_B, 1)], [18],
                           [(0x23, [_r(18)]), (0x01, [_r(43), _b(1)])], extra=3),
    ('2002', '3'): Modelo([_P, (4, SAIDA_B, 2), (5, MASCARA), (42, SAIDA_F, 4), (43, SAIDA_B, 1)], [0, 5], [],
                          extra=3, espera=([_disp(0x30, 1, 1, 2, 4), (0x11, [_r(43), _r(4), _r(5)])], 43,
                                           [(0x0D, [_b(0x15), _r(4), _r(4)])])),
    ('2002', '4'): Modelo([_P, (8, BYTE), (6, _F), (4, SAIDA_F, 2), (42, SAIDA_F, 4), (43, SAIDA_B, 1)],
                          [0, 8, 6], [], extra=3,
                          espera=([_disp(0x30, 1, 2, 4, 4), (0x2B, [_r(8), _r(43), _r(4), _r(6)])], 43,
                                  [(0x04, [_r(42), _r(4)])])),
    ('2002', '33'): Modelo([_P, (27, BYTE), (28, SAIDA_B, 1), (42, SAIDA_F, 4), (43, SAIDA_B, 1)], [0, 27], [],
                           extra=7, espera=([_disp(0x30, 7, 1, 1, 28),
                                             (0x29, [_b(1), _r(43), _r(28), _r(27)])], 43, [])),
    ('2002', '35'): Modelo([_P, (8, BYTE), (6, _F), (29, SAIDA_F, 4), (43, SAIDA_B, 1)], [0, 8, 6], [],
                           extra=3, espera=([_disp(0x30, 8, 3, 4, 29),
                                             (0x2B, [_r(8), _r(43), _r(29), _r(6)])], 43, [])),
    # ---- switch (o resultado fica no id 14) ----
    ('2004', '4'): Modelo([_P, (3, MASCARA), (13, SAIDA_F, 4), (14, SAIDA_B, 1)], [0, 3],
                          [_disp(0x30, 1, 1, 4, 13), (0x11, [_r(14), _r(13), _r(3)])], extra=3),
    ('2004', '5'): Modelo([_P, (4, _F), (5, BYTE), (13, SAIDA_F, 4), (14, SAIDA_B, 1)], [0, 5, 4],
                          [_disp(0x30, 1, 2, 4, 13), (0x2B, [_r(5), _r(14), _r(13), _r(4)])], extra=3),
    ('2004', '20'): Modelo([_P, (2, BYTE), (13, SAIDA_F, 4), (14, SAIDA_B, 1)], [0, 2],
                           [_disp(0x30, 7, 1, 1, 13), (0x29, [_b(1), _r(14), _r(13), _r(2)])], extra=7),
    ('2004', '21'): Modelo([_P, (5, BYTE), (4, _F), (13, SAIDA_F, 4), (14, SAIDA_B, 1)], [0, 5, 4],
                           [_disp(0x30, 8, 3, 4, 13), (0x2B, [_r(5), _r(14), _r(13), _r(4)])], extra=3),
    ('2004', '37'): Modelo([(11, _L), (14, SAIDA_B, 1)], [11], [(0x03, [_r(14), _r(11)])], extra=3),
    # ---- loops ----
    ('2003', '2'): _laco([_P, (3, MASCARA), (16, SAIDA_F, 4), (17, SAIDA_F, 4), (15, ZERO_F), (18, ZERO_B)],
                         [0, 3], [_disp(0x30, 1, 1, 4, 16), (0x11, [_r(17), _r(16), _r(3)])]),
    ('2003', '3'): _laco([_P, (4, _F), (5, BYTE), (16, SAIDA_F, 4), (17, SAIDA_F, 4), (15, ZERO_F), (18, ZERO_B)],
                         [0, 5, 4], [_disp(0x30, 1, 2, 4, 16), (0x10, [('p+1', 5), _r(17), _r(16), _r(4)])]),
    ('2003', '33'): _laco([(15, ZERO_F), (17, SAIDA_F, 4), (18, ZERO_B)], [], [(0x01, [_r(17), _b(0)])]),
    ('2003', '34'): _laco([(12, _F), (16, SAIDA_F, 4), (17, SAIDA_F, 4), (15, ZERO_F), (18, ZERO_B)], [12],
                          [(0x10, [_b(4), _r(17), _r(15), _r(12)])]),
    ('2003', '35'): _laco([(13, _L), (16, SAIDA_F, 4), (17, SAIDA_F, 4), (15, ZERO_F), (18, ZERO_B)], [13],
                          [(0x03, [_r(17), _r(13)])]),
}
# no loop, o incremento do contador vem antes do teste (contagem) ou depois da leitura (sensor/logico)
MODELOS[('2003', '33')].passos.reverse()
MODELOS[('2003', '34')].passos.reverse()

# variaveis numericas (4001): o registrador da variavel e compartilhado pelo nome
LER_VAR, ESCREVER_VAR = ('4001', '2'), ('4001', '5')


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


def modelo(b):
    if (b.t, b.mode) in (LER_VAR, ESCREVER_VAR):
        return None
    try:
        return MODELOS[(b.t, b.mode)]
    except KeyError:
        raise NotImplementedError(f'bloco {b.t} modo {b.mode} ainda nao suportado pelo compilador') from None


class _Programa:
    def __init__(self, cadeia, compat_ide_fios):
        self.reg = {}          # id(bloco) -> {id_hw: endereco}
        self.dado = {}         # (id(bloco), id_hw) -> 'f' | 'b' | 't'
        self.texto = {}        # (id(bloco), id_hw) -> endereco na area de textos
        self.var = {}          # nome da variavel -> endereco
        self.flag = {}         # id(loop) -> registrador de interrupcao (compartilhado pelo nome do loop)
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
        end, vagas, flags_nome = 0, 0, {}
        for b in self.blocos():
            regs = {}
            if b.t == '4001':
                if b.port not in self.var:
                    self.var[b.port] = end
                    end += 4
                if (b.t, b.mode) == LER_VAR:
                    regs[2] = self.var[b.port]
                    self.dado[(id(b), 2)] = 'f'
                elif (id(b), 7) in self.ligados:
                    regs[7] = end
                    self.dado[(id(b), 7)] = 'f'
                    end += 4
                self.reg[id(b)] = regs
                continue
            m = modelo(b)
            for h in m.hw:
                hw, tipo = h[0], h[1]
                regs[hw] = end
                self.dado[(id(b), hw)] = DADO[tipo]
                end += h[2] if tipo in (SAIDA_F, SAIDA_B) else TAMANHO[tipo]
                if tipo == TEXTO:
                    self.texto[(id(b), hw)] = TEXTO_BASE + TEXTO_PASSO * vagas
                    vagas += 1
            self.reg[id(b)] = regs
            if m.laco:
                # loops com o mesmo nome usam o registrador de interrupcao do primeiro (o seu fica reservado)
                self.flag[id(b)] = regs[m.laco[3]] = flags_nome.setdefault(b.label, regs[m.laco[3]])
            end += m.extra
        self.base_const = end

    def const(self, cid):
        return self.base_const + 4 * (cid - 100)


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


def _e(end): return struct.pack('>I', end)


def _texto(s):
    return str(s).encode('latin-1', 'replace') + b'\x00'


def compilar(cadeia, compat_ide_fios=False):
    """Compila uma lista de blocos (comecando por start()) para bytes prontos para o robo."""
    p = _Programa(cadeia, compat_ide_fios)
    a = _Montador()

    for i, v in enumerate(CONSTANTES):
        valor = struct.pack('<f', v) if isinstance(v, float) else struct.pack('<I', v)
        a.emite(b'\x02' + _e(p.const(100 + i)) + valor)
    ligados = [(id(b), e) for b in p.blocos() for e in p.reg[id(b)] if (id(b), e) in p.ligados]
    for end in sorted(p.reg[bid][e] for bid, e in ligados if p.dado[(bid, e)] == 'f'):
        a.emite(b'\x02' + _e(end) + FIO_VAZIO)
    for txt in sorted(p.texto[k] for k in ligados if k in p.texto):
        a.emite(b'\x2f' + _e(txt) + bytes([len(TEXTO_VAZIO)]) + TEXTO_VAZIO)

    def init(b, hw, tipo):
        end = p.reg[id(b)][hw]
        if tipo == PORTA:
            a.emite(b'\x01' + _e(end) + bytes([porta_byte(b.port)]))
        elif tipo == FLOAT:
            a.emite(b'\x02' + _e(end) + struct.pack('<f', float(b.param(hw))))
        elif tipo == BYTE:
            a.emite(b'\x01' + _e(end) + bytes([int(b.param(hw)) & 0xFF]))
        elif tipo == LOGICO:
            a.emite(b'\x01' + _e(end) + bytes([1 - int(b.param(hw))]))
        elif tipo == MASCARA:
            a.emite(b'\x2d' + _e(end) + struct.pack('<H', mascara_cores(b.param(hw))))
        elif tipo == TEXTO:
            vaga = p.texto[(id(b), hw)]
            if (id(b), hw) not in p.ligados:
                t = _texto(b.port)
                a.emite(b'\x2f' + _e(vaga) + bytes([len(t)]) + t)
            a.emite(b'\x02' + _e(end) + _e(vaga))
        elif tipo == ZERO_F:
            a.emite(b'\x02' + _e(end) + struct.pack('<f', 0.0))
        elif tipo == ZERO_B:
            a.emite(b'\x01' + _e(end) + b'\x00')

    def inicializa(b, m, ids):
        for hw in ids:
            tipo = m.tipo(hw)
            if (id(b), hw) not in p.ligados or tipo == TEXTO:   # texto ligado ainda recebe o endereco da vaga
                init(b, hw, tipo)

    def passos(b, lista):
        regs = p.reg[id(b)]
        for op, operandos in lista:
            out = bytes([op])
            for tipo, v in operandos:
                if tipo == 'b':
                    out += bytes([v])
                elif tipo == 'p+1':
                    out += bytes([int(b.param(v)) + 1])
                elif tipo == 'raw':
                    out += v
                else:
                    out += _e(regs[v] if tipo == 'r' else p.const(v))
            a.emite(out)

    def fios(b):
        for destino, entrada, saida in p.fios_de.get(id(b), []):
            orig = (p.dado[(id(b), saida)], p.dado[(id(destino), entrada)])
            src = _e(p.reg[id(b)][saida])
            if orig[1] == 't':
                a.emite(b'\x47' + _e(p.texto[(id(destino), entrada)]) + src)
            else:
                a.emite(bytes([COPIA[orig]]) + _e(p.reg[id(destino)][entrada]) + src)

    def variavel(b):
        guarda = _e(p.var[b.port])
        if (b.t, b.mode) == LER_VAR:
            a.emite(b'\x04' + guarda + guarda)
        elif (id(b), 7) in p.ligados:
            a.emite(b'\x04' + guarda + _e(p.reg[id(b)][7]))
        else:
            a.emite(b'\x02' + guarda + struct.pack('<f', float(b.param(7))))

    def bloco(b, n):
        a.emite(b'\x48')
        if b.t == '4001':
            variavel(b)
            fios(b)
            return
        m = modelo(b)
        regs = p.reg[id(b)]
        if m.laco:
            dentro, contador, condicao, _ = m.laco
            inicializa(b, m, m.inicio)
            tid = p.tids[id(b)][0]
            a.rotulo(f'laco{n}')
            a.emite(b'\x1d'); a.pc(f't{tid}'); a.emite(bytes([tid, 0]))
            a.emite(bytes([0x20, tid, 0]))
            inicializa(b, m, dentro)
            passos(b, m.passos)
            a.emite(b'\x1a'); a.pc(f'fim{n}'); a.emite(_e(p.flag[id(b)]))
            a.emite(b'\x1b'); a.pc(f'laco{n}'); a.emite(_e(regs[condicao]))
            a.emite(b'\x0a' + _e(regs[contador]) + _e(regs[contador]) + _e(p.const(C1)))
            a.rotulo(f'fim{n}')
        elif m.espera:
            repetir, condicao, depois = m.espera
            inicializa(b, m, m.inicio)
            a.rotulo(f'espera{n}')
            passos(b, repetir)
            a.emite(b'\x1b'); a.pc(f'espera{n}'); a.emite(_e(regs[condicao]))
            passos(b, depois)
        elif b.t == '2004':
            inicializa(b, m, m.inicio)
            passos(b, m.passos)
            sim, nao = p.tids[id(b)]
            res = _e(regs[14])
            a.emite(b'\x1f'); a.pc(f't{nao}'); a.emite(res + bytes([nao, 0]))
            a.emite(b'\x1e'); a.pc(f't{sim}'); a.emite(res + bytes([sim, 0]))
            a.emite(bytes([0x20, sim, 0, 0x20, nao, 0]))
        else:
            inicializa(b, m, m.inicio)
            passos(b, m.passos)
        fios(b)

    n = 0
    for tid, ch in p.segmentos:
        a.rotulo(f't{tid}')
        for b in ch:
            if b.t != '2001':
                bloco(b, n); n += 1
        a.emite(b'\x24' if tid == 0 else bytes([0x21, tid, 0]))
    return a.bytes()
