import time
import pygame
import music
import arduino
import config

pygame.init()
WIDTH, HEIGHT = 800, 550
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EIIT Project")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 32)

# layout vars
NUM_SLIDERS = 5
x_margin = 80
spacing = (WIDTH - 2 * x_margin) // NUM_SLIDERS
slider_x = [x_margin + spacing // 2 + i * spacing for i in range(NUM_SLIDERS)]
slider_y = 100
slider_h = 380
slider_w = 12
knob_r = 20

# initial values and per-slider maxima
initial_values = list(config.INITIAL_VALUES)
max_values = list(config.MAX_VALUES)
sensitivity = list(config.SENSITIVITY)
sustain_threshold = config.SUSTAIN_THRESHOLD

# state
state = {
    # committed states
    "values": list(initial_values),
    "prev_values": list(initial_values),
    # from ultrasonic sensor
    "distance": 0.0,
    # from ir sensor
    "sustain": False,

    # knob states
    "pending": list(initial_values),
    "knob_ys": [0] * NUM_SLIDERS,
    "drag": None,

    # general states
    "running": True,
    "last_commit": 0.0,
    "commit_interval": 0.5, # seconds
}

def value_to_knob(val, maxv):
    t = 0.0 if maxv == 0 else (1.0 - (val / maxv))
    return int(slider_y + max(0.0, min(1.0, t)) * slider_h)

def knob_to_value(ky, maxv):
    t = (ky - slider_y) / slider_h
    return maxv * (1.0 - max(0.0, min(1.0, t)))

# initialize knob positions
for i in range(NUM_SLIDERS):
    state["knob_ys"][i] = value_to_knob(state["values"][i], max_values[i])

def handle_inputs(st):
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            st["running"] = False
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            for i, x in enumerate(slider_x):
                if (mx - x) ** 2 + (my - st["knob_ys"][i]) ** 2 <= (knob_r + 5) ** 2:
                    st["drag"] = i
                    break
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            st["drag"] = None
        elif ev.type == pygame.MOUSEMOTION and st["drag"] is not None:
            _, my = ev.pos
            i = st["drag"]
            ky = max(slider_y, min(slider_y + slider_h, my))
            st["knob_ys"][i] = ky
            st["pending"][i] = round(knob_to_value(ky, max_values[i]), 3)

def commit_pending(st):
    now = time.time()
    st["prev_values"] = list(st["values"])
    if now - st["last_commit"] >= st["commit_interval"] and st["pending"] != st["values"]:
        st["values"] = list(st["pending"])
        st["last_commit"] = now
        # sync knob positions to committed values for non-dragged sliders
        for i in range(NUM_SLIDERS):
            if st["drag"] != i:
                st["knob_ys"][i] = value_to_knob(st["values"][i], max_values[i])
        print("Committed values:", [round(v, 3) for v in st["values"]], end="   ", flush=True)
        return True
    return False

def drawUI(scr, st):
    scr.fill((25, 25, 30))
    
    sustain_text = font.render(f"Sustain: {'On' if st['sustain'] else 'Off'}", True, (255, 255, 180))
    scr.blit(sustain_text, (WIDTH - sustain_text.get_width() - 20, 20))
    
    dist_text = font.render(f"Distance: {st['distance']:.2f}", True, (255, 255, 180))
    scr.blit(dist_text, (WIDTH - dist_text.get_width() - 20, 50))

    for i, x in enumerate(slider_x):
        pygame.draw.rect(scr, (220, 220, 220), (x - slider_w // 2, slider_y, slider_w, slider_h))
        color = (255, 80, 80) if st["drag"] == i else (230, 60, 60)
        pygame.draw.circle(scr, color, (x, int(st["knob_ys"][i])), knob_r)
        lab = font.render(f"S{i+1}", True, (255, 255, 180))
        lab_y = slider_y + slider_h + 6
        scr.blit(lab, (x - lab.get_width() // 2, lab_y))
        # show committed value on UI (not pending)
        val_str = f"{st['values'][i]:.3f}"
        val_txt = font.render(val_str, True, (0, 255, 255))
        scr.blit(val_txt, (x - val_txt.get_width() // 2, lab_y + lab.get_height() + 6))

# main logic
def run_UI():
    last_snapshot = list(state["values"])
    drawUI(screen, state)
    pygame.display.flip()

    while state["running"]:
        handle_inputs(state)
        arduino.setup()
        arduino.update_state(state, sustain_threshold)
        music.generate_music(state, sensitivity)

        # when not dragging, keep pending & knob synced to committed values
        # if state["drag"] is None:
        #     for i in range(NUM_SLIDERS):
        #         state["knob_ys"][i] = value_to_knob(state["values"][i], max_values[i])
        #         state["pending"][i] = state["values"][i]

        committed = commit_pending(state)

        # redraw on state change
        if committed or state["values"] != last_snapshot:
            drawUI(screen, state)
            pygame.display.flip()
            last_snapshot = list(state["values"])
        
        clock.tick(60)

    pygame.quit()
    print()

if __name__ == "__main__":
    run_UI()
