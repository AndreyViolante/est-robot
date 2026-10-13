"""Compila um programa escrito com blocos.py e envia ao robo (Ctrl+Shift+B no VS Code).

O arquivo do programa deve definir  PROGRAMA = [start(), ...]
Uso:  python enviar.py seguidor_linha.py            compila e envia
      python enviar.py seguidor_linha.py --so-compilar   so mostra o tamanho e os bytes
"""
import importlib.util, os, re, sys

from estc import compilar


def carregar(arquivo):
    pasta = os.path.dirname(os.path.abspath(arquivo))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    spec = importlib.util.spec_from_file_location('programa_usuario', arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, 'PROGRAMA'):
        sys.exit(f'ERRO: {arquivo} precisa definir PROGRAMA = [start(), ...]')
    return mod.PROGRAMA


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
