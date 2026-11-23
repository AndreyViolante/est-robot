"""Cifra os extras do simulador com um código que só você sabe: o arquivo cifrado (simulador/extras.dat) vai para
o site, e o original fica fora do repositório (a pasta meus_programas não vai para o GitHub).

No simulador, abra o endereço com #codigo no fim (ex.: .../simulador/#codigo), digite o código e os extras
aparecem. Com "Lembrar neste computador", abrem sozinhos da próxima vez naquele navegador.

Uso:  python ferramentas/cifrar_extras.py [arquivo.js]     (padrão: meus_programas/extras/extras.js)
Precisa do node. O código não aparece na tela e não fica gravado em lugar nenhum: guarde-o bem, sem ele o arquivo
não abre (para trocar o código, rode de novo).
"""
import getpass, json, os, subprocess, sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PADRAO = os.path.join(RAIZ, 'meus_programas', 'extras', 'extras.js')
SAIDA = os.path.join(RAIZ, 'simulador', 'extras.dat')


def main():
    entrada = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    if not os.path.isfile(entrada):
        sys.exit(f'Não achei {entrada}')
    if not os.path.relpath(entrada, RAIZ).startswith('meus_programas'):
        print('Aviso: o original não está em meus_programas/ e pode acabar indo para o GitHub sem cifrar.')
    codigo = getpass.getpass('Código (não aparece enquanto digita): ')
    if len(codigo) < 6:
        sys.exit('Use um código com pelo menos 6 letras ou números.')
    if getpass.getpass('Digite o código de novo: ') != codigo:
        sys.exit('Os dois códigos não são iguais. Nada foi cifrado.')
    pedido = json.dumps({'codigo': codigo, 'entrada': entrada, 'saida': SAIDA})
    r = subprocess.run(['node', os.path.join(RAIZ, 'ferramentas', 'cifrar_extras.js')], input=pedido, text=True,
                       encoding='utf-8')
    if r.returncode:
        sys.exit('Não deu para cifrar (o node está instalado?).')
    print('Agora publique o site (python ferramentas/publicar_simulador.py e publicar_programar.py) e envie para o GitHub.')


if __name__ == '__main__':
    main()
