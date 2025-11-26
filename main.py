import pygame  # type: ignore

pygame.init()
WIDTH, HEIGHT = 800, 550
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EIIT Project Test")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 32)

# UI layout setup
NUM_SLIDERS = 5
x_margin = 80
spacing = (WIDTH - 2 * x_margin) // NUM_SLIDERS
slider_x_positions = [x_margin + spacing // 2 + i * spacing for i in range(NUM_SLIDERS)]
slider_y = 80
slider_height = 380
slider_width = 12
knob_radius = 20

knob_ys = [slider_y for _ in range(NUM_SLIDERS)]
dragging_index = None

def knob_to_value(knob_y):
    t = (knob_y - slider_y) / slider_height
    return 1.0 - max(0.0, min(1.0, t))


# Global state container
state = {
    "knob_ys": knob_ys,
    "dragging_index": dragging_index,
    "running": True,
    "last_update_time": 0,
    "values": [0.0] * NUM_SLIDERS
}

# INPUT HANDLER
def handle_inputs(state):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state["running"] = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, x in enumerate(slider_x_positions):
                ky = state["knob_ys"][i]
                if (mx - x)**2 + (my - ky)**2 <= (knob_radius + 5)**2:
                    state["dragging_index"] = i
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            state["dragging_index"] = None

        elif event.type == pygame.MOUSEMOTION and state["dragging_index"] is not None:
            _, my = event.pos
            i = state["dragging_index"]
            state["knob_ys"][i] = max(slider_y, min(slider_y + slider_height, my))

def draw_ui(screen, state):
    screen.fill((25, 25, 30))

    for i, x in enumerate(slider_x_positions):
        # Slider bar
        pygame.draw.rect(screen, (220, 220, 220),
                         (x - slider_width // 2, slider_y, slider_width, slider_height))

        # Slider knob
        knob_color = (255, 80, 80) if state["dragging_index"] == i else (230, 60, 60)
        pygame.draw.circle(screen, knob_color, (x, int(state["knob_ys"][i])), knob_radius)

        # Label
        label = font.render(f"S{i+1}", True, (255, 255, 180))
        label_y = slider_y + slider_height + 10
        screen.blit(label, (x - label.get_width() // 2, label_y))
        # Value text
        val = f"{state['values'][i]:.3f}"
        value_text = font.render(val, True, (0, 255, 255))
        value_y = label_y + label.get_height() + 8
        screen.blit(value_text, (x - value_text.get_width() // 2, value_y))


# limit value updation at 2 times per second
def update_values(state):
    now = pygame.time.get_ticks()  # milliseconds
    if now - state["last_update_time"] >= 500:  # 500 ms = 0.5 sec → 2 updates per second
        state["last_update_time"] = now
        state["values"] = [knob_to_value(k) for k in state["knob_ys"]]

        print("Updated values:", [round(v, 3) for v in state["values"]])


#  main loop
while state["running"]:
    handle_inputs(state)
    update_values(state)
    draw_ui(screen, state)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print()
