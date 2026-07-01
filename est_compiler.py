"""
Compilador EST: converte instrucoes Python para binario do robo.

Formato geral do binario:
  [secao init: N escrita de registradores de 9 bytes cada]
  [corpo do bloco 1]
  [corpo do bloco 2]
  ...

Cada REG write:  02 [addr BE32] [val LE32 float/int]  (9 bytes)
"""
import struct

# ── Constantes de enderecos de hardware ──────────────────────────────────────

# Registradores de hardware do motor tipo A/C (drive, 4 regs)
# Confirmado em aa.pcapng (slot C fisico)
_MOTOR_SPEED1 = 0x01
_MOTOR_SPEED2 = 0x05
_MOTOR_DIR    = 0x09
_MOTOR_REF    = 0x0D

# Registradores de hardware do motor tipo B
# Modo ON (solomotorb.pcapng):       1 hw reg  (0x01=speed)       → init base 0x05
# Modo ROTACAO (motorrotacao.pcapng): 3 hw regs (0x01=speed, 0x05=rotacoes, 0x09=ref) → init base 0x0A
# Velocidade e assinalada: positivo=frente, negativo=tras
_MOTOR_B_SPEED   = 0x01
_MOTOR_B_ROT_REG = 0x05   # numero de rotacoes (float32)
_MOTOR_B_REF_REG = 0x09   # registro de referencia do motor B

# Offset dos registradores de hardware quando o motor está DENTRO de um loop
_MOTOR_IN_LOOP_OFFSET = 0x14   # todos os enderecos de hw +0x14

# Registradores de contador do loop (fixos no primeiro loop)
_LOOP_COUNTER_REG = 0x0C       # registrador de contagem atual
_LOOP_LIMIT_REG   = 0x10       # registrador de limite

# ── Bases de init por tipo de bloco (confirmadas em capturas) ─────────────────
#
# Cada bloco aloca 8 registradores de inicializacao (4 bytes cada = 32 bytes).
# A base depende de quais registradores de hardware/contador ja estao ocupados.
#
#   Motor A/C standalone:   base = 0x0E  (apos hw 0x0D)
#   Motor B standalone:     base = 0x05  (apos hw 0x01)
#   Timer/loop infinito:    base = 0x0C
#   Loop contado (vazio):   base = 0x0C → reserva 0x0C e 0x10 → init em 0x14
#   Loop contado c/ motor:  base = 0x22 (apos hw motor+offset 0x21, e contadores)

_BASE_MOTOR_STANDALONE  = 0x0E
_BASE_MOTOR_B           = 0x05  # motor tipo B modo ON: 1 hw reg (0x01)
_BASE_MOTOR_B_ROTACAO   = 0x0A  # motor tipo B modo rotacao: 3 hw regs (0x01,0x05,0x09)
_BASE_TIMER_LOOP        = 0x0C   # base inicial; loop contado avanca 8 antes de init
_BASE_LOOP_COM_MOTOR    = 0x22   # loop contado com motor interno

# ── Constantes de sensor de cor ───────────────────────────────────────────────
#
# Dois formatos de bloco, confirmados em capturas:
#
#   'rgbcores' (40 bytes, marcador 0x01): 11 regs locais por bloco
#              Confirmado em sensorrgbcores.pcapng (slot 3, 4 cores)
#
#   'cores'    (64 bytes, marcador 0x03): 6 regs locais por bloco
#              Confirmado em sensorcores.pcapng (slot 3, 4 cores)
#
# Codificacao da cor: bitmask LE16 = 1 << color_id
#   preto=1 → 0x0002,  verde=3 → 0x0008
#   vermelho=5 → 0x0020, branco=6 → 0x0040
#
# Codificacao do slot (porta S1-S4):
#   rgbcores: byte pos 22 = slot + 1
#   cores:    hw1 = 1 + slot*4,  hw2 = hw1 + 8
#
# A secao de init e COMPARTILHADA entre todos os blocos sensor:
#   init_base = n_blocos × regs_por_bloco
#   (cores: 6 regs/bloco → init_base = n*6; rgbcores: 11 regs/bloco → init_base = n*11)

PRETO    = 1
VERDE    = 3
VERMELHO = 5
BRANCO   = 6

_SENSOR_RGBCORES_REGS = 11  # regs locais por bloco (formato 40B)
_SENSOR_CORES_REGS    = 6   # regs locais por bloco (formato 64B)

def _sensor_slot_hw(slot: int):
    """Retorna (hw1, hw2) = enderecos de hardware do sensor para o slot dado."""
    hw1 = 1 + slot * 4
    return hw1, hw1 + 8

# ── Constantes do bloco condicional (se_sensor_cor) ──────────────────────────
#
# O bloco condicional usa enderecos LOCAIS fixos (como se sensor_base=0),
# independente do contexto de loop.  Confirmado em sepreto.pcapng e sepreto50.pcapng.
#
# Layout local (sem loop):
#   regs 0x00..0x0A → sensor rgbcores (11 regs)
#   regs 0x0B..0x14 → motor B ramo IF   (speed=+1, rot=+5, ref=+9)
#   regs 0x15..0x1E → motor B ramo ELSE
#   regs 0x1F..     → init section
#
# Constantes fixas confirmadas (iguais em sepreto e sepreto50):
#   _LOCAL_INIT_BASE      = 0x1F  → byte [0] do bloco condicional (sempre 0x1F)
#   _LOCAL_INIT_BASE + 1  = 0x20  → bytes [22] e [25] do bloco condicional
#   _LOCAL_INIT_BASE + 2  = 0x21  → state_ref nos blocos motor, e byte [28] (loop)
#   _LOCAL_ELSE_MOTOR_REF = 0x1E  → bytes [11..14] do bloco condicional
#
# Quando o condicional esta dentro de 1 loop infinito (sepreto50.pcapng):
#   - sensor_base ABSOLUTO = _LOOP_HW_REGS = 0x0C  (loop ocupa regs 0x00..0x0B)
#   - if_offset ABSOLUTO   = 0x0C + 0x0B = 0x17
#   - else_offset ABSOLUTO = 0x0C + 0x15 = 0x21
#   - init_base ABSOLUTO   = 0x0C + 0x1F = 0x2B
#   - state_ref            = 0x21 = _LOCAL_INIT_BASE + 2 (sempre fixo)
#   - marcador sensor      = 0x01 (dentro de loop; era 0x03 em condicional standalone)
#   - else_abs codificado como 2 bytes BE em [3..4] do bloco condicional
#   - contadores no bloco condicional: todos +1 por nivel de loop
#   - triplet extra ao final: (0x21, 0x01, 0x00) por nivel de loop
#   - SEM END BLOCK 0x24 ao final (o loop provê o seu proprio)

_LOCAL_INIT_BASE      = 0x1F   # endereco local do init no bloco condicional (fixo)
_LOCAL_ELSE_MOTOR_REF = 0x1E   # local_else_offset + _MOTOR_B_REF_REG = 0x15+9
_STATE_REF            = 0x21   # _LOCAL_INIT_BASE + 2, referencia de estado no motor
_LOOP_HW_REGS         = 0x0C   # regs de hardware que o loop infinito ocupa (0x00..0x0B)

# ── Templates de blocos (capturados via Wireshark) ────────────────────────────

# Corpo do bloco LOOP INFINITO (67 bytes).
# Confirmado em loop.pcapng.
_LOOP_INFINITO_BODY = bytes.fromhex(
    '48020000000000000000'
    '010000000800090000000000000000000000'
    '100100000004001a0000008a00000008'
    '1b00000058000000040a000000000000'
    '00000000001024'
)
assert len(_LOOP_INFINITO_BODY) == 67, len(_LOOP_INFINITO_BODY)

# Corpo do bloco LOOP CONTADO VAZIO (84 bytes, confirmado em loop3.pcapng N=3).
# Posicoes variaveis:
#   +5 ..+8  : contador reg LE32       (= _LOOP_COUNTER_REG = 0x0C)
#   +21..+24 : contagem como float32 LE (ex: 00 00 40 40 = 3.0)
#   +56      : posicao absoluta do END BLOCK (1 byte; = init_size + 84 - 1)
_LOOP_CONTADO_BODY = bytes.fromhex(
    '48020000000c00000000010000001000'
    '02000000000000404009000000'
    '0c0000000c00000018'
    '1004000000080000000c000000'
    '001a0000009b000000101b0000005800000008'
    '0a0000000c0000000c0000001824'
)
assert len(_LOOP_CONTADO_BODY) == 84, len(_LOOP_CONTADO_BODY)

# Corpo do bloco LOOP CONTADO COM MOTOR DENTRO (94 bytes,
# confirmado em loopmotor1rotacao.pcapng, loop 3x, motor B+C 50% FRENTE).
#
# Diferenca em relacao ao LOOP_CONTADO_BODY:
#   - 10 bytes extras em posicao 16: 1D 00 00 00 [child_start] 01 00 20 01 00
#     onde child_start = byte baixo do inicio do corpo do bloco motor filho
#   - dois bytes 0x18 viram 0x26 (pre-end = "tem filho")
#   - byte 0x9B (posicao END BLOCK) muda para 0xA5 conforme o tamanho total
#
# Posicoes variaveis:
#   +5 ..+8  : contador reg LE32         (= 0x0C)
#   +20      : child_start byte           (= init_size + 94 = 0xA6 para este prog)
#   +31..+34 : contagem como float32 LE  (ex: 00 00 40 40 = 3.0)
#   +47      : 0x26 (fixo = tem filho)
#   +66      : posicao absoluta END BLOCK (1 byte; = init_size + 94 - 1 = 0xA5)
#   +92      : 0x26 (fixo)
#   +93      : 0x24 END BLOCK (fixo)
_LOOP_COM_MOTOR_BODY = bytes.fromhex(
    # pos 0-15  (same as counted loop)
    '48020000000c00000000010000001000'
    # pos 16-25 (10 extra bytes: child-block pointer + opaque bytes)
    '1d000000a6010020'
    '0100'
    # pos 26-93 (same as counted loop[16..83] but with 0x18→0x26 and 0x9B→0xA5)
    '02000000000000404009000000'
    '0c0000000c00000026'                # <-- 0x26 (era 0x18)
    '1004000000080000000c000000'
    '001a000000a5000000101b0000005800000008'  # <-- 0xA5 (era 0x9B)
    '0a0000000c0000000c00000026'        # <-- 0x26 (era 0x18)
    '24'
)
assert len(_LOOP_COM_MOTOR_BODY) == 94, len(_LOOP_COM_MOTOR_BODY)


# ── Helpers binários ──────────────────────────────────────────────────────────

def reg_write(addr: int, value) -> bytes:
    """
    Escreve valor num registrador.
    9 bytes: 02 [addr BE32] [val LE32 float ou int]
    """
    if isinstance(value, float):
        val_bytes = struct.pack('<f', value)
    elif isinstance(value, int) and not isinstance(value, bool):
        val_bytes = struct.pack('<I', value)
    else:
        val_bytes = struct.pack('<f', float(value))
    return b'\x02' + struct.pack('>I', addr) + val_bytes


def instr_48(val: int) -> bytes:
    """INSTR 0x48: 5 bytes, identificador de tipo de bloco."""
    return b'\x48' + struct.pack('<I', val)


def instr_90() -> bytes:
    """INSTR 0x90: 1 byte, inicio de valores ativos."""
    return b'\x90'


def instr_01(addr: int) -> bytes:
    """INSTR 0x01: 5 bytes, referencia de registrador."""
    return b'\x01' + struct.pack('>I', addr)


def end_block() -> bytes:
    """Fim de bloco: 0x24."""
    return b'\x24'


# ── Alocador de registros ─────────────────────────────────────────────────────

class RegAllocator:
    """
    Aloca enderecos de registradores para os blocos de init.
    Cada bloco de init ocupa 8 registradores de 4 bytes cada (32 bytes total).
    """
    def __init__(self, base: int):
        self.next_reg = base

    def alloc_block_regs(self, n: int = 8) -> int:
        """Aloca n registradores e retorna o endereco base alocado."""
        addr = self.next_reg
        self.next_reg += n * 4   # cada registrador = 4 bytes
        return addr


# ── Compilador de blocos ──────────────────────────────────────────────────────

class Compiler:

    # Valores padrao das 8 variaveis de inicializacao de cada bloco.
    # Confirmado em TODAS as capturas (aa, wait, loop, loop3, loopmotor).
    _INIT_VALS = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 1, 2]

    # Mapa de direcoes
    _DIRECAO = {'frente': 1.0, 'tras': -1.0, 'parar': 0.0}

    def __init__(self):
        self._alloc: RegAllocator | None = None
        self.init_writes: list[bytes] = []

    def _get_alloc(self, base: int) -> RegAllocator:
        """Retorna (ou cria) o alocador de registradores."""
        if self._alloc is None:
            self._alloc = RegAllocator(base)
        return self._alloc

    def _alloc_init_regs(self, base_hint: int) -> int:
        """
        Aloca 8 registradores de inicializacao e gera os REG writes.
        Retorna o endereco base alocado.
        """
        alloc = self._get_alloc(base_hint)
        block_base = alloc.alloc_block_regs(8)
        for i, v in enumerate(self._INIT_VALS):
            addr = block_base + i * 4
            val = float(v) if isinstance(v, float) else v
            self.init_writes.append(reg_write(addr, val))
        return block_base

    # ── Motor (standalone) ────────────────────────────────────────────────────

    def compile_motor(self, porta: str, velocidade: int, direcao: str,
                      rotacoes: int = 0) -> bytes:
        """
        Compila um bloco motor STANDALONE. Roteia para o formato correto.

        Args:
            porta:    A, B, C ou D
            velocidade: 0-100
            direcao:  frente, tras ou parar
            rotacoes: numero de rotacoes (0 = modo ON; >0 = modo rotacao)
        """
        if porta.upper() == 'B':
            if rotacoes > 0:
                return self._compile_motor_B_rotacao(velocidade, direcao, rotacoes)
            return self._compile_motor_B(velocidade, direcao)
        if porta.upper() == 'C':
            if rotacoes > 0:
                return self._compile_motor_B_rotacao(velocidade, direcao, rotacoes)
            return self._compile_motor_C_on(velocidade, direcao)
        return self._compile_motor_AC(porta, velocidade, direcao)

    def _compile_motor_AC(self, porta: str, velocidade: int, direcao: str) -> bytes:
        """
        Motor tipo A/C (drive): velocidade + direcao separados, 3 registradores.

        Confirmado em aa.pcapng (slot C fisico) e motormaisespera1.pcapng.

        Formato (54 bytes corpo):
          48 01 00 00 00   ← tipo = motor (1)
          00               ← padding
          90               ← marcador de valores ativos
          [REG speed1 addr=0x01]  ← velocidade float
          [REG speed2 addr=0x05]  ← velocidade float
          [REG dir   addr=0x09]   ← 1.0=frente -1.0=tras 0.0=parar
          01 00 00 00 0D   ← INSTR 0x01 ref=0x0D
          01               ← byte fixo
          31 00 00 00 00   ← INSTR 0x31 size=0
          00               ← NOP
          83 05 0D 00 00   ← INSTR 0x83 modo=indefinido
          00 01            ← NOP + pre-end (execucao unica)
          24               ← END BLOCK
        """
        vel_f = float(velocidade)
        dir_f = self._DIRECAO.get(direcao.lower(), 1.0)

        self._alloc_init_regs(_BASE_MOTOR_STANDALONE)

        block  = instr_48(1)
        block += b'\x00'                               # padding
        block += instr_90()
        block += reg_write(_MOTOR_SPEED1, vel_f)
        block += reg_write(_MOTOR_SPEED2, vel_f)
        block += reg_write(_MOTOR_DIR,    dir_f)
        block += instr_01(_MOTOR_REF)                  # ref=0x0D
        block += bytes([0x01])
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00]) # INSTR 0x31 size=0
        block += bytes([0x00])                          # NOP
        block += bytes([0x83, 0x05, 0x0D, 0x00, 0x00]) # INSTR 0x83 indefinido
        block += bytes([0x00, 0x01])                    # NOP + pre-end
        block += end_block()
        return block

    def _compile_motor_bc_on_block(self, offset: int, velocidade: int,
                                    direcao: str, marker: int,
                                    is_last: bool,
                                    in_loop: bool = False) -> bytes:
        """
        Bloco motor B ou C modo ON (sem alocar init).

        Confirmado em 2motorfrente.pcapng (motor B offset=0x00, motor C offset=0x05).

        Formato base (29B nao-ultimo):
          48 01 00 00 00        ← tipo = motor (1)
          [offset]             ← base do motor (0x00 para 1o, 0x05 para 2o, ...)
          [marker]             ← 0x06=B, 0x07=C
          [REG speed offset+1] ← velocidade float assinalada
          31 00 00 00 00       ← INSTR 0x31
          [offset]             ← byte = offset (mesmo que padding)
          81 02 04 00 00 00    ← INSTR 0x81 modo ON
          [offset+1]           ← speed_addr = offset + 1

        Terminador (so se is_last=True):
          standalone (in_loop=False): 24            ← END BLOCK  (30B total)
          dentro de loop (in_loop=True): 21 01 00   ← state_ref triplet (32B total)

        Padrao derivado de todos os loops com filhos confirmados:
          loop+C rotacao (196B), loop+B+C rotacao (240B): ultimo filho = ...21 01 00
        """
        vel_f = float(velocidade)
        if direcao.lower() == 'tras':    vel_f = -vel_f
        elif direcao.lower() == 'parar': vel_f = 0.0

        spd_addr = (offset + _MOTOR_B_SPEED) & 0xFF   # offset + 0x01

        block  = instr_48(1)
        block += bytes([offset & 0xFF])                          # padding = offset
        block += bytes([marker & 0xFF])                          # marker
        block += reg_write(offset + _MOTOR_B_SPEED, vel_f)      # speed
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00])
        block += bytes([offset & 0xFF])                          # NOP = offset
        block += bytes([0x81, 0x02, 0x04, 0x00, 0x00, 0x00])
        block += bytes([spd_addr])                               # speed_addr
        if is_last:
            if in_loop:
                block += bytes([_STATE_REF, 0x01, 0x00])        # 21 01 00 (loop context)
            else:
                block += end_block()                             # 24 (standalone)
        return block

    def compile_motors_on(self, motores: list) -> bytes:
        """
        Compila N motores B/C em modo ON simultaneo (sem loop, sem sensor).

        Motor nao-ultimo: 29B (sem END BLOCK).
        Motor ultimo:     30B (com END BLOCK).
        init_base = n_motores * _BASE_MOTOR_B (0x05 por motor).

        Confirmado em:
          cmodoon.pcapng:      1 motor C (30B, offset=0x00) → 102B total
          2motorfrente.pcapng: motor B (29B, offset=0x00) + C (30B, offset=0x05) → 131B
        """
        n = len(motores)
        init_base = n * _BASE_MOTOR_B          # 0x05, 0x0A, ...
        self._alloc_init_regs(init_base)

        _MARKER = {'B': 0x06, 'C': 0x07}
        blocks = b''
        for i, m in enumerate(motores):
            offset  = i * _BASE_MOTOR_B        # 0x00, 0x05, 0x0A, ...
            marker  = _MARKER.get(m['porta'].upper(), 0x06)
            is_last = (i == n - 1)
            blocks += self._compile_motor_bc_on_block(
                offset, m['velocidade'], m['direcao'], marker, is_last
            )
        return blocks

    def _compile_motor_B(self, velocidade: int, direcao: str) -> bytes:
        """Motor tipo B modo ON standalone (30 bytes). Confirmado em solomotorb.pcapng."""
        self._alloc_init_regs(_BASE_MOTOR_B)
        return self._compile_motor_bc_on_block(0x00, velocidade, direcao, 0x06, True)

    def _compile_motor_C_on(self, velocidade: int, direcao: str) -> bytes:
        """
        Motor tipo C modo ON: identico ao motor B modo ON, marker 0x07.

        Confirmado em cmodoon.pcapng (50% FRENTE).

        Formato (30 bytes corpo):
          48 01 00 00 00        ← tipo = motor (1)
          00                   ← padding
          07                   ← marcador motor C  (unica diferenca do motor B)
          [REG speed addr=0x01] ← velocidade float assinalada
          31 00 00 00 00        ← INSTR 0x31
          00                   ← NOP
          81 02 04 00 00 00    ← INSTR 0x81 modo ON
          01 24                ← pre-end + END BLOCK

        init_base = 0x05 (igual ao motor B — compartilham espaco de registradores).
        """
        vel_f = float(velocidade)
        if direcao.lower() == 'tras':    vel_f = -vel_f
        elif direcao.lower() == 'parar': vel_f = 0.0

        self._alloc_init_regs(_BASE_MOTOR_B)   # base 0x05, mesmo que motor B

        block  = instr_48(1)
        block += b'\x00'
        block += b'\x07'                                 # marker motor C
        block += reg_write(_MOTOR_B_SPEED, vel_f)        # speed at reg 0x01
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00])
        block += bytes([0x00])
        block += bytes([0x81, 0x02, 0x04, 0x00, 0x00, 0x00])
        block += bytes([0x01])
        block += end_block()
        return block

    def _compile_motor_B_rotacao(self, velocidade: int, direcao: str,
                                  rotacoes: int) -> bytes:
        """
        Motor tipo B modo ROTACAO: gira N rotacoes a velocidade dada.

        Confirmado em motorrotacao.pcapng (1 rot) e motor2rotacoes.pcapng (2 rot).

        Campos variaveis:
          REG 0x05 = float(rotacoes)         ← numero de rotacoes
          REG 0x01 = float(velocidade)*sinal ← velocidade assinalada (+frente, -tras)

        Formato (45 bytes corpo):
          48 01 00 00 00        ← tipo = motor (1)
          00                   ← padding
          06                   ← marcador motor B
          01 00 00 00 09        ← instr_01(0x09) referencia
          01                   ← byte fixo
          [REG rot  addr=0x05] ← rotacoes como float32
          [REG speed addr=0x01] ← velocidade assinalada
          31 00 00 00 00 00    ← INSTR 0x31 + NOP
          81 05 09 00 00 00    ← INSTR 0x81 modo rotacao
          01 24                ← pre-end + END BLOCK
        """
        vel_f = float(velocidade)
        if direcao.lower() == 'tras':    vel_f = -vel_f
        elif direcao.lower() == 'parar': vel_f = 0.0
        rot_f = float(rotacoes)

        self._alloc_init_regs(_BASE_MOTOR_B_ROTACAO)

        block  = instr_48(1)
        block += b'\x00'                                 # padding
        block += b'\x06'                                 # marcador motor B
        block += instr_01(_MOTOR_B_REF_REG)              # instr_01(0x09)
        block += bytes([0x01])                           # byte fixo
        block += reg_write(_MOTOR_B_ROT_REG, rot_f)     # rotacoes
        block += reg_write(_MOTOR_B_SPEED,   vel_f)     # velocidade assinalada
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00])  # INSTR 0x31
        block += bytes([0x00])                           # NOP
        block += bytes([0x81, 0x05,
                        _MOTOR_B_REF_REG & 0xFF,
                        0x00, 0x00, 0x00])               # run rotacao
        block += bytes([0x01])                           # pre-end
        block += end_block()
        return block

    # ── Motor (dentro de loop) ────────────────────────────────────────────────

    def compile_motor_in_loop(self, porta: str, velocidade: int,
                              direcao: str) -> bytes:
        """
        Compila um bloco motor DENTRO de um loop.

        Confirmado em loopmotor1rotacao.pcapng.

        Diferencas em relacao ao motor standalone:
          - Padding apos INSTR 0x48: 0x14 (era 0x00)
          - Todos os enderecos de HW: +0x14 (0x01→0x15, 0x05→0x19, 0x09→0x1D, 0x0D→0x21)
          - Byte fixo antes de INSTR 0x83: 0x14 (era 0x00)
          - Sequencia final: 0x15 0x21 0x01 0x00 (sem END BLOCK 0x24!)

        NB: nao ha secao de init propria; o loop pai ja alocou os registradores.
        """
        vel_f = float(velocidade)
        dir_f = self._DIRECAO.get(direcao.lower(), 1.0)

        off = _MOTOR_IN_LOOP_OFFSET          # = 0x14
        s1 = _MOTOR_SPEED1 + off             # = 0x15
        s2 = _MOTOR_SPEED2 + off             # = 0x19
        dr = _MOTOR_DIR    + off             # = 0x1D
        rf = _MOTOR_REF    + off             # = 0x21

        block  = instr_48(1)
        block += bytes([off])                # padding = 0x14
        block += instr_90()
        block += reg_write(s1, vel_f)
        block += reg_write(s2, vel_f)
        block += reg_write(dr, dir_f)
        block += instr_01(rf)                # INSTR 0x01 ref=0x21
        block += bytes([0x01])
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00])  # INSTR 0x31 size=0
        block += bytes([off])                # 0x14 (era 0x00)
        block += bytes([0x83, 0x05, 0x0D, 0x00, 0x00])  # INSTR 0x83
        block += bytes([0x00])               # NOP
        block += bytes([s1 & 0xFF])          # 0x15 = speed1 addr
        block += bytes([rf & 0xFF])          # 0x21 = ref addr
        block += bytes([0x01])               # pre-end = execucao unica
        block += bytes([0x00])               # trailing NOP
        # SEM end_block() (0x24) — o loop pai marca o fim
        return block

    # ── Timer / Esperar ────────────────────────────────────────────────────────

    def compile_esperar(self, segundos: float) -> bytes:
        """
        Compila um bloco de espera/timer.

        Confirmado em wait.pcapng.

        Formato (21 bytes corpo):
          48 02 00 00 00   ← tipo = timer/loop (2)
          00               ← padding
          [float32 LE]     ← duracao em segundos
          23 00 00 00 00   ← bytecode fixo
          01 00 00 00 08   ← bytecode fixo
          01               ← pre-end (execucao unica)
          24               ← END BLOCK
        """
        self._alloc_init_regs(_BASE_TIMER_LOOP)

        dur = struct.pack('<f', float(segundos))

        block  = instr_48(2)
        block += b'\x00'
        block += dur
        block += b'\x23\x00\x00\x00\x00'
        block += b'\x01\x00\x00\x00\x08\x01'
        block += end_block()
        return block

    # ── Sensor de cor ─────────────────────────────────────────────────────────

    def _compile_sensor_cor_rgbcores(self, base: int, slot: int, cor: int) -> bytes:
        """
        Bloco sensor de cor formato 'rgbcores' (40 bytes, marcador 0x01).

        Confirmado em sensorrgbcores.pcapng (slot 3, cores preto/verde/branco/vermelho).

        Campos variaveis:
          pos  5, 19 : r0 = base       (registro da porta)
          pos  6     : slot             (porta: S1=1, S2=2 — inicializa r0 no sub-header)
          pos 11, 39 : r1 = base + 1   (registro da cor alvo)
          pos 12     : color_id = cor  (1=PRETO, 3=VERDE, 5=VERMELHO, 6=BRANCO)
          pos 22     : 0x04 FIXO       (tipo sensor RGB — compile_xml/2004.xml modo 4, v5=4)
          pos 26, 35 : r3 = base + 3   (leitura bruta do sensor)
          pos 31     : r7 = base + 7   (resultado booleano da comparacao)
        """
        r0 = base & 0xFF
        r1 = (base + 1) & 0xFF
        r3 = (base + 3) & 0xFF
        r7 = (base + 7) & 0xFF
        cm = cor & 0xFF          # direct color ID, not bitmask
        se = slot & 0xFF         # hardware port matches API slot number directly

        blk = bytearray(40)
        blk[0:5]    = b'\x48\x01\x00\x00\x00'
        blk[5]      = r0
        blk[6]      = se          # ← porta no sub-header (inicializa r0 = porta)
        blk[7]      = 0x2D
        blk[8:11]   = b'\x00\x00\x00'
        blk[11]     = r1
        blk[12]     = cm
        blk[13]     = 0x00
        blk[14]     = 0x30
        blk[15:19]  = b'\x00\x00\x00\x00'
        blk[19]     = r0
        blk[20]     = 0x01
        blk[21]     = 0x01
        blk[22]     = 0x04        # ← FIXO: tipo sensor RGB (compile_xml/2004.xml modo 4, v5=4)
        blk[23:26]  = b'\x00\x00\x00'
        blk[26]     = r3
        blk[27]     = 0x11
        blk[28:31]  = b'\x00\x00\x00'
        blk[31]     = r7
        blk[32:35]  = b'\x00\x00\x00'
        blk[35]     = r3
        blk[36:39]  = b'\x00\x00\x00'
        blk[39]     = r1
        return bytes(blk)

    def _compile_sensor_cor_cores(self, base: int, slot: int, cor: int,
                                   init_base: int) -> bytes:
        """
        Bloco sensor de cor formato 'cores' (64 bytes, marcador 0x03).

        Confirmado em sensorcores.pcapng (slot 3, cores vermelho/branco/preto/verde).

        Campos variaveis:
          pos  5, 19 : r0 = base
          pos 11, 35 : r1 = base + 1
          pos 12     : color_mask_low = (1 << cor) & 0xFF
          pos 26, 39, 59, 63 : r3 = base + 3
          pos 31, 45, 49     : r5 = base + 5
          pos 53     : init_base (= n_blocos * 6)
          pos 54     : hw1 = 1 + slot * 4
          pos 55     : hw2 = hw1 + 8
        """
        r0 = base & 0xFF
        r1 = (base + 1) & 0xFF
        r3 = (base + 3) & 0xFF
        r5 = (base + 5) & 0xFF
        cm = (1 << cor) & 0xFF
        hw1, hw2 = _sensor_slot_hw(slot)

        blk = bytearray(64)
        blk[0:5]    = b'\x48\x01\x00\x00\x00'
        blk[5]      = r0
        blk[6]      = 0x03
        blk[7]      = 0x2D
        blk[8:11]   = b'\x00\x00\x00'
        blk[11]     = r1
        blk[12]     = cm
        blk[13]     = 0x00
        blk[14]     = 0x30
        blk[15:19]  = b'\x00\x00\x00\x00'
        blk[19]     = r0
        blk[20]     = 0x01
        blk[21]     = 0x01
        blk[22]     = 0x01
        blk[23:26]  = b'\x00\x00\x00'
        blk[26]     = r3
        blk[27]     = 0x11
        blk[28:31]  = b'\x00\x00\x00'
        blk[31]     = r5
        blk[32:35]  = b'\x00\x00\x00'
        blk[35]     = r1
        blk[36:39]  = b'\x00\x00\x00'
        blk[39]     = r3
        blk[40]     = 0x29
        blk[41:45]  = b'\x03\x00\x00\x00'
        blk[45]     = r5
        blk[46:49]  = b'\x00\x00\x00'
        blk[49]     = r5
        blk[50:53]  = b'\x00\x00\x00'
        blk[53]     = init_base & 0xFF
        blk[54]     = hw1 & 0xFF
        blk[55]     = hw2 & 0xFF
        blk[56:59]  = b'\x00\x00\x00'
        blk[59]     = r3
        blk[60:63]  = b'\x00\x00\x00'
        blk[63]     = r3
        return bytes(blk)

    def compile_sensores_cor(self, instrucoes_sensor: list) -> bytes:
        """
        Compila uma lista de instrucoes 'sensor_cor' para binario.

        Cada instrucao deve ter:
            {'tipo': 'sensor_cor', 'porta': S, 'cor': C, 'sensor_tipo': 'rgbcores'|'cores'}

        Gera:
          [init section 72B compartilhada]
          [bloco sensor 1]
          [bloco sensor 2]
          ...
          [0x24 terminador]

        NB: Sensor blocks NAO tem END BLOCK individual; um unico 0x24 encerra o programa.
        """
        if not instrucoes_sensor:
            return b''

        # Detecta tipo (assume uniforme na lista)
        sensor_tipo = instrucoes_sensor[0].get('sensor_tipo', 'rgbcores')
        regs_per  = (_SENSOR_RGBCORES_REGS if sensor_tipo == 'rgbcores'
                     else _SENSOR_CORES_REGS)

        # Init base = total de regs locais antes da secao de init
        n = len(instrucoes_sensor)
        init_base = n * regs_per

        # Gera a secao de init (unica para o programa inteiro)
        self._alloc_init_regs(init_base)

        # Gera os blocos sensor
        blocks = b''
        sensor_alloc = 0   # proximo base local disponivel
        for instr in instrucoes_sensor:
            slot = instr['porta']       # S1=1 … S4=4
            cor  = instr['cor']         # PRETO=1, VERDE=3, VERMELHO=5, BRANCO=6
            if sensor_tipo == 'rgbcores':
                blocks += self._compile_sensor_cor_rgbcores(sensor_alloc, slot, cor)
            else:
                blocks += self._compile_sensor_cor_cores(sensor_alloc, slot, cor, init_base)
            sensor_alloc += regs_per

        init_bytes = b''.join(self.init_writes)
        return init_bytes + blocks + b'\x24'

    # ── Condicional: se sensor_cor → motor B rotacao ─────────────────────────
    #
    # Confirmado em sepreto.pcapng:
    #   se sensor(S3) == PRETO: motor B 50% FRENTE 1 rot
    #   senao:                  motor B 50% TRAS  1 rot
    #
    # Estrutura (235 bytes totais):
    #   [72B init]  init_base = if_offset + 2*0x0A
    #   [40B sensor] marcador 0x03 (diferente do standalone 0x01)
    #   [29B cond]  referencias a init_base, offsets absolutos dos ramos, sensor_r7
    #   [47B if]    motor B rotacao, offset=if_offset,   branch_id=0x01
    #   [47B else]  motor B rotacao, offset=else_offset, branch_id=0x02
    #
    # Layout de registradores:
    #   regs 0..10          → sensor rgbcores (11 regs)
    #   regs 0x0B..0x14     → motor B if-ramo  (speed=+1, rot=+5, ref=+9)
    #   regs 0x15..0x1E     → motor B else-ramo
    #   reg  0x1F           → init_base (primeiro reg de init)

    def _compile_motor_rotacao_in_cond(self, branch_offset: int, velocidade: int,
                                       direcao: str, rotacoes: int,
                                       branch_id: int, marker: int = 0x06,
                                       is_last: bool = True) -> bytes:
        """
        Motor rotacao DENTRO de bloco condicional.

        Formato base (sempre):
          [0-4]   instr_48(1)
          [5]     branch_offset (absoluto)
          [6]     marker  (0x06=motor B, 0x07=motor C)
          [7-11]  instr_01(branch_offset + 0x09)   (ref reg BE32)
          [12]    0x01 (fixo)
          [13-21] reg_write(branch_offset + 0x05, rot)
          [22-30] reg_write(branch_offset + 0x01, speed)
          [31-35] 0x31 0x00 0x00 0x00 0x00
          [36]    branch_offset (padding)
          [37-42] 0x81 0x05 0x09 0x00 0x00 0x00
          [43]    branch_offset + 0x01  (speed reg addr)

        Se is_last=True (47 bytes, ultimo motor do ramo):
          [44]    0x21 = _STATE_REF  (fixo)
          [45]    branch_id  (loop: 0x02=if, 0x03=else; sem loop: 0x01=if, 0x02=else)
          [46]    0x00

        Se is_last=False (44 bytes, motor nao-ultimo do ramo):
          (sem [44][45][46])

        Confirmado em:
          sepreto.pcapng/sepreto50.pcapng: motor B (0x06), is_last=True
          dois_sensores_loop.pcapng: motor B (0x06) is_last=False + motor C (0x07) is_last=True
        """
        vel_f = float(velocidade)
        if direcao.lower() == 'tras':    vel_f = -vel_f
        elif direcao.lower() == 'parar': vel_f = 0.0
        rot_f = float(rotacoes)

        spd_addr = branch_offset + _MOTOR_B_SPEED    # +0x01
        rot_addr = branch_offset + _MOTOR_B_ROT_REG  # +0x05
        ref_addr = branch_offset + _MOTOR_B_REF_REG  # +0x09

        block  = instr_48(1)
        block += bytes([branch_offset & 0xFF])           # [5]  offset
        block += bytes([marker & 0xFF])                  # [6]  motor marker
        block += instr_01(ref_addr)                      # [7-11] ref BE32
        block += bytes([0x01])                           # [12] fixo
        block += reg_write(rot_addr, rot_f)              # [13-21] rotacoes
        block += reg_write(spd_addr, vel_f)              # [22-30] velocidade
        block += bytes([0x31, 0x00, 0x00, 0x00, 0x00])  # [31-35] INSTR 0x31
        block += bytes([branch_offset & 0xFF])           # [36]  offset (padding)
        block += bytes([0x81, 0x05, 0x09, 0x00, 0x00, 0x00])  # [37-42] INSTR 0x81
        block += bytes([spd_addr & 0xFF])                # [43] speed addr
        if is_last:
            block += bytes([_STATE_REF])                 # [44] 0x21 fixo
            block += bytes([branch_id & 0xFF])           # [45] branch_id
            block += bytes([0x00])                       # [46] NOP
        return block

    def _compile_motor_B_rotacao_in_cond(self, branch_offset: int, velocidade: int,
                                          direcao: str, rotacoes: int,
                                          branch_id: int) -> bytes:
        """Motor B rotacao em bloco condicional (47 bytes, is_last=True). Retrocompat."""
        return self._compile_motor_rotacao_in_cond(
            branch_offset, velocidade, direcao, rotacoes,
            branch_id, marker=0x06, is_last=True
        )

    def _compile_condicional_b(self, sensor_r7: int, if_abs: int, else_abs: int,
                                loop_depth: int = 0) -> bytes:
        """
        Bloco condicional (29 bytes standalone, 31 bytes dentro de 1 loop).

        Confirmado em sepreto.pcapng (depth=0) e sepreto50.pcapng (depth=1).

        Campos com enderecos LOCAIS fixos (independentes de sensor_base/init_base):
          [0]     0x1F = _LOCAL_INIT_BASE (sempre fixo)
          [1..2]  0x00 0x00
          [3..4]  else_abs como 2 bytes big-endian
          [5..7]  0x00 0x00 0x00
          [8]     sensor_r7
          [9]     0x02 + loop_depth
          [10]    0x00
          [11..14] 0x1E 00 00 00 = _LOCAL_ELSE_MOTOR_REF LE32 (sempre fixo)
          [15]    if_abs (1 byte)
          [16..18] 0x00 0x00 0x00
          [19]    sensor_r7
          [20]    0x01 + loop_depth
          [21]    0x00
          [22]    0x20 = _LOCAL_INIT_BASE + 1 (sempre fixo)
          [23]    0x01 + loop_depth
          [24]    0x00
          [25]    0x20 = _LOCAL_INIT_BASE + 1 (sempre fixo)
          [26]    0x02 + loop_depth
          [27]    0x00
          [28]    0x24 END BLOCK  (depth=0)  ou  0x21 (depth=1, _LOCAL_INIT_BASE+2)
          [29]    0x01  (so depth=1)
          [30]    0x00  (so depth=1)
        """
        # depth=0: 29B (bloco termina com END BLOCK 0x24)
        # depth=1: 31B (END BLOCK substituido por triplet 3B = +2 liquido)
        size = 29 + 2 * loop_depth
        blk = bytearray(size)

        # [0..7]: endereco local fixo + else_abs como 2 bytes BE
        blk[0] = _LOCAL_INIT_BASE & 0xFF          # = 0x1F
        blk[1] = 0x00
        blk[2] = 0x00
        blk[3] = (else_abs >> 8) & 0xFF           # high byte de else_abs
        blk[4] = else_abs & 0xFF                   # low byte de else_abs
        blk[5] = 0x00; blk[6] = 0x00; blk[7] = 0x00

        blk[8]  = sensor_r7 & 0xFF
        blk[9]  = (0x02 + loop_depth) & 0xFF
        blk[10] = 0x00

        # [11..14]: else_motor_ref LOCAL fixo = 0x1E (local_else_offset + ref_reg)
        struct.pack_into('<I', blk, 11, _LOCAL_ELSE_MOTOR_REF)

        blk[15] = if_abs & 0xFF
        blk[16] = 0x00; blk[17] = 0x00; blk[18] = 0x00

        blk[19] = sensor_r7 & 0xFF
        blk[20] = (0x01 + loop_depth) & 0xFF
        blk[21] = 0x00
        blk[22] = (_LOCAL_INIT_BASE + 1) & 0xFF   # = 0x20
        blk[23] = (0x01 + loop_depth) & 0xFF
        blk[24] = 0x00
        blk[25] = (_LOCAL_INIT_BASE + 1) & 0xFF   # = 0x20
        blk[26] = (0x02 + loop_depth) & 0xFF
        blk[27] = 0x00

        if loop_depth == 0:
            blk[28] = 0x24                          # END BLOCK (termina o programa)
        else:
            # Triplet extra por nivel de loop: (_LOCAL_INIT_BASE+2, 0x01, 0x00)
            blk[28] = (_LOCAL_INIT_BASE + 2) & 0xFF  # = 0x21
            blk[29] = 0x01
            blk[30] = 0x00
            # Para depth > 1 seria necessario mais triplets (nao implementado ainda)

        return bytes(blk)

    def compile_se_sensor_cor(self, porta_sensor: int, cor: int,
                               if_motor: dict, else_motor: dict) -> bytes:
        """
        Compila: se sensor(porta) == cor: if_motor; senao: else_motor

        Suporta motor B rotacao em ambos os ramos.

        Confirmado em sepreto.pcapng (slot=3, cor=PRETO, 50/-50, 1 rot).

        Args:
            porta_sensor: S1..S4 (ex: 3)
            cor:          PRETO, VERDE, VERMELHO ou BRANCO
            if_motor:     dict com 'velocidade', 'direcao', 'rotacoes'
            else_motor:   dict com 'velocidade', 'direcao', 'rotacoes'
        """
        # ── Layout de registradores ──────────────────────────────────────────
        n_sensor  = 1
        if_offset   = n_sensor * _SENSOR_RGBCORES_REGS      # = 11 = 0x0B
        else_offset = if_offset   + _BASE_MOTOR_B_ROTACAO   # = 21 = 0x15
        init_base   = else_offset + _BASE_MOTOR_B_ROTACAO   # = 31 = 0x1F

        # ── Offsets absolutos no binario ─────────────────────────────────────
        init_size   = 8 * 9        # 72B
        sensor_size = 40           # sensor rgbcores block
        cond_size   = 29           # conditional block
        motor_size  = 47           # each motor branch block

        if_abs   = init_size + sensor_size + cond_size           # = 141 = 0x8D
        else_abs = if_abs + motor_size                           # = 188 = 0xBC

        # ── 1. Sensor block (marcador 0x03, diferente do standalone 0x01) ───
        sensor_base = 0
        sensor_r7   = sensor_base + 7   # = 7
        sb = bytearray(self._compile_sensor_cor_rgbcores(sensor_base, porta_sensor, cor))
        sb[6] = 0x03                     # marcador para sensor dentro de condicional standalone
        sensor_block = bytes(sb)

        # ── 2. Conditional block (depth=0, sem loop) ─────────────────────────
        cond_block = self._compile_condicional_b(
            sensor_r7=sensor_r7,
            if_abs=if_abs,
            else_abs=else_abs,
            loop_depth=0,
        )

        # ── 3. Motor B if-ramo ────────────────────────────────────────────────
        if_block = self._compile_motor_B_rotacao_in_cond(
            branch_offset=if_offset,
            velocidade=if_motor['velocidade'],
            direcao=if_motor['direcao'],
            rotacoes=if_motor.get('rotacoes', 1),
            branch_id=0x01,
        )

        # ── 4. Motor B else-ramo ──────────────────────────────────────────────
        el_block = self._compile_motor_B_rotacao_in_cond(
            branch_offset=else_offset,
            velocidade=else_motor['velocidade'],
            direcao=else_motor['direcao'],
            rotacoes=else_motor.get('rotacoes', 1),
            branch_id=0x02,
        )

        # ── 5. Init section (init_base = 0x1F) ──────────────────────────────
        self._alloc_init_regs(init_base)
        init_bytes = b''.join(self.init_writes)

        return init_bytes + sensor_block + cond_block + if_block + el_block

    # ── Loop ───────────────────────────────────────────────────────────────────

    def compile_loop(self, vezes: int = 0) -> bytes:
        """
        Compila um bloco de loop VAZIO (sem instrucoes internas).

        vezes=0 → loop infinito
        vezes=N → loop contado N vezes
        """
        if vezes == 0:
            # Loop infinito (67 bytes)
            self._alloc_init_regs(_BASE_TIMER_LOOP)
            return _LOOP_INFINITO_BODY

        else:
            # Loop contado (84 bytes)
            # Reserva os 2 regs de contador (0x0C e 0x10) antes do init
            alloc = self._get_alloc(_BASE_TIMER_LOOP)
            alloc.next_reg += 2 * 4   # avanca 2 regs (0x0C → 0x14)
            self._alloc_init_regs(_BASE_TIMER_LOOP)  # usa next_reg=0x14

            body = bytearray(_LOOP_CONTADO_BODY)

            # Patch: endereco do reg-contador (pos 5-8)
            struct.pack_into('<I', body, 5, _LOOP_COUNTER_REG)

            # Patch: contagem como float32 (pos 21-24)
            struct.pack_into('<f', body, 21, float(vezes))

            # Patch: posicao absoluta do END BLOCK (pos 56)
            # END BLOCK = init_section + corpo_loop = 72 + 84 - 1 = 155 = 0x9B
            init_size = len(self.init_writes) * 9   # 8 × 9 = 72
            end_pos = init_size + 84 - 1
            body[56] = end_pos & 0xFF

            return bytes(body)

    # ── Loop com motor dentro ─────────────────────────────────────────────────

    def compile_loop_with_motor(self, vezes: int,
                                motor_instrucoes: list) -> bytes:
        """
        Compila um loop CONTADO que contem um bloco motor interno.

        Confirmado em loopmotor1rotacao.pcapng (loop 3x, motor B+C 50% FRENTE).

        Estrutura do binario gerado:
          [init section 72B, base=0x22]
          [loop body 94B, com pointer para o motor]
          [motor body 56B, sem END BLOCK proprio]

        Args:
            vezes:             numero de repeticoes (>0)
            motor_instrucoes:  lista de dicts 'motor' (suporta 1 motor por enquanto)
        """
        if vezes == 0:
            raise NotImplementedError(
                "Loop infinito com motor ainda nao implementado; use vezes > 0.")
        if not motor_instrucoes:
            return self.compile_loop(vezes)
        if len(motor_instrucoes) > 1:
            raise NotImplementedError(
                "Loop com mais de 1 bloco motor ainda nao implementado.")

        # 1) Init section em base 0x22
        # Reserva manualmente: aloca em 0x22 (hardcoded para 1 motor no loop)
        alloc = self._get_alloc(_BASE_LOOP_COM_MOTOR)
        self._alloc_init_regs(_BASE_LOOP_COM_MOTOR)
        init_size = len(self.init_writes) * 9   # = 72 bytes

        # 2) Corpo do loop (94 bytes), com campos calculados
        loop_body_size = 94
        motor_start_abs = init_size + loop_body_size   # = 72 + 94 = 166
        end_block_abs   = motor_start_abs - 1           # = 165

        body = bytearray(_LOOP_COM_MOTOR_BODY)

        # Patch: contador reg (pos 5-8)
        struct.pack_into('<I', body, 5, _LOOP_COUNTER_REG)

        # Patch: child_block_start (pos 20, 1 byte)
        body[20] = motor_start_abs & 0xFF

        # Patch: contagem float32 (pos 31-34)
        struct.pack_into('<f', body, 31, float(vezes))

        # Patch: posicao END BLOCK (pos 66, 1 byte)
        body[66] = end_block_abs & 0xFF

        loop_bytes = bytes(body)

        # 3) Corpo do motor (56 bytes, sem END BLOCK)
        m = motor_instrucoes[0]
        motor_bytes = self.compile_motor_in_loop(
            m['porta'], m['velocidade'], m['direcao']
        )

        return loop_bytes + motor_bytes

    # ── Loop infinito com condicional sensor ─────────────────────────────────

    def _build_infinite_loop_with_child(self, child_abs: int,
                                         end_blk_abs: int,
                                         init_base: int = 0x2B) -> bytes:
        """
        Corpo do loop infinito com bloco filho (77 bytes).

        Confirmado em sepreto50.pcapng (loop + se_sensor_cor).

        Construido a partir de _LOOP_INFINITO_BODY (67B):
          1. Insere 10 bytes na posicao 16:
             1D 00 00 00 [child_abs] 01 00 20 01 00
          2. Byte na posicao 38 (era LOOP_INF[28]=0x10): muda para init_base + 4
          3. Byte na posicao 49 (era LOOP_INF[39]=0x8A): vira end_blk_abs
          4. Byte na posicao 75 (era LOOP_INF[65]=0x10): muda para init_base + 4

        A flag 'tem filho' = init_base + 4 (= endereco do 2o reg de init).
        Confirmado em:
          sepreto50:     init_base=0x2B → flag=0x2F
          motor_c_loop:  init_base=0x16 → flag=0x1A
          dois_motores:  init_base=0x20 → flag=0x24
          dois_sensores: init_base=0x3F → flag=0x43
        """
        has_child_flag = (init_base + 4) & 0xFF

        extra10 = bytes([0x1D, 0x00, 0x00, 0x00,
                         child_abs & 0xFF,
                         0x01, 0x00, 0x20, 0x01, 0x00])

        body = bytearray(_LOOP_INFINITO_BODY[:16]
                         + extra10
                         + _LOOP_INFINITO_BODY[16:])   # 67 - 16 + 10 + 16 = 77B

        body[38] = has_child_flag            # "tem filho" flag
        body[49] = end_blk_abs & 0xFF        # posicao absoluta do END BLOCK
        body[75] = has_child_flag            # "tem filho" flag (repete)

        return bytes(body)

    def compile_loop_se_sensor_cor(self, porta_sensor: int, cor: int,
                                    if_motor: dict, else_motor: dict) -> bytes:
        """
        Compila: com repetir(): se sensor(porta) == cor: if_motor; senao: else_motor

        Confirmado em sepreto50.pcapng (loop infinito, slot S3, PRETO, +50/-50, 1 rot).

        O loop infinito ocupa os registradores de hardware 0x00..0x0B (_LOOP_HW_REGS=0x0C),
        deslocando o layout do condicional para enderecos absolutos mais altos.

        Estrutura do binario (314 bytes totais):
          [72B init]   init_base = _LOOP_HW_REGS + _LOCAL_INIT_BASE = 0x0C + 0x1F = 0x2B
          [77B loop]   loop infinito com child pointer para o sensor
          [40B sensor] marcador 0x01 (diferente do standalone 0x03)
          [31B cond]   bloco condicional depth=1 (sem END BLOCK proprio)
          [47B if]     motor B ramo IF,   branch_offset = _LOOP_HW_REGS + 0x0B = 0x17
          [47B else]   motor B ramo ELSE, branch_offset = _LOOP_HW_REGS + 0x15 = 0x21
        """
        # ── Layout de registradores (absoluto, com 1 loop) ───────────────────
        sensor_base  = _LOOP_HW_REGS                       # = 0x0C
        if_offset    = sensor_base + 0x0B                  # = 0x17
        else_offset  = sensor_base + 0x15                  # = 0x21
        init_base    = sensor_base + _LOCAL_INIT_BASE      # = 0x2B

        # ── Tamanhos dos blocos ───────────────────────────────────────────────
        init_size   = 8 * 9    # = 72B
        loop_size   = 77       # loop infinito com child pointer
        sensor_size = 40       # sensor rgbcores
        cond_size   = 31       # condicional depth=1
        motor_size  = 47       # cada ramo motor

        # ── Posicoes absolutas ────────────────────────────────────────────────
        child_abs   = init_size + loop_size                          # = 149 = 0x95
        if_abs      = child_abs + sensor_size + cond_size           # = 220 = 0xDC
        else_abs    = if_abs   + motor_size                          # = 267 = 0x10B
        end_blk_abs = init_size + loop_size - 1                     # = 148 = 0x94

        # ── 1. Sensor block (marcador 0x01 dentro de loop, nao patchear) ─────
        sensor_r7    = (sensor_base + 7) & 0xFF              # = 0x13
        sensor_block = bytes(
            self._compile_sensor_cor_rgbcores(sensor_base, porta_sensor, cor)
        )
        # Marcador = 0x01 (padrao do metodo; NAO patchar para 0x03 aqui)

        # ── 2. Bloco condicional (depth=1, sem END BLOCK) ────────────────────
        cond_block = self._compile_condicional_b(
            sensor_r7=sensor_r7,
            if_abs=if_abs,
            else_abs=else_abs,
            loop_depth=1,
        )

        # ── 3. Motor B ramo IF ────────────────────────────────────────────────
        # branch_id dentro de loop é deslocado por 1: if=0x02, else=0x03
        if_block = self._compile_motor_B_rotacao_in_cond(
            branch_offset=if_offset,
            velocidade=if_motor['velocidade'],
            direcao=if_motor['direcao'],
            rotacoes=if_motor.get('rotacoes', 1),
            branch_id=0x02,
        )

        # ── 4. Motor B ramo ELSE ──────────────────────────────────────────────
        el_block = self._compile_motor_B_rotacao_in_cond(
            branch_offset=else_offset,
            velocidade=else_motor['velocidade'],
            direcao=else_motor['direcao'],
            rotacoes=else_motor.get('rotacoes', 1),
            branch_id=0x03,
        )

        # ── 5. Init section — popula self.init_writes (compile() prepoe o init) ──
        self._alloc_init_regs(init_base)

        # ── 6. Corpo do loop infinito com child pointer (77B) ────────────────
        loop_body = self._build_infinite_loop_with_child(child_abs, end_blk_abs,
                                                          init_base=init_base)

        # Retorna APENAS os blocos (sem init); compile() prepoe init_bytes.
        return loop_body + sensor_block + cond_block + if_block + el_block

    def compile_loop_with_rotacao_motors(self,
                                          motores: list) -> bytes:
        """
        Compila loop infinito com N motores em modo rotacao (sem condicional).

        Formato: mesmo layout do modo condicional mas sem sensor/cond block.
        Branch_id = 0x01 (nao ha if/else).
        Motor nao-ultimo: 44B; motor ultimo: 47B.

        Confirmado em:
          motor_c_loop.pcapng:    1 motor C 50 FRENTE 1rot → 196B
          dois_motores_loop.pcapng: motor B (non-last) + motor C (last) → 240B

        Mapeamento de porta para marker:
          B → 0x06,  C → 0x07

        Args:
            motores: lista de dicts {'porta', 'velocidade', 'direcao', 'rotacoes'}
        """
        if not motores:
            raise ValueError("compile_loop_with_rotacao_motors: lista de motores vazia")

        _MARKER = {'B': 0x06, 'C': 0x07}

        # ── Layout de registradores ───────────────────────────────────────────
        first_offset = _LOOP_HW_REGS             # = 0x0C
        offsets = [first_offset + i * _BASE_MOTOR_B_ROTACAO
                   for i in range(len(motores))]  # 0x0C, 0x16, 0x20, …
        init_base = offsets[-1] + _BASE_MOTOR_B_ROTACAO

        # ── Tamanhos dos blocos ───────────────────────────────────────────────
        init_size = 8 * 9    # = 72B
        loop_size = 77

        # ── Posicoes absolutas ────────────────────────────────────────────────
        child_abs   = init_size + loop_size        # = 149
        end_blk_abs = init_size + loop_size - 1   # = 148

        # ── Blocos de motor ───────────────────────────────────────────────────
        motor_blocks = b''
        for idx, (m, off) in enumerate(zip(motores, offsets)):
            is_last = (idx == len(motores) - 1)
            marker  = _MARKER.get(m['porta'].upper(), 0x06)
            motor_blocks += self._compile_motor_rotacao_in_cond(
                branch_offset=off,
                velocidade=m['velocidade'],
                direcao=m['direcao'],
                rotacoes=m.get('rotacoes', 1),
                branch_id=0x01,           # sem condicional → branch 1
                marker=marker,
                is_last=is_last,
            )

        # ── Init section ──────────────────────────────────────────────────────
        self._alloc_init_regs(init_base)

        # ── Loop infinito com child pointer ───────────────────────────────────
        loop_body = self._build_infinite_loop_with_child(child_abs, end_blk_abs,
                                                          init_base=init_base)

        return loop_body + motor_blocks

    def compile_loop_se_sensor_cor_2motors(self, porta_sensor: int, cor: int,
                                            if_B_motor: dict, if_C_motor: dict,
                                            else_B_motor: dict, else_C_motor: dict) -> bytes:
        """
        Compila: com repetir():
                     se sensor(porta) == cor:
                         motor_B(...); motor_C(...)
                     senao:
                         motor_B(...); motor_C(...)

        Confirmado em dois_sensores_loop.pcapng (loop, S3, PRETO, B+C por ramo).

        Estrutura do binario (402 bytes totais):
          [72B init]   init_base = sensor_base + local_else_C_offset + 0x0A = 0x3F
          [77B loop]   loop infinito com child pointer (flag=init_base+4=0x43)
          [40B sensor] marcador 0x01
          [31B cond]   bloco condicional depth=1
          [44B if-B]   motor B if-ramo (nao-ultimo: 44B, sem trailing 3B)
          [47B if-C]   motor C if-ramo (ultimo: 47B, branch_id=0x02)
          [44B else-B] motor B else-ramo (nao-ultimo: 44B)
          [47B else-C] motor C else-ramo (ultimo: 47B, branch_id=0x03)

        Layout de registradores (absoluto, com 1 loop infinito):
          sensor:  base=0x0C  (loop ocupa 0x00..0x0B)
          if_B:    offset=0x17 (sensor usa 0x0B regs)
          if_C:    offset=0x21 (if_B usa 0x0A regs)
          else_B:  offset=0x2B (if_C usa 0x0A regs)
          else_C:  offset=0x35 (else_B usa 0x0A regs)
          init:    base=0x3F   (else_C usa 0x0A regs)
        """
        # ── Layout de registradores (absoluto) ───────────────────────────────
        sensor_base  = _LOOP_HW_REGS                       # = 0x0C
        if_B_offset  = sensor_base + 0x0B                  # = 0x17
        if_C_offset  = if_B_offset  + _BASE_MOTOR_B_ROTACAO # = 0x21
        else_B_offset = if_C_offset + _BASE_MOTOR_B_ROTACAO # = 0x2B
        else_C_offset = else_B_offset + _BASE_MOTOR_B_ROTACAO# = 0x35
        init_base    = else_C_offset + _BASE_MOTOR_B_ROTACAO # = 0x3F

        # ── Tamanhos dos blocos ───────────────────────────────────────────────
        init_size   = 8 * 9    # = 72B
        loop_size   = 77       # loop infinito com child pointer
        sensor_size = 40       # sensor rgbcores
        cond_size   = 31       # condicional depth=1
        motor_B_nl  = 44       # motor nao-ultimo (sem trailing 3B)
        motor_C_l   = 47       # motor ultimo (com trailing 3B)

        # ── Posicoes absolutas ────────────────────────────────────────────────
        child_abs   = init_size + loop_size                                 # = 149
        if_abs      = child_abs + sensor_size + cond_size                  # = 220
        else_abs    = if_abs   + motor_B_nl   + motor_C_l                  # = 311
        end_blk_abs = init_size + loop_size - 1                            # = 148

        # ── 1. Sensor block (marcador 0x01 = padrao dentro de loop) ──────────
        sensor_r7    = (sensor_base + 7) & 0xFF              # = 0x13
        sensor_block = self._compile_sensor_cor_rgbcores(sensor_base, porta_sensor, cor)

        # ── 2. Bloco condicional (depth=1) ────────────────────────────────────
        cond_block = self._compile_condicional_b(
            sensor_r7=sensor_r7,
            if_abs=if_abs,
            else_abs=else_abs,
            loop_depth=1,
        )

        # ── 3. Motor B ramo IF (nao-ultimo, 44B) ─────────────────────────────
        if_B_block = self._compile_motor_rotacao_in_cond(
            branch_offset=if_B_offset,
            velocidade=if_B_motor['velocidade'],
            direcao=if_B_motor['direcao'],
            rotacoes=if_B_motor.get('rotacoes', 1),
            branch_id=0x02,     # nao usado (is_last=False), mas mantido por clareza
            marker=0x06,
            is_last=False,
        )

        # ── 4. Motor C ramo IF (ultimo, 47B) ─────────────────────────────────
        if_C_block = self._compile_motor_rotacao_in_cond(
            branch_offset=if_C_offset,
            velocidade=if_C_motor['velocidade'],
            direcao=if_C_motor['direcao'],
            rotacoes=if_C_motor.get('rotacoes', 1),
            branch_id=0x02,     # if dentro de loop = 0x02
            marker=0x07,
            is_last=True,
        )

        # ── 5. Motor B ramo ELSE (nao-ultimo, 44B) ────────────────────────────
        else_B_block = self._compile_motor_rotacao_in_cond(
            branch_offset=else_B_offset,
            velocidade=else_B_motor['velocidade'],
            direcao=else_B_motor['direcao'],
            rotacoes=else_B_motor.get('rotacoes', 1),
            branch_id=0x03,     # nao usado (is_last=False)
            marker=0x06,
            is_last=False,
        )

        # ── 6. Motor C ramo ELSE (ultimo, 47B) ───────────────────────────────
        else_C_block = self._compile_motor_rotacao_in_cond(
            branch_offset=else_C_offset,
            velocidade=else_C_motor['velocidade'],
            direcao=else_C_motor['direcao'],
            rotacoes=else_C_motor.get('rotacoes', 1),
            branch_id=0x03,     # else dentro de loop = 0x03
            marker=0x07,
            is_last=True,
        )

        # ── 7. Init section ───────────────────────────────────────────────────
        self._alloc_init_regs(init_base)

        # ── 8. Loop infinito com child pointer ────────────────────────────────
        loop_body = self._build_infinite_loop_with_child(child_abs, end_blk_abs,
                                                          init_base=init_base)

        return (loop_body + sensor_block + cond_block
                + if_B_block + if_C_block
                + else_B_block + else_C_block)

    def compile_loop_with_on_motors(self, motores: list) -> bytes:
        """
        Compila loop infinito + N motores B/C em modo ON simultaneo.

        Por analogia com compile_loop_with_rotacao_motors, mas usando blocos ON
        (0x81 0x02) em vez de rotacao (0x81 0x05).

        Layout de registradores:
          loop:    0x00..0x0B  (_LOOP_HW_REGS = 0x0C)
          motor 0: offset = 0x0C
          motor 1: offset = 0x11  (0x0C + 0x05)
          init:    base   = 0x16  (0x11 + 0x05)

        Motor nao-ultimo: 29B (sem END BLOCK).
        Motor ultimo:     30B (com END BLOCK).

        NB: formato especulativo, nao confirmado em captura dedicada.
            Se o robo nao responder, capture loop+B+C ON no EST e envie o pcapng.
        """
        if not motores:
            raise ValueError("compile_loop_with_on_motors: lista de motores vazia")

        _MARKER = {'B': 0x06, 'C': 0x07}

        # ── Layout de registradores ───────────────────────────────────────────
        first_offset = _LOOP_HW_REGS             # = 0x0C
        offsets = [first_offset + i * _BASE_MOTOR_B for i in range(len(motores))]
        init_base = offsets[-1] + _BASE_MOTOR_B  # ex: 2 motores → 0x16

        # ── Tamanhos e posicoes ───────────────────────────────────────────────
        init_size   = 8 * 9    # = 72B
        loop_size   = 77

        child_abs   = init_size + loop_size        # = 149
        end_blk_abs = init_size + loop_size - 1   # = 148

        # ── Blocos de motor ───────────────────────────────────────────────────
        motor_blocks = b''
        for idx, (m, off) in enumerate(zip(motores, offsets)):
            is_last = (idx == len(motores) - 1)
            marker  = _MARKER.get(m['porta'].upper(), 0x06)
            motor_blocks += self._compile_motor_bc_on_block(
                off, m['velocidade'], m['direcao'], marker, is_last,
                in_loop=True    # ultimo filho termina com 21 01 00, nao 24
            )

        # ── Init section ──────────────────────────────────────────────────────
        self._alloc_init_regs(init_base)

        # ── Loop infinito com child pointer ───────────────────────────────────
        loop_body = self._build_infinite_loop_with_child(child_abs, end_blk_abs,
                                                          init_base=init_base)

        return loop_body + motor_blocks

    # ── Loop com conteudo geral ───────────────────────────────────────────────

    def compile_loop_with_content(self, vezes: int,
                                  instrucoes: list) -> bytes:
        """
        Compila um loop com instrucoes internas.

        Rota para o metodo especializado conforme o tipo de conteudo.
        """
        motor_instrs = [i for i in instrucoes if i['tipo'] == 'motor']
        cond_instrs  = [i for i in instrucoes if i['tipo'] == 'se_sensor_cor']
        outros       = [i for i in instrucoes
                        if i['tipo'] not in ('motor', 'se_sensor_cor')]

        if outros:
            raise NotImplementedError(
                f"Instrucoes {[i['tipo'] for i in outros]} dentro de loop "
                f"ainda nao suportadas.")

        if cond_instrs:
            if len(cond_instrs) > 1:
                raise NotImplementedError(
                    "Multiplos blocos se_sensor_cor dentro de loop nao suportados.")
            if motor_instrs:
                raise NotImplementedError(
                    "Combinacao de motor + se_sensor_cor dentro de loop nao suportada.")
            if vezes != 0:
                raise NotImplementedError(
                    "Loop contado com se_sensor_cor nao suportado ainda; use repetir().")
            c = cond_instrs[0]
            # Verifica se usa 2 motores (B+C) ou 1 motor (B)
            if 'se_motor_B' in c and 'se_motor_C' in c:
                return self.compile_loop_se_sensor_cor_2motors(
                    porta_sensor=c['porta'],
                    cor=c['cor'],
                    if_B_motor=c['se_motor_B'],
                    if_C_motor=c['se_motor_C'],
                    else_B_motor=c['senao_motor_B'],
                    else_C_motor=c['senao_motor_C'],
                )
            return self.compile_loop_se_sensor_cor(
                porta_sensor=c['porta'],
                cor=c['cor'],
                if_motor=c['se_motor'],
                else_motor=c['senao_motor'],
            )

        # Motores B/C em modo ON (rotacoes=0) dentro de loop infinito
        is_on_mode = (
            motor_instrs
            and all(
                m.get('rotacoes', 0) == 0
                and m.get('porta', '').upper() in ('B', 'C')
                for m in motor_instrs
            )
        )
        if is_on_mode and vezes == 0:
            return self.compile_loop_with_on_motors(motor_instrs)

        # Motores B/C em modo rotacao (formato condicional, branch_id=0x01)
        # Motores A/C drive (formato antigo com 0x14 offset) usam o caminho anterior
        is_rotacao = all(
            m.get('rotacoes', 0) > 0 and m.get('porta', '').upper() in ('B', 'C')
            for m in motor_instrs
        )
        if is_rotacao and vezes == 0:
            return self.compile_loop_with_rotacao_motors(motor_instrs)

        return self.compile_loop_with_motor(vezes, motor_instrs)

    # ── Dispatch principal ─────────────────────────────────────────────────────

    def compile(self, instrucoes: list) -> bytes:
        """
        Compila lista de instrucoes para binario.

        Instrucoes de sensor_cor sao tratadas em grupo (init compartilhado).
        Instrucoes de motor/loop/esperar seguem o fluxo normal.
        """
        # ── Bloco especial: programa puro de sensores ──────────────────────────
        sensor_instrs = [i for i in instrucoes if i['tipo'] == 'sensor_cor']
        outros_instrs = [i for i in instrucoes if i['tipo'] != 'sensor_cor']

        if sensor_instrs and not outros_instrs:
            # Programa so com sensores: delega ao metodo especializado
            return self.compile_sensores_cor(sensor_instrs)

        # ── Bloco especial: se_sensor_cor standalone (sem loop envolvente) ───────
        cond_instrs = [i for i in outros_instrs if i['tipo'] == 'se_sensor_cor']
        loop_instrs = [i for i in outros_instrs if i['tipo'] == 'loop']
        non_cond    = [i for i in outros_instrs if i['tipo'] != 'se_sensor_cor']

        if cond_instrs and not loop_instrs:
            if len(cond_instrs) > 1:
                raise NotImplementedError("Multiplos blocos se_sensor_cor ainda nao suportados.")
            c = cond_instrs[0]
            return self.compile_se_sensor_cor(
                porta_sensor=c['porta'],
                cor=c['cor'],
                if_motor=c['se_motor'],
                else_motor=c['senao_motor'],
            )

        if sensor_instrs and outros_instrs:
            raise NotImplementedError(
                "Mistura de blocos sensor_cor com outros tipos ainda nao suportada.")

        # ── Bloco especial: motores B/C em modo ON simultaneo ──────────────────
        # Se TODAS as instrucoes sao motores B ou C com rotacoes=0, compila em
        # modo simultaneo (init section unica compartilhada, um slot de 0x05 cada).
        # Confirmado em 2motorfrente.pcapng (B+C ON, 131B).
        bc_on = [i for i in instrucoes
                 if i['tipo'] == 'motor'
                 and i.get('porta', '').upper() in ('B', 'C')
                 and i.get('rotacoes', 0) == 0]
        outros_bc = [i for i in instrucoes if i not in bc_on]
        if bc_on and not outros_bc:
            body = self.compile_motors_on(bc_on)
            init_bytes = b''.join(self.init_writes)
            return init_bytes + body

        # ── Fluxo normal (motor / loop / esperar) ──────────────────────────────
        blocks_bytes = b''

        for instr in instrucoes:
            tipo = instr['tipo']

            if tipo == 'motor':
                blocks_bytes += self.compile_motor(
                    instr['porta'],
                    instr['velocidade'],
                    instr['direcao'],
                    instr.get('rotacoes', 0),
                )
            elif tipo == 'esperar':
                blocks_bytes += self.compile_esperar(instr['segundos'])

            elif tipo == 'loop':
                vezes = instr.get('vezes', 0)
                inner = instr.get('instrucoes', [])
                if inner:
                    blocks_bytes += self.compile_loop_with_content(vezes, inner)
                else:
                    blocks_bytes += self.compile_loop(vezes)

            elif tipo == 'parar_tudo':
                for porta in ['A', 'B', 'C', 'D']:
                    blocks_bytes += self.compile_motor(porta, 0, 'parar')

            else:
                raise NotImplementedError(
                    f"Bloco '{tipo}' ainda nao implementado.")

        init_bytes = b''.join(self.init_writes)
        return init_bytes + blocks_bytes


# ── API de alto nível ─────────────────────────────────────────────────────────

def compile_program(instrucoes: list) -> bytes:
    """
    Compila lista de instrucoes (gerada por est.py) para binario do robo.

    Args:
        instrucoes: lista de dicts com as instrucoes

    Returns:
        bytes do programa compilado
    """
    c = Compiler()
    return c.compile(instrucoes)
