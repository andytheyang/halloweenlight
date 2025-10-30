#!/bin/python
import sys
import os
import random
from time import time, sleep
from dataclasses import dataclass
from typing import Optional, List
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics


@dataclass
class AnimationRow:
    """Represents a single animation row in a sprite sheet."""
    name: str
    num_frames: int
    row_index: int  # Which row in the sprite sheet (0-based)
    min_loops: int = 1  # Minimum number of times to play this animation before switching


@dataclass
class SpriteSheet:
    """Represents a sprite sheet with multiple animation rows."""
    filepath: str  # Relative to script directory
    sprite_width: int = 32
    sprite_height: int = 32
    animations: Optional[List[AnimationRow]] = None  # Configure these manually
    animation_sequence: Optional[List[str]] = None  # Optional custom play order
    
    def __post_init__(self):
        """Initialize internal state after configuration."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.full_path = os.path.join(script_dir, self.filepath)
        
        if self.animations is None:
            self.animations = []
        
        # Build lookup dict for quick access by name
        self.animation_dict = {anim.name: anim for anim in self.animations}
        
        # Determine playback mode
        self.random_mode = (self.animation_sequence is None or 
                          len(self.animation_sequence) == 0)


class AnimationApp:
    def __init__(self, sprite_sheet: SpriteSheet, rows: int = 32, cols: int = 64, fps: int = 10):
        options = RGBMatrixOptions()
        options.rows = rows
        options.cols = cols
        options.gpio_slowdown = 2
        options.pwm_bits = 6

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.width = cols
        self.height = rows
        self.frame_delay = 1.0 / max(1, fps)
        self.start_time = time()
        
        # Store sprite sheet config
        self.sprite_sheet = sprite_sheet
        
        # Load PNG once
        img = Image.open(sprite_sheet.full_path).convert("RGBA")
        # Composite on black to handle transparency
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
        # Keep original PNG size; do not resize. We'll crop when drawing.
        self.source_image = img
        
        # Animation state
        self.current_animation_name = None
        self.current_frame = 0
        self.current_loop = 0  # Track how many times current animation has looped
        self.sequence_index = 0
        
        # Initialize to first animation
        self._select_next_animation()

    def _select_next_animation(self) -> None:
        """Select the next animation based on mode (random or sequence)."""
        if not self.sprite_sheet.animations:
            return
        
        if self.sprite_sheet.random_mode:
            # Random selection
            self.current_animation_name = random.choice(
                [anim.name for anim in self.sprite_sheet.animations]
            )
        else:
            # Sequence mode
            if self.sequence_index >= len(self.sprite_sheet.animation_sequence):
                self.sequence_index = 0
            self.current_animation_name = self.sprite_sheet.animation_sequence[self.sequence_index]
            self.sequence_index += 1
        
        self.current_frame = 0
        self.current_loop = 0  # Reset loop counter when selecting new animation
    
    def _get_current_animation(self) -> Optional[AnimationRow]:
        """Get the currently selected animation, or None if invalid."""
        if not self.current_animation_name:
            return None
        return self.sprite_sheet.animation_dict.get(self.current_animation_name)
    
    def draw_sprite_frame(self, row_idx: int, frame_index: int, dest_x: int = 0, dest_y: int = 0) -> None:
        """Draw a single sprite frame from a specific row at (dest_x, dest_y)."""
        left = frame_index * self.sprite_sheet.sprite_width
        top = row_idx * self.sprite_sheet.sprite_height
        right = left + self.sprite_sheet.sprite_width
        bottom = top + self.sprite_sheet.sprite_height
        frame_img = self.source_image.crop((left, top, right, bottom))
        self.canvas.SetImage(frame_img, dest_x, dest_y)

    def draw_image_at(self, start_x: int, start_y: int) -> None:
        """Draw a panel-sized crop of the PNG starting at (start_x, start_y).

        Coordinates are in source PNG space. Areas outside the PNG are filled black.
        """
        panel_w, panel_h = self.width, self.height
        src = self.source_image

        # Compute intersection of requested box with source image bounds
        req_left = start_x
        req_top = start_y
        req_right = start_x + panel_w
        req_bottom = start_y + panel_h

        left = max(0, req_left)
        top = max(0, req_top)
        right = min(src.width, req_right)
        bottom = min(src.height, req_bottom)

        # Prepare an empty panel-sized image (black background)
        panel_img = Image.new("RGB", (panel_w, panel_h), (0, 0, 0))

        if right > left and bottom > top:
            crop = src.crop((left, top, right, bottom))
            # Where to paste within the panel image
            paste_x = max(0, -req_left)
            paste_y = max(0, -req_top)
            panel_img.paste(crop, (paste_x, paste_y))

        # Draw onto the canvas at the top-left of the panel
        self.canvas.SetImage(panel_img, 0, 0)

    def animate(self, frame_count: int, t_seconds: float) -> None:
        """Animate the current sprite sheet animation."""
        anim = self._get_current_animation()
        if not anim:
            return
        
        # Draw current frame
        dest_x = max(0, (self.width - self.sprite_sheet.sprite_width) // 2)
        dest_y = max(0, (self.height - self.sprite_sheet.sprite_height) // 2)
        self.draw_sprite_frame(anim.row_index, self.current_frame, dest_x, dest_y)
        
        # Advance to next frame
        self.current_frame += 1
        
        # If animation complete, check if we've looped enough times
        if self.current_frame >= anim.num_frames:
            self.current_loop += 1
            
            # Only switch to next animation if we've completed minimum loops
            if self.current_loop >= anim.min_loops:
                self._select_next_animation()
            else:
                # Loop the current animation again
                self.current_frame = 0

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
        # Configure your sprite sheet here
        # Example for ZombieCatsSprites.png (you need to fill in actual data):
        zombie_cats_sheet = SpriteSheet(
            filepath="ZombieCatsSprites.png",
            sprite_width=32,
            sprite_height=32,
            animations=[
                AnimationRow(name="idle", num_frames=10, row_index=0),
                AnimationRow(name="idle2", num_frames=10, row_index=1),
                AnimationRow(name="cry", num_frames=4, row_index=2, min_loops=2),
                AnimationRow(name="stand", num_frames=4, row_index=3, min_loops=2),
                AnimationRow(name="eat", num_frames=15, row_index=4),
                AnimationRow(name="die", num_frames=11, row_index=5),
                AnimationRow(name="sleep", num_frames=2, row_index=6, min_loops=4),
                AnimationRow(name="box1", num_frames=12, row_index=7),
                AnimationRow(name="box2", num_frames=4, row_index=8, min_loops=2),
                AnimationRow(name="box3", num_frames=4, row_index=9, min_loops=2),
                AnimationRow(name="zombie_walk", num_frames=4, row_index=10, min_loops=2),
                AnimationRow(name="shocked", num_frames=2, row_index=11, min_loops=4),
                AnimationRow(name="red", num_frames=6, row_index=12)
            ],
            # Optional: define custom play order
            # animation_sequence=["idle", "walk", "jump", "idle"]
            # Or leave None for random order
        )
        
        AnimationApp(sprite_sheet=zombie_cats_sheet).run()
    except KeyboardInterrupt:
        print('Exiting...')
        sys.exit(0)


if __name__ == "__main__":
    main()
