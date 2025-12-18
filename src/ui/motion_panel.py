"""
Панель управления движением тренажёра.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QSlider,
    QSpinBox, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..motion_controller import MotionMode


class MotionPanel(QWidget):
    """Панель управления режимами движения."""
    
    # Сигналы
    on_mode_change = pyqtSignal(MotionMode)
    on_emergency_stop = pyqtSignal()
    on_pattern_change = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_mode = MotionMode.STOPPED
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Заголовок
        header = QLabel("🎛️ УПРАВЛЕНИЕ ДВИЖЕНИЕМ")
        header.setObjectName("panelHeader")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Текущий режим
        mode_frame = QFrame()
        mode_frame.setObjectName("modeFrame")
        mode_layout = QVBoxLayout(mode_frame)
        
        self.mode_label = QLabel("ОСТАНОВЛЕН")
        self.mode_label.setObjectName("modeLabel")
        self.mode_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_layout.addWidget(self.mode_label)
        
        layout.addWidget(mode_frame)
        
        # Кнопка АВАРИЙНЫЙ СТОП
        self.emergency_btn = QPushButton("🛑 АВАРИЙНЫЙ СТОП")
        self.emergency_btn.setObjectName("emergencyBtn")
        self.emergency_btn.setFixedHeight(70)
        self.emergency_btn.clicked.connect(self.on_emergency_stop.emit)
        layout.addWidget(self.emergency_btn)
        
        # Группа выбора режима
        mode_group = QGroupBox("📋 Выбор режима")
        mode_group_layout = QVBoxLayout(mode_group)
        
        # Кнопки режимов
        self.stop_btn = QPushButton("⏹️ СТОП")
        self.stop_btn.setObjectName("modeBtn")
        self.stop_btn.setCheckable(True)
        self.stop_btn.setChecked(True)
        self.stop_btn.clicked.connect(lambda: self._set_mode(MotionMode.STOPPED))
        mode_group_layout.addWidget(self.stop_btn)
        
        self.manual_btn = QPushButton("🎮 РУЧНОЙ")
        self.manual_btn.setObjectName("modeBtn")
        self.manual_btn.setCheckable(True)
        self.manual_btn.clicked.connect(lambda: self._set_mode(MotionMode.MANUAL))
        mode_group_layout.addWidget(self.manual_btn)
        
        self.walk_btn = QPushButton("🚶 ШАГ")
        self.walk_btn.setObjectName("modeBtn")
        self.walk_btn.setCheckable(True)
        self.walk_btn.clicked.connect(lambda: self._set_mode(MotionMode.WALK))
        mode_group_layout.addWidget(self.walk_btn)
        
        self.gallop_btn = QPushButton("🏇 ГАЛОП")
        self.gallop_btn.setObjectName("modeBtn")
        self.gallop_btn.setCheckable(True)
        self.gallop_btn.clicked.connect(lambda: self._set_mode(MotionMode.GALLOP))
        mode_group_layout.addWidget(self.gallop_btn)
        
        layout.addWidget(mode_group)
        
        # Группа настроек паттерна
        pattern_group = QGroupBox("⚙️ Параметры движения")
        pattern_layout = QGridLayout(pattern_group)
        
        # Время цикла
        pattern_layout.addWidget(QLabel("Время цикла (мс):"), 0, 0)
        self.cycle_time_spin = QSpinBox()
        self.cycle_time_spin.setRange(200, 5000)
        self.cycle_time_spin.setValue(2000)
        self.cycle_time_spin.setSingleStep(100)
        pattern_layout.addWidget(self.cycle_time_spin, 0, 1)
        
        # Амплитуда переднего
        pattern_layout.addWidget(QLabel("Амплитуда перед:"), 1, 0)
        self.front_amp_spin = QSpinBox()
        self.front_amp_spin.setRange(0, 10000)
        self.front_amp_spin.setValue(3000)
        self.front_amp_spin.setSingleStep(100)
        pattern_layout.addWidget(self.front_amp_spin, 1, 1)
        
        # Амплитуда заднего
        pattern_layout.addWidget(QLabel("Амплитуда зад:"), 2, 0)
        self.rear_amp_spin = QSpinBox()
        self.rear_amp_spin.setRange(0, 10000)
        self.rear_amp_spin.setValue(3000)
        self.rear_amp_spin.setSingleStep(100)
        pattern_layout.addWidget(self.rear_amp_spin, 2, 1)
        
        # Сдвиг фазы
        pattern_layout.addWidget(QLabel("Сдвиг фазы (°):"), 3, 0)
        self.phase_spin = QSpinBox()
        self.phase_spin.setRange(0, 360)
        self.phase_spin.setValue(180)
        self.phase_spin.setSingleStep(15)
        pattern_layout.addWidget(self.phase_spin, 3, 1)
        
        layout.addWidget(pattern_group)
        
        # Индикатор позиций
        pos_group = QGroupBox("📍 Текущие позиции")
        pos_layout = QHBoxLayout(pos_group)
        
        front_col = QVBoxLayout()
        front_col.addWidget(QLabel("Передний:"))
        self.front_pos_label = QLabel("0")
        self.front_pos_label.setObjectName("posLabel")
        self.front_pos_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.front_pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        front_col.addWidget(self.front_pos_label)
        pos_layout.addLayout(front_col)
        
        rear_col = QVBoxLayout()
        rear_col.addWidget(QLabel("Задний:"))
        self.rear_pos_label = QLabel("0")
        self.rear_pos_label.setObjectName("posLabel")
        self.rear_pos_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.rear_pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rear_col.addWidget(self.rear_pos_label)
        pos_layout.addLayout(rear_col)
        
        layout.addWidget(pos_group)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """Применить стили."""
        self.setStyleSheet("""
            MotionPanel {
                background-color: #1a1a2e;
                border: 2px solid #e94560;
                border-radius: 10px;
            }
            
            #panelHeader {
                color: #e94560;
                padding: 10px;
            }
            
            #modeFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16213e, stop:1 #0f3460);
                border: 2px solid #e94560;
                border-radius: 10px;
                padding: 20px;
            }
            
            #modeLabel {
                color: #00ff88;
            }
            
            #emergencyBtn {
                background-color: #cc0000;
                color: #ffffff;
                border: 3px solid #ff0000;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
            }
            
            #emergencyBtn:hover {
                background-color: #ff0000;
            }
            
            #emergencyBtn:pressed {
                background-color: #990000;
            }
            
            QGroupBox {
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #0f3460;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            
            QLabel {
                color: #a0a0a0;
            }
            
            #posLabel {
                color: #00ff88;
                background: rgba(0,0,0,0.3);
                border-radius: 5px;
                padding: 10px;
            }
            
            #modeBtn {
                background-color: #0f3460;
                color: #ffffff;
                border: 2px solid #16213e;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                min-height: 30px;
            }
            
            #modeBtn:hover {
                border-color: #e94560;
            }
            
            #modeBtn:checked {
                background-color: #e94560;
                border-color: #ff6b8a;
            }
            
            QSpinBox {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
            }
            
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #16213e;
                border: none;
                width: 20px;
            }
            
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #e94560;
            }
        """)
    
    def _set_mode(self, mode: MotionMode):
        """Установить режим движения."""
        self.current_mode = mode
        
        # Обновить кнопки
        self.stop_btn.setChecked(mode == MotionMode.STOPPED)
        self.manual_btn.setChecked(mode == MotionMode.MANUAL)
        self.walk_btn.setChecked(mode == MotionMode.WALK)
        self.gallop_btn.setChecked(mode == MotionMode.GALLOP)
        
        # Обновить метку
        mode_names = {
            MotionMode.STOPPED: "ОСТАНОВЛЕН",
            MotionMode.MANUAL: "РУЧНОЙ РЕЖИМ",
            MotionMode.WALK: "🚶 ШАГ",
            MotionMode.GALLOP: "🏇 ГАЛОП",
            MotionMode.CUSTOM: "ПОЛЬЗОВАТЕЛЬСКИЙ"
        }
        self.mode_label.setText(mode_names.get(mode, mode.name))
        
        # Цвет метки
        if mode == MotionMode.STOPPED:
            self.mode_label.setStyleSheet("color: #a0a0a0;")
        elif mode == MotionMode.MANUAL:
            self.mode_label.setStyleSheet("color: #ffaa00;")
        else:
            self.mode_label.setStyleSheet("color: #00ff88;")
        
        # Отправить сигнал
        self.on_mode_change.emit(mode)
    
    def set_mode(self, mode: MotionMode):
        """Установить режим извне (без отправки сигнала)."""
        self.current_mode = mode
        
        # Обновить кнопки
        self.stop_btn.setChecked(mode == MotionMode.STOPPED)
        self.manual_btn.setChecked(mode == MotionMode.MANUAL)
        self.walk_btn.setChecked(mode == MotionMode.WALK)
        self.gallop_btn.setChecked(mode == MotionMode.GALLOP)
        
        # Обновить метку
        mode_names = {
            MotionMode.STOPPED: "ОСТАНОВЛЕН",
            MotionMode.MANUAL: "РУЧНОЙ РЕЖИМ",
            MotionMode.WALK: "🚶 ШАГ",
            MotionMode.GALLOP: "🏇 ГАЛОП",
            MotionMode.CUSTOM: "ПОЛЬЗОВАТЕЛЬСКИЙ"
        }
        self.mode_label.setText(mode_names.get(mode, mode.name))
    
    def update_positions(self, front_pos: int, rear_pos: int):
        """Обновить отображение позиций."""
        self.front_pos_label.setText(f"{front_pos:,}")
        self.rear_pos_label.setText(f"{rear_pos:,}")
    
    def get_pattern_params(self) -> dict:
        """Получить параметры паттерна из UI."""
        return {
            "cycle_time_ms": self.cycle_time_spin.value(),
            "front_amplitude": self.front_amp_spin.value(),
            "rear_amplitude": self.rear_amp_spin.value(),
            "phase_shift": self.phase_spin.value()
        }

