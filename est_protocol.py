"""
Protocolo HID do robo EST.
Monta os pacotes, envia e le as respostas via USB HID.
"""
import struct, ctypes, ctypes.wintypes as wt, time

VID, PID = 0x0483, 0x5750
REPORT_SIZE = 1025   # 1 byte report-ID + 1024 bytes payload

# ── Estruturas Win32 ──────────────────────────────────────────────────────────

k32 = ctypes.WinDLL('kernel32.dll')

class OVERLAPPED(ctypes.Structure):
    """Estrutura OVERLAPPED para I/O assincrono no Windows (32 e 64-bit)."""
    _fields_ = [
        ('Internal',     ctypes.c_size_t),   # ULONG_PTR (4 ou 8 bytes)
        ('InternalHigh', ctypes.c_size_t),
        ('Offset',       wt.DWORD),
        ('OffsetHigh',   wt.DWORD),
        ('hEvent',       wt.HANDLE),
    ]

# ── Checksum e frame ──────────────────────────────────────────────────────────

def checksum(data: bytes) -> int:
    return sum(data) & 0xFF

def frame(cmd: int, payload: bytes) -> bytes:
    body = bytes([0x68, 0x11, cmd]) + payload
    return body + bytes([checksum(body), 0x16])

# ── Pacotes do protocolo ──────────────────────────────────────────────────────

HEARTBEAT = frame(0x01, b'\x00\x00')
DOWNLOAD  = frame(0x0C, b'\x01\x00\x01')

def pkt_select(path: str) -> bytes:
    path_b = path.encode('ascii')
    inner_len = 1 + len(path_b)
    payload = inner_len.to_bytes(2, 'little') + b'\x02' + path_b
    return frame(0x0A, payload)

def pkt_filename(filepath: str) -> bytes:
    path_b = filepath.encode('ascii')
    # O byte na posicao 8 e o comprimento do diretorio (ate a ultima barra inclusive)
    # Ex: '/project1/program1.dbf' -> dir='/project1/' -> len=10=0x0A
    last_slash = filepath.rfind('/') + 1   # inclui a barra
    inner = b'\x01\x00' + bytes([last_slash]) + path_b
    payload = (len(inner) + 1).to_bytes(2, 'little') + b'\x01' + inner
    return frame(0x04, payload)

def pkt_data(data: bytes) -> bytes:
    inner = b'\x01\x00' + data
    payload = (len(inner) + 1).to_bytes(2, 'little') + b'\x02' + inner
    return frame(0x04, payload)

def build_upload_sequence(program_data: bytes,
                          prog_path: str = '/project1/CLAUDE') -> list:
    dbf_path = prog_path + '.dbf'
    return [
        (pkt_select(prog_path),  "SELECT PROGRAM",  0.15),
        (HEARTBEAT,              "HEARTBEAT",        0.15),
        (DOWNLOAD,               "DOWNLOAD trigger", 0.30),
        (pkt_filename(dbf_path), "SEND FILENAME",    0.15),
        (pkt_data(program_data), "SEND DATA",        0.30),
        (HEARTBEAT,              "HEARTBEAT",        0.15),
        (DOWNLOAD,               "DOWNLOAD confirm", 0.20),
    ]

# ── HID via WinAPI (modo assincrono) ─────────────────────────────────────────

GENERIC_READ     = 0x80000000
GENERIC_WRITE    = 0x40000000
FILE_SHARE_RW    = 0x03
OPEN_EXISTING    = 3
FILE_FLAG_OVERLAPPED = 0x40000000
ERROR_IO_PENDING = 997
WAIT_OBJECT_0    = 0
WAIT_TIMEOUT     = 0x102

def find_robot():
    try:
        import pywinusb.hid as hid_lib
        devs = hid_lib.HidDeviceFilter(vendor_id=VID, product_id=PID).get_devices()
        if devs:
            return devs[0].device_path
    except ImportError:
        pass
    raise RuntimeError("Robo nao encontrado! Instala pywinusb: pip install pywinusb")

def open_device(path: str):
    h = k32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_RW,
        None,
        OPEN_EXISTING,
        FILE_FLAG_OVERLAPPED,
        None,
    )
    if h == -1 or h == ctypes.c_void_p(-1).value:
        raise RuntimeError(
            f"Nao abriu HID (erro {k32.GetLastError()}). "
            "Tente rodar como Administrador.")
    return h

def _make_overlapped() -> tuple:
    """Cria OVERLAPPED com evento manual-reset. Retorna (ov, evt)."""
    evt = k32.CreateEventW(None, True, False, None)
    ov  = OVERLAPPED()
    ov.hEvent = evt
    return ov, evt

def send_report(handle, data: bytes):
    """Envia Output Report HID (1025 bytes). Aguarda conclusao."""
    buf = bytearray(REPORT_SIZE)
    buf[0] = 0x00
    buf[1:1+len(data)] = data[:REPORT_SIZE-1]
    buf_c = (ctypes.c_ubyte * REPORT_SIZE)(*buf)

    ov, evt = _make_overlapped()
    ok  = k32.WriteFile(handle, buf_c, REPORT_SIZE, None, ctypes.byref(ov))
    err = k32.GetLastError()

    if not ok and err != ERROR_IO_PENDING:
        k32.CloseHandle(evt)
        raise RuntimeError(f"WriteFile falhou: {err}")

    k32.WaitForSingleObject(evt, 2000)
    k32.CloseHandle(evt)

def read_response(handle, timeout_ms: int = 400) -> bytes | None:
    """
    Le um Input Report HID do robo com timeout.
    Retorna os bytes (sem zeros finais) ou None se nao chegou nada.
    """
    buf_c = (ctypes.c_ubyte * REPORT_SIZE)()
    ov, evt = _make_overlapped()

    ok  = k32.ReadFile(handle, buf_c, REPORT_SIZE, None, ctypes.byref(ov))
    err = k32.GetLastError()

    if not ok and err != ERROR_IO_PENDING:
        k32.CloseHandle(evt)
        return None

    ret = k32.WaitForSingleObject(evt, timeout_ms)
    k32.CloseHandle(evt)

    if ret != WAIT_OBJECT_0:
        k32.CancelIo(handle)
        return None

    data = bytes(buf_c)
    j = len(data) - 1
    while j > 0 and data[j] == 0:
        j -= 1
    return data[:j+1] if j > 0 else None


def upload(program_data: bytes,
           prog_path: str = '/project1/CLAUDE',
           verbose: bool = True):
    """
    Envia programa compilado ao robô, lendo o ACK do robo entre cada pacote.
    """
    if verbose:
        print("[*] Conectando ao robo...")

    device_path = find_robot()
    handle = open_device(device_path)

    if verbose:
        print(f"[OK] Robo encontrado")
        print(f"[OK] Programa: {len(program_data)} bytes")
        print()

    sequence = build_upload_sequence(program_data, prog_path)

    try:
        for pkt, name, delay in sequence:
            send_report(handle, pkt)
            preview = pkt[:8].hex().upper()

            resp = read_response(handle, timeout_ms=int(delay * 1000) + 300)

            if verbose:
                if resp:
                    resp_hex = resp[:8].hex().upper()
                    print(f"  -> {name:25s}  tx={preview}...  rx={resp_hex}")
                else:
                    print(f"  -> {name:25s}  tx={preview}...  rx=(sem resposta)")

        if verbose:
            print()
            print("[OK] Upload concluido!")

    finally:
        k32.CloseHandle(handle)
