import tkinter as tk
from tkinter import Canvas, PhotoImage
from typing import Sequence, Tuple
from xml.dom import minidom
from svg.path import parse_path, Move, Line

MASK_COLOR = "black"


class Application(tk.Frame):
    def __init__(self, background, mask, master=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.pack(fill="both", expand=True)
        self.background = PhotoImage(file=background)
        master.geometry(f"{self.background.width()}x{self.background.height()}+100+100")

        self.canvas = Canvas(
            self, width=self.background.width(), height=self.background.height()
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_image(0, 0, image=self.background, anchor="nw")

        mask_svg = minidom.parse(mask)
        self.rectangles = self.add_rects_from_svg(mask_svg, init_fill=MASK_COLOR)
        self.polygons = self.add_paths_from_svg(mask_svg, init_fill=MASK_COLOR)

        self.canvas.bind("<Button-1>", self.click_event)

    def add_rects_from_svg(
        self, svg: minidom.Document, init_fill: str
    ) -> Sequence[int]:
        """Add each <rect> element from an svg"""
        rectangles = []

        # Loop through all the <rect> elements in the SVG
        for rect in svg.getElementsByTagName("rect"):
            # Get the x, y, width, and height attributes for this rectangle
            x = int(rect.getAttribute("x"))
            y = int(rect.getAttribute("y"))
            w = int(rect.getAttribute("width"))
            h = int(rect.getAttribute("height"))

            # Add the rectangle to the canvas
            rectangles.append(
                self.canvas.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + h,
                    fill=init_fill,
                    outline="",
                    tags=[rect.getAttribute("id")],
                )
            )

        # Update the image with the current state of the canvas
        self.canvas.itemconfigure(self.background, image=self.canvas)

        return rectangles

    def add_paths_from_svg(
        self, svg: minidom.Document, init_fill: str
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
        ]

        # Update the image with the current state of the canvas
        self.canvas.itemconfigure(self.background, image=self.canvas)

        return paths

    def click_event(self, event):
        """On click event do stuff."""
        for rectangle in self.rectangles:
            x1, y1, x2, y2 = self.canvas.coords(rectangle)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                print(f"Touch surface {rectangle} was touched!")
                print(self.canvas.itemcget(rectangle, "tags"))
                self.toggle_item(rectangle)

    def toggle_item(self, item):
        """Hide or show the item using the fill color."""
        if self.canvas.itemcget(item, "fill") == "":
            self.canvas.itemconfigure(item, fill=MASK_COLOR)
        else:
            self.canvas.itemconfigure(item, fill="")
        self.canvas.itemconfigure(self.background, image=self)


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

    app = Application(master=root, background="background.png", mask="Masked.svg")
    app.mainloop()
