# game.py
# High-level game API: init_game(), tick_game(), render_game()

import random
import pygame as pg

import settings as S
from ecs import make_registry
from helpers import clamp, circles_overlap, random_vel
from commands import make_command_buffer, enqueue, cmd_spawn_player, cmd_spawn_bullet, cmd_destroy

# ------------------ initialization ------------------

def init_game():
    reg = make_registry()
    state = {
        "hits": 0,
        "commands": make_command_buffer(),  # pending commands applied by main
        "player_eid": None,                 # will be set by spawn_player command
    }

    # Enqueue initial entities (spawn only via commands)
    enqueue(state["commands"], cmd_spawn_player((S.SCREEN_W * 0.5, S.SCREEN_H * 0.5)))

    for _ in range(S.BULLET_COUNT):
        x = random.uniform(S.BULLET_RADIUS, S.SCREEN_W - S.BULLET_RADIUS)
        y = random.uniform(S.BULLET_RADIUS, S.SCREEN_H - S.BULLET_RADIUS)
        vel = random_vel(S.BULLET_SPEED_MIN, S.BULLET_SPEED_MAX)
        enqueue(state["commands"], cmd_spawn_bullet((x, y), vel))

    return reg, state

# ------------------ tick (input + logic) ------------------

def tick_game(reg, state, dt):
    """Advance game logic by dt seconds.

    This function is allowed to mutate component data (movement, velocity, etc.).
    But it must NOT create/destroy entities directly — it enqueues commands instead.
    """
    _input_player(reg, state)
    _update_movement_and_bounds(reg, dt)
    _update_collisions(reg, state)

def _input_player(reg, state):
    p = state.get("player_eid")
    if p is None or p not in reg["velocity"]:
        return

    keys = pg.key.get_pressed()
    move = pg.Vector2(0, 0)

    if keys[pg.K_w]: move.y -= 1
    if keys[pg.K_s]: move.y += 1
    if keys[pg.K_a]: move.x -= 1
    if keys[pg.K_d]: move.x += 1

    if move.length_squared() > 0:
        move = move.normalize()

    reg["velocity"][p] = move * S.PLAYER_SPEED

def _update_movement_and_bounds(reg, dt):
    # integrate entities that have velocity+transform
    for e, vel in list(reg["velocity"].items()):
        if e not in reg["transform"]:
            continue
        pos = reg["transform"][e]
        pos += vel * dt
        reg["transform"][e] = pos

        # player: clamp inside window
        if e in reg["player"] and e in reg["collider"]:
            rad = reg["collider"][e]
            pos.x = clamp(pos.x, rad, S.SCREEN_W - rad)
            pos.y = clamp(pos.y, rad, S.SCREEN_H - rad)
            reg["transform"][e] = pos

        # bullets: bounce off window edges
        if e in reg["bullet"] and e in reg["collider"]:
            rad = reg["collider"][e]

            if pos.x - rad < 0:
                pos.x = rad
                vel.x = -vel.x
            elif pos.x + rad > S.SCREEN_W:
                pos.x = S.SCREEN_W - rad
                vel.x = -vel.x

            if pos.y - rad < 0:
                pos.y = rad
                vel.y = -vel.y
            elif pos.y + rad > S.SCREEN_H:
                pos.y = S.SCREEN_H - rad
                vel.y = -vel.y

            reg["transform"][e] = pos
            reg["velocity"][e] = vel

def _update_collisions(reg, state):
    p = state.get("player_eid")
    if p is None or p not in reg["transform"] or p not in reg["collider"]:
        return

    ppos = reg["transform"][p]
    prad = reg["collider"][p]

    cmd_buf = state["commands"]

    # iterate bullets without mutating sets/dicts; enqueue destroy/spawn instead
    for b in list(reg["bullet"]):
        if b not in reg["transform"] or b not in reg["collider"]:
            continue

        bpos = reg["transform"][b]
        brad = reg["collider"][b]

        if circles_overlap(ppos, prad, bpos, brad):
            state["hits"] += 1

            # destroy bullet and spawn a new one (deferred via commands)
            enqueue(cmd_buf, cmd_destroy(b))

            new_x = random.uniform(S.BULLET_RADIUS, S.SCREEN_W - S.BULLET_RADIUS)
            new_y = random.uniform(S.BULLET_RADIUS, S.SCREEN_H - S.BULLET_RADIUS)
            new_vel = random_vel(S.BULLET_SPEED_MIN, S.BULLET_SPEED_MAX)
            enqueue(cmd_buf, cmd_spawn_bullet((new_x, new_y), new_vel))

# ------------------ rendering ------------------

def render_game(screen, reg, state, font):
    screen.fill((0, 0, 0))

    # bullets
    for e in reg["bullet"]:
        if e in reg["transform"] and e in reg["collider"]:
            pos = reg["transform"][e]
            rad = int(reg["collider"][e])
            pg.draw.circle(screen, (235, 235, 235), (int(pos.x), int(pos.y)), rad)

    # player
    p = state.get("player_eid")
    if p is not None and p in reg["transform"] and p in reg["collider"]:
        pos = reg["transform"][p]
        rad = int(reg["collider"][p])
        pg.draw.circle(screen, (120, 190, 255), (int(pos.x), int(pos.y)), rad)

    txt = font.render(f"Hits: {state['hits']}", True, (0, 255, 0))
    screen.blit(txt, (12, 10))
