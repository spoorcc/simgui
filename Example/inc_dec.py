import zmq

import custom_lcd


PLUS = 1
MINUS = 23

BCD0_A = 2
BCD0_D = 3
BCD0_C = 4
BCD0_B = 5
BCD0_F = 6
BCD0_E = 7
BCD0_G = 8

BCD1_A = 9
BCD1_D = 10
BCD1_C = 11
BCD1_B = 12
BCD1_F = 13
BCD1_E = 14
BCD1_G = 15

BCD2_A = 16
BCD2_D = 17
BCD2_C = 18
BCD2_B = 19
BCD2_F = 20
BCD2_E = 21
BCD2_G = 22


TOUCH_PLUS = 1 << 6
TOUCH_MINUS = 1 << 7

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

socket.send(bytes((custom_lcd.I2C_LCD_ADDRESS, custom_lcd.I2C_LCD_READ_CMD)))
led_state = socket.recv()
led_state = bytes((0, 0, 0))

value = 0

def bcd_digits(value):
    return [
        1 << BCD0_A
        | 1 << BCD0_B
        | 1 << BCD0_C
        | 1 << BCD0_D
        | 1 << BCD0_E
        | 1 << BCD0_F,
        1 << BCD0_B | 1 << BCD0_C,
        1 << BCD0_A | 1 << BCD0_B | 1 << BCD0_D | 1 << BCD0_E | 1 << BCD0_G,
        1 << BCD0_A | 1 << BCD0_B | 1 << BCD0_C | 1 << BCD0_D | 1 << BCD0_G,
        1 << BCD0_B | 1 << BCD0_C | 1 << BCD0_F | 1 << BCD0_G,
        1 << BCD0_A | 1 << BCD0_C | 1 << BCD0_D | 1 << BCD0_F | 1 << BCD0_G,
        1 << BCD0_A
        | 1 << BCD0_C
        | 1 << BCD0_D
        | 1 << BCD0_E
        | 1 << BCD0_F
        | 1 << BCD0_G,
        1 << BCD0_A | 1 << BCD0_B | 1 << BCD0_C,
        1 << BCD0_A
        | 1 << BCD0_B
        | 1 << BCD0_C
        | 1 << BCD0_D
        | 1 << BCD0_E
        | 1 << BCD0_F
        | 1 << BCD0_G,
        1 << BCD0_A
        | 1 << BCD0_B
        | 1 << BCD0_C
        | 1 << BCD0_D
        | 1 << BCD0_F
        | 1 << BCD0_G,
    ][value]



while True:
    socket.send(bytes((custom_lcd.I2C_TOUCH_ADDRESS, custom_lcd.I2C_TOUCH_READ_CMD)))
    touch_state = int.from_bytes(socket.recv(), "little")
    if touch_state:

        if touch_state == TOUCH_PLUS and value < 120:
            value += 1
        elif touch_state == TOUCH_MINUS and value > 0:
            value -= 1

        led_state_int = 0

        if value > 0:
            led_state_int |=  1 << MINUS
        if value < 120:
            led_state_int |= 1 << PLUS

        led_state_int |= bcd_digits(value % 10)
        if value >= 10:
            led_state_int |= bcd_digits((value // 10) % 10) << 7
        if value >= 100:
            led_state_int |= bcd_digits((value // 100) % 10) << 14

        led_state = int.to_bytes(led_state_int, len(led_state), "big")

        socket.send(
            bytes((custom_lcd.I2C_LCD_ADDRESS, custom_lcd.I2C_LCD_WRITE_ALL_CMD))
            + led_state
        )
        socket.recv()
