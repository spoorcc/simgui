"""Module for simulating a custom LCD interface."""
import contextlib
import copy
import tkinter as tk
from tkinter import Canvas, PhotoImage
from typing import Sequence, Tuple
from xml.dom import minidom
from svg.path import parse_path, Move, Line
import zmq
import re

MASK_COLOR = "black"
I2C_TOUCH_ADDRESS = 0x30
I2C_LCD_ADDRESS = 0x32

I2C_TOUCH_READ_CMD = 0x20

I2C_LCD_READ_CMD = 0x40
I2C_LCD_WRITE_ALL_CMD = 0x41
I2C_LCD_WRITE_SINGLE_CMD = 0x42


class RamMemory:
    """Block of RAM memory."""

    def __init__(self, bit_count: int):
        self._memory = bytearray((bit_count + 7) // 8)
        self._bit_count = bit_count

    def write_from_bytes(self, data: bytes) -> bool:
        """Copy bytes to RAM object respecting the size of the bytearray."""
        old_state = copy.deepcopy(self._memory)
        copy_length = min(len(data), len(self._memory))
        self._memory[:copy_length] = data[:copy_length]
        return old_state != self._memory

    def set_bit(self, idx: int) -> None:
        """Set single bit of memory."""
        self._memory[idx // 8] |= 0x80 >> (idx % 8)

    def toggle_bit(self, idx: int) -> None:
        """Toggle single bit of memory."""
        self._memory[idx // 8] ^= 0x80 >> (idx % 8)

    def as_bytes(self) -> bytes:
        """Get entire memory as bytes."""
        return bytes(self._memory)

    def clear(self) -> None:
        """Clear all memory to 0."""
        self._memory = bytearray(len(self._memory))

    def iterate_bits(self) -> Tuple[int, int]:
        """Iterate over each bit in RAM memory and get each bit index and value."""
        for byte_index, byte_value in enumerate(self._memory):
            binary_string = bin(byte_value)[2:].zfill(8)
            for bit_index, bit_value in enumerate(binary_string):
                index = byte_index * 8 + bit_index
                if index >= self._bit_count:
                    return
                yield byte_index * 8 + bit_index, int(bit_value)


class CustomLCD(tk.Frame):
    """Custom LCD class."""

    def __init__(self, layout, master=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        layout_svg = minidom.parse(layout)

        self.bg_color, self.fg_color = "black", "white"

        svg_elt = layout_svg.documentElement
        assert svg_elt.tagName == "svg"
        width, height = svg_elt.getAttribute("width"), svg_elt.getAttribute("height")
        width = int(re.search(r"^\d+", width).group(0))
        height = int(re.search(r"^\d+", height).group(0))

        self.pack(fill="both", expand=True)
        self.layout = PhotoImage(width=width, height=height)
        master.geometry(f"{width}x{height}+100+100")

        self.canvas = Canvas(self, width=width, height=height, bg=self.bg_color)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_image(0, 0, image=self.layout, anchor="nw")

        self.touch_surfaces = self.add_rects_from_svg(
            layout_svg, init_fill="", class_filter="touch"
        )
        self.elements = self.add_rects_from_svg(
            layout_svg, init_fill=self.fg_color, class_filter="segment"
        ) + self.add_paths_from_svg(
            layout_svg, init_fill=self.fg_color, class_filter="segment"
        )

        self.touch_state = RamMemory(len(self.touch_surfaces))
        self.display_state = RamMemory(len(self.elements))

        self.redraw_all_elements()

        self.canvas.bind("<Button-1>", self.click_event)

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:5555")

        self.receive_message()

    def receive_message(self):
        """Read bytes and always reply."""
        with contextlib.suppress(zmq.Again):
            message = self.socket.recv(flags=zmq.NOBLOCK)
            self.socket.send(self.process_message(message))
        self.master.after(50, self.receive_message)

    def process_message(self, message: bytes) -> bytes:
        """Process a received message and reply."""
        if message[0] == I2C_TOUCH_ADDRESS:
            if message[1] == I2C_TOUCH_READ_CMD:
                reply = self.touch_state.as_bytes()
                self.touch_state.clear()
                return reply
        elif message[0] == I2C_LCD_ADDRESS:
            if message[1] == I2C_LCD_READ_CMD:
                return self.display_state.as_bytes()
            if message[1] == I2C_LCD_WRITE_SINGLE_CMD:
                self.display_state.toggle_bit(message[3])
                self.redraw_single_segment(message[2], message[3])
                return bytes((I2C_LCD_ADDRESS, I2C_LCD_WRITE_SINGLE_CMD))
            if message[1] == I2C_LCD_WRITE_ALL_CMD:
                any_change = self.display_state.write_from_bytes(message[2:])
                if any_change:
                    self.redraw_all_elements()
                return bytes((I2C_LCD_ADDRESS, I2C_LCD_WRITE_ALL_CMD))
        else:
            return b"Illegal: " + message

    def add_rects_from_svg(
        self, svg: minidom.Document, init_fill: str, class_filter: str = ""
    ) -> Sequence[int]:
        """Add each <rect> element from an svg"""
        rectangles = []

        # Loop through all the <rect> elements in the SVG
        for rect in svg.getElementsByTagName("rect"):
            if not class_filter or class_filter in rect.getAttribute("class"):
                # Get the x, y, width, and height attributes for this rectangle
                x = int(rect.getAttribute("x"))
                y = int(rect.getAttribute("y"))
                width = int(float(rect.getAttribute("width")))
                height = int(float(rect.getAttribute("height")))

                # Add the rectangle to the canvas
                rectangles.append(
                    self.canvas.create_rectangle(
                        x,
                        y,
                        x + width,
                        y + height,
                        fill=init_fill,
                        outline="",
                        tags=[rect.getAttribute("id")],
                    )
                )

        # Update the image with the current state of the canvas
        self.canvas.itemconfigure(self.layout, image=self.canvas)

        return rectangles

    def add_paths_from_svg(
        self, svg: minidom.Document, init_fill: str, class_filter: str = "segment"
    ) -> Sequence[int]:
        """Add each <path> element from an svg."""
        paths = [
            self.canvas.create_polygon(
                *parse_path_data(
                    path_data=path.getAttribute("d"),
                    transform=path.getAttribute("transform"),
                ),
                fill=init_fill,
                outline="",
                tags=[path.getAttribute("id")],
            )
            for path in svg.getElementsByTagName("path")
            if class_filter or class_filter in path.getAttribute("class")
        ]
        print(paths)

        # Update the image with the current state of the canvas
        self.canvas.itemconfigure(self.layout, image=self.canvas)

        return paths

    def click_event(self, event):
        """On click event find touch surfaces."""
        for idx, surface in enumerate(self.touch_surfaces):
            x1, y1, x2, y2 = self.canvas.coords(surface)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                print(f"Touch surface {surface} was touched!")
                self.touch_state.set_bit(idx)

    def toggle_item(self, item):
        """Hide or show the item using the fill color."""
        if self.canvas.itemcget(item, "fill") == "":
            self.canvas.itemconfigure(item, fill=MASK_COLOR)
        else:
            self.canvas.itemconfigure(item, fill="")
        self.canvas.itemconfigure(self.layout, image=self)

    def redraw_single_segment(self, item_id, state):
        """Turn on/off single segment."""
        with contextlib.suppress(IndexError):
            self.canvas.itemconfigure(
                self.elements[item_id], fill=self.fg_color if state else ""
            )
            self.canvas.itemconfigure(self.layout, image=self)

    def redraw_all_elements(self):
        """Turn on/off mask elements."""
        for idx, value in self.display_state.iterate_bits():
            self.canvas.itemconfigure(
                self.elements[idx], fill=self.fg_color if value else ""
            )

        self.canvas.itemconfigure(self.layout, image=self)


def parse_path_data(path_data: str, transform: str) -> Sequence[Tuple[int, int]]:
    """Parse svg path data and get coordinates."""
    path = parse_path(path_data)

    if transform:
        raise NotImplementedError("Not implemented (yet)")

    return [
        (int(segment.end.real), int(segment.end.imag))
        for segment in path
        if isinstance(segment, (Move, Line))
    ]


if __name__ == "__main__":
    root = tk.Tk()

    # Remove the window border and title bar
    # root.overrideredirect(True)

    app = CustomLCD(master=root, layout="3digitBCD_plusminus.svg")
    app.mainloop()
