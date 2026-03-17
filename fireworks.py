#!/usr/bin/env python3
import time
import os
import random
import sys

# ANSI color codes
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    RESET = '\033[0m'

Fore = Colors()

class Firework:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.exploded = False
        self.particles = []
        self.lifetime = 0
        self.max_lifetime = random.randint(20, 40)

    def update(self):
        if not self.exploded:
            self.y -= 1
            if self.y <= random.randint(5, 10):
                self.explode()
        else:
            self.lifetime += 1
            for p in self.particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vy'] += 0.1  # gravity
            self.particles = [p for p in self.particles if p['y'] < 30 and p['y'] > 0 and abs(p['x']) < 40]

    def explode(self):
        self.exploded = True
        num_particles = random.randint(20, 40)
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(1, 3)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'vx': speed * 2 if abs(self.x) < 5 else speed * 1.5 * (1 if self.x > 0 else -1),
                'vy': speed * 1.5 * (-1 if random.random() < 0.5 else -0.5)
            })

    def get_chars(self):
        if not self.exploded:
            return [(self.x, self.y, '*')]
        else:
            chars = []
            for p in self.particles:
                dist = (p['x'] - self.x) ** 2 + (p['y'] - self.y) ** 2
                if dist < 5:
                    char = '@'
                elif dist < 15:
                    char = 'O'
                elif dist < 30:
                    char = 'o'
                else:
                    char = '.'
                chars.append((p['x'], p['y'], char))
            return chars

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def countdown():
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    for i in range(10, 0, -1):
        clear_screen()
        color = random.choice(colors)
        print("\n" * 10)
        print(color + f"\n          {i}".center(50), flush=True)
        time.sleep(1)

    clear_screen()
    print("\n" * 10)
    print(Fore.YELLOW + "\n          🎆 FIREWORKS! 🎆".center(50))
    time.sleep(1)

def fireworks_animation():
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.WHITE]
    fire_works = []
    width = 80
    height = 30

    try:
        while True:
            clear_screen()
            frame = [[' ' for _ in range(width)] for _ in range(height)]

            # Randomly launch new fireworks
            if random.random() < 0.1:
                fire_works.append(Firework(
                    x=random.randint(-30, 30),
                    y=height - 1,
                    color=random.choice(colors)
                ))

            # Update and draw fireworks
            for fw in fire_works:
                fw.update()
                for x, y, char in fw.get_chars():
                    draw_x = width // 2 + int(x)
                    draw_y = int(y)
                    if 0 <= draw_x < width and 0 <= draw_y < height:
                        frame[draw_y][draw_x] = char

            # Remove dead fireworks
            fire_works = [fw for fw in fire_works if not (fw.exploded and fw.lifetime > fw.max_lifetime)]

            # Print frame
            print("\033[?25l")  # Hide cursor
            print("\n".join("".join(row) for row in frame))
            print("\n" + Fore.WHITE + "Press Ctrl+C to exit".center(width))
            time.sleep(0.05)

    except KeyboardInterrupt:
        clear_screen()
        print("\n" * 10)
        print(Fore.GREEN + "Fireworks show ended! Thanks for watching!".center(50))
        print("\033[?25h")  # Show cursor

if __name__ == "__main__":
    try:
        countdown()
        fireworks_animation()
    except KeyboardInterrupt:
        clear_screen()
        print("\n" * 10)
        print(Fore.YELLOW + "Program interrupted. Goodbye!".center(50))
        sys.exit(0)