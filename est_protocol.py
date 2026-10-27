"""
Protocolo HID do robo EST.
Monta os pacotes, envia e le as respostas via USB HID.
"""
import re, struct, ctypes, ctypes.wintypes as wt, time

VID, PID = 0x0483, 0x5750
REPORT_SIZE = 1025   # 1 byte report-ID + 1024 bytes payload
PEDACO = REPORT_SIZE - 1 - 10   # bytes de programa por pacote (o pacote tem mais 10 bytes)

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

def _pkt_0a(sub: int, path: str) -> bytes:
    path_b = path.encode('ascii')
    payload = (1 + len(path_b)).to_bytes(2, 'little') + bytes([sub]) + path_b
    return frame(0x0A, payload)

def pkt_select(path: str) -> bytes:
    return _pkt_0a(0x02, path)

def pkt_run(dbf_path: str) -> bytes:
    """Executa o programa gravado. A IDE manda isto logo apos os dados (capturas 2026-10-13)."""
    return _pkt_0a(0x01, dbf_path)

def pkt_filename(filepath: str) -> bytes:
    path_b = filepath.encode('ascii')
    # O byte na posicao 8 e o comprimento do diretorio (ate a ultima barra inclusive)
    # Ex: '/project1/program1.dbf' -> dir='/project1/' -> len=10=0x0A
    last_slash = filepath.rfind('/') + 1   # inclui a barra
    inner = b'\x01\x00' + bytes([last_slash]) + path_b
    payload = (len(inner) + 1).to_bytes(2, 'little') + b'\x01' + inner
    return frame(0x04, payload)

def pkt_data(data: bytes, total: int = 1, indice: int = 0) -> bytes:
    inner = bytes([total, indice]) + data
    payload = (len(inner) + 1).to_bytes(2, 'little') + b'\x02' + inner
    return frame(0x04, payload)

def pacotes_de_dados(data: bytes) -> list:
    """Programa maior que um pacote vai em pedaços de 1014 bytes, cada um com o total de pedaços
    e o seu número (0, 1, ...). Visto no envio do BrickPID_v6 pela IDE: 8762 bytes em 9 pedaços."""
    pedacos = [data[i:i + PEDACO] for i in range(0, len(data), PEDACO)] or [b'']
    if len(pedacos) > 255:
        raise RuntimeError(f'programa grande demais ({len(data)} bytes)')
    return [pkt_data(p, len(pedacos), i) for i, p in enumerate(pedacos)]

def build_upload_sequence(program_data: bytes,
                          prog_path: str = '/vscode/programa', executar: bool = True) -> list:
    dbf_path = prog_path + '.dbf'
    dados = pacotes_de_dados(program_data)
    nomes = ["SEND DATA"] if len(dados) == 1 else [f"SEND DATA {i + 1}/{len(dados)}" for i in range(len(dados))]
    return [
        (pkt_select(prog_path),  "SELECT PROGRAM",  0.15),
        (HEARTBEAT,              "HEARTBEAT",        0.15),
        (DOWNLOAD,               "DOWNLOAD trigger", 0.30),
        (pkt_filename(dbf_path), "SEND FILENAME",    0.15),
        *[(pkt, nome, 0.30) for pkt, nome in zip(dados, nomes)],
        (HEARTBEAT,              "HEARTBEAT",        0.15),
        (DOWNLOAD,               "DOWNLOAD confirm", 0.20),
    ] + ([(pkt_run(dbf_path),    "RUN",              0.20)] if executar else [])

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
    except ImportError:
        raise RuntimeError("Falta o pywinusb: pip install pywinusb") from None
    devs = hid_lib.HidDeviceFilter(vendor_id=VID, product_id=PID).get_devices()
    if not devs:
        raise RuntimeError("Robo nao encontrado no USB: confira se o cabo esta ligado e o robo esta ligado.")
    return devs[0].device_path

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
    if len(data) > REPORT_SIZE - 1:
        raise RuntimeError(f'pacote de {len(data)} bytes nao cabe num report HID')
    buf = bytearray(REPORT_SIZE)
    buf[0] = 0x00
    buf[1:1+len(data)] = data
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


CONSULTA_ESTADO = frame(0x02, b'\x01\x00\x00')      # a IDE manda isto sem parar
NOMES_PORTAS = ['1', '2', '3', '4', 'A', 'B', 'C', 'D']


def ler_portas(resposta: bytes) -> dict | None:
    """Resposta da consulta de estado -> {porta: tipo} só das portas com algo ligado.
    Visto no robô (22/10): 8 grupos [00, porta, tipo, ?] (porta 1-4 sensores, 5-8 = A-D; porta 0 = nada).
    Tipos vistos: 1 = sensor de cor, 4 = motor. Ex.: {'1': 1, '2': 1, 'B': 4, 'C': 4}"""
    i = resposta.find(b'\x68\x21\x02')
    if i < 0 or len(resposta) < i + 5 + 33:
        return None
    dados = resposta[i + 5:i + 5 + 33]          # depois de 68 21 02 e do tamanho (2 bytes)
    portas = {}
    for k in range(8):
        _, porta, tipo, _ = dados[1 + 4 * k:5 + 4 * k]
        if 1 <= porta <= 8:
            portas[NOMES_PORTAS[porta - 1]] = tipo
    return portas


def portas_ligadas(timeout_ms: int = 400) -> dict | None:
    """Pergunta ao robô o que está ligado em cada porta. None se não der para saber."""
    try:
        handle = open_device(find_robot())
    except RuntimeError:
        return None
    try:
        while read_response(handle, 50):          # descarta respostas velhas
            pass
        for _ in range(3):
            send_report(handle, CONSULTA_ESTADO)
            resposta = read_response(handle, timeout_ms)
            portas = ler_portas(resposta) if resposta else None
            if portas is not None:
                return portas
        return None
    finally:
        k32.CloseHandle(handle)


def upload(program_data: bytes,
           prog_path: str = '/vscode/programa',
           verbose: bool = True, executar: bool = True):
    """
    Envia programa compilado ao robô, lendo o ACK do robo entre cada pacote.
    executar=False só grava: o programa fica no robô para ser iniciado pelo menu dele.
    """
    if verbose:
        print("[*] Conectando ao robo...")

    device_path = find_robot()
    handle = open_device(device_path)

    if verbose:
        print(f"[OK] Robo encontrado")
        print(f"[OK] Programa: {len(program_data)} bytes")
        print()

    sequence = build_upload_sequence(program_data, prog_path, executar)

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


# ── Arquivos gravados e bateria ──────────────────────────────────────────────
# Achados no maintest.exe da IDE (22/10): ao conectar ela manda 01, 0C 01, 09 03 e 03 (ver o
# order_content.txt). O 09 é o comando de arquivos: sub 03 = listar, 02 = apagar, 04 = ler, 01 = copiar.
# Resposta do robô: 68 21 [CMD] [len16] [payload] [soma] 16, igual aos pacotes que vão.

LISTAR_ARQUIVOS = frame(0x09, b'\x01\x00\x03')
INFO_ROBO = DOWNLOAD          # 0C 01: a resposta traz o nível da bateria (o upload já manda este pacote)
NIVEL_FRACO = 1               # 0 ou 1 tracinho de 4: bateria fraca


def _partes(caminho: str) -> tuple:
    """'/pasta/arquivo' -> ('pasta', 'arquivo'). Como a IDE: sempre pasta e arquivo, nunca uma pasta inteira."""
    partes = caminho.split('/')
    if (len(partes) != 3 or partes[0] or not partes[1] or not partes[2] or '..' in partes
            or not all(32 < ord(c) < 127 for c in caminho)):
        raise ValueError(f'caminho inválido: {caminho!r} (use /pasta/arquivo, como aparece na lista)')
    return partes[1], partes[2]


def pkt_apagar(caminho: str) -> bytes:
    """Apaga um arquivo do robô: 09 sub 02 + '/pasta/arquivo' (como a IDE monta no send_deletefile)."""
    pasta, arquivo = _partes(caminho)
    path_b = f'/{pasta}/{arquivo}'.encode('ascii')
    return frame(0x09, (1 + len(path_b)).to_bytes(2, 'little') + b'\x02' + path_b)


def pacotes_resposta(resposta: bytes, cmd: int) -> list:
    """Payloads (o que vem depois do tamanho) dos pacotes 68 21 [cmd] inteiros e com a soma certa."""
    achados, cabeca = [], bytes([0x68, 0x21, cmd])
    i = resposta.find(cabeca)
    while i >= 0:
        fim = i + 5 + int.from_bytes(resposta[i + 3:i + 5], 'little')
        if fim + 2 <= len(resposta) and resposta[fim + 1] == 0x16 and checksum(resposta[i:fim]) == resposta[fim]:
            achados.append(resposta[i + 5:fim])
            i = resposta.find(cabeca, fim + 2)
        else:
            i = resposta.find(cabeca, i + 1)
    return achados


def ler_info(resposta: bytes) -> tuple | None:
    """Resposta do 0C 01 -> (nível da bateria de 0 a 4, texto). O nível é o número de tracinhos da pilha na
    tela de monitor da IDE (figuras dianchi/0..4.png). O texto a IDE só guarda (não se sabe o que é)."""
    for p in pacotes_resposta(resposta, 0x0C):
        if p:
            return p[0], p[1:].split(b'\x00')[0].decode('ascii', 'replace')
    return None


def ler_lista(payload: bytes) -> list:
    """Payload de uma resposta 09 sub 03 -> [(total, número, tamanho, '/pasta/arquivo')].
    Depois do 03 vem cada arquivo: [total] [número, de 1 a total] [tamanho: float de 4 bytes] [/pasta/arquivo] 00."""
    itens, i = [], 1
    while i + 7 <= len(payload):
        fim = payload.find(b'\x00', i + 6)
        if fim < 0:
            fim = len(payload)
        tamanho = struct.unpack('<f', payload[i + 2:i + 6])[0]
        tamanho = int(tamanho) if abs(tamanho) < 2 ** 31 else 0          # (NaN também vira 0)
        itens.append((payload[i], payload[i + 1], tamanho, payload[i + 6:fim].decode('ascii', 'replace')))
        i = fim + 1
    return itens


def _abrir():
    handle = open_device(find_robot())
    while read_response(handle, 50):          # descarta respostas velhas
        pass
    return handle


def info_robo(timeout_ms: int = 600) -> tuple:
    """Pergunta ao robô o nível da bateria: (nível de 0 a 4, texto). RuntimeError se não der."""
    handle = _abrir()
    try:
        for _ in range(3):
            send_report(handle, INFO_ROBO)
            resposta = read_response(handle, timeout_ms)
            info = ler_info(resposta) if resposta else None
            if info is not None:
                return info
    finally:
        k32.CloseHandle(handle)
    raise RuntimeError('o robô não respondeu à pergunta da bateria')


def bateria(timeout_ms: int = 600) -> int | None:
    """Nível da bateria de 0 (vazia) a 4 (cheia), como os tracinhos da IDE. None se não der para saber.
    Bateria fraca (nível <= NIVEL_FRACO) deixa motores e sensores estranhos."""
    try:
        return info_robo(timeout_ms)[0]
    except RuntimeError:
        return None


def listar_arquivos(timeout_ms: int = 1500) -> list:
    """Arquivos gravados no robô, em todas as pastas: [('/vscode/meu_programa.dbf', tamanho), ...].
    RuntimeError se o robô não estiver no USB, não responder ou mandar a lista pela metade."""
    handle = _abrir()
    try:
        send_report(handle, LISTAR_ARQUIVOS)
        arquivos, total, respondeu = {}, 0, False
        while not respondeu or len(arquivos) < total:
            resposta = read_response(handle, timeout_ms)
            if resposta is None:
                break
            for p in pacotes_resposta(resposta, 0x09):
                if p[:1] == b'\x03':
                    respondeu = True
                    for total, n, tamanho, nome in ler_lista(p):
                        arquivos[n] = (nome, tamanho)
    finally:
        k32.CloseHandle(handle)
    if not respondeu:
        raise RuntimeError('o robô não mandou a lista de arquivos')
    if len(arquivos) < total:
        raise RuntimeError(f'a lista de arquivos veio pela metade ({len(arquivos)} de {total}): tente de novo')
    return [arquivos[n] for n in sorted(arquivos)]


def apagar_arquivo(caminho: str, timeout_ms: int = 10000) -> bool:
    """Apaga um arquivo do robô ('/pasta/arquivo', como vem em listar_arquivos). True se o robô disse que
    apagou, False se disse que não. A IDE espera a resposta (09 sub 02 [1 = apagou]) por até 10 s."""
    pacote = pkt_apagar(caminho)
    handle = _abrir()
    try:
        send_report(handle, pacote)
        limite = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < limite:
            for p in pacotes_resposta(read_response(handle, 500) or b'', 0x09):
                if len(p) >= 2 and p[0] == 0x02:
                    return p[1] == 1
    finally:
        k32.CloseHandle(handle)
    raise RuntimeError('o robô não respondeu ao pedido de apagar')


# ── Firmware e memória ───────────────────────────────────────────────────────

CONSULTA_MEMORIA = frame(0x03, b'\x00\x00')     # a IDE chama de send_queryraminfo


def _perguntar(pacote: bytes, cmd: int, timeout_ms: int) -> bytes | None:
    """Manda um pacote e devolve o payload da resposta 68 21 [cmd]. None se o robô não responder."""
    handle = _abrir()
    try:
        for _ in range(3):
            send_report(handle, pacote)
            payloads = pacotes_resposta(read_response(handle, timeout_ms) or b'', cmd)
            if payloads:
                return payloads[0]
    finally:
        k32.CloseHandle(handle)
    return None


def firmware(timeout_ms: int = 600) -> str | None:
    """Versão do firmware da controladora (ex.: '03.04'), pela resposta do heartbeat. None se não der."""
    p = _perguntar(HEARTBEAT, 0x01, timeout_ms)
    if p is None:
        return None
    versao = re.search(rb'\d+\.\d+', p)
    return versao.group().decode() if versao else p.hex(' ')


def memoria_bruta(timeout_ms: int = 600) -> bytes | None:
    """Resposta da consulta de memória: 4 bytes que ainda não foram decifrados (ex.: 80 6e 6c 6e).
    O diagnóstico mostra os bytes para comparar robôs diferentes. None se o robô não responder."""
    return _perguntar(CONSULTA_MEMORIA, 0x03, timeout_ms)
