# Medidas do seu robô. Todos os programas desta pasta usam estes números sozinhos.
# Meça uma vez por robô. Um programa ainda pode mudar algum valor só para ele com configurar(...).

MOTOR_ESQUERDO = 'B'
MOTOR_DIREITO = 'C'
INVERTIDO = False          # True se o robô anda de ré quando deveria ir para frente

RODA_CM = 4.3              # acerta o andar_cm: se andar_cm(30) andar menos que 30 cm, diminua
ENTRE_RODAS_CM = 12.0      # acerta o virar_direita(90): se virar menos que 90°, aumente
PAUSA = 0.5                # segundos parado depois de cada movimento que freia (0 = sem pausa)

# Luz refletida de cada sensor no preto e no branco. Para ver os números:
# Terminal > Executar Tarefa > Ver sensores na tela do robô.
# limite(1) devolve o meio entre os dois, para usar em: if luz_refletida(1) < limite(1):
PRETO = {1: 18, 2: 21, 3: 10}
BRANCO = {1: 100, 2: 100, 3: 100}
