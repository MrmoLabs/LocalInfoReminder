import unittest
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.command_manager import CommandManager

class TestCommandFull(unittest.TestCase):
    def setUp(self):
        self.config = {
            "command_skills": [
                {"name": "Ult", "cooldown": 60, "is_enabled": True}
            ],
            "miracle_skills": [
                {"name": "Miracle1", "cooldown": 30, "is_enabled": True}
            ]
        }
        self.em = CommandManager(self.config)

    def test_lifecycle(self):
        """Active -> Cooldown -> Ready."""
        # Trigger
        self.em.trigger_skill({"name": "Ult", "cooldown": 60, "duration": 5})
        
        t0 = time.time()
        
        # 1. Active Phase (t+2)
        actives = self.em.update(t0 + 2)
        ult = next(x for x in actives if x['name'] == 'Ult')
        self.assertEqual(ult['state'], 'ACTIVE')
        
        # 2. Cooldown Phase (t+10)
        actives = self.em.update(t0 + 10)
        ult = next(x for x in actives if x['name'] == 'Ult')
        self.assertEqual(ult['state'], 'COOLDOWN')
        self.assertAlmostEqual(ult['remaining'], 50, delta=1) # 60 - 10
        
        # 3. Ready Phase (t+61)
        # Note: logic might remove it or mark as ready.
        # But for configured skills, it keeps them.
        actives = self.em.update(t0 + 61)
        ult = next(x for x in actives if x['name'] == 'Ult')
        self.assertEqual(ult['state'], 'READY')

    def test_overwrite_logic(self):
        """Triggering an active skill should restart the timer."""
        # Trigger 1
        self.em.trigger_skill({"name": "Ult", "cooldown": 60})
        t1 = self.em.command_cds["Ult"]["start_time"]
        
        time.sleep(0.1)
        
        # Trigger 2 (Overwrite)
        self.em.trigger_skill({"name": "Ult", "cooldown": 60})
        t2 = self.em.command_cds["Ult"]["start_time"]
        
        self.assertNotEqual(t1, t2)
        self.assertTrue(t2 > t1)

    def test_miracle_skills(self):
        """Verify miracles appear even if not triggered (just ready)."""
        actives = self.em.update(time.time())
        m = next((x for x in actives if x['name'] == 'Miracle1'), None)
        self.assertIsNotNone(m)
        self.assertEqual(m['state'], 'READY')

    def test_dynamic_cleanup(self):
        """Non-configured skills should disappear after CD."""
        # Trigger dynamic
        self.em.trigger_skill({"name": "UnknownSkill", "cooldown": 1})
        
        t0 = time.time()
        # Active
        actives = self.em.update(t0)
        self.assertTrue(any(x['name'] == 'UnknownSkill' for x in actives))
        
        # Expired (t+2)
        actives = self.em.update(t0 + 2)
        self.assertFalse(any(x['name'] == 'UnknownSkill' for x in actives))

    def test_command_cd_threshold_emits_audio_once_and_exposes_flash_state(self):
        self.config['command_skills'][0].update({
            'duration': 5,
            'cd_threshold': 3,
            'cd_flash': True,
            'cd_sound': 'command_skills/ult_ready.mp3',
        })
        self.em = CommandManager(self.config)
        self.em.trigger_skill(self.config['command_skills'][0])

        t0 = self.em.command_cds['Ult']['start_time']

        before_threshold = self.em.collect_due_audio_notifications(t0 + 56.0)
        self.assertEqual(before_threshold, [])

        at_threshold = self.em.collect_due_audio_notifications(t0 + 57.2)
        self.assertEqual(at_threshold, ['command_skills/ult_ready.mp3'])

        repeat_tick = self.em.collect_due_audio_notifications(t0 + 57.5)
        self.assertEqual(repeat_tick, [])

        entries = self.em.update(t0 + 57.5)
        ult = next(x for x in entries if x['name'] == 'Ult')
        self.assertEqual(ult['state'], 'COOLDOWN')
        self.assertEqual(ult['flash_threshold'], 3.0)
        self.assertTrue(ult['flash_enabled'])

if __name__ == '__main__':
    unittest.main()
