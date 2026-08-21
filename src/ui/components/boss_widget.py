import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class BossWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(200, 50, 50, 0.9);
                border-radius: 8px;
                border: 2px solid #FF8888;
            }
            QLabel {
                background: transparent;
                color: #FFFFFF;
                font-family: 'Segoe UI';
                font-weight: bold;
                border: none;
            }
        """)
        # [CHANGE] Vertical Layout for Icon top, Time bottom
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(2) # Tight spacing "紧挨着"
        
        # Icon
        self.icon_label = QLabel("🐲") 
        self.icon_label.setFont(QFont("Segoe UI Emoji", 24)) 
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        


        # Timer
        self.timer_label = QLabel("25:30")
        self.timer_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)) # Smaller font for side-bar
        self.timer_label.setStyleSheet("color: #FFFFFF;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # [NEW] Buff Progress Bar
        self.buff_bar = QProgressBar()
        self.buff_bar.setOrientation(Qt.Orientation.Vertical)
        self.buff_bar.setTextVisible(True)
        self.buff_bar.setFormat("%v") # Show remaining seconds
        self.buff_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buff_bar.setFixedSize(30, 100) # [FIX] Wider for 3-digit text (was 14)
        self.buff_bar.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.buff_bar.hide()
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.timer_label)  
        layout.addWidget(self.buff_bar) # Add bar to layout
        layout.addStretch() # Push to top
        
        self.setFixedWidth(60) # Fixed width for the side bar look
        self.hide() 

        # Base sizes for scaling
        self.base_width = 60
        self.base_buff_width = 30 # For buff mode width (container) and bar width
        self.base_icon_size = 24
        self.base_timer_size = 12
        self.base_bar_h = 100
        self.base_bar_w = 30
        
        self.current_scale = 1.0

    def set_scale(self, scale: float):
        self.current_scale = scale
        
        # Scale Font
        icon_size = max(12, int(self.base_icon_size * scale))
        text_size = max(8, int(self.base_timer_size * scale))
        
        self.icon_label.setFont(QFont("Segoe UI Emoji", icon_size))
        
        font_text = QFont("Segoe UI", text_size, QFont.Weight.Bold)
        self.timer_label.setFont(font_text)
        
        # Scale Bar
        bar_w = max(10, int(self.base_bar_w * scale))
        bar_h = max(30, int(self.base_bar_h * scale))
        self.buff_bar.setFixedSize(bar_w, bar_h)
        self.buff_bar.setFont(QFont("Segoe UI", max(7, int(10 * scale)), QFont.Weight.Bold))
        
        # Scale Container Width
        # Note: We toggle width based on mode in update_info, so we need to respect scale there too.
        # Rerun update_info logic if active to re-apply width
        if self.isVisible():
             self.update_info(self.last_info if hasattr(self, 'last_info') else {})

    def update_info(self, info: dict):
        self.last_info = info # Cache for rescaling
        
        if not info.get('active', False):
            self.hide()
            return
            
        self.show()
        
        # Check for Kill Status
        kill_status = info.get('kill_status', None) # 'ally' or 'enemy'
        
        if kill_status:
            # --- Buff Timer Mode ---
            kill_time = info.get('kill_detected_time', 0)
            duration = info.get('buff_duration', 0)
            elapsed = time.time() - kill_time
            remaining = int(duration - elapsed)
            
            if remaining <= 0:
                self.hide() # Buff expired
                return
                
            # [CHANGE] Hide Icon in Buff Mode
            self.icon_label.hide()
            
            # Scaled Width
            w = max(16, int(34 * self.current_scale))
            self.setFixedWidth(w) 
            
            # Hide text timer, Show Bar
            self.timer_label.hide()
            self.buff_bar.show()
            
            # Update Bar
            self.buff_bar.setRange(0, duration)
            self.buff_bar.setValue(remaining)
            
            if kill_status == 'ally':
                # Blue Style (#89B4FA)
                self.setStyleSheet("""
                    QWidget {
                        background-color: rgba(50, 50, 150, 0.9);
                        border-radius: 8px;
                        border: 2px solid #89B4FA;
                    }
                    QLabel { background: transparent; color: white; border: none; }
                """)
                self.buff_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #89B4FA;
                        border-radius: 4px;
                        background-color: rgba(0, 0, 50, 0.5);
                        color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #89B4FA;
                        border-radius: 2px;
                    }
                """)
            else:
                # Red Style (#FF5555)
                self.setStyleSheet("""
                    QWidget {
                        background-color: rgba(150, 50, 50, 0.9);
                        border-radius: 8px;
                        border: 2px solid #FF5555;
                    }
                    QLabel { background: transparent; color: white; border: none; }
                """)
                self.buff_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #FF5555;
                        border-radius: 4px;
                        background-color: rgba(50, 0, 0, 0.5);
                        color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #FF5555;
                        border-radius: 2px;
                    }
                """)
        else:
            # --- Spawn Timer Mode ---
            self.buff_bar.hide()
            self.timer_label.show()
            
            # [CHANGE] Show Icon in Spawn Mode
            self.icon_label.show()
            self.icon_label.setText("🐲") 
            
            # Scaled Width
            w = max(30, int(60 * self.current_scale))
            self.setFixedWidth(w)
            
            self.setStyleSheet("""
                QWidget {
                    background-color: rgba(200, 50, 50, 0.9);
                    border-radius: 8px;
                    border: 2px solid #FF8888;
                }
                QLabel { background: transparent; color: #FFFFFF; font-family: 'Segoe UI'; font-weight: bold; border: none; }
            """)
            
            # Separate Time and Location
            time_str = info.get('spawn_str', '00:00')
            
            self.timer_label.setText(time_str)
