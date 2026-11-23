"""Cifra os extras do simulador com um código que só você sabe: o arquivo cifrado (simulador/extras.dat) vai para
o site, e o original fica fora do repositório (a pasta meus_programas não vai para o GitHub).

No simulador, abra o endereço com #codigo no fim (ex.: .../simulador/#codigo), digite o código e os extras
aparecem. Com "Lembrar neste computador", abrem sozinhos da próxima vez naquele navegador.

Uso:  python ferramentas/cifrar_extras.py [arquivo.js]     (padrão: meus_programas/extras/extras.js)
Precisa do node. O código (pelo menos 6 letras ou números; se for fácil de chutar, ela avisa) não aparece na tela
e não fica gravado em lugar nenhum: guarde-o bem, sem ele o arquivo não abre (para trocar o código, rode de novo).
Rode numa janela do PowerShell do Windows: em alguns terminais embutidos o que se digita não chega ao campo escondido.
"""
import getpass, json, os, subprocess, sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PADRAO = os.path.join(RAIZ, 'meus_programas', 'extras', 'extras.js')
SAIDA = os.path.join(RAIZ, 'simulador', 'extras.dat')
MINIMO = 6
COMUNS = {'senha123', 'password', 'qwertyui', 'robotica', 'robotica1', 'est-robot', 'estrobot', 'obr2026'}


def facil_demais(codigo):
    """Um aluno chutaria: tudo igual (aaaaaaaa), sequência (12345678, abcdefgh) ou uma senha comum."""
    c = codigo.lower()
    if len(set(c)) == 1 or c in COMUNS:
        return True
    passos = {ord(b) - ord(a) for a, b in zip(c, c[1:])}
    return passos in ({1}, {-1})


def pedir_codigo(tentativas=3):
    for _ in range(tentativas):
        codigo = getpass.getpass('Código (não aparece enquanto digita, Enter no fim): ')
        if len(codigo) < MINIMO:
            print(f'Muito curto: use pelo menos {MINIMO} letras ou números. Tente de novo.')
        elif facil_demais(codigo) and input('Esse código é fácil de chutar (um aluno pode tentar). Usar mesmo assim? '
                                            '(s/n) ').strip().lower() not in ('s', 'sim'):
            print('Então escolha outro.')
        elif getpass.getpass('Digite o mesmo código de novo: ') != codigo:
            print('Os dois não são iguais. Tente de novo.')
        else:
            return codigo
    sys.exit('Nada foi cifrado. Rode de novo quando quiser.')


def main():
    entrada = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    if not os.path.isfile(entrada):
        sys.exit(f'Não achei {entrada}')
    if not os.path.relpath(entrada, RAIZ).startswith('meus_programas'):
        print('Aviso: o original não está em meus_programas/ e pode acabar indo para o GitHub sem cifrar.')
    codigo = pedir_codigo()
    pedido = json.dumps({'codigo': codigo, 'entrada': entrada, 'saida': SAIDA})
    r = subprocess.run(['node', os.path.join(RAIZ, 'ferramentas', 'cifrar_extras.js')], input=pedido, text=True,
                       encoding='utf-8')
    if r.returncode:
        sys.exit('Não deu para cifrar (o node está instalado?).')
    print('Agora publique o site (python ferramentas/publicar_simulador.py e publicar_programar.py) e envie para o GitHub.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('\nCancelado. Nada foi cifrado.')
