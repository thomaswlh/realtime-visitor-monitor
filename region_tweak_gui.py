import cv2
import numpy as np
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.button import Button
from kivy.core.window import Window

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

class ClickableImage(Image):
    """Kivy Image widget that tracks mouse position over image."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mouse_x = None
        self.mouse_y = None
        self.bind(on_touch_move=self.on_mouse_move)
        self.bind(on_touch_down=self.on_mouse_move)

    def on_mouse_move(self, instance, touch):
        if not self.collide_point(*touch.pos):
            self.mouse_x = None
            self.mouse_y = None
            return False
        # Translate widget coordinates to image pixel coordinates
        rel_x = (touch.x - self.x) / self.width
        rel_y = (touch.y - self.y) / self.height
        if hasattr(self, 'img_w') and hasattr(self, 'img_h'):
            self.mouse_x = int(rel_x * self.img_w)
            self.mouse_y = int((1 - rel_y) * self.img_h)  # flip y
        return True

class RegionTweakWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.capture = cv2.VideoCapture(0)
        ret, frame = self.capture.read()
        if not ret:
            raise RuntimeError("Cannot access camera.")
        self.img_h, self.img_w = frame.shape[:2]

        # --- Default params ---
        self.default_x = 50
        self.default_y = 50
        self.default_w = 200
        self.default_h = 120
        self.default_tilt = 0

        self.rect_x = self.default_x
        self.rect_y = self.default_y
        self.rect_w = self.default_w
        self.rect_h = self.default_h
        self.tilt_angle = self.default_tilt

        # Controls
        controls = BoxLayout(orientation='horizontal', size_hint=(1, .16), spacing=8, padding=8)
        controls.add_widget(Label(text="X:", size_hint=(.08, 1)))
        self.x_input = TextInput(text=str(self.rect_x), input_filter='int', multiline=False, size_hint=(.09, None), height=36)
        controls.add_widget(self.x_input)
        controls.add_widget(Label(text="Y:", size_hint=(.08, 1)))
        self.y_input = TextInput(text=str(self.rect_y), input_filter='int', multiline=False, size_hint=(.09, None), height=36)
        controls.add_widget(self.y_input)
        controls.add_widget(Label(text="W:", size_hint=(.08, 1)))
        self.w_slider = Slider(min=50, max=self.img_w, value=self.rect_w, step=1, size_hint=(.18, 1))
        controls.add_widget(self.w_slider)
        controls.add_widget(Label(text="H:", size_hint=(.08, 1)))
        self.h_slider = Slider(min=50, max=self.img_h, value=self.rect_h, step=1, size_hint=(.18, 1))
        controls.add_widget(self.h_slider)
        controls.add_widget(Label(text="Tilt:", size_hint=(.08, 1)))
        self.tilt_slider = Slider(min=-30, max=30, value=self.tilt_angle, step=1, size_hint=(.13, 1))
        controls.add_widget(self.tilt_slider)
        # --- Reset Button ---
        self.reset_button = Button(text="Reset", size_hint=(.08, 1), background_color=[0.9,0.3,0.3,1])
        controls.add_widget(self.reset_button)

        self.add_widget(controls)

        # Image Widget
        self.img_widget = ClickableImage(size_hint=(1, .75), allow_stretch=True, keep_ratio=True)
        self.img_widget.img_w = self.img_w
        self.img_widget.img_h = self.img_h
        self.add_widget(self.img_widget)

        # Status bar
        self.status_bar = Label(size_hint=(1, .09), font_size='16sp', halign='left', valign='middle')
        self.status_bar.bind(size=self.status_bar.setter('text_size'))
        self.add_widget(self.status_bar)

        # Binds
        self.x_input.bind(text=self.update_from_input)
        self.y_input.bind(text=self.update_from_input)
        self.w_slider.bind(value=self.update_from_slider)
        self.h_slider.bind(value=self.update_from_slider)
        self.tilt_slider.bind(value=self.update_from_slider)
        self.reset_button.bind(on_release=self.reset_params)

        # Video update
        Clock.schedule_interval(self.update, 1/30)

    def update_from_input(self, *args):
        try:
            self.rect_x = int(self.x_input.text)
        except:
            self.rect_x = 0
        try:
            self.rect_y = int(self.y_input.text)
        except:
            self.rect_y = 0

    def update_from_slider(self, instance, value):
        self.rect_w = int(self.w_slider.value)
        self.rect_h = int(self.h_slider.value)
        self.tilt_angle = int(self.tilt_slider.value)

    def reset_params(self, instance):
        self.rect_x = self.default_x
        self.rect_y = self.default_y
        self.rect_w = self.default_w
        self.rect_h = self.default_h
        self.tilt_angle = self.default_tilt
        self.x_input.text = str(self.default_x)
        self.y_input.text = str(self.default_y)
        self.w_slider.value = self.default_w
        self.h_slider.value = self.default_h
        self.tilt_slider.value = self.default_tilt

    def update(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return

        # Draw region
        polygon = keystone_polygon(self.rect_x, self.rect_y, self.rect_w, self.rect_h, self.tilt_angle, self.img_w)
        cv2.polylines(frame, [polygon], isClosed=True, color=(0, 0, 255), thickness=2)

        # Kivy image
        buf = cv2.flip(frame, 0).tostring()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_widget.texture = texture

        # --- Update status bar ---
        mouse_info = ""
        mx, my = self.img_widget.mouse_x, self.img_widget.mouse_y
        if mx is not None and my is not None:
            mouse_info = f" | Pointer: ({mx}, {my})"
        status = (f"Image Size: {self.img_w}x{self.img_h} | "
                  f"X: {self.rect_x}  Y: {self.rect_y}  "
                  f"W: {self.rect_w}  H: {self.rect_h}  "
                  f"Tilt: {self.tilt_angle}°"
                  f"{mouse_info}")
        self.status_bar.text = status

    def on_stop(self):
        self.capture.release()

class RegionTweakApp(App):
    def build(self):
        return RegionTweakWidget()

    def on_stop(self):
        self.root.on_stop()

if __name__ == '__main__':
    RegionTweakApp().run()
