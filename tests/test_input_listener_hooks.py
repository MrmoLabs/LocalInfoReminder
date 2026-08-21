import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.input.input_listener import InputListener


class FakeMouseButtonEvent:
    def __init__(self, button, event_type):
        self.button = button
        self.event_type = event_type


class TestInputListenerHooks(unittest.TestCase):
    def test_start_registers_keyboard_mouse_and_only_non_debug_hotkeys_by_default(self):
        hotkeys = {}
        state = {}
        events = []

        fake_mouse = SimpleNamespace(
            LEFT='left',
            RIGHT='right',
            MIDDLE='middle',
            X='x',
            X2='x2',
            DOWN='down',
            UP='up',
            ButtonEvent=FakeMouseButtonEvent,
            hook=MagicMock(side_effect=lambda cb: state.__setitem__('mouse_cb', cb)),
            unhook_all=MagicMock(),
        )

        with patch('core.input.input_listener.HAS_MOUSE', True), \
             patch('core.input.input_listener.mouse', fake_mouse), \
             patch('core.input.input_listener.keyboard.on_press', side_effect=lambda cb: state.__setitem__('press_cb', cb)), \
             patch('core.input.input_listener.keyboard.on_release', side_effect=lambda cb: state.__setitem__('release_cb', cb)), \
             patch('core.input.input_listener.keyboard.add_hotkey', side_effect=lambda combo, cb: hotkeys.__setitem__(combo, cb)), \
             patch('core.input.input_listener.keyboard.unhook_all') as unhook_all, \
             patch('core.input.input_listener.keyboard.is_pressed', side_effect=lambda key: key in {'ctrl', 'shift'}):
            listener = InputListener()
            listener.key_pressed.connect(lambda key: events.append(('press', key)))
            listener.key_released.connect(lambda key: events.append(('release', key)))
            listener.global_hotkey_triggered.connect(lambda name: events.append(('global', name)))

            listener.start()

            self.assertTrue(listener._active)
            self.assertEqual(sorted(hotkeys.keys()), ['ctrl+m'])
            self.assertIn('press_cb', state)
            self.assertIn('release_cb', state)
            self.assertIn('mouse_cb', state)

            state['press_cb'](SimpleNamespace(name='a', is_keypad=False))
            state['release_cb'](SimpleNamespace(name='a', is_keypad=False))
            state['mouse_cb'](FakeMouseButtonEvent(fake_mouse.RIGHT, fake_mouse.DOWN))
            state['mouse_cb'](FakeMouseButtonEvent(fake_mouse.RIGHT, fake_mouse.UP))
            hotkeys['ctrl+m']()

            self.assertIn(('press', 'ctrl+shift+a'), events)
            self.assertIn(('release', 'ctrl+shift+a'), events)
            self.assertIn(('press', 'mouse_right'), events)
            self.assertIn(('release', 'mouse_right'), events)
            self.assertIn(('global', 'overlay'), events)

            listener.stop()

            self.assertFalse(listener._active)
            unhook_all.assert_called_once()
            fake_mouse.unhook_all.assert_called_once()

    def test_start_registers_debug_hotkeys_when_enabled(self):
        hotkeys = {}

        with patch('core.input.input_listener.HAS_MOUSE', False), \
             patch('core.input.input_listener.keyboard.on_press'), \
             patch('core.input.input_listener.keyboard.on_release'), \
             patch('core.input.input_listener.keyboard.add_hotkey', side_effect=lambda combo, cb: hotkeys.__setitem__(combo, cb)):
            listener = InputListener(enable_debug_hotkeys=True)
            listener.start()

            self.assertEqual(sorted(hotkeys.keys()), ['ctrl+i', 'ctrl+m', 'ctrl+o', 'ctrl+u'])
            listener.stop()

    def test_register_globals_failure_does_not_crash_start(self):
        with patch('core.input.input_listener.HAS_MOUSE', False), \
             patch('core.input.input_listener.keyboard.on_press'), \
             patch('core.input.input_listener.keyboard.on_release'), \
             patch('core.input.input_listener.keyboard.add_hotkey', side_effect=RuntimeError('boom')):
            listener = InputListener(enable_debug_hotkeys=True)
            listener.start()
            self.assertTrue(listener._active)
            listener.stop()

    def test_canonical_key_formats_keypad_values(self):
        listener = InputListener()

        with patch('core.input.input_listener.keyboard.is_pressed', return_value=False):
            self.assertEqual(listener._get_canonical_key('num 1', is_keypad=False), 'num_1')
            self.assertEqual(listener._get_canonical_key('1', is_keypad=True), 'num_1')
            self.assertEqual(listener._get_canonical_key('enter', is_keypad=True), 'num_enter')


if __name__ == '__main__':
    unittest.main()
