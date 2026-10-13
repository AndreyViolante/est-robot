"""Compila um programa e envia ao robo (Ctrl+Shift+B no VS Code).

O programa pode ser escrito com robo.py (comandos em portugues, ex.: andar(rotacoes=2))
ou com blocos.py, definindo  PROGRAMA = [start(), ...]
Uso:  python enviar.py seguidor_linha.py            compila e envia
      python enviar.py seguidor_linha.py --so-compilar   so mostra o tamanho e os bytes
"""
import importlib.util, os, re, sys

from estc import compilar


def carregar(arquivo):
    pasta = os.path.dirname(os.path.abspath(arquivo))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    import robo
    robo.novo_programa()
    spec = importlib.util.spec_from_file_location('programa_usuario', arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'PROGRAMA'):
        return mod.PROGRAMA
    feito = robo.programa()
    if len(feito) > 1:
        return feito
    sys.exit(f'ERRO: {arquivo} nao tem nenhum comando para o robo')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arquivo = sys.argv[1]
    nome = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(os.path.basename(arquivo))[0])[:20] or 'programa'

    try:
        dados = compilar(carregar(arquivo))
    except NotImplementedError as e:
        sys.exit(f'ERRO: {e}')
    print(f'[OK] {arquivo}: {len(dados)} bytes')

    if '--so-compilar' in sys.argv:
        print(dados.hex(' '))
        return
    from est_protocol import upload
    try:
        upload(dados, prog_path=f'/vscode/{nome}')
    except RuntimeError as e:
        sys.exit(f'ERRO: {e}')


if __name__ == '__main__':
    main()
