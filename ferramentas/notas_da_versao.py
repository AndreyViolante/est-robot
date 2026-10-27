"""Texto da página de uma versão em Releases: as novidades dela (do NOVIDADES.md), como instalar e o
SHA-256 do pacote (de dist/est-robot-windows.zip, se ele já foi montado).
Uso: python ferramentas/notas_da_versao.py v0.2.0     (usado pelo .github/workflows/publicar.yml)
"""
import hashlib, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PACOTE = RAIZ / 'dist' / 'est-robot-windows.zip'

CONFERIR = """**Conferir o arquivo (opcional):** o código SHA-256 do est-robot-windows.zip desta versão é

`{sha}`

No PowerShell, na pasta onde o zip foi baixado: `Get-FileHash est-robot-windows.zip`. Se o código for
igual, o arquivo é exatamente o que foi publicado aqui."""

COMO_INSTALAR = """**est-robot-windows.zip**: o projeto com o Python dentro. Não instala o Python e não precisa de administrador.
1. Clique com o botão direito no zip → **Extrair Tudo**.
2. Abra a pasta no VS Code (Arquivo → Abrir Pasta).
3. Abra o `meu_programa.py` e aperte **Ctrl+Shift+B**: o robô acende a luz, apita e escreve "Funcionou!".

Já tem o projeto? Use **Terminal → Executar Tarefa → Atualizar o projeto**: ele pega esta versão e não mexe
no `calibracao.py` nem nos programas dos alunos.

Sem instalar nada: https://andreyviolante.github.io/est-robot/programar/ (Chrome ou Edge).
Detalhes no [INSTALAR.md](https://github.com/AndreyViolante/est-robot/blob/master/INSTALAR.md)."""


def novidades(versao):
    texto = (RAIZ / 'NOVIDADES.md').read_text(encoding='utf-8')
    for secao in re.split(r'(?m)^## ', texto)[1:]:
        cabeca, _, corpo = secao.partition('\n')
        if cabeca.split()[0] == versao:
            return corpo.strip()
    return ''


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    versao = sys.argv[1].lstrip('vV')
    texto = novidades(versao)
    partes = ([f'## Novidades da {versao}\n\n{texto}'] if texto else []) + [COMO_INSTALAR]
    if PACOTE.exists():
        partes.append(CONFERIR.format(sha=hashlib.sha256(PACOTE.read_bytes()).hexdigest().upper()))
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n\n'.join(partes))


if __name__ == '__main__':
    main()
