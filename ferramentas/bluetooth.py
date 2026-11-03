"""Bluetooth do robô pelo computador (Windows): confere, no laboratório, o caminho que a página de programar usa pelo
Bluetooth do celular. Só faz perguntas: não grava, não apaga e não roda nada no robô.

Antes: ligue o Bluetooth do robô e pareie nas Configurações do Windows (Bluetooth e dispositivos; a senha costuma
ser 1234). Feche a IDE EST e a página de programar, que podem estar conectadas ao robô.
Uso:
  python ferramentas/bluetooth.py                        lista os pareados e testa o que parecer o robô
  python ferramentas/bluetooth.py --listar               só lista os aparelhos pareados (nome e endereço)
  python ferramentas/bluetooth.py --testar 00:1A:7D:DA:71:13
                                                         conecta e pergunta o firmware, as portas e a bateria
  python ferramentas/bluetooth.py --escutar 00:1A:7D:DA:71:13 30
                                                         mostra tudo o que o robô mandar em 30 segundos
No VS Code: Terminal > Executar Tarefa > "Testar o Bluetooth do robô".

O --escutar serve para descobrir como chegam as mensagens: com ele rodando, ligue no robô um programa que manda
mensagens (enviar_mensagem('teste', 1), que vai para o nome EST-LAB, o nome com que esta ferramenta se apresenta).
"""
import os, re, socket, subprocess, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import est_protocol as P
from enviar import TIPOS

CANAL = 1                                        # a IDE conecta no canal 1 do Bluetooth do robô
# como a IDE se apresenta logo depois de conectar: nome e os 12 dígitos do endereço de quem conecta, e \r\n
# (a página de programar manda a mesma linha)
APRESENTACAO = b'EST-LAB000000000000\r\n'


def pareados():
    """[(nome, 'AA:BB:CC:DD:EE:FF')] dos aparelhos Bluetooth pareados com o Windows."""
    comando = ['powershell', '-NoProfile', '-Command',
               "Get-PnpDevice -Class Bluetooth | ForEach-Object { $_.FriendlyName + '|' + $_.InstanceId }"]
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    achados = {}
    for linha in saida.splitlines():
        nome, _, instancia = linha.partition('|')
        m = re.search(r'DEV_([0-9A-F]{12})', instancia, re.I)
        if m:
            mac = ':'.join(m.group(1)[i:i + 2] for i in range(0, 12, 2)).upper()
            achados.setdefault(mac, nome.strip() or '(sem nome)')
    return [(nome, mac) for mac, nome in achados.items()]


def pacote_em(dados, i):
    """Tamanho do pacote inteiro e válido (68 .. tamanho .. soma 16) que começa em i, ou 0."""
    if dados[i] != 0x68 or len(dados) - i < 5:
        return 0
    total = 7 + int.from_bytes(dados[i + 3:i + 5], 'little')
    if len(dados) - i < total:
        return 0
    fim = i + total
    return total if dados[fim - 1] == 0x16 and P.checksum(dados[i:fim - 2]) == dados[fim - 2] else 0


class Canal:
    """A conversa com o robô pelo Bluetooth: manda pacotes e junta o que chega em pacotes inteiros."""

    def __init__(self, endereco, espera=10):
        if not hasattr(socket, 'AF_BLUETOOTH'):
            sys.exit('Este Python não tem Bluetooth: use o Python 3.9 ou mais novo, no Windows.')
        self.s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.s.settimeout(espera)
        self.s.connect((endereco, CANAL))
        self.bruto = b''

    def mandar(self, pacote):
        self.s.sendall(pacote)

    def ler(self, segundos):
        """O que chegar em alguns segundos: (pacotes inteiros, bytes soltos que não formaram pacote)."""
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            self.s.settimeout(max(0.05, fim - time.monotonic()))
            try:
                dados = self.s.recv(1024)
            except socket.timeout:
                break
            if not dados:
                raise ConnectionError('o robô fechou a conexão')
            self.bruto += dados
        pacotes, soltos, i = [], b'', 0
        while i < len(self.bruto):
            n = pacote_em(self.bruto, i)
            if n:
                pacotes.append(self.bruto[i:i + n])
                i += n
            else:
                soltos += self.bruto[i:i + 1]
                i += 1
        self.bruto = b''
        return pacotes, soltos

    def perguntar(self, pacote, segundos=0.8):
        self.mandar(pacote)
        return self.ler(segundos)

    def fechar(self):
        self.s.close()


def descrever(pacote):
    """Um pacote do robô em texto: comando e dados (com o texto legível, se tiver)."""
    cmd, dados = pacote[2], pacote[5:-2]
    texto = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dados)
    return f'68 {pacote[1]:02X} cmd {cmd:02X}  {dados.hex(" ")}  |{texto}|'


def testar(endereco):
    print(f'Conectando a {endereco}, canal {CANAL}...')
    try:
        c = Canal(endereco)
    except OSError as e:
        print(f'NÃO CONECTOU: {e}')
        print('Confira se o robô está ligado, perto, com o Bluetooth ligado e pareado, e se a IDE EST e a página de '
              'programar estão fechadas (só um aparelho conecta por vez).')
        return False
    ok = {}
    try:
        print('Conectou. Mandando a linha de apresentação (como a IDE)...')
        pacotes, soltos = c.perguntar(APRESENTACAO, 1.5)
        print(f'  resposta: {len(pacotes)} pacote(s)' + (f', bytes soltos: {soltos.hex(" ")}' if soltos else ''))
        for p in pacotes:
            print('   ', descrever(p))
        pacotes, _ = c.perguntar(P.HEARTBEAT)
        firmware = next((p[5:-2].rstrip(b'\x00').decode('ascii', 'replace') for p in pacotes if p[2] == 0x01), None)
        ok['firmware'] = firmware
        print(f'Firmware: {firmware or "sem resposta"}')
        pacotes, _ = c.perguntar(P.CONSULTA_ESTADO)
        portas = next((P.ler_portas(p) for p in pacotes if p[2] == 0x02), None)
        ok['portas'] = portas
        print('Portas: ' + (', '.join(f'{k} = {TIPOS.get(v, f"tipo {v}")}' for k, v in sorted(portas.items()))
                            if portas else 'sem resposta' if portas is None else 'nada ligado'))
        pacotes, _ = c.perguntar(P.INFO_ROBO)
        info = next((P.ler_info(p) for p in pacotes if p[2] == 0x0C), None)
        ok['bateria'] = info
        print(f'Bateria: {f"{info[0]} de 4" if info else "sem resposta"}')
    except (OSError, ConnectionError) as e:
        print(f'A conexão caiu: {e}')
    finally:
        c.fechar()
    funcionou = any(v is not None for v in ok.values())
    print('\nRESULTADO: ' + ('o robô respondeu pelo Bluetooth. O envio pela página de programar deve funcionar.'
                             if funcionou else 'conectou, mas o robô não respondeu às perguntas.'))
    return funcionou


def escutar(endereco, segundos):
    print(f'Conectando a {endereco}...')
    c = Canal(endereco)
    try:
        c.mandar(APRESENTACAO)
        print(f'Conectou. Mostrando tudo o que o robô mandar por {segundos} s (Ctrl+C para parar)...')
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            pacotes, soltos = c.ler(min(1.0, fim - time.monotonic()))
            for p in pacotes:
                print(f'{time.strftime("%H:%M:%S")}  {descrever(p)}')
            if soltos:
                print(f'{time.strftime("%H:%M:%S")}  bytes soltos: {soltos.hex(" ")}  |{soltos.decode("latin-1")!r}|')
    except KeyboardInterrupt:
        pass
    finally:
        c.fechar()


def main():
    args = sys.argv[1:]
    if args[:1] == ['--testar'] and len(args) >= 2:
        sys.exit(0 if testar(args[1].upper()) else 1)
    if args[:1] == ['--escutar'] and len(args) >= 2:
        escutar(args[1].upper(), float(args[2]) if len(args) > 2 else 30)
        return
    lista = pareados()
    if not lista:
        print('Nenhum aparelho Bluetooth pareado com este computador. Ligue o Bluetooth do robô e pareie nas '
              'Configurações do Windows (Bluetooth e dispositivos; a senha costuma ser 1234).')
        sys.exit(1)
    print('Aparelhos Bluetooth pareados:')
    for nome, mac in lista:
        print(f'  {mac}  {nome}')
    if args[:1] == ['--listar']:
        return
    robo = [x for x in lista if re.search(r'est|robo|robot|brick', x[0], re.I)]
    if len(robo) != 1:
        print('\nNão sei qual deles é o robô. Rode de novo com o endereço dele:')
        print('  python ferramentas/bluetooth.py --testar ENDERECO')
        sys.exit(1)
    print(f'\nTestando {robo[0][0]} ({robo[0][1]}):')
    sys.exit(0 if testar(robo[0][1]) else 1)


if __name__ == '__main__':
    main()
