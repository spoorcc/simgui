import zmq

import custom_lcd

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

socket.send(bytes((custom_lcd.I2C_LCD_ADDRESS, custom_lcd.I2C_LCD_READ_CMD)))
led_state = socket.recv()

while True:
    socket.send(bytes((custom_lcd.I2C_TOUCH_ADDRESS, custom_lcd.I2C_TOUCH_READ_CMD)))
    touch_state = socket.recv()
    led_state = bytes(a ^ b for a, b in zip(led_state, touch_state))

    socket.send(
        bytes((custom_lcd.I2C_LCD_ADDRESS, custom_lcd.I2C_LCD_WRITE_CMD)) + led_state
    )
    touch_state = socket.recv()
