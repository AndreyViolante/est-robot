"""Mostra na tela do robô a luz refletida dos sensores S1, S2 e S3, sem parar (o robô não se mexe).
Serve para medir o preto e o branco de cada sensor e escrever no calibracao.py.
A controladora não manda as leituras pelo USB: os números aparecem só na tela dela.
Uso: python ferramentas/ver_sensores.py   (ou, no VS Code: Terminal > Executar Tarefa > Ver sensores na tela do robô)
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def main():
    import robo
    from enviar import AVISO_IDE, ide_est_aberta
    from estc import compilar
    from est_protocol import upload

    robo.novo_programa()
    with robo.para_sempre():
        for porta in (1, 2, 3):
            robo.mostrar(f'S{porta}', linha=porta)
            robo.mostrar(robo.luz_refletida(porta), linha=porta, x=40, limpar=False)
        robo.esperar(0.3)
    if ide_est_aberta():
        print(f'{AVISO_IDE}\n')
    try:
        upload(compilar(robo.programa()), prog_path='/vscode/sensores', verbose=False)
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')
    print('Pronto! A tela do robô mostra S1, S2 e S3 (0 = escuro, 100 = claro).')
    print('Passe cada sensor no branco e no preto e anote os números no calibracao.py (PRETO e BRANCO).')
    print('Para parar, use o botão do robô. O programa fica no menu dele, pasta vscode, com o nome sensores.')


if __name__ == '__main__':
    main()
