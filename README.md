# EST Robot — Compilador Python

Engenharia reversa do robô educacional **Dr. Luck EST** para programá-lo via Python puro, sem depender da IDE proprietária.

## O que é

O robô EST usa um protocolo HID USB proprietário e uma IDE fechada para upload de programas. Este projeto reverse-engineerou o protocolo e o formato binário dos programas, permitindo escrever e enviar código diretamente do Python.

## Estrutura

| Arquivo | Descrição |
|---|---|
| `est.py` | API de alto nível (`motor`, `repetir`, `se_sensor_cor_2motores`, etc.) |
| `est_compiler.py` | Compilador Python → binário da VM do robô |
| `est_protocol.py` | Protocolo HID USB (upload via WinAPI) |
| `run.py` | Script principal: compila e envia para o robô |
| `meu_programa.py` | Programa atual carregado no robô |

## Como usar

```python
# meu_programa.py
from est import *

# Seguidor de linha simples
with repetir():
    se_sensor_cor_2motores(
        S1, PRETO,
        se_motor_B_args    = (50, TRAS,   1),
        se_motor_C_args    = (50, FRENTE, 1),
        senao_motor_B_args = (50, FRENTE, 1),
        senao_motor_C_args = (50, TRAS,   1),
    )
```

```bash
python run.py meu_programa.py
```

## Requisitos

- Python 3.10+
- `pywinusb` (`pip install pywinusb`)
- Windows (protocolo HID via WinAPI)
- Robô Dr. Luck EST conectado via USB

## Layout físico do robô

- **Motor B** = motor esquerdo
- **Motor C** = motor direito
- **S1** = sensor RGB esquerdo
- **S2** = sensor RGB direito

## Constantes disponíveis

```python
# Direção
FRENTE, TRAS

# Sensores
S1, S2, S3, S4

# Cores
PRETO, VERDE, VERMELHO, BRANCO
```

## Protocolo

- VID=`0x0483`, PID=`0x5750`
- Reports HID de 1025 bytes
- Upload em 7 pacotes: SELECT → HEARTBEAT → DOWNLOAD → FILENAME → DATA → HEARTBEAT → DOWNLOAD
