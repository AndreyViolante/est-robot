from est import *

with repetir():
    se_sensor_cor_2motores(
        S1, PRETO,
        se_motor_B_args    = (50, TRAS,   1),
        se_motor_C_args    = (50, FRENTE, 1),
        senao_motor_B_args = (50, FRENTE, 1),
        senao_motor_C_args = (50, TRAS,   1),
    )
