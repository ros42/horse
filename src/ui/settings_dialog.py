"""
Диалог настроек COM-портов и параметров подключения.
"""

from typing import Tuple, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QGroupBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import serial.tools.list_ports

from modbus_manager import ConnectionConfig


class SettingsDialog(QDialog):
    """Диалог настроек подключения."""
    
    def __init__(self, parent, front_config: ConnectionConfig, rear_config: ConnectionConfig):
        super().__init__(parent)
        
        self.front_config = front_config
        self.rear_config = rear_config
        
        self.setWindowTitle("⚙ Настройки")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._apply_styles()
        self._load_values()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Получить список COM-портов
        self.available_ports = self._get_com_ports()
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка переднего привода
        front_tab = self._create_connection_tab("front")
        tabs.addTab(front_tab, "🔌 Передний привод")
        
        # Вкладка заднего привода
        rear_tab = self._create_connection_tab("rear")
        tabs.addTab(rear_tab, "🔌 Задний привод")
        
        layout.addWidget(tabs)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Обновить порты")
        refresh_btn.clicked.connect(self._refresh_ports)
        btn_layout.addWidget(refresh_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Сохранить")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_connection_tab(self, servo_id: str) -> QWidget:
        """Создать вкладку настроек подключения."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # COM-порт
        port_group = QGroupBox("Порт")
        port_layout = QGridLayout(port_group)
        
        port_layout.addWidget(QLabel("COM-порт:"), 0, 0)
        port_combo = QComboBox()
        port_combo.setEditable(True)
        port_combo.addItems(self.available_ports)
        port_layout.addWidget(port_combo, 0, 1)
        
        port_layout.addWidget(QLabel("Адрес Modbus:"), 1, 0)
        slave_spin = QSpinBox()
        slave_spin.setRange(1, 247)
        slave_spin.setValue(1)
        port_layout.addWidget(slave_spin, 1, 1)
        
        layout.addWidget(port_group)
        
        # Параметры связи
        comm_group = QGroupBox("Параметры связи")
        comm_layout = QGridLayout(comm_group)
        
        comm_layout.addWidget(QLabel("Скорость (бод):"), 0, 0)
        baud_combo = QComboBox()
        baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        baud_combo.setCurrentText("115200")
        comm_layout.addWidget(baud_combo, 0, 1)
        
        comm_layout.addWidget(QLabel("Чётность:"), 1, 0)
        parity_combo = QComboBox()
        parity_combo.addItems(["Нет (N)", "Чётность (E)", "Нечётность (O)"])
        comm_layout.addWidget(parity_combo, 1, 1)
        
        comm_layout.addWidget(QLabel("Стоп-биты:"), 2, 0)
        stop_combo = QComboBox()
        stop_combo.addItems(["1", "2"])
        comm_layout.addWidget(stop_combo, 2, 1)
        
        layout.addWidget(comm_group)
        
        layout.addStretch()
        
        # Сохранить ссылки на виджеты
        if servo_id == "front":
            self.front_port_combo = port_combo
            self.front_slave_spin = slave_spin
            self.front_baud_combo = baud_combo
            self.front_parity_combo = parity_combo
            self.front_stop_combo = stop_combo
        else:
            self.rear_port_combo = port_combo
            self.rear_slave_spin = slave_spin
            self.rear_baud_combo = baud_combo
            self.rear_parity_combo = parity_combo
            self.rear_stop_combo = stop_combo
        
        return tab
    
    def _apply_styles(self):
        """Применить стили."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            
            QTabWidget::pane {
                border: 1px solid #0f3460;
                border-radius: 5px;
                background-color: #16213e;
            }
            
            QTabBar::tab {
                background-color: #0f3460;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            
            QTabBar::tab:selected {
                background-color: #e94560;
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
            
            QComboBox, QSpinBox {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                border-radius: 5px;
                padding: 8px;
                min-width: 150px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #0f3460;
                color: #ffffff;
                selection-background-color: #e94560;
            }
            
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #16213e;
            }
            
            #saveBtn {
                background-color: #e94560;
            }
            
            #saveBtn:hover {
                background-color: #ff6b8a;
            }
        """)
    
    def _get_com_ports(self) -> List[str]:
        """Получить список доступных COM-портов."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def _refresh_ports(self):
        """Обновить список COM-портов."""
        self.available_ports = self._get_com_ports()
        
        # Сохранить текущие значения
        front_current = self.front_port_combo.currentText()
        rear_current = self.rear_port_combo.currentText()
        
        # Обновить списки
        self.front_port_combo.clear()
        self.front_port_combo.addItems(self.available_ports)
        self.rear_port_combo.clear()
        self.rear_port_combo.addItems(self.available_ports)
        
        # Восстановить значения
        self.front_port_combo.setCurrentText(front_current)
        self.rear_port_combo.setCurrentText(rear_current)
    
    def _load_values(self):
        """Загрузить текущие значения."""
        # Передний привод
        self.front_port_combo.setCurrentText(self.front_config.port)
        self.front_slave_spin.setValue(self.front_config.slave_id)
        self.front_baud_combo.setCurrentText(str(self.front_config.baudrate))
        self._set_parity_combo(self.front_parity_combo, self.front_config.parity)
        self.front_stop_combo.setCurrentText(str(self.front_config.stopbits))
        
        # Задний привод
        self.rear_port_combo.setCurrentText(self.rear_config.port)
        self.rear_slave_spin.setValue(self.rear_config.slave_id)
        self.rear_baud_combo.setCurrentText(str(self.rear_config.baudrate))
        self._set_parity_combo(self.rear_parity_combo, self.rear_config.parity)
        self.rear_stop_combo.setCurrentText(str(self.rear_config.stopbits))
    
    def _set_parity_combo(self, combo: QComboBox, parity: str):
        """Установить значение комбобокса чётности."""
        mapping = {"N": 0, "E": 1, "O": 2}
        combo.setCurrentIndex(mapping.get(parity, 0))
    
    def _get_parity_from_combo(self, combo: QComboBox) -> str:
        """Получить значение чётности из комбобокса."""
        mapping = {0: "N", 1: "E", 2: "O"}
        return mapping.get(combo.currentIndex(), "N")
    
    def _save_and_accept(self):
        """Сохранить настройки и закрыть диалог."""
        # Обновить конфигурацию переднего привода
        self.front_config = ConnectionConfig(
            port=self.front_port_combo.currentText(),
            slave_id=self.front_slave_spin.value(),
            baudrate=int(self.front_baud_combo.currentText()),
            parity=self._get_parity_from_combo(self.front_parity_combo),
            stopbits=int(self.front_stop_combo.currentText())
        )
        
        # Обновить конфигурацию заднего привода
        self.rear_config = ConnectionConfig(
            port=self.rear_port_combo.currentText(),
            slave_id=self.rear_slave_spin.value(),
            baudrate=int(self.rear_baud_combo.currentText()),
            parity=self._get_parity_from_combo(self.rear_parity_combo),
            stopbits=int(self.rear_stop_combo.currentText())
        )
        
        self.accept()
    
    def get_configs(self) -> Tuple[ConnectionConfig, ConnectionConfig]:
        """Получить конфигурации."""
        return self.front_config, self.rear_config

