"""Gera a cola do aluno para imprimir: docs/cola-do-aluno.pdf, a partir de docs/cola-do-aluno.md.

Rode de novo sempre que mudar o cola-do-aluno.md. Ferramenta de quem desenvolve o projeto: precisa do
pacote markdown (pip install markdown) e do Edge ou do Chrome, que transforma a página em PDF.
Uso:  python ferramentas/cola_pdf.py
"""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / 'docs' / 'cola-do-aluno.md'
DESTINO = RAIZ / 'docs' / 'cola-do-aluno.pdf'
NAVEGADORES = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'msedge', 'google-chrome', 'chromium', 'chrome',
]

ESTILO = """
@page { size: A4; margin: 11mm 12mm 12mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.6pt; line-height: 1.35; color: #111; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 1mm; padding-bottom: 1.5mm; border-bottom: 2.5px solid #1d5fbf; color: #1d5fbf; }
h2 { font-size: 11.5pt; margin: 3.2mm 0 1.2mm; color: #1d5fbf; break-after: avoid; }
p { margin: 1.2mm 0; }
p:has(+ pre), p:has(+ table) { break-after: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #eef2f8; padding: 0 2px;
       border-radius: 2px; }
pre { background: #f3f6fa; border-left: 3px solid #1d5fbf; padding: 1.6mm 2.5mm; margin: 1.4mm 0;
      break-inside: avoid; white-space: pre-wrap; }
pre code { background: none; padding: 0; font-size: 8.8pt; line-height: 1.3; }
table { border-collapse: collapse; width: 100%; margin: 1.2mm 0; break-inside: avoid; }
th, td { border: 1px solid #c9d3e0; padding: 0.9mm 1.8mm; text-align: left; vertical-align: top; }
th { background: #e3ebf6; }
td:first-child { white-space: nowrap; }
ul { margin: 1mm 0; padding-left: 5mm; }
li { margin: 0.5mm 0; }
.rodape { margin-top: 3mm; padding-top: 1.2mm; border-top: 1px solid #c9d3e0; font-size: 8pt; color: #555; }
"""

RODAPE = ('EST-ROBOT, criado por Andrey Violante, para uso pedagógico · '
          'andreyviolante.github.io/est-robot · mais exemplos no simulador e no guia do professor')


def navegador():
    for nome in NAVEGADORES:
        caminho = nome if os.path.isabs(nome) else shutil.which(nome)
        if caminho and os.path.isfile(caminho):
            return caminho
    sys.exit('ERRO: não achei o Edge nem o Chrome para gerar o PDF.')


def main():
    try:
        import markdown
    except ImportError:
        sys.exit('ERRO: falta o pacote markdown: pip install markdown')
    corpo = markdown.markdown(ORIGEM.read_text(encoding='utf-8'), extensions=['tables', 'fenced_code'])
    html = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Cola de comandos do robô</title>'
            f'<style>{ESTILO}</style></head><body>{corpo}<p class="rodape">{RODAPE}</p></body></html>')
    with tempfile.TemporaryDirectory() as pasta:
        pagina = Path(pasta) / 'cola.html'
        pagina.write_text(html, encoding='utf-8')
        pdf = Path(pasta) / 'cola.pdf'
        subprocess.run([navegador(), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        f'--user-data-dir={Path(pasta) / "perfil"}', f'--print-to-pdf={pdf}', pagina.as_uri()],
                       check=True, capture_output=True, timeout=120)
        tamanho, limite = -1, time.monotonic() + 30       # o Edge volta antes de terminar de gravar
        while time.monotonic() < limite:
            atual = pdf.stat().st_size if pdf.exists() else -1
            if atual > 0 and atual == tamanho:
                break
            tamanho = atual
            time.sleep(1)
        else:
            sys.exit('ERRO: o navegador não gerou o PDF.')
        shutil.copyfile(pdf, DESTINO)
    try:
        from pypdf import PdfReader
        paginas = f', {len(PdfReader(DESTINO).pages)} página(s)'
    except ImportError:
        paginas = ''
    print(f'[OK] {DESTINO.relative_to(RAIZ)}: {DESTINO.stat().st_size // 1024} KB{paginas}')


if __name__ == '__main__':
    main()
