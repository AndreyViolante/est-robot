# Cola de comandos do robô

```python
from robo import *          # sempre a primeira linha

andar(rotacoes=2)           # cada comando numa linha
virar_direita(90)
```

Para mandar para o robô: **`Ctrl+Shift+B`**. O robô começa a andar logo: deixe-o no chão.

## Mover

| Comando | O que faz |
|---|---|
| `andar(rotacoes=2)` | anda para frente (também: `segundos=1`, `graus=360`, `potencia=30`) |
| `re(rotacoes=1)` | anda de ré |
| `andar_cm(20)` | anda 20 centímetros |
| `virar_direita(90)` / `virar_esquerda(90)` | vira no lugar |
| `motores(30, 10)` | liga os motores (esquerdo, direito) e deixa ligados |
| `parar()` | para os motores |
| `esperar(1)` | espera 1 segundo |

## Sensores

| Comando | Dá |
|---|---|
| `luz_refletida(1)` | luz no sensor 1: 0 (escuro) a 100 (claro) |
| `cor_vista(1)` | a cor: compare com `PRETO`, `AZUL`, `VERDE`, `AMARELO`, `VERMELHO`, `BRANCO`, `MARROM` (ex.: `se(cor_vista(1) == VERDE)`) |
| `distancia(4)` | distância em centímetros (ultrassom) |
| `tocado(4)` | 1 se o botão de toque estiver apertado, 0 se não |

## Repetir e decidir

```python
with repetir(4):                 # repete 4 vezes
    andar_cm(30)
    virar_direita(90)

with para_sempre():              # repete sem parar
    with se_ver_cor(1, PRETO):   # se o sensor 1 vê preto...
        motores(10, 30)
    with senao():                # ...senão
        motores(30, 10)

with se(distancia(4) < 15):      # se a distância for menor que 15 cm
    parar()

with repetir_ate(lambda: distancia(4) < 15):   # repete até chegar perto
    motores(30, 30)
```

Outros: `esperar_toque(4)`, `esperar_distancia(4, '<', 20)`, `esperar_luz(1, '<', 30)`,
`esperar_cor(1, VERDE)`, `se_tocado(4)`, `se_luz(1, '<', 30)`, `repetir_ate_cor(1, PRETO)`.

## Tela, som, luz e variáveis

| Comando | O que faz |
|---|---|
| `mostrar('Oi')` / `mostrar(distancia(4), linha=2)` | escreve na tela (linhas 1, 2 e 3; a linha 1 apaga a tela) |
| `bip()` / `tocar(440, 0.5)` | som (frequência, segundos) |
| `luz('azul')` / `apagar_luz()` | luz do robô (`'azul'`, `'roxo'`, `'vermelho'`) |
| `guardar('pontos', 0)` / `ler('pontos')` | guarda e lê um número |

## Regras que evitam erro

- Número com casa decimal usa **ponto**: `0.5` (e não `0,5`).
- `with ...` termina com **dois-pontos** `:` e as linhas de dentro começam com **4 espaços**.
- Texto vai entre **aspas**: `mostrar('Oi')`.
- Para comparar sensores use `with se(...)`, e não `if`.
- Para linha preta no chão branco, use a **luz refletida** (`luz_refletida`, `se_luz`): é mais confiável que a cor.
- Use **um modo só para cada sensor**: misturar cor e luz refletida no mesmo sensor deixa ele lento e errando (o programa avisa).
- Se der erro, leia a mensagem: ela diz **a linha** e o que corrigir.
