
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
from typing import Union

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


TEXT_WIDTH = 60
FONT_PATH = 'fonts/Ubuntu_Mono/UbuntuMono-Regular.ttf'
BACKGROUND_COLOR = (255, 253, 232)
TEXT_COLOR = (0, 0, 0)


class Model:

    def __init__(self):
        self.reset()

    def reset(self):
        self.data_path = None
        self.anno_path = None
        self.target_path = None

        self.idx2name = {}
        self.idx2anno = {}
        self.idx2image = {}
        self.current_idx = 0

    def get_current_idx(self):
        return self.current_idx

    def all_changes_saved(self, idx):
        anno = self.read_anno_by_idx(idx)
        if anno is not None and anno == self.idx2anno[idx]:
            return True
        return False

    def next(self):
        if self.current_idx + 1 in self.idx2image:
            self.current_idx += 1

    def prev(self):
        if self.current_idx - 1 in self.idx2image:
            self.current_idx -= 1

    def get_image(self, idx):
        return self.idx2image[idx]

    def get_images(self, idx, offset=3):
        return {i: frame for i, frame in self.idx2image.items() if abs(idx - i) <= 3}

    def read_anno_by_idx(self, idx) -> Union[str, None]:

        anno_file = self.anno_path / f'{self.idx2name[idx]}.txt'
        if anno_file.exists():
            with open(str(anno_file), 'r') as file:
                return file.read()
        return None

    def get_annotation(self, idx):
        if idx not in self.idx2anno:
            self.idx2anno[idx] = ''
        return self.idx2anno[idx]

    def set_annotation(self, idx, anno):
        self.idx2anno[idx] = anno

    def open_folder(self, data_path):
        self.reset()

        self.data_path = Path(data_path)
        self.anno_path = self.data_path / 'annotation'
        self.target_path = self.data_path / 'target'

        self.anno_path.mkdir(exist_ok=True)
        self.target_path.mkdir(exist_ok=True)

        image_paths = []

        for pattern in [
            '*.png',
            '*.PNG',
            '*.jpeg',
            '*.JPEG',
            '*.jpg',
            '*.JPG'
        ]:
            image_paths.extend([x for x in self.data_path.glob(pattern)])

        image_paths = sorted(image_paths)

        if len(image_paths) == 0:
            return False

        for index, image_path in enumerate(image_paths):
            img_name = image_path.stem
            self.idx2name[index] = img_name

            image = cv2.imread(str(image_path))
            self.idx2image[index] = image

            anno = self.read_anno_by_idx(index)
            self.idx2anno[index] = anno

        self.current_idx = 0
        return True

    def save_text(self):

        text = self.idx2anno[self.current_idx]

        if len(text) == 0:
            return

        annotation_file = self.anno_path / f'{self.idx2name[self.current_idx]}.txt'
        with open(str(annotation_file), 'w') as file:
            file.write(text)

    def save_image(self):
        image = self.idx2image[self.current_idx]
        text = self.idx2anno[self.current_idx]
        image_with_text = self.get_image_with_text(image, text)
        cv2.imwrite(str(self.target_path / f'{self.idx2name[self.current_idx]}.png'), image_with_text)

    @lru_cache(maxsize=64)
    def get_font(self, font_size):
        return ImageFont.truetype(FONT_PATH, font_size)

    @staticmethod
    def background(width, height, color: (int, int, int)):
        img = np.ones(shape=(height, width, 3), dtype=np.uint8)
        for i, c in enumerate(color):
            img[:, :, i] = img[:, :, i] * c
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def get_image_with_text(self, image, text):

        if image is not None:
            h, w, _ = image.shape

            lines = []

            # TODO: problem with interim space
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
            horizontal_offset = w - text_width
            vertical_offset = font_size

            text_box_height = vertical_offset  + font_size * len(lines)

            text_box = self.background(height=text_box_height, width=w, color=BACKGROUND_COLOR)
            text_box = self.put_text(
                text_box, '\n'.join([x for x in lines]),
                x=horizontal_offset // 2,
                y=vertical_offset // 2,
                font=font,
                color=TEXT_COLOR
            )

            border = int(h * 0.025)
            header = self.background(height=border, width=w, color=BACKGROUND_COLOR)
            captioned = np.vstack([header, image, text_box])

            oh, ow, _ = captioned.shape
            side = self.background(height=oh, width=border, color=BACKGROUND_COLOR)
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

    def open_folder(self, folder_path):
        status = self.model.open_folder(folder_path)
        if status:
            self.on_frame_update()

    def on_frame_update(self):
        self.update_views('frame', None)

    def on_text_change(self, text):
        idx = self.model.get_current_idx()
        self.model.set_annotation(idx, text)

    def save_image(self):
        self.model.save_image()

    def save_text(self):
        self.model.save_text()

    def next_frame(self):
        self.model.next()
        self.on_frame_update()

    def prev_frame(self):
        self.model.prev()
        self.on_frame_update()

    def on_zoom_in(self):
        self.update_views(hint='zoom_in')

    def on_zoom_out(self):
        self.update_views(hint='zoom_out')


class Application(QApplication):
    key_pressed_signal = pyqtSignal(object)

    def __init__(self, argv: typing.List[str]):
        super().__init__(argv)

    def notify(self, receiver, e):
        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Left:
                self.key_pressed_signal.emit(e)
                return True
            elif e.key() == Qt.Key_Right:
                self.key_pressed_signal.emit(e)
                return True

        return QApplication.notify(self, receiver, e)


class UI(QObject):

    def setup_ui(self, main_window):

        main_window.setStyleSheet('background: white')

        font = QFont()
        font.setFamily("Ubuntu Mono")
        font.setPointSize(14)

        main_window.setWindowTitle('Paspartu')

        self.central_widget = QWidget(main_window)
        self.central_widget.setObjectName('central_widget')

        self.central_layout = QHBoxLayout()

        self.main = QWidget(self.central_widget)
        self.main.setObjectName('main')
        self.main_layout = QVBoxLayout(self.main)

        self.tool_bar = QToolBar()
        self.tool_bar.setFont(font)

        self.open_folder = QPushButton()
        self.open_folder.setFixedHeight(50)
        self.tool_bar.addWidget(self.open_folder)

        self.tool_bar.addSeparator()

        self.prev_frame = QPushButton()
        self.prev_frame.setFixedHeight(50)
        self.prev_frame.setToolTip('Key Left')
        self.tool_bar.addWidget(self.prev_frame)

        self.next_frame = QPushButton()
        self.next_frame.setFixedHeight(50)
        self.next_frame.setToolTip('Key Right')
        self.tool_bar.addWidget(self.next_frame)

        self.tool_bar.addSeparator()

        self.save_image = QPushButton()
        self.save_image.setFixedHeight(50)
        self.tool_bar.addWidget(self.save_image)

        self.save_text = QPushButton()
        self.save_text.setFixedHeight(50)
        self.tool_bar.addWidget(self.save_text)

        # sequence visualization
        self.sequence_view = SequenceView(self.main)
        self.sequence_view.setMaximumHeight(150)
        self.sequence_view.setFixedWidth(770)

        self.image_view = ImageView(self.main)
        self.image_view.setMaximumHeight(720)
        self.image_view.setMinimumWidth(900)
        self.image_view.setStyleSheet("background: transparent")

        self.text_box = TextEditView(self.main)
        self.text_box.setMaximumHeight(120)
        self.text_box.setFixedWidth(770)
        self.text_box.setFont(font)

        for w in [
            self.tool_bar,
            self.sequence_view,
            self.image_view,
            self.text_box
        ]:
            self.main_layout.addWidget(w, alignment=Qt.AlignHCenter)

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
        self.open_folder.setText(_translate('Wrapper', 'Open\nfolder'))
        self.prev_frame.setText(_translate('Wrapper', '<'))
        self.next_frame.setText(_translate('Wrapper', '>'))
        self.save_text.setText(_translate('Wrapper', 'Save\ntext'))
        self.save_image.setText(_translate('Wrapper', 'Save\nimage'))


class TextEditView(QTextEdit):

    def __init__(self, parent):
        super().__init__(parent=parent)

    def set_model(self, model):
        self.model = model

    def set_controller(self, controller):
        self.controller = controller

    def update_view(self, hint, data):
        if hint == 'frame':
            idx = self.model.get_current_idx()
            anno = self.model.get_annotation(idx)
            self.setPlainText(anno)


class ImageView(QGraphicsView):
    def __init__(self, parent):
        QGraphicsView.__init__(self, parent=parent)
        self.model = None
        self.controller = None
        self.scale = 1.0

        self.curr_idx = None
        self.img = None

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

    def set_model(self, model):
        self.model = model

    def set_controller(self, controller):
        self.controller = controller

    def update_view(self, hint, data):
        if hint == "frame":
            self.curr_idx = self.model.get_current_idx()
            self.img = self.model.get_image(self.curr_idx)

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


class SequenceView(QGraphicsView):
    def __init__(self, parent):
        QGraphicsView.__init__(self, parent=parent)
        self.model: Model = None
        self.controller: Controller = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setStyleSheet("background: transparent")

    def set_model(self, model: Model):
        self.model = model

    def set_controller(self, controller):
        self.controller = controller

    def add_padding(self, img, color, size):
        return cv2.copyMakeBorder(img, size, size, size, size, cv2.BORDER_CONSTANT, value=color)

    def plot_text(self, image, x, y, text, font_size):
        img = Image.fromarray(image)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_PATH, font_size)
        draw.text((x, y), text, fill=(255, 255, 255), anchor="lb", font=font, align='left')
        return np.array(img)

    def update_view(self, hint, data):

        def get_square_crop(image):
            height, width, _ = image.shape
            base = height if height <= width else width
            base -= 5
            cx = width // 2
            cy = height // 2
            x0 = cx - base // 2
            x1 = cx + base // 2
            y0 = cy - base // 2
            y1 = cy + base // 2
            return image[y0:y1, x0:x1, :]

        if hint == 'frame':
            current_idx = self.model.get_current_idx()
            idx_to_image = self.model.get_images(current_idx)

            resized_images = []

            for index in range(current_idx - 3, current_idx + 4):
                if index in idx_to_image:
                    img = idx_to_image[index]
                    crop = get_square_crop(img)
                    crop = cv2.resize(crop, dsize=(100, 100))

                    img = self.plot_text(crop, x=10, y=90, text=f'{index + 1}', font_size=30)

                    if self.model.all_changes_saved(index):
                        gray = np.zeros_like(img)
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        gray[:, :, 0] = img
                        gray[:, :, 1] = img
                        gray[:, :, 2] = img
                        img = gray
                else:
                    img = np.ones(shape=(100, 100, 3), dtype=np.uint8) * 255

                border_color = [153, 153, 0] if index == current_idx else [255, 255, 255]
                img = self.add_padding(img, color=border_color, size=5)
                resized_images.append(img)

            seq_img = cv2.hconcat(resized_images)
            self.set_image(seq_img)

    def set_image(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, colors = image.shape
        bytesPerLine = 3 * width
        qimage = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGB888)
        self.scene.clear()
        pixmap = self.scene.addPixmap(QPixmap.fromImage(qimage))
        self.ensureVisible(self.scene.sceneRect())
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        pixmap.setTransformationMode(Qt.SmoothTransformation)


class MainWindowUI(UI):

    def __init__(self):
        super().__init__()
        self.model = Model()
        self.controller = Controller(self.model)

    def setup_ui(self, main_window):
        super().setup_ui(main_window)
        self.ui = main_window
        self.open_folder.clicked.connect(self.open_folder_clicked)
        self.save_image.clicked.connect(self.save_image_clicked)
        self.save_text.clicked.connect(self.save_text_clicked)
        self.prev_frame.clicked.connect(self.prev_frame_clicked)
        self.next_frame.clicked.connect(self.next_frame_clicked)

        self.controller.add_view(self)
        self.controller.add_view(self.image_view)
        self.controller.add_view(self.sequence_view)
        self.controller.add_view(self.text_box)

        self.zoom_in.activated.connect(self.on_zoom_in)
        self.zoom_out.activated.connect(self.on_zoom_out)
        self.text_box.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        text = self.text_box.toPlainText()
        self.controller.on_text_change(text)

    @pyqtSlot()
    def on_zoom_in(self):
        self.controller.on_zoom_in()

    @pyqtSlot()
    def on_zoom_out(self):
        self.controller.on_zoom_out()

    def open_folder_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontResolveSymlinks
        folder_path = QFileDialog.getExistingDirectory(
            self.ui,
            "Open Folder",
            "/home/andrii/Desktop/hands",
            options=options)

        if folder_path:
            self.controller.open_folder(folder_path)

    def next_frame_clicked(self):
        self.controller.next_frame()

    def prev_frame_clicked(self):
        self.controller.prev_frame()

    def save_image_clicked(self):
        self.controller.save_image()

    def save_text_clicked(self):
        self.controller.save_text()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Left:
            self.prev_frame_clicked()
        elif e.key() == Qt.Key_Right:
            self.next_frame_clicked()

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
    app.key_pressed_signal.connect(ui.keyPressEvent)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    Fire(main)
