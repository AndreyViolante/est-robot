"""Mostra, instrucao por instrucao, o bytecode de um programa do robo EST.

Uso:
  python ferramentas/decodificar.py exemplos/seguidor_proporcional.py   o que o estc.py gera
  python ferramentas/decodificar.py gabaritos/t5_loop_cont.hex          um gabarito salvo
  python ferramentas/decodificar.py order_content.txt                   uma captura da IDE EST
"""
import sys, struct

LEN = {0x01: 6, 0x02: 9, 0x03: 9, 0x04: 9, 0x07: 9, 0x08: 9, 0x09: 13, 0x0A: 13, 0x0B: 13,
       0x0C: 13, 0x0E: 13, 0x0F: 9, 0x1D: 7, 0x2D: 7, 0x10: 14, 0x11: 13, 0x12: 13, 0x13: 9, 0x14: 13,
       0x15: 13, 0x16: 13, 0x17: 9, 0x18: 13, 0x19: 5, 0x1A: 9, 0x1B: 9, 0x1C: 9,
       0x1E: 11, 0x1F: 11, 0x20: 3, 0x21: 3, 0x22: 1, 0x23: 5, 0x24: 1, 0x25: 5, 0x26: 6,
       0x30: 13, 0x31: 13, 0x32: 8, 0x33: 8, 0x37: 14, 0x38: 6, 0x48: 1}


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
    """(nome, codigo) de cada envio, sem repetir reenvios identicos."""
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


def disasm(code):
    i = 0
    while i < len(code):
        op = code[i]
        n = LEN.get(op)
        if n is None or i + n > len(code):
            print(f'  {i:4d}: ?? {code[i:].hex(" ")}')
            return
        b = code[i:i + n]
        d = ''
        if op == 0x48: d = 'marcador de modulo'
        elif op == 0x01: d = f'r{be(b[1:5]):#04x} = byte {b[5]}'
        elif op == 0x02: d = f'r{be(b[1:5]):#04x} = {flt(b[5:9])!r}  (int {int.from_bytes(b[5:9],"little")})'
        elif op in (0x30, 0x31): d = (f'{"LER" if op == 0x30 else "ESCREVER"} disp: v1={b[1]} porta=r{be(b[2:6]):#04x} '
                                      f'tipo={b[6]:#04x} modo={b[7]} tam={b[8]} dados=r{be(b[9:13]):#04x}')
        elif op in (0x11, 0x12, 0x14, 0x15, 0x16, 0x18):
            d = f'r{be(b[1:5]):#04x} = r{be(b[5:9]):#04x} op{op:#04x} r{be(b[9:13]):#04x}'
        elif op in (0x1E, 0x1F): d = f'salta pc={be(b[1:5])} se r{be(b[5:9]):#04x}  ({b[9]},{b[10]})'
        elif op == 0x19: d = f'jump pc={be(b[1:5])}'
        elif op == 0x2D: d = f'r{be(b[1:5]):#04x} = u16 {int.from_bytes(b[5:7], "little"):#06x}'
        elif op == 0x1D: d = f'inicia thread {b[5]} em pc={be(b[1:5])}  ({b[6]})'
        elif op in (0x20, 0x21): d = f'{"espera" if op == 0x20 else "fim da"} thread {b[1]}'
        elif op == 0x24: d = 'fim'
        elif op == 0x04: d = f'r{be(b[1:5]):#04x} = r{be(b[5:9]):#04x}  (copia float)'
        elif op in (0x09, 0x0A, 0x0B, 0x0C):
            d = f'r{be(b[1:5]):#04x} = r{be(b[5:9]):#04x} {"+-*/"[op - 9]} r{be(b[9:13]):#04x}'
        elif op == 0x10: d = f'cmp tipo={b[1]}: r{be(b[2:6]):#04x} = r{be(b[6:10]):#04x} ? r{be(b[10:14]):#04x}'
        elif op in (0x1A, 0x1B, 0x1C): d = f'salta{"!=0" if op == 0x1A else "==0" if op == 0x1B else "?"} pc={be(b[1:5])} r{be(b[5:9]):#04x}'
        elif op == 0x23: d = f'espera segundos em r{be(b[1:5]):#04x}'
        print(f'  {i:4d}: {b.hex(" "):42s} {d}')
        i += n


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    if path.endswith('.py'):
        import os
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
        tag = {0x01: 'HEARTBEAT', 0x02: 'STATUS?', 0x04: 'ARQUIVO', 0x0A: 'SELECT/RUN', 0x0C: 'DOWNLOAD'}.get(f[2], '?')
        print(f'  x{n:<4d} cmd={f[2]:#04x} {tag:10s} {h[:90]}{"..." if len(h) > 90 else ""}')
    for nome, code in programs(path):
        print(f'\n== programa {nome} ({len(code)} bytes)')
        disasm(code)


if __name__ == '__main__':
    main()
