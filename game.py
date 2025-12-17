# CSCE 31903 Programming Paradigms
# Name: Adedayo Arigbede
# Date: 12/01/25
# Assignment 7 

import pygame
import time
import json
import math
import random

from pygame.locals import *
from time import sleep

# Constants
SPRITES_DIR = "sprites/"    # Holds all sprite images
VIEW_W = 800                # Room width
VIEW_H = 600                # Room height
WORLD_W = 3500              # World Width
WORLD_H = 3000              # World Height
LINK_SPEED = 9              # Link speed
BOOMERANG_SPEED = 8         # Boomerang speed
RUPEE_DELAY = 5             # Frames before rupee becomes collectible
RUPEE_TTL = 40              # Rupee timespan
FPS_DELAY = 0.04
EDIT_BOX = pygame.Rect(10, 10, 220, 60) # Edit box

# Loads Sprites
# Convert_alpha() converts images to the same pixel format
def load_image(path):
    img = pygame.image.load(path)
    return img.convert_alpha() if pygame.display.get_surface() else img

# Handles collision
def aabb_collide(a, b):
    return not (a.x + a.w <= b.x or a.x >= b.x + b.w or a.y + a.h <= b.y or a.y >= b.y + b.h)


# Sprite class
class Sprite():
    def __init__(self, x, y, w, h, image_path=None):
        self.x = float(x)
        self.y = float(y)
        self.w = int(w)
        self.h = int(h)
        self.valid = True
        self.dead = False
        self.to_remove = False
        self._img = load_image(image_path) if image_path else None

    # Update method
    def update(self):
        return self.valid

    # Saves sprites to map.json
    def marshal(self):
        return {
            "x": int(self.x),
            "y": int(self.y)
        }
    
    # Returns image
    def get_draw_image(self):
        return self._img
    
    # Type guards
    def is_tree(self):
        return False
    def is_chest(self):
        return False
    def is_item(self):
        return False
    def is_link(self):
        return False
    def is_boomerang(self):
        return False
    def is_cucco(self):
        return False

# Tree class
class Tree(Sprite):
    TREE_W = 75     # Tree width
    TREE_H = 100    # Tree height

    # Loads Trees
    def __init__(self, x, y, w=None, h=None):
            super().__init__(x, y, w or Tree.TREE_W, h or Tree.TREE_H, SPRITES_DIR + "tree.png")
    def is_tree(self):
        return True

# TreasureChest class
class TreasureChest(Sprite):
    CHEST_W = 71    # Chest width
    CHEST_H = 72    # Chest height
    
    # Loads TreasureChest
    def __init__(self, x, y, w=None, h=None):
        super().__init__(x, y, w or TreasureChest.CHEST_W, h or TreasureChest.CHEST_H, SPRITES_DIR + "treasurechest.png")
                         
        self.opened = False     # Draws chest if false (Draws rupee if true)
        self.timer = 0          # Counts frames if opened
        self._rupee_img = load_image(SPRITES_DIR + "rupee.png")
    
    def is_chest(self):
        return True
    def is_item(self):
        return not self.opened
    
    # Timer starts once chest is opened (rupee appears)
    def open(self):
        if not self.opened:
            self.opened = True
            self.timer = 0
    
    # Returns true once rupee delay passes
    def can_collect(self):
        return self.opened and self.timer >= RUPEE_DELAY
    
    def collect(self):
        self.timer = RUPEE_DELAY + RUPEE_TTL + 1

    # Update method (counts down rupee lifetime)
    def update(self):
        if self.opened:
            self.timer += 1
            if self.timer > RUPEE_DELAY + RUPEE_TTL:
                self.dead = True
        return True
    
    # Draws either rupee or chest depending on state
    def get_draw_image(self):
        return self._rupee_img if self.opened else super().get_draw_image()

# Boomerang Class
class Boomerang(Sprite):
    def __init__(self, cx, cy, direction):
        super().__init__(cx, cy, 24, 24, None)
        self.frames = [load_image(SPRITES_DIR + f"boomerang{i}.png") for i in range(1, 5)]
        self.animate = 0

        # Shoots from the center of Link
        self.x -= self.w / 2
        self.y -= self.h / 2

        # Handles Velocity
        if direction == "left":
            self.vx = -BOOMERANG_SPEED
            self.vy = 0
        elif direction == "right":
            self.vx = BOOMERANG_SPEED
            self.vy = 0
        elif direction == "up":
            self.vx = 0
            self.vy = -BOOMERANG_SPEED
        else:
            self.vx = 0
            self.vy = BOOMERANG_SPEED
    
    def is_boomerang(self):
        return True
    def kill(self):
        self.dead = True

    # Update Method
    def update(self):
        if self.dead:
            self.to_remove = True
            return False
        self.x += self.vx
        self.y += self.vy
        self.animate += 1

        # Off-world cleanup
        if (self.x + self.w < 0) or (self.y + self.h < 0) or (self.x > WORLD_W) or (self.y > WORLD_H):
            self.to_remove = True
        return True
    
    # Draws boomerang (cylces images as it animates)
    def get_draw_image(self):
        if self.frames:
            return self.frames[(self.animate // 3) % len(self.frames)]
        return super().get_draw_image()
    
# Link class
class Link(Sprite):
    LINK_W = 48     # Link width
    LINK_H = 48     # Link height

    # Load Link
    def __init__(self, x, y):
        super().__init__(x, y, Link.LINK_W, Link.LINK_H, SPRITES_DIR + "link1.png")
        
        # Previous position
        self.px = self.x
        self.py = self.y 

        # Velocity
        self.dx = 0
        self.dy = 0

        # Handles animation
        self.direction = "down"
        self.moving = False
        self.frames = [load_image(SPRITES_DIR + f"link{i}.png") for i in range(1, 45)]
        self.frame = 0
        self.frameDelay = 1
        self.frameCounter = 0

        # Cycles Link's frame based on direction (11 frames per direction)
        self.dirBase = {"down": 0, "left": 11, "right": 22, "up": 33}

    def is_link(self):
        return True
    
    # Sets velocity based on direction
    def set_input(self, ax, ay):
        self.dx = ax
        self.dy = ay

        if ax > 0:
            self.direction = "right"
        elif ax < 0:
            self.direction = "left"
        elif ay > 0:
            self.direction = "down"
        elif ay < 0:
            self.direction = "up"
        self.moving = (ax != 0 or ay != 0)
    
    def begin_frame(self):
        self.px = self.x
        self.py = self.y

    # Pushes Link back to object depending on which side he entered from
    # Previous position is used to help determine which side
    def push_back(self, ob):
        if self.py + self.h <= ob.y:
            self.y = ob.y - self.h      # from above
        elif self.py >= ob.y + ob.h:
            self.y = ob.y + ob.h        # from below
        elif self.px + self.w <= ob.x:
            self.x = ob.x - self.w      # from left
        elif self.px >= ob.x + ob.w:
            self.x = ob.x + ob.w        # from right

    # Update method
    def update(self):
        self.begin_frame()
        self.x += self.dx
        self.y += self.dy

        #clamp to world
        if self.x < 0:
            self.x = 0
        if self.y < 0:
            self.y = 0
        if self.x > WORLD_W - self.w: self.x = WORLD_W - self.w
        if self.y > WORLD_H - self.h: self.y = WORLD_H - self.h

        # Animates Link as he moves
        if self.moving:
            self.frameCounter += 1
            if self.frameCounter >= self.frameDelay:
                self.frame = (self.frame + 1) % 11
                self.frameCounter = 0
        else:
            self.frame = 0
            self.frameCounter = 0
        return True
    
    # Draws Link's frames based on movement 
    def get_draw_image(self):
        if len(self.frames) == 44:
            base = self.dirBase.get(self.direction, 0)
            return self.frames[base + self.frame]
        return super().get_draw_image()

# Cucco Class
class Cucco(Sprite):
    COUNT = 0           # Number of cuccos
    HITS = 0            # Number of hits from either Link or the boomerangs
    ANGRY = False       # angry flag
    DISAPPEARED = 0     # Number of cuccos that disappeared    
    linkx = 0.0         # Link center x
    linky = 0.0         # Link center y

    CUCCO_W = 40        # Cucco width
    CUCCO_H = 32        # Cucco height

    # Resets flock state
    @staticmethod
    def reset():
        Cucco.COUNT = 0
        Cucco.HITS = 0
        Cucco.ANGRY = False
        Cucco.DISAPPEARED = 0

    # Draws Cucco
    def __init__(self, x, y):
        super().__init__(x, y, Cucco.CUCCO_W, Cucco.CUCCO_H, None)
        Cucco.COUNT += 1

        # Handles movement when Cucco is not angry
        self.roam_speed = 2.0
        self.xdir = random.choice([-1, 1])
        self.ydir = random.choice([-1, 1])
        
        # Handles movement when Cucco is angry
        self.angry_speed = 5.0
        self.attached = False
        self.attach_timer = 0

        # Handles animation
        self.animate = 0
        self.facing_right = True

        # Images drawn based on Cucco's mood
        self.images_left = [
            load_image(SPRITES_DIR + "cucco1.png"),
            load_image(SPRITES_DIR + "cucco2.png")
        ]

        self.images_right = [
            load_image(SPRITES_DIR + "cucco3.png"),
            load_image(SPRITES_DIR + "cucco4.png")
        ]

        self.angry_left = [
            load_image(SPRITES_DIR + "angrycucco1.png"),
            load_image(SPRITES_DIR + "angrycucco2.png")
        ]

        self.angry_right = [
            load_image(SPRITES_DIR + "angrycucco3.png"), 
            load_image(SPRITES_DIR + "angrycucco4.png")
        ]

        # Bounce side resolution
        self.px = self.x
        self.py = self.y
    
    def is_cucco(self):
        return True
    
    def begin_frame(self):
        self.px = self.x
        self.py = self.y

    # Hit counter (Flock becomes angry if hit >= 5 times and more than one cucco is alive)
    def is_hit(self):
        Cucco.HITS += 1
        if Cucco.HITS >= 5 and Cucco.COUNT > 1:
            Cucco.ANGRY = True
    
    # Resolves bouncing off an item (only when not angry)
    def _bounce_from_item(self, ob):
        if self.py + self.h <= ob.y:
            #from above
            self.y = ob.y - self.h
            self.ydir *= -1
        elif self.py >= ob.y + ob.h:
            # from below
            self.y = ob.y + ob.h
            self.ydir *= -1
        elif self.px + self.w <= ob.x:
            # from left
            self.x = ob.x - self.w
            self.xdir *= -1
        elif self.px >= ob.x + ob.w:
            # from right
            self.x = ob.x + ob.w
            self.xdir *= -1
    
    # Update method
    def update(self, link=None):
        self.begin_frame()
        self.animate += 1
    
        # Calms the flock
        if Cucco.COUNT <= 1 or Cucco.DISAPPEARED >= 3:
            Cucco.ANGRY = False
            Cucco.HITS = 0
            Cucco.DISAPPEARED = 0
        
        # Cucco stays attached to Link until timer runs out
        if self.attached:
            if link:
                self.x = link.x + link.w/2 - self.w/2
                self.y = link.y + link.h/2 - self.h/2
            self.attach_timer -= 1
            if self.attach_timer <= 0:
                self.to_remove = True
                Cucco.COUNT = max(0, Cucco.COUNT - 1)
                Cucco.DISAPPEARED += 1
            return True
        
        # Cucco flues towards Link if angry
        if Cucco.ANGRY and link is not None:
            dx = (Cucco.linkx - self.x)
            dy = (Cucco.linky - self.y)
            dist = math.hypot(dx, dy)
            if dist < 0.001:
                dist = 0.001
            self.x += (dx / dist) * self.angry_speed
            self.y += (dy / dist) * self.angry_speed
            self.facing_right = dx >= 0
        
        # Cucco simply roams 
        else:
            self.x += self.xdir * self.roam_speed
            self.y += self.ydir * self.roam_speed
            self.facing_right = (self.xdir > 0)

            if self.x < 0:
                self.x = 0; self.xdir = +1
            if self.x + self.w > WORLD_W:
                self.x = WORLD_W - self.w; self.xdir = -1
            if self.y < 0:
                self.y = 0; self.ydir = +1
            if self.y + self.h > WORLD_H:
                self.y = WORLD_H - self.h; self.ydi = -1
        
        return True
    
    # Triggers pecking for 20 frames
    def attach_to_link(self):
        if not self.attached:
            self.attached = True
            self.attach_timer = 20
        
    # Draws cucco based on mood
    def get_draw_image(self):
        idx = (self.animate // 8) % 2
        if Cucco.ANGRY or self.attached:
            return self.angry_right[idx] if self.facing_right else self.angry_left[idx]
        else:
            return self.images_right[idx] if self.facing_right else self.images_left[idx]

# Model Class
class Model():
    filename = "map.json"
    
    def __init__(self):
        self.sprites = []
        self.link = Link(200, 300)
        self.sprites.append(self.link)

        # Camera position
        self.camX = 0
        self.camY = 0

        # HUD counter
        self.rupees = 0

        # Edit mode
        self.items = ["Tree", "Chest", "Cucco"]
        self.add_type = "Tree"
        
        # Shows sprites in edit-box
        self.sprite = {
            "Tree": load_image(SPRITES_DIR + "tree.png"),
            "Chest": load_image(SPRITES_DIR + "treasurechest.png"),
            "Cucco": load_image(SPRITES_DIR + "cucco3.png")
        }

        # Loads map
        self.load_map()
        
        # Ensures atleast one Cucco is one screen
        if not any(s.is_cucco() for s in self.sprites):
            self.sprites.append(Cucco(self.link.x + 100, self.link.y))
        
    
    # Save items to map.json
    def save_map(self):
        trees = []
        chests = []
        cuccos = []
        for s in self.sprites:
            if s.is_tree():
                trees.append(s.marshal())
            elif s.is_chest():
                chests.append(s.marshal())
            elif s.is_cucco():
                cuccos.append(s.marshal())
        data = {
            "trees": trees,
            "chests": chests,
            "cuccos": cuccos,
            "linkx": int(self.link.x),
            "linky": int(self.link.y)
        }
        with open(Model.filename, "w") as f:
            json.dump(data, f)

    # Loads items from map.json
    def load_map(self):
        self.sprites = [self.link]
        self.rupees = 0
        Cucco.reset()
        try:
            with open(Model.filename) as f:
                data = json.load(f)
        except FileNotFoundError:
            return
        
        trees = data.get("trees", [])
        chests = data.get("chests", [])
        cuccos = data.get("cuccos", [])
        self.link.x = data.get("linkx", 200)
        self.link.y = data.get("linky", 300)
        for e in trees:
            self.sprites.append(Tree(e["x"], e["y"]))
        for e in chests:
            self.sprites.append(TreasureChest(e["x"], e["y"]))
        for e in cuccos:
            self.sprites.append(Cucco(e["x"], e["y"]))
    

    # Clear map    
    def clear_map(self):
        self.sprites = [self.link]
        self.rupees = 0
        Cucco.reset()
        self.sprites.append(Cucco(self.link.x + 120, self.link.y))

    # Add selected sprite to game world
    # Screen click is converted to world coordinates
    def add_at(self, screen_pos):
        wx = screen_pos[0] + self.camX
        wy = screen_pos[1] + self.camY
        if self.add_type == "Tree":
            self.sprites.append(Tree(wx, wy))
        elif self.add_type == "Chest":
            self.sprites.append(TreasureChest(wx, wy))
        elif self.add_type == "Cucco":
            self.sprites.append(Cucco(wx, wy))

    # Allows link to throw boomerang from middle of his chest
    def throw_boomerang(self):
        cx = self.link.x + self.link.w/2
        cy = self.link.y + self.link.h/2
        self.sprites.append(Boomerang(cx, cy, self.link.direction))
    
    # Displays ruppee counter
    def _collect_rupee(self, chest):
        self.rupees += 1
        chest.collect()

    # Update method
    def update(self):
        for i in range(len(self.sprites) - 1, -1, -1):
            s = self.sprites[i]
            if isinstance(s, Cucco):
                s.update(self.link)
            else:
                s.update()
            if getattr(s, "dead", False) or getattr(s, "to_remove", False):
                self.sprites.pop(i)
            
        # Ensures at least one Cucco is on screen
        if not any(s.is_cucco() for s in self.sprites):
            self.sprites.append(Cucco(self.link.x + 80, self.link.y + 40))

        # Collison handling
        n = len(self.sprites)
        for i in range(n):
            a = self.sprites[i]
            for j in range(i + 1, n):
                b = self.sprites[j]
                if not aabb_collide(a, b):
                    continue

                # Link vs Tree or Chest (Link pushes back when chest is closed)
                if a.is_link() and (b.is_tree() or (b.is_chest() and b.is_item())):
                    a.push_back(b)
                elif b.is_link() and (a.is_tree() or (a.is_chest() and a.os_item())):
                    b.push_back(a)

                # Link vs chest (Collects if chest is open)
                if a.is_link() and b.is_chest():
                    if not b.opened:
                        a.push_back(b); b.open()
                    elif b.can_collect():
                        self._collect_rupee(b)
                elif b.is_link() and a.is_chest():
                    if not a.opened:
                        b.push_back(a); a.open()
                    elif a.can_collect():
                        self._collect_rupee(a)

                # Boomerang vs Tree (Boomerang dies after collision)
                if a.is_boomerang() and b.is_tree():
                    a.kill()
                elif b.is_boomerang() and a.is_tree():
                    b.kill()
                
                # Boomerang vs Chest (Boomerang dies after collison)
                if a.is_boomerang() and b.is_chest():
                    if not b.opened:
                        b.open()
                    else:
                        self._collect_rupee(b)
                        a.kill()
                elif b.is_boomerang() and a.is_chest():
                    if not a.opened:
                        a.open()
                    else: 
                        self._collect_rupee(a)
                        b.kill()
                
                # Helps cucco bounce off items
                def cucco_bounce(cucco, item):
                    if isinstance(cucco, Cucco) and not Cucco.ANGRY:
                        cucco._bounce_from_item(item)
                
                # Cucco vs Tree or chest (Bounces when he's not angry)
                if a.is_cucco() and (b.is_tree() or b.is_chest()):
                    cucco_bounce(a, b)
                elif b.is_cucco() and (a.is_tree() or a.is_chest()):
                    cucco_bounce(b, a)

                # Cucco vs Link (Attaches to Link when angry, hit count total increases)
                if a.is_cucco() and b.is_link():
                    if not Cucco.ANGRY:
                        a._bounce_from_item(b)
                    a.is_hit()
                    if Cucco.ANGRY:
                        a.attach_to_link()
                elif b.is_cucco() and a.is_link():
                    if not Cucco.ANGRY:
                        b._bounce_from_item(a)
                    b.is_hit()
                    if Cucco.ANGRY:
                        b.attach_to_link()

                # Boomerang vs Cucco (Boomerang dies after collion, hit count total increases)
                # Attaches to Link when hit
                if a.is_boomerang() and b.is_cucco():
                    b.is_hit(); a.kill()
                    if Cucco.ANGRY:
                        b.attach_to_link()
                elif b.is_boomerang() and a.is_cucco():
                    a.is_hit(); b.kill()
                    if Cucco.ANGRY:
                        a.attach_to_link()

        # Snaps camera to room
        midx = self.link.x + self.link.w/2
        midy = self.link.y + self.link.h/2
        roomX = int(midx // VIEW_W)
        roomY = int(midy // VIEW_H)
        self.camX = max(0, min(roomX * VIEW_W, WORLD_W - VIEW_W))
        self.camY = max(0, min(roomY * VIEW_H, WORLD_H - VIEW_H))

                        
# View Class
class View():
    def __init__(self, model):
        self.model = model
        self.screen = pygame.display.set_mode((VIEW_W, VIEW_H), 32)

    def update(self):
        # change background color if the user is in edit_mode
        if Controller.edit_mode:
            self.screen.fill([146, 203, 146]) #light green
        else:
            self.screen.fill([72, 152, 72]) #dark forest green

        # draw sprites to the screen
        for s in self.model.sprites:
            img = s.get_draw_image()
            draw_x = int(s.x - self.model.camX)
            draw_y = int(s.y - self.model.camY)
            if img is not None:
                self.screen.blit(pygame.transform.scale(img, (s.w, s.h)), (draw_x, draw_y))
            else:
                pygame.draw.rect(self.screen, (255, 213, 79), pygame.Rect(draw_x, draw_y, s.w, s.h))

        # add text to the screen
        # Default font, size 32
        font = pygame.font.SysFont(None, 32)   
        text = f"Rupees: {self.model.rupees}    Mode: {'EDIT' if Controller.edit_mode else 'GAME'} Add: {self.model.add_type}"
        surf = font.render(text, True, (0, 0, 0))
        self.screen.blit(surf, (VIEW_W - surf.get_width() - 12, 10))

        # Edit mode
        if Controller.edit_mode:
            pygame.draw.rect(self.screen, (235, 255, 235), EDIT_BOX, border_radius = 8)
            pygame.draw.rect(self.screen, (30, 120, 30), EDIT_BOX, 2, border_radius = 8)
            s1 = font.render("Click to cycle item", True, (0, 60, 0))
            self.screen.blit(s1, (EDIT_BOX.x + 8, EDIT_BOX.y + 8))

            # Shows sprite in edix box (scaled to fit in the box)
            sprite = self.model.sprite.get(self.model.add_type)
            if sprite:
                max_w = EDIT_BOX.width - 20
                max_h = EDIT_BOX.height - 30
                iw, ih = sprite.get_width(), sprite.get_height()
                scale = min(max_w / iw, max_h / ih, 1.0)
                pw, ph = max(1, int(iw * scale)), max(1, int(ih * scale))
                px = EDIT_BOX.x + (EDIT_BOX.width - pw) // 2
                py = EDIT_BOX.y + EDIT_BOX.height - ph - 6
                self.screen.blit(pygame.transform.scale(sprite, (pw, ph)), (px, py))
        
        # update display screen
        pygame.display.flip()

# Controller Class
class Controller():
    edit_mode = False
    
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.keep_going = True
        self.key_space = False

    def update(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.keep_going = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE or event.key == K_q:
                    self.keep_going = False
            elif event.type == pygame.MOUSEBUTTONUP:
                if Controller.edit_mode:
                    mouse_pos = pygame.mouse.get_pos()
                    if EDIT_BOX.collidepoint(mouse_pos):
                        i = self.model.items.index(self.model.add_type)
                        self.model.add_type = self.model.items[(i + 1) % len(self.model.items)]
                    else:
                        self.model.add_at(mouse_pos)
            elif event.type == pygame.KEYUP: #this is keyReleased!
                if event.key == K_c:
                    self.model.clear_map()
                    print("Map cleared and game reset")
                if event.key == K_e:
                    Controller.edit_mode = not Controller.edit_mode
                if event.key == K_l:
                    self.model.load_map()
                    print("Map loaded")
                if event.key == K_s:
                    self.model.save_map()
                    print("Map saved")
                if event.key == K_SPACE:
                    self.key_space = False
        

        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        if keys[K_LEFT]:
            dx -= LINK_SPEED
        if keys[K_RIGHT]:
            dx += LINK_SPEED
        if keys[K_UP]:
            dy -= LINK_SPEED
        if keys[K_DOWN]:
            dy += LINK_SPEED
        self.model.link.set_input(dx, dy)

        # Throws boomerang
        if keys[K_SPACE] and not self.key_space and not Controller.edit_mode:
            self.key_space = True
            self.model.throw_boomerang()
        
        Cucco.linkx = self.model.link.x + self.model.link.w/2
        Cucco.linky = self.model.link.y + self.model.link.h/2

print("Use the arrow keys to move. Press Esc to quit.")
pygame.init()
pygame.font.init()
m = Model()
v = View(m)
c = Controller(m, v)
while c.keep_going:
    c.update()
    m.update()
    v.update()
    sleep(0.04)
print("Goodbye!")