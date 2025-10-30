#!/bin/python
import sys
from time import time, sleep
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics


class AnimationApp:
    def __init__(self, rows: int = 32, cols: int = 64, fps: int = 50):
        options = RGBMatrixOptions()
        options.rows = rows
        options.cols = cols
        options.gpio_slowdown = 2
        options.pwm_bits = 3

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.width = cols
        self.height = rows
        self.frame_delay = 1.0 / max(1, fps)
        self.start_time = time()

    def animate(self, frame_count: int, t_seconds: float) -> None:
        # Draw your hardcoded animation here using self.canvas
        # Example placeholder: moving horizontal line
        y = frame_count % self.height
        color = graphics.Color(255, 80, 0)
        graphics.DrawLine(self.canvas, 0, y, self.width - 1, y, color)

    def run(self) -> None:
        frame = 0
        while True:
            self.canvas.Clear()
            t = time() - self.start_time
            self.animate(frame, t)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frame += 1
            sleep(self.frame_delay)


def main() -> None:
    try:
        AnimationApp().run()
    except KeyboardInterrupt:
        print('Exiting...')
        sys.exit(0)


if __name__ == "__main__":
    main()
