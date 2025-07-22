#!/usr/bin/env python3
"""
Simple test script to generate a 5-second black screen video with text overlay.
Uses MoviePy for easy experimentation with TextClip settings.
"""

from moviepy import ColorClip, TextClip, CompositeVideoClip
import textwrap


def create_black_screen_with_text():
    """Creates a 5-second 1080x1920 black screen video with text overlay."""

    # Create black background clip (5 seconds, 1080x1920)
    black_clip = ColorClip(size=(1080, 1920), color=(255, 255, 255), duration=5)

    wrapped_text = "\n".join(
        textwrap.wrap(
            "Hello World! These are some subtitles I am hoping don't get pushed off the screen!",
            width=25,  # Adjust this number to control line length
        )
    )
    # Create text clip - experiment with these settings
    text_clip = (
        TextClip(
            "./test/static/Roboto-Var.ttf",
            text=wrapped_text,
            font_size=60,
            color="black",
            stroke_color="white",
            margin=(10, 20),
            stroke_width=2,
            method="caption",
            size=(1000, None),  # Width is fixed, height is auto-calculated
            text_align="center",
        )
        .with_position("center", 0.45)
        .with_duration(5)
    )

    # Composite the text over the black background
    final_video = CompositeVideoClip([black_clip, text_clip])

    # Write the video file
    output_path = "test/output_black_screen_text.mp4"
    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

    print(f"Video saved to: {output_path}")


if __name__ == "__main__":
    create_black_screen_with_text()

