import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.match_summary import MatchSummaryWriter


class TestMatchSummaryWriter(unittest.TestCase):
    def _make_output_path(self, name: str) -> str:
        base_dir = os.path.join(os.path.dirname(__file__), 'generated_tmp')
        os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, name)
        if os.path.exists(output_path):
            os.remove(output_path)
        return output_path

    def test_writes_spawn_kill_and_skill_rows(self):
        output_path = self._make_output_path('match_summary_rows.md')
        try:
            writer = MatchSummaryWriter(output_path=output_path, boss_targets=[{
                'id': 'target_b', 'display_name': '\u76ee\u6807B', 'match_names': ['Target B'], 'ocr_keywords': ['\u76ee\u6807B'],
                'time_windows': [{'start': '17:20', 'end': '14:30'}], 'kill_window_seconds': 180, 'kill_keywords': ['\u5b8c\u6210'],
                'faction_match': 'distinguish', 'ignore_keywords': [], 'spawn_sound': '', 'kill_sound': '', 'buff_duration': 300
            }])

            writer.record_boss_spawn(
                boss_name='Target B',
                countdown_seconds=1040,
                predicted_seconds=990,
                detected_at=datetime(2026, 3, 9, 10, 0, 0),
            )
            writer.record_boss_kill(
                boss_name='Target B',
                faction='enemy',
                countdown_seconds=930,
                detected_at=datetime(2026, 3, 9, 10, 1, 0),
            )
            writer.record_command_skill(
                skill_name='Primary A',
                countdown_seconds=920,
                source='OCR',
                faction='\u5bf9\u65b9',
                detected_at=datetime(2026, 3, 9, 10, 1, 5),
            )

            content = Path(output_path).read_text(encoding='utf-8')

            self.assertIn('\u5bf9\u5c40\u5173\u952e\u4fe1\u606f\u6c47\u603b', content)
            self.assertIn('\u76ee\u6807B', content)
            self.assertIn('\u4e8b\u4ef6\u5b8c\u6210', content)
            self.assertIn('\u5bf9\u65b9', content)
            self.assertIn('17:20', content)
            self.assertIn('| \u76ee\u6807B | \u4e8b\u4ef6\u51fa\u73b0 | \u76ee\u6807B | - | 16:30 | \u9884\u6d4b |', content)
            self.assertIn('Primary A', content)
            self.assertIn('| \u4e3b\u6280\u80fd | \u4f7f\u7528 | Primary A | \u5bf9\u65b9 | 15:20 | OCR |', content)
            self.assertIn('OCR', content)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_splits_matches_when_countdown_jumps_up_by_threshold(self):
        output_path = self._make_output_path('match_summary_split.md')
        try:
            writer = MatchSummaryWriter(output_path=output_path, split_threshold_seconds=300)

            writer.record_command_skill(
                skill_name='Skill A',
                countdown_seconds=600,
                source='\u70ed\u952e',
                detected_at=datetime(2026, 3, 9, 11, 0, 0),
            )
            writer.update_countdown(120)
            writer.update_countdown(480)
            writer.record_command_skill(
                skill_name='Skill B',
                countdown_seconds=480,
                source='OCR',
                detected_at=datetime(2026, 3, 9, 11, 5, 0),
            )

            content = Path(output_path).read_text(encoding='utf-8')

            self.assertIn('## \u5bf9\u5c40 1', content)
            self.assertIn('## \u5bf9\u5c40 2', content)
            self.assertEqual(content.count('| \u4e3b\u6280\u80fd | \u4f7f\u7528 |'), 2)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == '__main__':
    unittest.main()
