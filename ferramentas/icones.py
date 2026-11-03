"""Desenha os ícones do EST-LAB (página instalável no celular e aba do navegador): as três luzes do robô,
como no topo do site, sobre uma linha de pista. Grava em docs/programar/icones/.

Ferramenta de quem desenvolve o projeto: precisa do Pillow (pip install pillow). Rode de novo só se mudar o desenho.
Uso:  python ferramentas/icones.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / 'docs' / 'programar' / 'icones'
FUNDO = (13, 18, 34)                                     # --fg da página: #0d1222
LUZES = [(97, 135, 255), (165, 125, 255), (255, 96, 100)]   # azul, roxo e vermelho do tema escuro
LINHA = (231, 235, 246)
AUMENTO = 4                                              # desenha grande e reduz: bordas lisas


def desenhar(lado, cantos=True, margem=0.0):
    """Ícone quadrado. margem: fração de cada lado que fica só com o fundo (área segura do ícone 'maskable')."""
    g = lado * AUMENTO
    img = Image.new('RGBA', (g, g), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if cantos:
        d.rounded_rectangle([0, 0, g - 1, g - 1], radius=int(g * 0.22), fill=FUNDO)
    else:
        d.rectangle([0, 0, g - 1, g - 1], fill=FUNDO)
    util = g * (1 - 2 * margem)
    x0 = y0 = g * margem
    # linha da pista: uma curva suave de um lado ao outro, embaixo
    r = util * 0.0375                                    # meia espessura: círculos encostados, sem emendas
    for i in range(401):
        t = i / 400
        x = x0 + util * (0.12 + 0.76 * t)
        y = y0 + util * (0.70 + 0.07 * (1 - (2 * t - 1) ** 2) - 0.035 * (2 * t - 1))
        d.ellipse([x - r, y - r, x + r, y + r], fill=LINHA)
    # as três luzes
    r = util * 0.105
    for i, cor in enumerate(LUZES):
        cx, cy = x0 + util * (0.25 + 0.25 * i), y0 + util * 0.40
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)
    return img.resize((lado, lado), Image.LANCZOS)


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    feitos = {
        'icone-192.png': desenhar(192),
        'icone-512.png': desenhar(512),
        'icone-maskable-512.png': desenhar(512, cantos=False, margem=0.1),   # o Android recorta em círculo/gota
        'icone-180.png': desenhar(180, cantos=False),                         # tela inicial do iPhone (ele arredonda)
        'icone-32.png': desenhar(32),                                         # aba do navegador
    }
    for nome, img in feitos.items():
        img.save(PASTA / nome, optimize=True)
        print(f'[OK] {(PASTA / nome).relative_to(RAIZ)}: {img.size[0]} px')


if __name__ == '__main__':
    main()
