import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ui.components.config_cards import SkillConfigCard


class TestSkillConfigCardGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_command_skill_card_persists_ocr_and_hotkey_changes(self):
        card = SkillConfigCard({
            'id': 'heal_reduction',
            'name': 'Healing Reduction',
            'duration': 8,
            'cooldown': 25,
            'default_hotkey': '',
            'ocr_color': '',
            'ocr_keywords': [],
            'cd_threshold': 0,
            'cd_flash': False,
            'cd_sound': ''
        })
        card.resize(600, 260)
        card.show()
        self.app.processEvents()

        try:
            card.combo_ocr_color.setCurrentIndex(1)
            card.edit_keywords.setText('目标文本,示例文本')
            card.spin_cd_threshold.setValue(3.0)
            card.chk_cd_flash.setChecked(True)
            card.edit_cd_sound.setText('command_skills/ult_ready.mp3')

            QTest.mouseClick(card.hk_default, Qt.MouseButton.LeftButton)
            QTest.keyPress(card.hk_default, Qt.Key.Key_Q, Qt.KeyboardModifier.AltModifier)

            data = card.get_data()

            self.assertEqual(data['ocr_color'], 'red')
            self.assertEqual(data['ocr_keywords'], ['目标文本', '示例文本'])
            self.assertEqual(data['cd_threshold'], 3.0)
            self.assertTrue(data['cd_flash'])
            self.assertEqual(data['cd_sound'], 'command_skills/ult_ready.mp3')
            self.assertEqual(data['default_hotkey'], 'alt+q')
        finally:
            card.close()
            self.app.processEvents()

    def test_miracle_skill_card_hides_ocr_controls(self):
        card = SkillConfigCard({
            'id': 'miracle',
            'name': 'Miracle',
            'cooldown': 40,
            'flash_threshold': 2.5,
            'default_hotkey': 'f4'
        }, is_miracle=True)
        card.resize(600, 240)
        card.show()
        self.app.processEvents()

        try:
            self.assertFalse(hasattr(card, 'combo_ocr_color'))
            self.assertFalse(hasattr(card, 'edit_keywords'))
            self.assertTrue(hasattr(card, 'spin_flash'))

            card.spin_flash.setValue(1.5)
            data = card.get_data()

            self.assertEqual(data['flash_threshold'], 1.5)
            self.assertNotIn('ocr_color', data)
            self.assertNotIn('ocr_keywords', data)
        finally:
            card.close()
            self.app.processEvents()

    def test_unset_hotkey_does_not_persist_placeholder_text(self):
        card = SkillConfigCard({
            'id': 'quick_step',
            'name': 'Primary A',
            'duration': 5,
            'cooldown': 20,
            'default_hotkey': 'Click to Set',
            'ocr_color': '',
            'ocr_keywords': [],
            'cd_threshold': 0,
            'cd_flash': False,
            'cd_sound': ''
        })
        card.resize(600, 260)
        card.show()
        self.app.processEvents()

        try:
            data = card.get_data()
            self.assertEqual(data['default_hotkey'], '')
            self.assertEqual(card.hk_default.current_hotkey, '')
            self.assertEqual(card.hk_default.text(), 'Click to Set')
        finally:
            card.close()
            self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
