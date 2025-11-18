import PIL.ImageQt
import PyQt6.QtGui
import PyQt6.QtWidgets
import json
import os
import qrcode


def json_file_read(filename):
    """reads filename with json inside and returns file data as dict

    param filename: filename to read
    type filename: str

    return: return dict of data from json file, empty dict returned if error in reading file or json
    rtype: dict
    """
    try:
        with open(file=filename, mode='r') as file:
            data = json.load(file)
    except Exception as e:
        print("Oops Error: {}".format(e))
        data = {}
        return data
    return data


class QRGuiApp:
    """QT App to generate and show QR Codes"""

    def __init__(self):
        """QT App init"""
        # read config
        filename = "{}/{}".format(os.getcwd(), "config/config.json")
        self.data = json_file_read(filename)

        # init qt app
        self.app = PyQt6.QtWidgets.QApplication([])
        self.main_window = PyQt6.QtWidgets.QWidget()
        if self.data.get("icon", False):
            self.main_window.setWindowIcon(PyQt6.QtGui.QIcon(self.data.get("icon", False)))
        self.main_window.setWindowTitle(self.data.get("main_window_name", "TGA"))

        # create layout with textbox, button, label, button
        layout = PyQt6.QtWidgets.QVBoxLayout()

        self.textbox = PyQt6.QtWidgets.QLineEdit(self.data.get("textbox", "https://vaultcity.net"))
        layout.addWidget(self.textbox)

        # add button to layout and connect button to function
        button_generate = PyQt6.QtWidgets.QPushButton("Generate")
        button_generate.clicked.connect(self.on_click_button_gen)
        layout.addWidget(button_generate)

        self.img_label = PyQt6.QtWidgets.QLabel()
        self.on_click_button_gen()
        layout.addWidget(self.img_label)

        # add button to layout and connect button to function
        button_save = PyQt6.QtWidgets.QPushButton("Save")
        button_save.clicked.connect(self.on_click_button_save)
        layout.addWidget(button_save)

        # set generated layout on main window
        self.main_window.setLayout(layout)

    def on_click_button_gen(self):
        """method to run after generate button clicked

        generates new qr code from textbox and shows it
        """
        img = qrcode.make(self.textbox.text())
        pixmap = PyQt6.QtGui.QPixmap.fromImage(PIL.ImageQt.ImageQt(img))
        self.img_label.setPixmap(pixmap)

    def on_click_button_save(self):
        """method to run after save button is clicked

        open save file dialog and save qr code image
        """
        self.on_click_button_gen()
        filename = PyQt6.QtWidgets.QFileDialog.getSaveFileName(None, "Save QR Code",
                                                               self.data.get("filename", "test.png"),
                                                               "Image File (*.png)")  # filename as String
        if filename:
            img = qrcode.make(self.textbox.text())
            img.save("{}".format(filename[0]))

    def run(self):
        """run qt app"""
        self.main_window.show()
        self.app.exec()


if __name__ == '__main__':
    """main - just to instantiate qt app class and run it"""
    gui = QRGuiApp()
    gui.run()
