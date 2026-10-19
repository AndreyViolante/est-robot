"""Mostra, instrucao por instrucao, o bytecode de um programa do robo EST.

Uso:
  python ferramentas/decodificar.py exemplos/11_seguidor_dois_sensores.py   o que o estc.py gera
  python ferramentas/decodificar.py gabaritos/t5_loop_cont.hex            um gabarito salvo
  python ferramentas/decodificar.py order_content.txt                     uma captura da IDE EST
"""
import os, sys, struct

# tamanho de cada instrucao no bytecode real (o InstructionSet.xml da IDE erra alguns)
TAM = {0x01: 6, 0x02: 9, 0x03: 9, 0x04: 9, 0x07: 9, 0x08: 9, 0x09: 13, 0x0A: 13, 0x0B: 13, 0x0C: 13,
       0x0D: 10, 0x0E: 13, 0x0F: 9, 0x10: 14, 0x11: 13, 0x12: 13, 0x13: 9, 0x14: 13, 0x15: 13, 0x16: 13,
       0x17: 9, 0x18: 13, 0x19: 5, 0x1A: 9, 0x1B: 9, 0x1C: 9, 0x1D: 7, 0x1E: 11, 0x1F: 11, 0x20: 3,
       0x21: 3, 0x22: 1, 0x23: 5, 0x24: 1, 0x25: 5, 0x26: 6, 0x29: 14, 0x2B: 17, 0x2D: 7, 0x30: 13,
       0x31: 13, 0x32: 8, 0x33: 8, 0x37: 14, 0x38: 6, 0x47: 9, 0x48: 1}


def frames(path):
    for line in open(path):
        line = line.strip()
        if line:
            yield bytes.fromhex(line[: len(line) // 2 * 2])


def sequence(path):
    out, prev, n = [], None, 0
    for f in frames(path):
        key = f.hex()
        if key == prev:
            n += 1
            continue
        if prev:
            out.append((prev, n))
        prev, n = key, 1
    out.append((prev, n))
    return out


def programs(path):
    """(nome, codigo) de cada envio de uma captura, sem repetir reenvios identicos."""
    nome, vistos = '?', set()
    for f in frames(path):
        if f[2] != 0x04:
            continue
        ln = f[3] | f[4] << 8
        if f[5] == 0x01:
            nome = f[9:9 + ln - 4].decode('ascii', 'replace')
        elif f[5] == 0x02:
            code = f[8:8 + ln - 3]
            if (nome, code) not in vistos:
                vistos.add((nome, code))
                yield nome, code


def be(b): return int.from_bytes(b, 'big')
def flt(b): return struct.unpack('<f', b)[0]
def r(b): return f'r{be(b):#04x}'


def descrever(op, b):
    if op == 0x48: return 'inicio de bloco'
    if op == 0x01: return f'{r(b[1:5])} = byte {b[5]}'
    if op == 0x02: return f'{r(b[1:5])} = {flt(b[5:9])!r}  (int {int.from_bytes(b[5:9], "little")})'
    if op == 0x03: return f'{r(b[1:5])} = {r(b[5:9])}  (copia byte)'
    if op == 0x04: return f'{r(b[1:5])} = {r(b[5:9])}  (copia float)'
    if op == 0x08: return f'{r(b[1:5])} = float(byte {r(b[5:9])})'
    if op in (0x09, 0x0A, 0x0B, 0x0C): return f'{r(b[1:5])} = {r(b[5:9])} {"+-*/"[op - 9]} {r(b[9:13])}'
    if op == 0x0D: return f'funcao {b[1]:#04x}: {r(b[2:6])} <- {r(b[6:10])}'
    if op == 0x10: return f'compara (tipo {b[1]}): {r(b[2:6])} = {r(b[6:10])} ? {r(b[10:14])}'
    if op == 0x11: return f'{r(b[1:5])} = cor {r(b[5:9])} esta na mascara {r(b[9:13])}'
    if op in (0x1A, 0x1B): return f'salta para {be(b[1:5])} se {r(b[5:9])} {"!= 0" if op == 0x1A else "== 0"}'
    if op == 0x1D: return f'inicia a thread {b[5]} em {be(b[1:5])}'
    if op in (0x1E, 0x1F): return f'inicia a thread {b[9]} em {be(b[1:5])} se {r(b[5:9])} {"verdadeiro" if op == 0x1E else "falso"}'
    if op == 0x20: return f'espera a thread {b[1]}'
    if op == 0x21: return f'fim da thread {b[1]}'
    if op == 0x23: return f'espera os segundos de {r(b[1:5])}'
    if op == 0x24: return 'fim do programa principal'
    if op == 0x29: return f'compara bytes (tipo {b[1]}): {r(b[2:6])} = {r(b[6:10])} ? {r(b[10:14])}'
    if op == 0x2B: return f'compara (tipo em {r(b[1:5])}): {r(b[5:9])} = {r(b[9:13])} ? {r(b[13:17])}'
    if op == 0x2D: return f'{r(b[1:5])} = {int.from_bytes(b[5:7], "little"):#06x} (16 bits)'
    if op in (0x30, 0x31):
        return (f'{"le" if op == 0x30 else "escreve"} dispositivo: porta {r(b[2:6])} tipo {b[6]:#04x} '
                f'modo {b[7]} {b[8]} bytes em {r(b[9:13])}')
    if op == 0x33: return f'escreve interno: tipo {b[1]} modo {b[2]} {b[3]} bytes em {r(b[4:8])}'
    if op == 0x47: return f'texto[{be(b[1:5]):#06x}] = numero {r(b[5:9])}'
    return ''


def disasm(code):
    i = 0
    while i < len(code):
        op = code[i]
        if op == 0x2F and i + 6 <= len(code):                       # texto: 2F endereco tamanho bytes
            tam = code[i + 5]
            b = code[i:i + 6 + tam]
            txt = b[6:].rstrip(b'\x00').decode('latin-1')
            print(f'  {i:4d}: {b.hex(" "):42s} texto[{be(b[1:5]):#06x}] = {txt!r}')
            i += 6 + tam
            continue
        n = TAM.get(op)
        if n is None or i + n > len(code):
            print(f'  {i:4d}: ?? {code[i:].hex(" ")}')
            return
        b = code[i:i + n]
        print(f'  {i:4d}: {b.hex(" "):42s} {descrever(op, b)}')
        i += n


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    if path.endswith('.py'):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from enviar import carregar
        from estc import compilar
        code = compilar(carregar(path))
        print(f'== {path} compilado ({len(code)} bytes)')
        disasm(code)
        return
    if path.endswith('.hex'):
        code = bytes.fromhex(open(path).read().strip())
        print(f'== {path} ({len(code)} bytes)')
        disasm(code)
        return
    print('== sequencia de pacotes (repeticoes colapsadas)')
    for h, n in sequence(path):
        f = bytes.fromhex(h)
        tag = {0x01: 'heartbeat', 0x02: 'consulta', 0x04: 'arquivo', 0x0A: 'executar', 0x0C: 'download'}.get(f[2], '?')
        print(f'  x{n:<4d} cmd={f[2]:#04x} {tag:10s} {h[:90]}{"..." if len(h) > 90 else ""}')
    for nome, code in programs(path):
        print(f'\n== programa {nome} ({len(code)} bytes)')
        disasm(code)


if __name__ == '__main__':
    main()
