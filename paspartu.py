
import cv2
import sys
import typing
import shutil
import textwrap

import numpy as np

from PIL import Image, ImageDraw, ImageFont
from fire import Fire
from pathlib import Path
from functools import lru_cache

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


TEXT_WIDTH = 60
FONT_PATH = 'fonts/Ubuntu_Mono/UbuntuMono-Regular.ttf'


class Model:

    def __init__(self):
        self.image_path = None
        self.image_name = None
        self.image = None

        self.target_dir = None

    def open_image(self, image_path):

        self.image_path = Path(image_path)
        self.image_name = self.image_path.name
        self.target_dir = self.image_path.parent / 'target'
        self.backup_dir = self.image_path.parent / 'backup'

        self.target_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

        try:
            image = cv2.imread(image_path)
        except:
            return False

        if image is not None:
            self.image = image
            return True
        else:
            return False

    def save_image(self, text):
        image_with_text = self.get_image_with_text(text)
        cv2.imwrite(str(self.target_dir / self.image_name), image_with_text)

        if self.image_path.exists():
            shutil.move(str(self.image_path), str(self.backup_dir / self.image_name))

    def get_image(self):
        if self.image is not None:
            return self.image

    @lru_cache(maxsize=64)
    def get_font(self, font_size):
        return ImageFont.truetype(FONT_PATH, font_size)

    def get_image_with_text(self, text):

        if self.image is not None:
            h, w, _ = self.image.shape

            lines = []

            for line in text.split('\n'):
                if len(line) > TEXT_WIDTH:
                    lines.extend([l for l in textwrap.wrap(line, width=TEXT_WIDTH)])
                else:
                    lines.append(line)

            font_size = 1
            font = self.get_font(font_size)

            while font.getsize('x' * TEXT_WIDTH)[0] < w:
                font_size += 1
                font = self.get_font(font_size)

            font_size -= 1
            font = self.get_font(font_size)

            text_width = font.getsize('x' * TEXT_WIDTH)[0]
            diff = w - text_width

            text_box_height = diff + font_size * len(lines)
            text_box = np.ones(shape=(text_box_height, w, 3), dtype=np.uint8) * 255
            text_box = self.put_text(text_box, '\n'.join([x for x in lines]),
                                     x=diff // 2, y=15,
                                     font=font, color=(0, 0, 0))

            border = int(h * 0.025)
            header = np.ones(shape=(border, w, 3), dtype=np.uint8) * 255
            captioned = np.vstack([header, self.image, text_box])

            oh, ow, _ = captioned.shape
            side = np.ones(shape=(oh, border, 3), dtype=np.uint8) * 255
            bordered = np.hstack([side, captioned, side])
            return bordered

    def put_text(self, image, text, x, y, font, color):
        image = Image.fromarray(image)
        draw = ImageDraw.Draw(image)
        draw.text((x, y), text, fill=color, font=font, align='left')
        return np.array(image)


class Controller:

    def __init__(self, model):
        self.model: Model = model
        self.views = []

    def add_view(self, view):
        view.set_model(self.model)
        view.set_controller(self)
        self.views.append(view)

    def update_views(self, hint, data=None):
        for view in self.views:
            view.update_view(hint, data)

    def update_text(self, text):
        self.update_views(hint='frame', data={'text': text})

    def on_frame_update(self, text):
        self.update_views('frame', data={'text': text})

    def open_image(self, image_path, text):
        status = self.model.open_image(image_path)
        if status:
            self.on_frame_update(text)

    def save_image(self, text):
        self.model.save_image(text)

    def on_zoom_in(self):
        self.update_views(hint='zoom_in')

    def on_zoom_out(self):
        self.update_views(hint='zoom_out')


class Application(QApplication):
    key_pressed_signal = pyqtSignal(object)

    def __init__(self, argv: typing.List[str]):
        super().__init__(argv)


class UI(QObject):

    def setup_ui(self, main_window):
        main_window.setWindowTitle('Paspartu')
        main_window.resize(1920, 1080)

        self.central_widget = QWidget(main_window)
        self.central_widget.setObjectName('central_widget')

        self.central_layout = QHBoxLayout()

        self.main = QWidget(self.central_widget)
        self.main.setObjectName('main')

        self.main_layout = QVBoxLayout(self.main)

        self.menu = QWidget(self.main)
        self.menu.setMinimumHeight(50)
        self.menu.setObjectName('tools')

        self.open_image = QPushButton(self.menu)
        self.open_image.setGeometry(QRect(20, 0, 120, 45))
        self.open_image.setObjectName('open_image')

        self.save_image = QPushButton(self.menu)
        self.save_image.setGeometry(QRect(160, 0, 120, 45))
        self.save_image.setObjectName('save_image')

        font = QFont()
        font.setFamily("Ubuntu Mono")
        font.setPointSize(14)

        self.menu.setFont(font)

        self.image_view = ImageView(self.main)
        self.image_view.setObjectName('frameView')
        self.image_view.setMaximumHeight(720)
        self.image_view.setStyleSheet("background: transparent")

        self.text_box = QTextEdit(self.main)
        self.text_box.setObjectName(('textBox'))
        self.text_box.setMaximumHeight(120)
        self.text_box.setFont(font)

        self.annotation_layout = QVBoxLayout(self.main)

        self.annotation = QWidget(self.main)

        for x in [
            self.image_view,
            self.text_box
        ]:
            self.annotation_layout.addWidget(x)

        self.annotation.setLayout(self.annotation_layout)

        for x in [
            self.menu,
            self.annotation
        ]:
            self.main_layout.addWidget(x)

        for w in [
            self.main,
        ]:
            self.central_layout.addWidget(w)

        self.zoom_in = QShortcut(QKeySequence('Ctrl+='), self.central_widget)
        self.zoom_out = QShortcut(QKeySequence('Ctrl+-'), self.central_widget)

        self.central_widget.setLayout(self.central_layout)
        main_window.setCentralWidget(self.central_widget)

        self.retranslate_ui()

        QMetaObject.connectSlotsByName(main_window)

    def retranslate_ui(self):
        _translate = QCoreApplication.translate
        self.open_image.setText(_translate('Wrapper', 'Open'))
        self.save_image.setText(_translate('Wrapper', 'Save'))


class ImageView(QGraphicsView):
    def __init__(self, parent):
        QGraphicsView.__init__(self, parent=parent)
        self.model = None
        self.controller = None
        self.scale = 1.0

        self.img = None

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

    def set_model(self, model):
        self.model = model

    def set_controller(self, controller):
        self.controller = controller

    def update_view(self, hint, data):
        if hint == "frame":
            self.img = self.model.get_image_with_text(data['text'])
        elif hint == "zoom_in":
            if self.scale < 3.0:
                self.scale += 0.1
        elif hint == 'zoom_out':
            if self.scale > 0.2:
                self.scale -= 0.1

        if self.img is not None:
            h, w, _ = self.img.shape
            h, w = int(h * self.scale), int(w * self.scale)
            rescaled = cv2.resize(self.img, (w, h))
            self.set_image(rescaled)
            self.setSceneRect(QRectF(0.0, 0.0, w, h))

    def set_image(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, colors = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

        self.scene.clear()
        pixmap = self.scene.addPixmap(QPixmap.fromImage(q_image))
        pixmap.setTransformationMode(Qt.SmoothTransformation)


class MainWindowUI(UI):

    def __init__(self):
        super().__init__()
        self.model = Model()
        self.controller = Controller(self.model)

    def setup_ui(self, main_window):
        super().setup_ui(main_window)
        self.ui = main_window
        self.open_image.clicked.connect(self.open_image_clicked)
        self.save_image.clicked.connect(self.save_image_clicked)
        self.controller.add_view(self)
        self.controller.add_view(self.image_view)

        self.zoom_in.activated.connect(self.on_zoom_in)
        self.zoom_out.activated.connect(self.on_zoom_out)

        self.text_box.textChanged.connect(self.text_changed)

    def text_changed(self):
        text = self.text_box.toPlainText()
        self.controller.update_text(text)

    @pyqtSlot()
    def on_zoom_in(self):
        self.controller.on_zoom_in()

    @pyqtSlot()
    def on_zoom_out(self):
        self.controller.on_zoom_out()

    def open_image_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontResolveSymlinks
        image_path, _ = QFileDialog.getOpenFileName(
            self.ui,
            "Open image",
            str(Path.home() / 'Desktop'),
            "Image (*.png *.jpeg *.jpg *.PNG *.JPEG *.JPG)",
            options=options)

        if image_path:
            self.controller.open_image(image_path, text=self.text_box.toPlainText())

    def save_image_clicked(self):
        text = self.text_box.toPlainText()
        self.controller.save_image(text)

    def set_model(self, model):
        pass

    def set_controller(self, controller):
        pass

    def update_view(self, hint, data=None):
        pass


def main(text_width=60):
    """
    Add a passe-partout for your photo without losing quality

    :param text_width: maximum number of characters per line in caption area
    """

    global TEXT_WIDTH
    TEXT_WIDTH = text_width

    app = Application(sys.argv)
    app.setStyle('Oxygen')
    main_window = QMainWindow()
    ui = MainWindowUI()
    ui.setup_ui(main_window)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    Fire(main)
