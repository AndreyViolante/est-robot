# est-robot

Programe o robô educacional **Dr. Luck EST** em Python, direto do **VS Code**, sem a IDE
proprietária. Pensado para aulas de robótica: os comandos são em português.

**Tem uma controladora EST?** Ajude a testar: [andreyviolante.github.io/est-robot](https://andreyviolante.github.io/est-robot/)

**Quer ver antes de instalar?** O exemplo roda no simulador, no navegador:
[andreyviolante.github.io/est-robot/simulador](https://andreyviolante.github.io/est-robot/simulador/)

```python
from robo import *

with repetir(4):            # desenha um quadrado
    andar_cm(30)
    virar_direita(90)
```

```python
from robo import *

with para_sempre():         # seguidor de linha proporcional com dois sensores
    erro = luz_refletida(1) - luz_refletida(2)
    correcao = erro * 0.4
    motores(25 + correcao, 25 - correcao)
```

O projeto tem um compilador próprio, que transforma o programa no bytecode que o robô executa, e
um cliente USB que grava e executa o programa no robô. O compilador foi construído por engenharia
reversa e é testado comparando, byte a byte, a saída dele com programas compilados pela IDE oficial.

## Para professores

| | |
|---|---|
| [INSTALAR.md](INSTALAR.md) | instalação passo a passo (Python, VS Code, `instalar.bat`, teste do robô) |
| [docs/guia-do-professor.md](docs/guia-do-professor.md) | roteiro de 8 aulas, com objetivos, desafios e erros comuns |
| [docs/cola-do-aluno.md](docs/cola-do-aluno.md) | uma página com todos os comandos, para imprimir |

## Uso

Funciona no **Windows**, com Python 3.10+ e VS Code (veja o [INSTALAR.md](INSTALAR.md)).

1. Abra esta pasta no VS Code.
2. Abra o [meu_programa.py](meu_programa.py) e aperte **`Ctrl+Shift+B`**: se o robô acender a luz,
   apitar e escrever "Funcionou!", o computador está conversando com a controladora.
3. Apague as linhas do teste e escreva o seu programa embaixo do `from robo import *` (ou crie outro
   arquivo `.py` começando com essa linha). **`Ctrl+Shift+B`** compila, grava e já executa no robô.

> **Atenção:** o robô começa a se mexer logo depois do envio. Deixe-o no chão ou segure-o.

Se o programa tiver um erro, nada é enviado e aparece uma explicação em português com a linha:

```
ERRO na linha 3 de quadrado.py:
    andr(rotacoes=2)
  não conheço "andr". Você quis dizer "andar"?
```

Para conferir se o computador fala com o robô: **Terminal → Executar Tarefa → Testar conexão com o
robô** (ele apita, acende a luz e escreve "Funcionou!").

Para gravar sem o robô sair andando (por exemplo, numa prova, em que ele precisa estar na posição
de largada): **Terminal → Executar Tarefa → Gravar no robô sem executar**. O programa fica na pasta
**vscode** do robô e é iniciado pelo menu dele.

Pelo terminal:

```bash
python enviar.py meu_programa.py
python enviar.py meu_programa.py --so-gravar
```

### Simulador (sem o robô)

**Terminal → Executar Tarefa → Simular no computador** abre o programa no navegador, numa pista
vista de cima. O simulador executa os mesmos bytes que iriam para o robô: dá para ver o caminho
(rastro), a linha do programa que está rodando, os sensores, os motores, as variáveis, a tela, a luz
e o som. Funciona sem internet e sem instalar nada. O exemplo do projeto está na
[demonstração online](https://andreyviolante.github.io/est-robot/simulador/).

- Pistas: chão quadriculado, oval, quadrado com cantos de 90°, curvas de 90° com uma falha na
  linha, e uma arena com uma caixa.
- Arraste o robô para escolher a largada; a bolinha azul na frente gira o robô. A caixa da arena
  também pode ser arrastada.
- Em **Medidas do robô** ficam a roda, a distância entre as rodas e a posição de cada sensor. O padrão
  é o robô do laboratório (S1 e S2 um de cada lado da linha, S3 no meio e mais à frente, ultrassom na
  porta 4); meça o seu e ajuste.

```bash
python simular.py meu_programa.py
```

O robô de verdade escorrega, a bateria muda a velocidade e a luz da sala muda os sensores: o
simulador serve para testar a lógica, mas confira no robô.

## Comandos

| Movimento | |
|---|---|
| `andar(rotacoes=2)`, `andar(segundos=1)`, `andar(graus=360)` | anda para frente (`potencia=50` por padrão) |
| `re(rotacoes=1)` | anda de ré |
| `andar_cm(20)` | anda 20 cm |
| `virar_direita(90)`, `virar_esquerda(90)` | vira o robô no lugar, em graus |
| `girar_direita(rotacoes=0.5)`, `girar_esquerda(...)` | gira as rodas em sentidos opostos |
| `motores(esq, dir)` | liga os dois motores e deixa ligados (aceita valores de sensor) |
| `parar()` | desliga os motores |
| `motor('A', 50, graus=180)`, `ligar_motor('A', 50)`, `desligar_motor('A')` | um motor sozinho (garra, braço) |

| Sensores (dão valores que entram em contas: `+ - * /`) | |
|---|---|
| `luz_refletida(porta)` | luz refletida, de 0 (escuro) a 100 (claro) |
| `cor_vista(porta)` | número da cor (`PRETO`, `AZUL`, `VERDE`, `AMARELO`, `VERMELHO`, `BRANCO`, `MARROM`) |
| `distancia(porta)` | sensor ultrassônico, em centímetros |
| `tocado(porta)` | sensor de toque: 1 apertado, 0 solto |

| Esperar | |
|---|---|
| `esperar(1.5)` | segundos |
| `esperar_toque(porta)` | até apertar o sensor de toque |
| `esperar_distancia(porta, '<', 20)` | até a distância passar do valor |
| `esperar_luz(porta, '<', 30)`, `esperar_cor(porta, VERDE)` | até o sensor de cor ver |

| Repetir e decidir | |
|---|---|
| `with para_sempre():` / `with repetir(4):` | repete o que está dentro |
| `with repetir_ate(lambda: distancia(4) < 20):` | repete até a condição acontecer |
| `with repetir_ate_luz(1, '<', 30):`, `with repetir_ate_cor(1, PRETO):` | repete até o sensor de cor ver |
| `with se(distancia(4) < 20):` | faz se a comparação for verdadeira |
| `with se_ver_cor(1, PRETO):`, `with se_luz(1, '<', 30):` | decide pelo sensor de cor |
| `with se_tocado(4):`, `with se_distancia(4, '<', 20):` | decide pelo toque / ultrassom |
| `with senao():` | logo depois de um `with se...`: o que fazer no caso contrário |

| Tela, som, luz e variáveis | |
|---|---|
| `mostrar('Oi')`, `mostrar(distancia(4), linha=2)` | escreve texto ou valor na tela (3 linhas; a linha 1 apaga a tela) |
| `tocar(440, 0.5)`, `bip()` | som (frequência em Hz, duração em segundos) |
| `luz('azul')`, `apagar_luz()` | luz do robô: `'azul'`, `'roxo'` ou `'vermelho'` |
| `guardar('contador', 0)`, `ler('contador')` | variáveis guardadas no robô |

Comparações (`<`, `<=`, `>`, `>=`, `==`, `!=`) com sensores funcionam dentro de `se(...)` e
`repetir_ate(...)`. O `if` do Python não serve para isso, porque a leitura acontece no robô, e não
no computador: o programa avisa se for usado assim.

### Ajustando ao seu robô

```python
configurar(esquerdo='B', direito='C', invertido=False, roda_cm=4.3, entre_rodas_cm=12, pausa=0.5)
```

Os valores acima são os padrões, medidos num robô EST: com eles, `andar_cm(30)` anda 30 cm e
`virar_direita(90)` vira 90°. Só use `configurar` se o seu robô for diferente.

- `invertido=True` se o robô andar de ré quando deveria ir para frente.
- `roda_cm` (diâmetro da roda) acerta o `andar_cm`.
- `entre_rodas_cm` acerta o `virar_direita(90)`: se o robô virar a mais, diminua; se virar a menos, aumente.
- `pausa` é o tempo parado depois de cada movimento que freia. Sem ela, o robô emenda um movimento no
  outro e as viradas saem erradas; `pausa=0` desliga.

## Exemplo

[exemplos/11_seguidor_dois_sensores.py](exemplos/11_seguidor_dois_sensores.py): seguidor básico com
dois sensores (se S1 vê preto vira, senão se S2 vê preto vira para o outro lado, senão anda reto),
conferido no simulador.

## Para quem quer ir além

Os comandos em português geram blocos de [blocos.py](blocos.py), que seguem os blocos da IDE
oficial (fios entre saídas e entradas, parâmetros por número). Os dois podem ser usados juntos: um
programa só de blocos define `PROGRAMA = [start(), ...]` (veja os testes em
[verificar_gabaritos.py](verificar_gabaritos.py)).

| Arquivo | Papel |
|---|---|
| [robo.py](robo.py) | a linguagem em português |
| [blocos.py](blocos.py) | os blocos da IDE |
| [estc.py](estc.py) | o compilador: registradores, threads, fios, saltos |
| [est_protocol.py](est_protocol.py) | o protocolo USB HID (gravar e executar) |
| [enviar.py](enviar.py) | compila o arquivo e envia |
| [simular.py](simular.py) | compila o arquivo e abre o simulador |
| [simulador/](simulador/) | o simulador: VM do robô em JavaScript (`vm.js`), física (`robo.js`), pistas (`mundo.js`) e a página |
| [verificar_gabaritos.py](verificar_gabaritos.py) | testes: compara com a IDE oficial e confere a linguagem |
| [gabaritos/](gabaritos/) | programas compilados pela IDE oficial, usados como referência |
| [ferramentas/decodificar.py](ferramentas/decodificar.py) | mostra o bytecode instrução por instrução |
| [ferramentas/testar_robo.py](ferramentas/testar_robo.py) | teste de conexão com o robô |
| [ferramentas/publicar_simulador.py](ferramentas/publicar_simulador.py) | copia o simulador para `docs/simulador/` com o exemplo compilado (a demonstração online) |
| [instalar.bat](instalar.bat) | prepara um computador novo |
| [docs/formato.md](docs/formato.md) | protocolo, estrutura do programa e instruções da VM |

```bash
python verificar_gabaritos.py
```

O resultado esperado é `13/13 gabaritos identicos` e `linguagem em portugues: OK`.

**Já testado no robô:** movimento, seguidor de linha (liga-desliga e proporcional), tela, som, luz,
esperar, ultrassom (`distancia`, `esperar_distancia`, `se_distancia`), `se(...)` e `repetir_ate(...)`.
**Ainda não visto funcionando:** a calibragem padrão de `andar_cm` e `virar_*` e o sensor de toque
(os bytes batem com a IDE, mas não foram testados no robô). Cada comando em português gera exatamente o que a IDE geraria para o bloco equivalente.

## Licença e aviso

Código e material sob a [licença MIT](LICENSE): pode usar, copiar e adaptar livremente, mantendo o
aviso de licença.

Projeto independente, sem relação com o fabricante do robô. O formato foi obtido por engenharia
reversa, para interoperabilidade. Use por sua conta e risco.
