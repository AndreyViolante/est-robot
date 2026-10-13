# est-robot

Programe o robô educacional **Dr. Luck EST** em Python, direto do **VS Code**, sem a IDE
proprietária.

O projeto tem um compilador próprio que transforma o programa em Python no bytecode que o robô
executa, e um cliente USB que grava e executa o programa no robô. O compilador foi construído por
engenharia reversa e é testado comparando, byte a byte, a saída dele com programas compilados pela
IDE oficial.

```python
from blocos import *

s1 = sensor_refl(1)
s2 = sensor_refl(2)
erro = math('-', a=(s1, 7), b=(s2, 7))
correcao = math('*', a=(erro, 1), cb=0.4)
esq = math('+', ca=25, b=(correcao, 1))
dir_ = math('-', ca=25, b=(correcao, 1))

sempre = loop_forever()
sempre.b1 = [s1, s2, erro, correcao, esq, dir_, tank_on(0, 0, wl=(esq, 1), wr=(dir_, 1))]

PROGRAMA = [start(), sempre]
```

*Seguidor de linha proporcional com dois sensores ([exemplos/seguidor_proporcional.py](exemplos/seguidor_proporcional.py)).*

## Requisitos

- Windows (a comunicação USB usa a API HID do Windows)
- Python 3.10 ou mais novo
- `pip install pywinusb`
- Robô EST ligado e conectado por cabo USB

## Uso

1. Abra esta pasta no VS Code.
2. Escreva o programa num arquivo `.py` que termine com `PROGRAMA = [start(), ...]`.
3. Com o arquivo aberto, aperte **`Ctrl+Shift+B`**: ele compila, grava e executa no robô.

Pelo terminal:

```bash
python enviar.py exemplos/seguidor_linha.py
```

```bash
python enviar.py exemplos/seguidor_linha.py --so-compilar
```

O programa fica gravado no robô em `/vscode/<nome do arquivo>`.

## Blocos disponíveis

Programas são listas de blocos. Loops e switches guardam os blocos de dentro em `.b1`
(e `.b2` no ramo "não" do switch).

| Bloco | Função |
|---|---|
| Mover tanque (B+C) | `tank_on(esq, dir)`, `tank_rot(esq, dir, rotacoes)`, `tank_deg(esq, dir, graus)`, `tank_sec(esq, dir, segundos)`, `tank_off()` |
| Motor grande | `motor_deg(porta, potencia, graus)` |
| Sensor de cor | `sensor_refl(porta)` (saída 7, luz refletida), `sensor_color_id(porta)` (saída 5, número da cor) |
| Contas | `math('+' \| '-' \| '*' \| '/', a=(bloco, saida), b=(bloco, saida), ca=constante, cb=constante)` (saída 1) |
| Variável | `var_wn(nome, valor)` ou `var_wn(nome, src=bloco, out=saida)` |
| Switch de cor | `switch_color(porta, PRETO)` (conjuntos: `PRETO + VERDE`) |
| Loop | `loop_forever()`, `loop_count(n)` |
| Esperar | `wait_sec(segundos)` |

- **Fios** ligam a saída de um bloco à entrada de outro: `(bloco, número_da_saída)`.
- **Potência**: de −100 a 100. No robô usado nos testes, positiva é para frente.
- **Motores**: o Move Tank usa B (esquerdo) e C (direito). Para mudar, altere `blocos.MOTORS`.

Um bloco que o compilador ainda não conhece gera um erro claro na compilação. Já implementados,
mas ainda sem conferência byte a byte com a IDE: `math('/')`, `sensor_color_id` e `var_wn` com valor
fixo.

## Como funciona

| Arquivo | Papel |
|---|---|
| [blocos.py](blocos.py) | a linguagem: funções que criam os blocos |
| [estc.py](estc.py) | o compilador: registradores, threads, fios e saltos |
| [est_protocol.py](est_protocol.py) | o protocolo USB HID (gravar e executar) |
| [enviar.py](enviar.py) | junta tudo: compila o arquivo e envia |
| [verificar_gabaritos.py](verificar_gabaritos.py) | compara o compilador com a IDE oficial |
| [gabaritos/](gabaritos/) | programas compilados pela IDE oficial, usados como referência |
| [ferramentas/decodificar.py](ferramentas/decodificar.py) | mostra o bytecode instrução por instrução |
| [docs/formato.md](docs/formato.md) | protocolo, estrutura do programa e instruções da VM |

```bash
python verificar_gabaritos.py
```

O resultado esperado é `8/8 gabaritos identicos`. Para acrescentar um bloco novo, siga a seção 5
de [docs/formato.md](docs/formato.md).

## Aviso

Projeto independente, sem relação com o fabricante do robô. O formato foi obtido por engenharia
reversa, para interoperabilidade. Use por sua conta e risco.
