# Custom LCD

Custom LCD is a Python package that provides a way to interact with a dummy custom LCD that is generated from an SVG file. The package implements a dummy I2C protocol to communicate with the logic of the LCD, which runs in another process and communicates through ZeroMQ.

## Installation

To install Custom LCD, clone the repository and run:

    pip install .

## Usage

To use Custom LCD, start the custom_lcd.py script:

    python custom_lcd.py

This will start a graphical user interface that displays the custom LCD.

To interact with the LCD, run the `toggle_onclick.py` script:

    python toggle_onclick.py

This will send a command to the logic of the LCD over the ZeroMQ link, toggling the state of the LCD.

## Customization

To customize the appearance of the LCD, modify the SVG file in the directory. To customize the behavior of the logic that controls the LCD, modify the Python script that implements the I2C protocol.
