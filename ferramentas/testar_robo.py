"""Testa a conexão com o robô: ele acende a luz, apita e escreve "Funcionou!" na tela.
Uso: python ferramentas/testar_robo.py   (ou, no VS Code: Terminal > Executar Tarefa > Testar conexão com o robô)
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    try:
        import pywinusb.hid  # noqa: F401
    except ImportError:
        sys.exit('ERRO: falta instalar o pywinusb. Rode o instalar.bat ou: pip install pywinusb')

    import robo
    from estc import compilar
    from est_protocol import find_robot, upload

    print('Procurando o robô no USB...')
    try:
        find_robot()
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    print('Robô encontrado. Enviando o teste...\n')

    robo.novo_programa()
    robo.luz('verde')
    robo.bip()
    robo.mostrar('Funcionou!', x=10, y=50)
    robo.esperar(3)
    robo.apagar_luz()
    try:
        upload(compilar(robo.programa()), prog_path='/vscode/teste', verbose=False)
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    print('Pronto! O robô deve ter apitado, acendido a luz e escrito "Funcionou!" na tela.')


if __name__ == '__main__':
    main()
