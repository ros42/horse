"""
Главное окно приложения Horse Trainer.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QToolBar, QMenuBar, QMenu,
    QMessageBox, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon

from .servo_panel import ServoPanel
from .motion_panel import MotionPanel
from .settings_dialog import SettingsDialog
from ..servo_device import A5ServoDevice
from ..motion_controller import MotionController, MotionMode
from ..modbus_manager import ConnectionConfig

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🐎 Horse Trainer - Спортивный тренажёр")
        self.setMinimumSize(1200, 800)
        
        # Устройства
        self.front_servo: Optional[A5ServoDevice] = None
        self.rear_servo: Optional[A5ServoDevice] = None
        self.motion_controller: Optional[MotionController] = None
        
        # Конфигурации по умолчанию
        self.front_config = ConnectionConfig(
            port="COM3",
            slave_id=1,
            baudrate=115200
        )
        self.rear_config = ConnectionConfig(
            port="COM4",
            slave_id=2,
            baudrate=115200
        )
        
        # Инициализация UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Таймер обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(200)  # 5 Гц обновление
        
        # Применить стили
        self._apply_styles()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Заголовок
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Разделитель для панелей
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Панель переднего сервопривода
        self.front_panel = ServoPanel("Передний привод", "front")
        self.front_panel.on_jog_start.connect(lambda d: self._jog_servo("front", d))
        self.front_panel.on_jog_stop.connect(lambda: self._jog_servo("front", 0))
        splitter.addWidget(self.front_panel)
        
        # Центральная панель движения
        self.motion_panel = MotionPanel()
        self.motion_panel.on_mode_change.connect(self._change_motion_mode)
        self.motion_panel.on_emergency_stop.connect(self._emergency_stop)
        splitter.addWidget(self.motion_panel)
        
        # Панель заднего сервопривода
        self.rear_panel = ServoPanel("Задний привод", "rear")
        self.rear_panel.on_jog_start.connect(lambda d: self._jog_servo("rear", d))
        self.rear_panel.on_jog_stop.connect(lambda: self._jog_servo("rear", 0))
        splitter.addWidget(self.rear_panel)
        
        # Пропорции панелей
        splitter.setSizes([350, 500, 350])
        
        main_layout.addWidget(splitter, stretch=1)
    
    def _create_header(self) -> QFrame:
        """Создать заголовок."""
        frame = QFrame()
        frame.setObjectName("headerFrame")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Логотип/название
        title = QLabel("🐎 HORSE TRAINER")
        title.setObjectName("headerTitle")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Статус подключения
        self.connection_status = QLabel("⚪ Не подключено")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.connection_status)
        
        return frame
    
    def _setup_menu(self):
        """Настройка меню."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        settings_action = QAction("⚙ Настройки...", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Подключение
        connect_menu = menubar.addMenu("Подключение")
        
        self.connect_action = QAction("🔌 Подключиться", self)
        self.connect_action.triggered.connect(self._toggle_connection)
        connect_menu.addAction(self.connect_action)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Настройка панели инструментов."""
        toolbar = QToolBar("Основная")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Кнопка подключения
        self.connect_btn = QAction("🔌 Подключить", self)
        self.connect_btn.triggered.connect(self._toggle_connection)
        toolbar.addAction(self.connect_btn)
        
        toolbar.addSeparator()
        
        # Кнопка настроек
        settings_btn = QAction("⚙ Настройки", self)
        settings_btn.triggered.connect(self._show_settings)
        toolbar.addAction(settings_btn)
        
        toolbar.addSeparator()
        
        # Аварийная остановка
        stop_btn = QAction("🛑 СТОП", self)
        stop_btn.triggered.connect(self._emergency_stop)
        toolbar.addAction(stop_btn)
    
    def _setup_statusbar(self):
        """Настройка статусной строки."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Виджеты статуса
        self.front_status_label = QLabel("Передний: --")
        self.rear_status_label = QLabel("Задний: --")
        self.mode_label = QLabel("Режим: Остановлен")
        
        self.statusbar.addWidget(self.front_status_label)
        self.statusbar.addWidget(QLabel(" | "))
        self.statusbar.addWidget(self.rear_status_label)
        self.statusbar.addPermanentWidget(self.mode_label)
    
    def _apply_styles(self):
        """Применить стили."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            
            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16213e, stop:1 #0f3460);
                border-radius: 10px;
                border: 1px solid #e94560;
            }
            
            #headerTitle {
                color: #e94560;
            }
            
            #connectionStatus {
                color: #a0a0a0;
                padding: 5px 10px;
                background: rgba(0,0,0,0.3);
                border-radius: 5px;
            }
            
            QMenuBar {
                background-color: #16213e;
                color: #ffffff;
                padding: 5px;
            }
            
            QMenuBar::item:selected {
                background-color: #e94560;
            }
            
            QMenu {
                background-color: #16213e;
                color: #ffffff;
                border: 1px solid #e94560;
            }
            
            QMenu::item:selected {
                background-color: #e94560;
            }
            
            QToolBar {
                background-color: #16213e;
                border: none;
                padding: 5px;
                spacing: 10px;
            }
            
            QToolBar QToolButton {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #e94560;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            
            QToolBar QToolButton:hover {
                background-color: #e94560;
            }
            
            QStatusBar {
                background-color: #16213e;
                color: #a0a0a0;
            }
            
            QSplitter::handle {
                background-color: #e94560;
                width: 2px;
            }
        """)
    
    def _toggle_connection(self):
        """Переключить подключение."""
        if self.front_servo and self.front_servo.is_connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """Подключиться к устройствам."""
        try:
            # Создать устройства
            self.front_servo = A5ServoDevice("Передний", self.front_config)
            self.rear_servo = A5ServoDevice("Задний", self.rear_config)
            
            # Подключиться
            front_ok = self.front_servo.connect()
            rear_ok = self.rear_servo.connect()
            
            if front_ok or rear_ok:
                # Создать контроллер движения
                self.motion_controller = MotionController(
                    self.front_servo, 
                    self.rear_servo
                )
                self.motion_controller.set_callbacks(
                    on_position_update=self._on_position_update,
                    on_mode_change=self._on_mode_change,
                    on_error=self._on_error
                )
                
                # Передать устройства в панели
                self.front_panel.set_device(self.front_servo)
                self.rear_panel.set_device(self.rear_servo)
                
                # Обновить UI
                status_parts = []
                if front_ok:
                    status_parts.append(f"Передний: {self.front_config.port}")
                if rear_ok:
                    status_parts.append(f"Задний: {self.rear_config.port}")
                
                self.connection_status.setText(f"🟢 {', '.join(status_parts)}")
                self.connect_btn.setText("🔌 Отключить")
                self.connect_action.setText("🔌 Отключиться")
                
                self.statusbar.showMessage("Подключено к устройствам", 3000)
                logger.info("Подключение установлено")
            else:
                QMessageBox.warning(
                    self, 
                    "Ошибка подключения",
                    "Не удалось подключиться к устройствам.\n"
                    "Проверьте настройки COM-портов."
                )
                
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения:\n{e}")
    
    def _disconnect(self):
        """Отключиться от устройств."""
        # Остановить движение
        if self.motion_controller:
            self.motion_controller.stop_motion()
            self.motion_controller = None
        
        # Отключить устройства
        if self.front_servo:
            self.front_servo.disconnect()
            self.front_servo = None
        
        if self.rear_servo:
            self.rear_servo.disconnect()
            self.rear_servo = None
        
        # Обновить панели
        self.front_panel.set_device(None)
        self.rear_panel.set_device(None)
        
        # Обновить UI
        self.connection_status.setText("⚪ Не подключено")
        self.connect_btn.setText("🔌 Подключить")
        self.connect_action.setText("🔌 Подключиться")
        
        self.statusbar.showMessage("Отключено", 3000)
        logger.info("Отключено от устройств")
    
    def _update_status(self):
        """Обновить статус устройств."""
        if self.front_servo and self.front_servo.is_connected:
            self.front_servo.read_status()
            status = self.front_servo.status
            self.front_status_label.setText(
                f"Передний: {status.position} / {status.speed} об/мин"
            )
            self.front_panel.update_status(status)
        
        if self.rear_servo and self.rear_servo.is_connected:
            self.rear_servo.read_status()
            status = self.rear_servo.status
            self.rear_status_label.setText(
                f"Задний: {status.position} / {status.speed} об/мин"
            )
            self.rear_panel.update_status(status)
    
    def _change_motion_mode(self, mode: MotionMode):
        """Изменить режим движения."""
        if self.motion_controller:
            self.motion_controller.start_motion(mode)
    
    def _emergency_stop(self):
        """Аварийная остановка."""
        logger.warning("Аварийная остановка!")
        
        if self.motion_controller:
            self.motion_controller.emergency_stop()
        
        self.motion_panel.set_mode(MotionMode.STOPPED)
        self.mode_label.setText("Режим: ⚠️ АВАРИЙНЫЙ СТОП")
        
        QMessageBox.warning(self, "Аварийная остановка", "Все приводы остановлены!")
    
    def _jog_servo(self, servo: str, direction: int):
        """Толчковое перемещение."""
        if self.motion_controller:
            self.motion_controller.manual_jog(servo, direction, speed=200)
    
    def _on_position_update(self, front_pos: int, rear_pos: int):
        """Колбэк обновления позиции."""
        self.motion_panel.update_positions(front_pos, rear_pos)
    
    def _on_mode_change(self, mode: MotionMode):
        """Колбэк смены режима."""
        mode_names = {
            MotionMode.STOPPED: "Остановлен",
            MotionMode.MANUAL: "Ручной",
            MotionMode.WALK: "🚶 Шаг",
            MotionMode.GALLOP: "🏇 Галоп",
            MotionMode.CUSTOM: "Пользовательский"
        }
        self.mode_label.setText(f"Режим: {mode_names.get(mode, mode.name)}")
        self.motion_panel.set_mode(mode)
    
    def _on_error(self, error: str):
        """Колбэк ошибки."""
        self.statusbar.showMessage(f"Ошибка: {error}", 5000)
    
    def _show_settings(self):
        """Показать диалог настроек."""
        dialog = SettingsDialog(self, self.front_config, self.rear_config)
        if dialog.exec():
            self.front_config, self.rear_config = dialog.get_configs()
            self.statusbar.showMessage("Настройки сохранены", 3000)
    
    def _show_about(self):
        """Показать информацию о программе."""
        QMessageBox.about(
            self,
            "О программе",
            "🐎 Horse Trainer v1.0\n\n"
            "Спортивный тренажёр для отработки навыков верховой езды.\n\n"
            "Управление двумя сервоприводами LICHUAN A5\n"
            "для имитации движений лошади.\n\n"
            "© 2024"
        )
    
    def closeEvent(self, event):
        """Обработка закрытия окна."""
        # Спросить подтверждение если подключено
        if self.front_servo and self.front_servo.is_connected:
            reply = QMessageBox.question(
                self,
                "Подтверждение выхода",
                "Устройства подключены. Отключиться и выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Отключиться перед выходом
        self._disconnect()
        
        event.accept()

