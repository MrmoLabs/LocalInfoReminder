import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ui.components.hotkey_recorder import HotkeyRecorder


class TestHotkeyRecorderGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.widget = HotkeyRecorder()
        self.widget.resize(160, 40)
        self.widget.show()
        self.app.processEvents()

    def tearDown(self):
        self.widget.close()
        self.app.processEvents()

    def test_click_enters_recording_mode(self):
        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton)

        self.assertTrue(self.widget.isChecked())
        self.assertEqual(self.widget.text(), 'Recording...')

    def test_ctrl_letter_hotkey_is_recorded_and_emitted(self):
        changes = []
        self.widget.hotkey_changed.connect(changes.append)

        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton)
        QTest.keyPress(self.widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)

        self.assertFalse(self.widget.isChecked())
        self.assertEqual(self.widget.current_hotkey, 'ctrl+a')
        self.assertEqual(self.widget.text(), 'ctrl+a')
        self.assertEqual(changes, ['ctrl+a'])

    def test_modifier_only_hotkey_finishes_on_release(self):
        changes = []
        self.widget.hotkey_changed.connect(changes.append)

        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton)
        QTest.keyPress(self.widget, Qt.Key.Key_Control, Qt.KeyboardModifier.ControlModifier)

        self.assertTrue(self.widget.isChecked())
        self.assertEqual(self.widget.current_hotkey, 'ctrl')

        QTest.keyRelease(self.widget, Qt.Key.Key_Control, Qt.KeyboardModifier.NoModifier)

        self.assertFalse(self.widget.isChecked())
        self.assertEqual(self.widget.text(), 'ctrl')
        self.assertEqual(changes, ['ctrl'])

    def test_right_click_clears_existing_hotkey(self):
        self.widget.close()
        self.widget = HotkeyRecorder('ctrl+a')
        self.widget.resize(160, 40)
        self.widget.show()
        self.app.processEvents()

        changes = []
        self.widget.hotkey_changed.connect(changes.append)

        QTest.mouseClick(self.widget, Qt.MouseButton.RightButton)

        self.assertEqual(self.widget.current_hotkey, '')
        self.assertEqual(self.widget.text(), 'Click to Set')
        self.assertEqual(changes, [''])

    def test_mouse_button_can_be_recorded(self):
        changes = []
        self.widget.hotkey_changed.connect(changes.append)

        QTest.mouseClick(self.widget, Qt.MouseButton.LeftButton)
        QTest.mouseClick(self.widget, Qt.MouseButton.MiddleButton)

        self.assertFalse(self.widget.isChecked())
        self.assertEqual(self.widget.current_hotkey, 'mouse_middle')
        self.assertEqual(self.widget.text(), 'mouse_middle')
        self.assertEqual(changes, ['mouse_middle'])


if __name__ == '__main__':
    unittest.main()
