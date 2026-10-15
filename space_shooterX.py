import pygame
import random
import math
import sys
import os
import json
import array

pygame.init()

_info = pygame.display.Info()
# Leave room for the taskbar/title bar so the whole window is always visible.
WIDTH = max(640, min(900, _info.current_w - 80))
HEIGHT = max(480, min(650, _info.current_h - 140))

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Galaxy Defender")
clock = pygame.time.Clock()
FPS = 60

WHITE = (255, 255, 255)
BLACK = (10, 10, 20)
RED = (255, 60, 60)
GREEN = (60, 255, 120)
BLUE = (80, 160, 255)
YELLOW = (255, 220, 60)
PURPLE = (200, 80, 255)
CYAN = (80, 255, 255)
ORANGE = (255, 150, 50)
GOLD = (255, 200, 60)
GRAY = (140, 140, 160)

font_huge = pygame.font.SysFont("consolas", 80, bold=True)
font_big = pygame.font.SysFont("consolas", 52, bold=True)
font_med = pygame.font.SysFont("consolas", 30, bold=True)
font_small = pygame.font.SysFont("consolas", 20)
font_tiny = pygame.font.SysFont("consolas", 16)

# ---------------------------------------------------------------------------
# Procedural sound effects (no external audio files needed)
# ---------------------------------------------------------------------------
SAMPLE_RATE = 44100
SOUND_ENABLED = True
SFX = {}

try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)

    def make_tone(freq=440, duration=0.1, volume=0.3, wave="square", sweep_to=None):
        n = int(SAMPLE_RATE * duration)
        buf = array.array('h', [0] * n * 2)
        for i in range(n):
            t = i / SAMPLE_RATE
            f = freq if sweep_to is None else freq + (sweep_to - freq) * (i / n)
            if wave == "square":
                val = 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0
            else:
                val = math.sin(2 * math.pi * f * t)
            env = min(1.0, i / 200) * min(1.0, (n - i) / 200)
            s = int(val * volume * 32767 * env)
            buf[2 * i] = s
            buf[2 * i + 1] = s
        return pygame.mixer.Sound(buffer=buf.tobytes())

    SFX = {
        "shoot": make_tone(880, 0.045, 0.12, "square"),
        "hit": make_tone(200, 0.05, 0.15, "square"),
        "explosion": make_tone(140, 0.28, 0.28, "square", sweep_to=35),
        "powerup": make_tone(440, 0.15, 0.25, "sine", sweep_to=880),
        "levelup": make_tone(523, 0.22, 0.3, "sine", sweep_to=1046),
        "gameover": make_tone(320, 0.7, 0.3, "sine", sweep_to=60),
        "select": make_tone(600, 0.06, 0.2, "square"),
        "playerhit": make_tone(160, 0.15, 0.28, "square", sweep_to=60),
    }
except Exception:
    SOUND_ENABLED = False


def play(name):
    if SOUND_ENABLED and name in SFX:
        try:
            SFX[name].play()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# High score persistence
# ---------------------------------------------------------------------------
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")


def load_highscore():
    try:
        with open(HS_FILE) as f:
            return int(json.load(f).get("high_score", 0))
    except Exception:
        return 0


def save_highscore(score):
    try:
        with open(HS_FILE, "w") as f:
            json.dump({"high_score": score}, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def draw_text(surf, text, font, color, x, y, center=True, alpha=None):
    img = font.render(text, True, color)
    if alpha is not None:
        img.set_alpha(alpha)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surf.blit(img, rect)


def draw_panel(surf, rect, fill=(20, 20, 40), border=CYAN, border_w=2, radius=12, alpha=210):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*fill, alpha), (0, 0, rect.width, rect.height), border_radius=radius)
    pygame.draw.rect(panel, border, (0, 0, rect.width, rect.height), border_w, border_radius=radius)
    surf.blit(panel, rect.topleft)


def make_gradient(w, h, top, bottom):
    surf = pygame.Surface((w, h))
    for y in range(h):
        r = y / h
        c = tuple(int(top[i] + (bottom[i] - top[i]) * r) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (w, y))
    return surf


BG_GRADIENT = make_gradient(WIDTH, HEIGHT, (8, 8, 24), (28, 12, 42))


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
class Star:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.speed = random.uniform(0.5, 3)
        self.size = random.choice([1, 1, 1, 2, 2, 3])

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.uniform(0, WIDTH)

    def draw(self, surf):
        b = min(255, 120 + self.speed * 40)
        pygame.draw.circle(surf, (b, b, b), (int(self.x), int(self.y)), self.size)


class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(20, 40)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            a = max(0, self.life / self.max_life)
            size = max(1, int(self.size * a))
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), size)


class FloatingText:
    def __init__(self, x, y, text, color, big=False):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 45
        self.max_life = 45
        self.font = font_med if big else font_small

    def update(self):
        self.y -= 1.1
        self.life -= 1

    def draw(self, surf):
        alpha = max(0, int(255 * (self.life / self.max_life)))
        draw_text(surf, self.text, self.font, self.color, self.x, self.y, alpha=alpha)


class Bullet:
    def __init__(self, x, y, vx, vy, color, damage=1, size=3, friendly=True, pierce=0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.damage = damage
        self.size = size
        self.friendly = friendly
        self.pierce = pierce
        self.rect = pygame.Rect(x - size, y - size, size * 2, size * 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (self.x, self.y)

    def draw(self, surf):
        glow = pygame.Surface((self.size * 5, self.size * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 70), (self.size * 2.5, self.size * 2.5), self.size * 2.2)
        surf.blit(glow, (self.x - self.size * 2.5, self.y - self.size * 2.5))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), max(1, self.size - 2))

    def offscreen(self):
        return self.y < -20 or self.y > HEIGHT + 20 or self.x < -20 or self.x > WIDTH + 20


class PowerUp:
    TYPES = ["rapid", "spread", "shield", "life"]
    COLORS = {"rapid": YELLOW, "spread": PURPLE, "shield": CYAN, "life": GREEN}

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.type = random.choice(self.TYPES)
        self.color = self.COLORS[self.type]
        self.rect = pygame.Rect(x - 12, y - 12, 24, 24)
        self.t = 0

    def update(self, player=None):
        self.t += 1
        pulled = False
        if player is not None and getattr(player, "magnet", 0) > 0:
            dx, dy = player.x - self.x, player.y - self.y
            dist = math.hypot(dx, dy) or 1
            if dist < player.magnet:
                speed = 9
                self.x += dx / dist * speed
                self.y += dy / dist * speed
                pulled = True
        if not pulled:
            self.y += 1.5
        self.rect.center = (self.x, self.y)

    def draw(self, surf):
        bob = math.sin(self.t * 0.1) * 3
        pygame.draw.rect(surf, self.color, (self.x - 10, self.y - 10 + bob, 20, 20), border_radius=5)
        pygame.draw.rect(surf, WHITE, (self.x - 10, self.y - 10 + bob, 20, 20), 2, border_radius=5)
        draw_text(surf, self.type[0].upper(), font_small, BLACK, self.x, self.y + bob)


class Enemy:
    def __init__(self, x, y, kind="basic", wave=1):
        self.x, self.y = x, y
        self.kind = kind
        self.t = 0
        self.hit_flash = 0
        self.shoot_timer = random.randint(30, 90)
        if kind == "basic":
            self.hp = 2 + wave // 3
            self.speed = 1.5 + wave * 0.05
            self.color = RED
            self.size = 16
            self.score = 10
        elif kind == "zigzag":
            self.hp = 2 + wave // 3
            self.speed = 2 + wave * 0.05
            self.color = ORANGE
            self.size = 14
            self.score = 15
        elif kind == "shooter":
            self.hp = 3 + wave // 2
            self.speed = 1 + wave * 0.03
            self.color = PURPLE
            self.size = 18
            self.score = 25
        elif kind == "boss":
            self.hp = 40 + wave * 10
            self.speed = 0.8
            self.color = (255, 40, 100)
            self.size = 45
            self.score = 300
        self.max_hp = self.hp
        self.rect = pygame.Rect(x - self.size, y - self.size, self.size * 2, self.size * 2)

    def update(self):
        self.t += 1
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.kind == "basic":
            self.y += self.speed
        elif self.kind == "zigzag":
            self.y += self.speed
            self.x += math.sin(self.t * 0.08) * 3
        elif self.kind == "shooter":
            if self.y < 120:
                self.y += self.speed
            else:
                self.x += math.sin(self.t * 0.03) * 1.5
        elif self.kind == "boss":
            if self.y < 100:
                self.y += self.speed
            else:
                self.x += math.sin(self.t * 0.02) * 2
        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.rect.center = (self.x, self.y)
        self.shoot_timer -= 1

    def want_shoot(self):
        if self.kind in ("shooter", "boss") and self.shoot_timer <= 0 and self.y > 60:
            self.shoot_timer = random.randint(70, 130) if self.kind == "shooter" else random.randint(20, 40)
            return True
        return False

    def draw(self, surf):
        s = self.size
        color = WHITE if self.hit_flash > 0 else self.color
        pts = [(self.x, self.y + s), (self.x - s, self.y - s), (self.x, self.y - s * 0.4), (self.x + s, self.y - s)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)
        if self.hp < self.max_hp:
            w = s * 2
            pygame.draw.rect(surf, (60, 0, 0), (self.x - w / 2, self.y - s - 14, w, 5))
            pygame.draw.rect(surf, GREEN, (self.x - w / 2, self.y - s - 14, w * (self.hp / self.max_hp), 5))


class Player:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT
        self.speed = 6.0
        self.size = 14
        self.hp = 5
        self.max_hp = 5
        self.rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)
        self.cooldown = 0
        self.fire_rate = 12
        self.bullet_damage = 1
        self.bullet_count = 1
        self.pierce = 0
        self.magnet = 0
        self.rapid_timer = 0
        self.spread_timer = 0
        self.shield_timer = 0
        self.invuln = 0

    def update(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += self.speed
        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.y = max(self.size, min(HEIGHT - self.size, self.y))
        self.rect.center = (self.x, self.y)
        if self.cooldown > 0: self.cooldown -= 1
        if self.rapid_timer > 0: self.rapid_timer -= 1
        if self.spread_timer > 0: self.spread_timer -= 1
        if self.shield_timer > 0: self.shield_timer -= 1
        if self.invuln > 0: self.invuln -= 1

    def shoot(self, bullets, particles):
        rate = 5 if self.rapid_timer > 0 else self.fire_rate
        if self.cooldown > 0:
            return
        self.cooldown = rate
        play("shoot")
        for _ in range(3):
            particles.append(Particle(self.x, self.y + self.size * 0.6, CYAN))
        if self.spread_timer > 0:
            angles = (-0.35, -0.2, -0.07, 0, 0.07, 0.2, 0.35)
            for ang in angles:
                bullets.append(Bullet(self.x, self.y - self.size, math.sin(ang) * 8, -math.cos(ang) * 8,
                                       CYAN, damage=self.bullet_damage, pierce=self.pierce))
        else:
            n = self.bullet_count
            spacing = 12
            start_x = self.x - spacing * (n - 1) / 2
            for i in range(n):
                bx = start_x + i * spacing
                bullets.append(Bullet(bx, self.y - self.size, 0, -10, CYAN,
                                       damage=self.bullet_damage, pierce=self.pierce))

    def draw(self, surf):
        if self.invuln > 0 and self.invuln % 10 < 5:
            return
        s = self.size
        pts = [(self.x, self.y - s), (self.x - s, self.y + s), (self.x, self.y + s * 0.4), (self.x + s, self.y + s)]
        pygame.draw.polygon(surf, BLUE, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)
        if self.shield_timer > 0:
            pygame.draw.circle(surf, CYAN, (int(self.x), int(self.y)), s + 10, 2)
        if self.magnet > 0:
            pygame.draw.circle(surf, (*PURPLE,), (int(self.x), int(self.y)), int(self.magnet), 1)


# ---------------------------------------------------------------------------
# Upgrades (roguelike-style permanent choices offered between waves)
# ---------------------------------------------------------------------------
def _reinforce(p):
    p.max_hp += 1
    p.hp = min(p.max_hp, p.hp + 1)


UPGRADES = [
    {"name": "Rapid Reload", "desc": "Fire rate +20%",
     "apply": lambda p: setattr(p, "fire_rate", max(3, int(p.fire_rate * 0.8)))},
    {"name": "Heavy Rounds", "desc": "+1 bullet damage",
     "apply": lambda p: setattr(p, "bullet_damage", p.bullet_damage + 1)},
    {"name": "Twin Cannons", "desc": "+1 parallel shot",
     "apply": lambda p: setattr(p, "bullet_count", p.bullet_count + 1)},
    {"name": "Piercing Rounds", "desc": "Bullets pierce +1 enemy",
     "apply": lambda p: setattr(p, "pierce", p.pierce + 1)},
    {"name": "Reinforced Hull", "desc": "+1 max HP, heal 1",
     "apply": _reinforce},
    {"name": "Afterburners", "desc": "Move speed +15%",
     "apply": lambda p: setattr(p, "speed", round(p.speed * 1.15, 2))},
    {"name": "Salvage Magnet", "desc": "Pulls in power-ups",
     "apply": lambda p: setattr(p, "magnet", p.magnet + 90)},
]


def spawn_wave(wave):
    enemies = []
    if wave % 5 == 0:
        enemies.append(Enemy(WIDTH / 2, -60, "boss", wave))
        return enemies
    count = 4 + wave
    for _ in range(count):
        kind = random.choices(["basic", "zigzag", "shooter"], weights=[5, 3, max(1, wave - 2)])[0]
        x = random.randint(60, WIDTH - 60)
        y = -random.randint(40, 400)
        enemies.append(Enemy(x, y, kind, wave))
    return enemies


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.stars = [Star() for _ in range(140)]
        self.high_score = load_highscore()
        self.state = "menu"
        self.upgrade_rects = []
        self.upgrade_choices = []
        self.new_high = False
        self.banner_timer = 0
        self.banner_text = ""
        self.start_button = pygame.Rect(0, 0, 220, 56)
        self.start_button.center = (WIDTH / 2, int(HEIGHT * 0.38))
        self.reset_run()

    def reset_run(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.powerups = []
        self.particles = []
        self.floaters = []
        self.wave = 0
        self.score = 0
        self.shake = 0
        self.combo = 0
        self.combo_timer = 0
        self.new_high = False

    def start_run(self):
        self.reset_run()
        self.state = "playing"
        self.next_wave()

    def next_wave(self):
        self.wave += 1
        self.enemies = spawn_wave(self.wave)
        self.banner_text = "BOSS WAVE" if self.wave % 5 == 0 else f"WAVE {self.wave}"
        self.banner_timer = 130
        if self.wave > 1:
            play("levelup")

    def show_upgrades(self):
        self.state = "upgrade"
        self.upgrade_choices = random.sample(UPGRADES, 3)
        play("levelup")

    def choose_upgrade(self, index):
        if 0 <= index < len(self.upgrade_choices):
            self.upgrade_choices[index]["apply"](self.player)
            play("select")
            self.state = "playing"
            self.next_wave()

    def add_score(self, base):
        self.combo += 1
        self.combo_timer = 90
        multiplier = min(1 + (self.combo - 1) * 0.15, 4.0)
        gained = int(base * multiplier)
        self.score += gained
        return gained, multiplier

    # ---- event handling ----
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if self.state == "menu":
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    play("select")
                    self.start_run()
                elif event.key == pygame.K_ESCAPE:
                    return False
            elif self.state == "playing":
                if event.key == pygame.K_ESCAPE:
                    self.state = "paused"
            elif self.state == "paused":
                if event.key == pygame.K_ESCAPE:
                    self.state = "playing"
                elif event.key == pygame.K_q:
                    self.state = "menu"
            elif self.state == "upgrade":
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self.choose_upgrade(0)
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    self.choose_upgrade(1)
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    self.choose_upgrade(2)
            elif self.state == "gameover":
                if event.key == pygame.K_r:
                    play("select")
                    self.start_run()
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.state == "menu" and self.start_button.collidepoint(mx, my):
                play("select")
                self.start_run()
            elif self.state == "upgrade":
                for i, rect in enumerate(self.upgrade_rects):
                    if rect.collidepoint(mx, my):
                        self.choose_upgrade(i)
                        break
        return True

    # ---- update ----
    def update(self):
        for s in self.stars:
            s.update()

        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys)
        if keys[pygame.K_SPACE]:
            self.player.shoot(self.bullets, self.particles)

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if not b.offscreen()]
        for b in self.enemy_bullets: b.update()
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.offscreen()]

        for e in self.enemies:
            e.update()
            if e.want_shoot():
                dx, dy = self.player.x - e.x, self.player.y - e.y
                dist = math.hypot(dx, dy) or 1
                spd = 5
                self.enemy_bullets.append(Bullet(e.x, e.y, dx / dist * spd, dy / dist * spd, ORANGE, friendly=False))

        for p in self.powerups: p.update(self.player)
        self.powerups = [p for p in self.powerups if p.y < HEIGHT + 30]

        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        for f in self.floaters: f.update()
        self.floaters = [f for f in self.floaters if f.life > 0]

        for e in self.enemies[:]:
            if e.kind != "boss" and e.y - e.size > HEIGHT:
                self.enemies.remove(e)

        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        if self.banner_timer > 0:
            self.banner_timer -= 1

        self._handle_collisions()

        if not self.enemies and self.state == "playing":
            self.show_upgrades()

        if self.shake > 0:
            self.shake -= 1

    def _handle_collisions(self):
        for b in self.bullets[:]:
            hit = None
            for e in self.enemies:
                if b.rect.colliderect(e.rect):
                    hit = e
                    break
            if hit is None:
                continue
            e = hit
            e.hp -= b.damage
            e.hit_flash = 6
            play("hit")
            for _ in range(6):
                self.particles.append(Particle(b.x, b.y, e.color))
            if b.pierce > 0:
                b.pierce -= 1
            elif b in self.bullets:
                self.bullets.remove(b)
            if e.hp <= 0:
                gained, mult = self.add_score(e.score)
                color = GOLD if mult > 1.5 else WHITE
                self.floaters.append(FloatingText(e.x, e.y, f"+{gained}", color, big=(mult > 2)))
                self.shake = 12 if e.kind == "boss" else 6
                play("explosion")
                for _ in range(30 if e.kind == "boss" else 15):
                    self.particles.append(Particle(e.x, e.y, e.color))
                if random.random() < (0.9 if e.kind == "boss" else 0.18):
                    self.powerups.append(PowerUp(e.x, e.y))
                if e in self.enemies:
                    self.enemies.remove(e)

        for b in self.enemy_bullets[:]:
            if b.rect.colliderect(self.player.rect) and self.player.invuln <= 0:
                self.enemy_bullets.remove(b)
                self._damage_player()

        for e in self.enemies[:]:
            if e.rect.colliderect(self.player.rect) and self.player.invuln <= 0:
                if self.player.shield_timer > 0:
                    self.player.shield_timer = 0
                    e.hp -= 5
                    if e.hp <= 0 and e in self.enemies:
                        self.enemies.remove(e)
                else:
                    self._damage_player()

        for p in self.powerups[:]:
            if p.rect.colliderect(self.player.rect):
                self.powerups.remove(p)
                play("powerup")
                if p.type == "rapid": self.player.rapid_timer = 400
                elif p.type == "spread": self.player.spread_timer = 400
                elif p.type == "shield": self.player.shield_timer = 600
                elif p.type == "life": self.player.hp = min(self.player.max_hp, self.player.hp + 1)

    def _damage_player(self):
        if self.player.shield_timer > 0:
            self.player.shield_timer = max(0, self.player.shield_timer - 60)
            return
        self.player.hp -= 1
        self.player.invuln = 60
        self.shake = 10
        play("playerhit")
        for _ in range(10):
            self.particles.append(Particle(self.player.x, self.player.y, RED))
        if self.player.hp <= 0:
            self.state = "gameover"
            if self.score > self.high_score:
                self.high_score = self.score
                self.new_high = True
                save_highscore(self.score)
            play("gameover")

    # ---- drawing ----
    def draw(self):
        screen.blit(BG_GRADIENT, (0, 0))

        offset_x = random.randint(-self.shake, self.shake) if self.shake > 0 else 0
        offset_y = random.randint(-self.shake, self.shake) if self.shake > 0 else 0

        temp = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for s in self.stars: s.draw(temp)

        if self.state in ("playing", "paused", "upgrade", "gameover"):
            for p in self.particles: p.draw(temp)
            for e in self.enemies: e.draw(temp)
            for b in self.bullets: b.draw(temp)
            for b in self.enemy_bullets: b.draw(temp)
            for p in self.powerups: p.draw(temp)
            if self.state != "gameover": self.player.draw(temp)
            for f in self.floaters: f.draw(temp)

        screen.blit(temp, (offset_x, offset_y))

        if self.state == "menu":
            self.draw_menu()
        elif self.state in ("playing", "paused", "upgrade"):
            self.draw_hud()
            if self.banner_timer > 0:
                self.draw_banner()
            if self.state == "paused":
                self.draw_pause()
            elif self.state == "upgrade":
                self.draw_upgrade()
        elif self.state == "gameover":
            self.draw_hud()
            self.draw_gameover()

        pygame.display.flip()

    def draw_menu(self):
        draw_text(screen, "GALAXY DEFENDER", font_big, CYAN, WIDTH / 2, int(HEIGHT * 0.14))
        draw_text(screen, "a procedurally-scored arcade shooter", font_small, GRAY, WIDTH / 2, int(HEIGHT * 0.22))

        mx, my = pygame.mouse.get_pos()
        hover = self.start_button.collidepoint(mx, my)
        draw_panel(screen, self.start_button, fill=(30, 90, 60) if hover else (20, 60, 40), border=GREEN)
        draw_text(screen, "START", font_med, WHITE, self.start_button.centerx, self.start_button.centery)

        draw_text(screen, f"HIGH SCORE: {self.high_score}", font_med, GOLD, WIDTH / 2, int(HEIGHT * 0.50))

        panel_w = min(520, WIDTH - 40)
        panel_top = int(HEIGHT * 0.58)
        panel_h = HEIGHT - panel_top - int(HEIGHT * 0.06)
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.centerx = WIDTH / 2
        panel.top = panel_top
        draw_panel(screen, panel, fill=(15, 15, 30), border=(80, 80, 120))
        lines = [
            "WASD / Arrows: Move        SPACE: Fire",
            "Survive waves, collect power-ups, and pick",
            "a permanent upgrade after every wave clear.",
            "ESC: Pause     R: Restart after Game Over",
        ]
        line_gap = max(18, min(28, (panel_h - 30) // max(1, len(lines))))
        start_y = panel.top + max(18, (panel_h - line_gap * len(lines)) // 2) + line_gap // 2
        for i, line in enumerate(lines):
            draw_text(screen, line, font_tiny, WHITE, panel.centerx, start_y + i * line_gap)

    def draw_hud(self):
        draw_text(screen, f"Score: {self.score}", font_med, WHITE, 10, 10, center=False)
        draw_text(screen, f"Wave: {self.wave}", font_med, WHITE, 10, 45, center=False)
        draw_text(screen, f"Best: {self.high_score}", font_tiny, GOLD, 10, 80, center=False)

        for i in range(self.player.max_hp):
            color = RED if i < self.player.hp else (60, 60, 60)
            pygame.draw.polygon(screen, color, [
                (WIDTH - 30 - i * 35, 25), (WIDTH - 45 - i * 35, 15), (WIDTH - 15 - i * 35, 15)
            ])

        buff_y = 50
        if self.player.rapid_timer > 0:
            draw_text(screen, "RAPID", font_small, YELLOW, WIDTH - 90, buff_y); buff_y += 20
        if self.player.spread_timer > 0:
            draw_text(screen, "SPREAD", font_small, PURPLE, WIDTH - 90, buff_y); buff_y += 20
        if self.player.shield_timer > 0:
            draw_text(screen, "SHIELD", font_small, CYAN, WIDTH - 90, buff_y)

        if self.combo >= 3 and self.combo_timer > 0:
            mult = min(1 + (self.combo - 1) * 0.15, 4.0)
            pulse = 1.0 + 0.08 * math.sin(pygame.time.get_ticks() * 0.02)
            size = int(34 * pulse)
            f = pygame.font.SysFont("consolas", size, bold=True)
            draw_text(screen, f"COMBO x{self.combo}  ({mult:.1f}x)", f, GOLD, WIDTH / 2, 40)

    def draw_banner(self):
        t = self.banner_timer
        alpha = 255
        if t > 100:
            alpha = int(255 * (130 - t) / 30)
        elif t < 30:
            alpha = int(255 * t / 30)
        draw_text(screen, self.banner_text, font_big, ORANGE, WIDTH / 2, 150, alpha=max(0, alpha))

    def draw_pause(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "PAUSED", font_big, WHITE, WIDTH / 2, HEIGHT / 2 - 40)
        draw_text(screen, "ESC to Resume   |   Q for Menu", font_small, GRAY, WIDTH / 2, HEIGHT / 2 + 20)

    def draw_upgrade(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        heading_y = int(HEIGHT * 0.13)
        draw_text(screen, "WAVE CLEAR — CHOOSE AN UPGRADE", font_med, GOLD, WIDTH / 2, heading_y)

        gap = 20
        side_margin = 20
        card_w = min(230, (WIDTH - 2 * side_margin - 2 * gap) / 3)
        top_space = heading_y + 40
        bottom_space = HEIGHT - int(HEIGHT * 0.08)
        card_h = max(150, min(260, bottom_space - top_space))
        total_w = 3 * card_w + 2 * gap
        start_x = (WIDTH - total_w) / 2
        y = top_space + (bottom_space - top_space - card_h) / 2
        mx, my = pygame.mouse.get_pos()

        self.upgrade_rects = []
        for i, up in enumerate(self.upgrade_choices):
            rect = pygame.Rect(start_x + i * (card_w + gap), y, card_w, card_h)
            self.upgrade_rects.append(rect)
            hover = rect.collidepoint(mx, my)
            draw_panel(screen, rect, fill=(35, 35, 65) if hover else (20, 20, 40),
                       border=GOLD if hover else CYAN)
            line_gap = max(16, min(22, card_h * 0.09))
            draw_text(screen, f"[{i + 1}]", font_small, GRAY, rect.centerx, rect.top + card_h * 0.11)
            draw_text(screen, up["name"], font_small, WHITE, rect.centerx, rect.top + card_h * 0.28)
            words = up["desc"].split(" ")
            line = ""
            ty = rect.top + card_h * 0.48
            for w in words:
                test = (line + " " + w).strip()
                if font_tiny.size(test)[0] > card_w - 30:
                    draw_text(screen, line, font_tiny, GRAY, rect.centerx, ty)
                    ty += line_gap
                    line = w
                else:
                    line = test
            if line:
                draw_text(screen, line, font_tiny, GRAY, rect.centerx, ty)

        hint_y = min(y + card_h + 30, HEIGHT - 15)
        draw_text(screen, "Press 1 / 2 / 3, or click a card", font_tiny, GRAY, WIDTH / 2, hint_y)

    def draw_gameover(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "GAME OVER", font_huge, RED, WIDTH / 2, HEIGHT / 2 - 90)
        draw_text(screen, f"Final Score: {self.score}   Wave: {self.wave}", font_med, WHITE, WIDTH / 2, HEIGHT / 2 - 20)
        if self.new_high:
            pulse = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() * 0.02)
            f = pygame.font.SysFont("consolas", int(30 * pulse), bold=True)
            draw_text(screen, "NEW HIGH SCORE!", f, GOLD, WIDTH / 2, HEIGHT / 2 + 25)
        draw_text(screen, "Press R to Restart  |  ESC for Menu", font_small, GRAY, WIDTH / 2, HEIGHT / 2 + 75)

    def run(self):
        running = True
        while running:
            clock.tick(FPS)
            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
