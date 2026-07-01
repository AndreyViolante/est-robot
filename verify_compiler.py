"""
Verifica o compilador comparando o output contra todas as capturas conhecidas.
Roda todos os testes e reporta PASS/FAIL por bloco.
"""
import struct, sys
sys.path.insert(0, r'C:\Users\andre\Desktop\est_robot')
from est_compiler import compile_program

def parse_pcapng(path):
    with open(path, 'rb') as f:
        raw = f.read()
    frames = []
    i = 0
    endian = '<'
    frame_num = 0
    while i < len(raw) - 8:
        bt = struct.unpack_from('<I', raw, i)[0]
        if bt == 0x0A0D0D0A:
            bl = struct.unpack_from('<I', raw, i+4)[0]
            endian = '<' if struct.unpack_from('<I', raw, i+8)[0] == 0x1A2B3C4D else '>'
            i += bl; continue
        bl = struct.unpack_from(endian+'I', raw, i+4)[0]
        if bl < 12 or bl > 0x10000000:
            i += 4; continue
        if bt == 0x00000006:
            frame_num += 1
            if i + 28 <= len(raw):
                cl = struct.unpack_from(endian+'I', raw, i+20)[0]
                pkt = raw[i+28: i+28+cl]
                frames.append((frame_num, pkt))
        i += bl
    return frames

def get_program_bytes(path):
    """Extrai bytes do programa a partir do primeiro frame CMD=04/sub=02."""
    frames = parse_pcapng(path)
    for fn, pkt in frames:
        idx = pkt.find(b'\x68\x11')
        if idx == -1: continue
        pl = pkt[idx:]
        if len(pl) < 6: continue
        if pl[2] != 0x04 or pl[5] != 0x02: continue
        decl = struct.unpack_from('<H', pl, 3)[0]
        data = pl[8: 8+decl]
        # Trunca nos zeros finais depois do END BLOCK
        j = len(data) - 1
        while j > 0 and data[j] == 0: j -= 1
        # Remove checksum (penultimo) e 16 (ultimo) se presentes
        if j >= 1 and data[j] == 0x16: j -= 2
        return data[:j+1]
    return None

def compare(label, compiled: bytes, expected: bytes, ignore_after: int = None):
    if ignore_after:
        compiled  = compiled[:ignore_after]
        expected  = expected[:ignore_after]
    ok = compiled == expected
    if ok:
        print(f"  [PASS] {label}  ({len(compiled)} bytes)")
        return True
    else:
        print(f"  [FAIL] {label}")
        n = max(len(compiled), len(expected))
        diffs = []
        for i in range(n):
            a = compiled[i] if i < len(compiled) else None
            b = expected[i] if i < len(expected) else None
            if a != b:
                diffs.append((i, a, b))
        print(f"         compiled={len(compiled)}B  expected={len(expected)}B  "
              f"diffs={len(diffs)}")
        for i, a, b in diffs[:10]:
            sa = f'{a:02X}' if a is not None else '--'
            sb = f'{b:02X}' if b is not None else '--'
            # contexto
            ctx_c = compiled[max(0,i-2):i+4].hex().upper() if compiled else ''
            ctx_e = expected[max(0,i-2):i+4].hex().upper() if expected else ''
            print(f"    [{i:4d}]: compiled={sa} expected={sb} "
                  f"ctx_c={ctx_c} ctx_e={ctx_e}")
        if len(diffs) > 10:
            print(f"    ... e mais {len(diffs)-10} diferencas")
        return False

# ── Testes ────────────────────────────────────────────────────────────────────

TESTS_OK = 0
TESTS_FAIL = 0

def run(label, instrucoes, capture_path):
    global TESTS_OK, TESTS_FAIL
    try:
        compiled = compile_program(instrucoes)
    except Exception as e:
        print(f"  [ERROR] {label}: {e}")
        TESTS_FAIL += 1
        return

    try:
        expected = get_program_bytes(capture_path)
    except FileNotFoundError:
        print(f"  [SKIP]  {label}: arquivo nao encontrado: {capture_path}")
        return

    if expected is None:
        print(f"  [SKIP]  {label}: dados nao encontrados na captura")
        return

    ok = compare(label, compiled, expected)
    if ok:
        TESTS_OK += 1
    else:
        TESTS_FAIL += 1

print("=" * 60)
print("VERIFICACAO DO COMPILADOR EST")
print("=" * 60)

# Teste 1: Motor A 50% FRENTE (indefinido)
print("\n[1] Motor standalone (aa.pcapng)")
run(
    "motor(A, 50, FRENTE)",
    [{'tipo': 'motor', 'porta': 'A', 'velocidade': 50, 'direcao': 'frente'}],
    r'C:\Users\andre\Downloads\aa.pcapng',
)

# Teste 2: Loop infinito vazio
print("\n[2] Loop infinito vazio (loop.pcapng)")
run(
    "repetir() vazio",
    [{'tipo': 'loop', 'vezes': 0, 'instrucoes': []}],
    r'C:\Users\andre\Downloads\loop.pcapng',
)

# Teste 3: Loop contado 3x vazio
print("\n[3] Loop contado 3x vazio (loop3.pcapng)")
run(
    "repetir(3) vazio",
    [{'tipo': 'loop', 'vezes': 3, 'instrucoes': []}],
    r'C:\Users\andre\Downloads\loop3.pcapng',
)

# Teste 4: Loop 3x com motor 50% FRENTE dentro
print("\n[4] Loop 3x com motor dentro (loopmotor1rotacao.pcapng)")
run(
    "repetir(3) com motor(50, FRENTE)",
    [{'tipo': 'loop', 'vezes': 3, 'instrucoes': [
        {'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente'}
    ]}],
    r'C:\Users\andre\Downloads\loopmotor1rotacao.pcapng',
)

# Teste 5: Timer 1 segundo
print("\n[5] Timer 1 segundo (wait.pcapng)")
run(
    "esperar(1)",
    [{'tipo': 'esperar', 'segundos': 1.0}],
    r'C:\Users\andre\Downloads\wait.pcapng',
)

# Teste 6: Motor B 50% FRENTE modo ON
print("\n[6] Motor B modo ON (solomotorb.pcapng)")
run(
    "motor(B, 50, FRENTE)",
    [{'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 0}],
    r'C:\Users\andre\Downloads\solomotorb.pcapng',
)

# Teste 7: Motor B 50% FRENTE 1 rotacao
print("\n[7] Motor B 1 rotacao (motorrotacao.pcapng)")
run(
    "motor(B, 50, FRENTE, rotacoes=1)",
    [{'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1}],
    r'C:\Users\andre\Downloads\motorrotacao.pcapng',
)

# Teste 8: Motor B 50% FRENTE 2 rotacoes
print("\n[8] Motor B 2 rotacoes (motor2rotacoes.pcapng)")
run(
    "motor(B, 50, FRENTE, rotacoes=2)",
    [{'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 2}],
    r'C:\Users\andre\Downloads\motor2rotacoes.pcapng',
)

from est_compiler import PRETO, VERDE, VERMELHO, BRANCO

# Teste 11: se sensor(S3)==PRETO: motor B +50 1rot; senao: motor B -50 1rot
print("\n[11] se_sensor_cor(S3, PRETO) motor B +50/-50 (sepreto.pcapng)")
run(
    "se_sensor_cor(S3, PRETO, +50, -50, 1rot)",
    [{'tipo': 'se_sensor_cor',
      'porta': 3,
      'cor': PRETO,
      'se_motor':    {'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
      'senao_motor': {'velocidade': 50, 'direcao': 'tras',   'rotacoes': 1},
    }],
    r'C:\Users\andre\Downloads\sepreto.pcapng',
)

# Teste 12: loop infinito + se_sensor_cor(S3, PRETO, +50/-50)
print("\n[12] loop() + se_sensor_cor(S3, PRETO) motor B +50/-50 (sepreto50.pcapng)")
run(
    "repetir(): se_sensor_cor(S3, PRETO, +50, -50, 1rot)",
    [{'tipo': 'loop', 'vezes': 0, 'instrucoes': [
        {'tipo': 'se_sensor_cor',
         'porta': 3,
         'cor': PRETO,
         'se_motor':    {'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
         'senao_motor': {'velocidade': 50, 'direcao': 'tras',   'rotacoes': 1},
        }
    ]}],
    r'C:\Users\andre\Downloads\sepreto50.pcapng',
)

# Teste 9: sensorrgbcores — 4 cores no slot 3 (formato rgbcores, 40B)
# Ordem capturada: preto, verde, branco, vermelho
print("\n[9] Sensor RGB cores slot 3 (sensorrgbcores.pcapng)")
run(
    "sensor_cor(S3, PRETO/VERDE/BRANCO/VERMELHO) tipo=rgbcores",
    [
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': PRETO,    'sensor_tipo': 'rgbcores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': VERDE,    'sensor_tipo': 'rgbcores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': BRANCO,   'sensor_tipo': 'rgbcores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': VERMELHO, 'sensor_tipo': 'rgbcores'},
    ],
    r'C:\Users\andre\Downloads\sensorrgbcores.pcapng',
)

# Teste 10: sensorcores — 4 cores no slot 3 (formato cores, 64B)
# Ordem capturada: vermelho, branco, preto, verde
print("\n[10] Sensor cores slot 3 (sensorcores.pcapng)")
run(
    "sensor_cor(S3, VERMELHO/BRANCO/PRETO/VERDE) tipo=cores",
    [
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': VERMELHO, 'sensor_tipo': 'cores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': BRANCO,   'sensor_tipo': 'cores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': PRETO,    'sensor_tipo': 'cores'},
        {'tipo': 'sensor_cor', 'porta': 3, 'cor': VERDE,    'sensor_tipo': 'cores'},
    ],
    r'C:\Users\andre\Downloads\sensorcores.pcapng',
)

# Teste 16: motor C modo ON 50% FRENTE standalone
print("\n[16] Motor C modo ON 50% FRENTE (cmodoon.pcapng)")
run(
    "motor(C, 50, FRENTE) ON mode",
    [{'tipo': 'motor', 'porta': 'C', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 0}],
    r'C:\Users\andre\Downloads\cmodoon.pcapng',
)

# Teste 14: loop infinito + motor C 50 FRENTE 1 rot
print("\n[14] loop() + motor C 50 FRENTE 1rot (motor_c_loop.pcapng)")
run(
    "repetir(): motor(C, 50, FRENTE, 1rot)",
    [{'tipo': 'loop', 'vezes': 0, 'instrucoes': [
        {'tipo': 'motor', 'porta': 'C', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
    ]}],
    r'C:\Users\andre\Downloads\motor_c_loop.pcapng',
)

# Teste 15: loop infinito + motor B + motor C, ambos 50 FRENTE 1 rot
print("\n[15] loop() + motor B+C 50 FRENTE 1rot (dois_motores_loop.pcapng)")
run(
    "repetir(): motor(B+C, 50, FRENTE, 1rot)",
    [{'tipo': 'loop', 'vezes': 0, 'instrucoes': [
        {'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
        {'tipo': 'motor', 'porta': 'C', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
    ]}],
    r'C:\Users\andre\Downloads\dois_motores_loop.pcapng',
)

# Teste 13: loop infinito + se_sensor_cor(S3, PRETO) + motor B+C por ramo
print("\n[13] loop() + se_sensor_cor(S3) + motor B+C por ramo (dois_sensores_loop.pcapng)")
run(
    "repetir(): se_sensor_cor(S3,PRETO) B+50/C-50 if; B-50/C+50 else",
    [{'tipo': 'loop', 'vezes': 0, 'instrucoes': [
        {'tipo': 'se_sensor_cor',
         'porta': 3,
         'cor': PRETO,
         'se_motor_B':    {'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
         'se_motor_C':    {'velocidade': 50, 'direcao': 'tras',   'rotacoes': 1},
         'senao_motor_B': {'velocidade': 50, 'direcao': 'tras',   'rotacoes': 1},
         'senao_motor_C': {'velocidade': 50, 'direcao': 'frente', 'rotacoes': 1},
        }
    ]}],
    r'C:\Users\andre\Downloads\dois_sensores_loop.pcapng',
)

# Teste 17: Motor B + Motor C simultaneo modo ON 50% FRENTE
print("\n[17] Motor B + Motor C simultaneo ON 50% FRENTE (2motorfrente.pcapng)")
run(
    "motor(B, 50, FRENTE) + motor(C, 50, FRENTE) simultaneo ON",
    [
        {'tipo': 'motor', 'porta': 'B', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 0},
        {'tipo': 'motor', 'porta': 'C', 'velocidade': 50, 'direcao': 'frente', 'rotacoes': 0},
    ],
    r'C:\Users\andre\Downloads\2motorfrente.pcapng',
)

print()
print("=" * 60)
print(f"RESULTADO: {TESTS_OK} PASS, {TESTS_FAIL} FAIL")
print("=" * 60)
