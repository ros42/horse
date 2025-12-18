"""
Панель управления одним сервоприводом.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame,
    QSpinBox, QDoubleSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from servo_device import A5ServoDevice, ServoStatus


class ServoPanel(QWidget):
    """Панель управления сервоприводом."""
    
    # Сигналы
    on_jog_start = pyqtSignal(int)   # direction: 1 или -1
    on_jog_stop = pyqtSignal()
    on_enable_change = pyqtSignal(bool)
    
    def __init__(self, title: str, servo_id: str, parent=None):
        super().__init__(parent)
        
        self.title = title
        self.servo_id = servo_id
        self.device: Optional[A5ServoDevice] = None
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Заголовок панели
        header = QLabel(self.title)
        header.setObjectName("panelHeader")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Статус подключения
        self.status_indicator = QLabel("⚪ Не подключено")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_indicator)
        
        # Группа мониторинга
        monitor_group = QGroupBox("📊 Мониторинг")
        monitor_layout = QGridLayout(monitor_group)
        
        # Позиция
        monitor_layout.addWidget(QLabel("Позиция:"), 0, 0)
        self.position_label = QLabel("---")
        self.position_label.setObjectName("valueLabel")
        self.position_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        monitor_layout.addWidget(self.position_label, 0, 1)
        
        # Скорость
        monitor_layout.addWidget(QLabel("Скорость:"), 1, 0)
        self.speed_label = QLabel("--- об/мин")
        self.speed_label.setObjectName("valueLabel")
        self.speed_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        monitor_layout.addWidget(self.speed_label, 1, 1)
        
        # Момент
        monitor_layout.addWidget(QLabel("Момент:"), 2, 0)
        self.torque_label = QLabel("--- %")
        self.torque_label.setObjectName("valueLabel")
        monitor_layout.addWidget(self.torque_label, 2, 1)
        
        # Прогресс-бар момента
        self.torque_bar = QProgressBar()
        self.torque_bar.setRange(-100, 100)
        self.torque_bar.setValue(0)
        self.torque_bar.setTextVisible(False)
        self.torque_bar.setFixedHeight(10)
        monitor_layout.addWidget(self.torque_bar, 3, 0, 1, 2)
        
        # Ошибки
        monitor_layout.addWidget(QLabel("Статус:"), 4, 0)
        self.fault_label = QLabel("OK")
        self.fault_label.setObjectName("faultLabel")
        monitor_layout.addWidget(self.fault_label, 4, 1)
        
        layout.addWidget(monitor_group)
        
        # Группа управления
        control_group = QGroupBox("🎮 Управление")
        control_layout = QVBoxLayout(control_group)
        
        # Кнопка Enable
        self.enable_btn = QPushButton("⚡ ВКЛЮЧИТЬ")
        self.enable_btn.setObjectName("enableBtn")
        self.enable_btn.setCheckable(True)
        self.enable_btn.setFixedHeight(50)
        self.enable_btn.clicked.connect(self._toggle_enable)
        control_layout.addWidget(self.enable_btn)
        
        # JOG управление
        jog_layout = QHBoxLayout()
        
        self.jog_down_btn = QPushButton("⬇ ВНИЗ")
        self.jog_down_btn.setObjectName("jogBtn")
        self.jog_down_btn.pressed.connect(lambda: self.on_jog_start.emit(-1))
        self.jog_down_btn.released.connect(self.on_jog_stop.emit)
        jog_layout.addWidget(self.jog_down_btn)
        
        self.jog_up_btn = QPushButton("⬆ ВВЕРХ")
        self.jog_up_btn.setObjectName("jogBtn")
        self.jog_up_btn.pressed.connect(lambda: self.on_jog_start.emit(1))
        self.jog_up_btn.released.connect(self.on_jog_stop.emit)
        jog_layout.addWidget(self.jog_up_btn)
        
        control_layout.addLayout(jog_layout)
        
        # Ввод позиции
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Позиция:"))
        
        self.position_input = QSpinBox()
        self.position_input.setRange(-1000000, 1000000)
        self.position_input.setSingleStep(100)
        pos_layout.addWidget(self.position_input)
        
        self.go_btn = QPushButton("GO")
        self.go_btn.setObjectName("goBtn")
        self.go_btn.clicked.connect(self._go_to_position)
        pos_layout.addWidget(self.go_btn)
        
        control_layout.addLayout(pos_layout)
        
        # Сброс ошибки
        self.clear_fault_btn = QPushButton("🔄 Сброс ошибки")
        self.clear_fault_btn.clicked.connect(self._clear_fault)
        control_layout.addWidget(self.clear_fault_btn)
        
        layout.addWidget(control_group)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """Применить стили."""
        self.setStyleSheet("""
            ServoPanel {
                background-color: #1a1a2e;
                border: 2px solid #0f3460;
                border-radius: 10px;
            }
            
            #panelHeader {
                color: #e94560;
                padding: 10px;
            }
            
            #statusIndicator {
                color: #a0a0a0;
                padding: 5px;
                background: rgba(0,0,0,0.3);
                border-radius: 5px;
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
            
            #valueLabel {
                color: #00ff88;
            }
            
            #faultLabel {
                color: #00ff88;
                font-weight: bold;
            }
            
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #16213e;
            }
            
            QPushButton:pressed {
                background-color: #e94560;
            }
            
            #enableBtn {
                font-size: 14px;
            }
            
            #enableBtn:checked {
                background-color: #00aa55;
                border-color: #00ff88;
            }
            
            #jogBtn {
                min-height: 40px;
                font-size: 12px;
            }
            
            #goBtn {
                background-color: #e94560;
                min-width: 60px;
            }
            
            QSpinBox {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                border-radius: 3px;
                padding: 5px;
            }
            
            QProgressBar {
                background-color: #0f3460;
                border: none;
                border-radius: 5px;
            }
            
            QProgressBar::chunk {
                background-color: #00ff88;
                border-radius: 5px;
            }
        """)
    
    def set_device(self, device: Optional[A5ServoDevice]):
        """Установить устройство."""
        self.device = device
        
        if device and device.is_connected:
            self.status_indicator.setText(f"🟢 {device.config.port}")
            self._set_controls_enabled(True)
        else:
            self.status_indicator.setText("⚪ Не подключено")
            self._set_controls_enabled(False)
    
    def _set_controls_enabled(self, enabled: bool):
        """Включить/выключить элементы управления."""
        self.enable_btn.setEnabled(enabled)
        self.jog_up_btn.setEnabled(enabled)
        self.jog_down_btn.setEnabled(enabled)
        self.position_input.setEnabled(enabled)
        self.go_btn.setEnabled(enabled)
        self.clear_fault_btn.setEnabled(enabled)
    
    def update_status(self, status: ServoStatus):
        """Обновить отображение статуса."""
        # Позиция
        self.position_label.setText(f"{status.position:,}")
        
        # Скорость
        self.speed_label.setText(f"{status.speed} об/мин")
        
        # Момент
        self.torque_label.setText(f"{status.torque} %")
        self.torque_bar.setValue(min(100, max(-100, status.torque)))
        
        # Ошибки
        if status.fault_code == 0:
            self.fault_label.setText("✅ OK")
            self.fault_label.setStyleSheet("color: #00ff88; font-weight: bold;")
        else:
            if self.device:
                fault_text = self.device.get_fault_description()
            else:
                fault_text = f"Er.{status.fault_code:02d}"
            self.fault_label.setText(f"❌ {fault_text}")
            self.fault_label.setStyleSheet("color: #ff4444; font-weight: bold;")
    
    def _toggle_enable(self, checked: bool):
        """Переключить включение привода."""
        if self.device:
            self.device.enable(checked)
            
            if checked:
                self.enable_btn.setText("⚡ ВЫКЛЮЧИТЬ")
            else:
                self.enable_btn.setText("⚡ ВКЛЮЧИТЬ")
        
        self.on_enable_change.emit(checked)
    
    def _go_to_position(self):
        """Перейти в указанную позицию."""
        if self.device:
            position = self.position_input.value()
            self.device.set_target_position(position)
    
    def _clear_fault(self):
        """Сбросить ошибку."""
        if self.device:
            self.device.clear_fault()

