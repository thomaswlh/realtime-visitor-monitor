import cv2
import numpy as np
import base64
import threading
import time
from nicegui import ui

def keystone_polygon(x, y, w, h, tilt_deg, frame_width):
    tilt_rad = np.radians(tilt_deg)
    max_shift = w // 3
    shift = int(max_shift * np.sin(abs(tilt_rad)))
    if tilt_deg > 0:
        pts = np.array([
            [x + shift, y],
            [x + w - shift, y],
            [x + w, y + h],
            [x, y + h]
        ])
    else:
        pts = np.array([
            [x, y],
            [x + w, y],
            [x + w - shift, y + h],
            [x + shift, y + h]
        ])
    pts[:, 0] = np.clip(pts[:, 0], 0, frame_width - 1)
    return pts

# ---- Webcam init ----
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if not ret:
    raise RuntimeError('Cannot open camera')
img_h, img_w = frame.shape[:2]

# ---- State ----
state = {'x': 50, 'y': 50, 'w': 200, 'h': 120, 'tilt': 0, 'pointer': None}
state['cmd'] = f"python people_counter.py -p models/MobileNetSSD_deploy.prototxt -m models/MobileNetSSD_deploy.caffemodel --rect-x {state['x']} --rect-y {state['y']} --rect-w {state['w']} --rect-h {state['h']} --tilt-angle {state['tilt']}"
frame_lock = threading.Lock()
last_frame = None

# ---- UI Elements ----
with ui.row().style('align-items:center; gap:8px; padding:8px'):
    ui.label('X')
    x_slider = ui.slider(min=0, max=img_w, value=state['x']).style('width:200px').bind_value(state, 'x')
    x_input = ui.input(value=state['x'], label='').style('width:80px; height:40px').bind_value(state, 'x')

    ui.label('Y')
    y_slider = ui.slider(min=0, max=img_h, value=state['y']).style('width:200px').bind_value(state, 'y')
    y_input = ui.input(value=state['y'], label='').style('width:80px; height:40px').bind_value(state, 'y')

    ui.label('W')
    w_slider = ui.slider(min=50, max=img_w, value=state['w']).style('width:200px').bind_value(state, 'w')
    w_input = ui.input(value=state['w'], label='').style('width:80px; height:40px').bind_value(state, 'w')

    ui.label('H')
    h_slider = ui.slider(min=50, max=img_h, value=state['h']).style('width:200px').bind_value(state, 'h')
    h_input = ui.input(value=state['h'], label='').style('width:80px; height:40px').bind_value(state, 'h')

    ui.label('Tilt')
    tilt_slider = ui.slider(min=-90, max=90, value=state['tilt']).style('width:180px').bind_value(state, 'tilt')
    tilt_input = ui.input(value=state['tilt'], label='').style('width:80px; height:40px').bind_value(state, 'tilt')

    ui.button('Reset', on_click=lambda: reset()).style('height:40px; background:#f33; color:white;')

with ui.row().style('align-items:center; gap:8px; padding:8px'):
    ui.label('Generated command for people_counter.py: ')
    cmd_textbox = ui.input(value=state['cmd'], label='').style('width:1200px; height:40px').bind_value(state, 'cmd')


image = ui.interactive_image().style(f'width:{img_w}px; height:{img_h}px; cursor:crosshair;')
status = ui.label('')

def reset():
    defaults = {'x': 50, 'y': 50, 'w': 200, 'h': 120, 'tilt': 0}
    for k, v in defaults.items():
        state[k] = v
    x_input.value = state['x']
    y_input.value = state['y']
    w_slider.value = state['w']
    h_slider.value = state['h']
    tilt_slider.value = state['tilt']


def on_click(e):
    ox, oy = e.args['offsetX'], e.args['offsetY']

    display_w = img_w  # 或者你在 style 設定的顯示寬度
    display_h = img_h  # 或者你在 style 設定的顯示高度

    px = int(ox * img_w / display_w)
    py = int(oy * img_h / display_h)
    state['pointer'] = (px, py)
    

image.on('click', on_click)

# ---- Background Thread: Grab & encode frames ----
def camera_loop():
    global last_frame
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        try:
            pts = keystone_polygon(
                int(state['x']),
                int(state['y']),
                int(state['w']),
                int(state['h']),
                int(state['tilt']),
                img_w
            )
        except:
            continue
        finally:
            state['cmd'] = f"python people_counter.py -p models/MobileNetSSD_deploy.prototxt -m models/MobileNetSSD_deploy.caffemodel --rect-x {state['x']} --rect-y {state['y']} --rect-w {state['w']} --rect-h {state['h']} --tilt-angle {state['tilt']}"
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
        _, buf = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buf).decode('utf-8')
        with frame_lock:
            last_frame = f'data:image/jpeg;base64,{img_b64}'
        time.sleep(1 / 60)  # Limit to 60 FPS

threading.Thread(target=camera_loop, daemon=True).start()

# ---- UI Timer Update ----
def update_image():
    with frame_lock:
        if last_frame:
            image.set_source(last_frame)
    ptr = state['pointer']
    ptr_text = f' | Pointer: ({ptr[0]}, {ptr[1]})' if ptr else ''
    status.text = (
        f'Image: {img_w}×{img_h} | '
        f'X:{state["x"]} Y:{state["y"]} '
        f'W:{state["w"]} H:{state["h"]} '
        f'Tilt:{state["tilt"]}°{ptr_text}'
    )


ui.timer(1/60, update_image)  # Update UI ~30 FPS
ui.run()
