"""
SCAMP Example: Leaf Loops

Generative process behind Marc Evanstein's "Leaf Loops" for violin and viola. The shapes, note attack points,
and worm shape for several different leaves are found in the LeafPoints directory.
"""

import pygame
import json
import math
import numpy as np
from shapely.geometry import LineString
from scamp import *
from scamp_extensions.pitch import Scale
import random

# ---------------------------------- Parameters -------------------------------------

WHICH_LEAF = "LeafPoints/dwarfBirch"
INSTRUMENT = "Vibraphone"
WORM_SPEED = 0.4
ROTATION_SPEED = 3  # Adjusted speed for leaf rotation
PITCH_RANGE = 30, 100

# SCALE = Scale.blues(34)
# SCALE = Scale.chromatic(64)
# SCALE = Scale.diatonic(55)
SCALE = Scale.from_pitches([40, 45, 47, 50, 52, 55, 55.86, 57, 59, 60.86, 61.69, 62,
                            64, 65.86, 66.69, 67, 69, 70.86, 71.69, 74, 76.69, 79], cycle=False)


# ---------------------------------- Music Setup -------------------------------------


s = Session().run_as_server()

# vibes = s.new_midi_part(INSTRUMENT, "MIDI Through Port 1", note_on_and_off_only=True)
vibes = s.new_part(INSTRUMENT, "vibraphone", note_on_and_off_only=True)


def get_pitch_from_length(dist):
    return SCALE.round(
        PITCH_RANGE[1] - dist * (PITCH_RANGE[1] - PITCH_RANGE[0])
    )

# ----------------------------------- Animation ---------------------------------------

WIDTH = 1200
DOT_WIDTH = 18
NOTE_LINE_WIDTH = 9
LEAF_OUTLINE_LINE_WIDTH = 6
LEAF_MINER_LINE_WIDTH = 10
PLAYBACK_DOT_SWELL_FACTOR = 2
PLAYBACK_DOT_SWELL_DECAY_FACTOR = 0.92

# Load configurations
def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)
    
    
# Load the leaf ring, worm curve, and attack points
leaf_ring_coords = load_json(f"{WHICH_LEAF}.json")
try:
    worm_curve_coords = load_json(f"{WHICH_LEAF}Worm.json")
except FileNotFoundError:
    worm_curve_coords = [[0.5, 0.5], [0.50001, 0.50001]]

# Convert to shapely LineString for interpolation
leaf_ring = LineString(leaf_ring_coords)
worm_curve = LineString(worm_curve_coords)
# worm_curve = LineString([(0.5, 0.8), (0.5, 0.8001)])


attack_points = load_json(f"{WHICH_LEAF}AttackPoints.json")
#attack_points = [leaf_ring.length * (i + 1)/ 400 for i in range(400)]


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, WIDTH))
pygame.display.set_caption('Leaf Animation')
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (19, 19, 19)
LEAF_COLOR = (0, 0, 255)
WORM_COLOR = (255, 0, 0)
LINE_COLOR = (0, 128, 0)

start_time = pygame.time.get_ticks()
leaf_progress = 0
worm_progress = 0
next_attack_idx = 0

playback_dot_swell_factor = 1


def render_bg_surface(upscale_factor=4):
    surface = pygame.Surface((WIDTH * upscale_factor, WIDTH * upscale_factor), pygame.SRCALPHA)
    
    # Draw leaf and worm paths
    pygame.draw.lines(surface, WHITE, True, [(int(x * WIDTH* upscale_factor), int(y * WIDTH* upscale_factor))
                                             for x, y in leaf_ring_coords], LEAF_OUTLINE_LINE_WIDTH * upscale_factor)
    pygame.draw.lines(surface, (100, 100, 100), False, [(int(x * WIDTH* upscale_factor), int(y * WIDTH* upscale_factor))
                                                        for x, y in worm_curve_coords], LEAF_MINER_LINE_WIDTH * upscale_factor)

    return pygame.transform.smoothscale(surface, (WIDTH, WIDTH))


leaf_bg = render_bg_surface(4)
    
    
def play_note():
    global playback_dot_swell_factor
    playback_dot_swell_factor = PLAYBACK_DOT_SWELL_FACTOR
    vibes.end_all_notes()
    pitch = get_pitch_from_length(math.hypot(
        (worm_position[0] - leaf_position[0]), (worm_position[1] - leaf_position[1])
    )) 
    vibes.start_note(pitch, random.uniform(0.5, 0.9))


# Main loop
running = True
while running:
    screen.fill(BLACK)
    current_time = (pygame.time.get_ticks() - start_time) / 1000  # In seconds

    # Update positions on leaf and worm paths
    leaf_progress = (leaf_progress + ROTATION_SPEED * clock.get_time() / 1000) % leaf_ring.length
    worm_progress = (worm_progress + WORM_SPEED * clock.get_time() / 1000) % worm_curve.length

    # Leaf position on leaf ring
    leaf_position = leaf_ring.interpolate(leaf_progress).coords[0]
    leaf_pos = (int(leaf_position[0] * WIDTH), int(leaf_position[1] * WIDTH))

    # Worm position on worm curve
    worm_position = worm_curve.interpolate(worm_progress).coords[0]
    worm_pos = (int(worm_position[0] * WIDTH), int(worm_position[1] * WIDTH))

    # Draw background
    screen.blit(leaf_bg, (0, 0))

    # Draw line between leaf and worm
    pygame.draw.line(screen, LINE_COLOR, leaf_pos, worm_pos, NOTE_LINE_WIDTH)
    
    # Draw dots for leaf and worm positions
    pygame.draw.circle(screen, LEAF_COLOR, leaf_pos, DOT_WIDTH * playback_dot_swell_factor)
    pygame.draw.circle(screen, WORM_COLOR, worm_pos, DOT_WIDTH)

    # Check if we crossed an attack point
    attack_point = attack_points[next_attack_idx]
    if abs(leaf_progress - attack_point) < ROTATION_SPEED * 0.05:
        # Trigger a visual effect (e.g., change colors or line width)
        next_attack_idx = (next_attack_idx + 1) % len(attack_points)
        play_note()

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if playback_dot_swell_factor > 1:
        playback_dot_swell_factor = max(PLAYBACK_DOT_SWELL_DECAY_FACTOR * playback_dot_swell_factor, 1)
        
    pygame.display.flip()
    clock.tick(60)  # Cap to 60 FPS

pygame.quit()