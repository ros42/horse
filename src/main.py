"""
Horse Trainer - Спортивный тренажёр "Конь"
Главный файл приложения.

Управление двумя сервоприводами LICHUAN A5 для имитации
движений лошади (шаг, галоп) при тренировке спортивных навыков.
"""

import sys
import logging
from pathlib import Path

# Добавляем путь src в sys.path для корректных импортов
SRC_DIR = Path(__file__).parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('horse_trainer.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Точка входа приложения."""
    logger.info("=" * 50)
    logger.info("🐎 Запуск Horse Trainer")
    logger.info("=" * 50)
    
    # Создать приложение
    app = QApplication(sys.argv)
    
    # Настройка приложения
    app.setApplicationName("Horse Trainer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("HorseTrainer")
    
    # Установить шрифт по умолчанию
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Глобальные стили
    app.setStyleSheet("""
        QToolTip {
            background-color: #16213e;
            color: #ffffff;
            border: 1px solid #e94560;
            padding: 5px;
            border-radius: 3px;
        }
        
        QScrollBar:vertical {
            background: #0f3460;
            width: 12px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background: #e94560;
            min-height: 30px;
            border-radius: 6px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """)
    
    # Импорт главного окна (после создания QApplication)
    from ui.main_window import MainWindow
    
    # Создать и показать главное окно
    window = MainWindow()
    window.show()
    
    logger.info("Приложение запущено")
    
    # Запустить главный цикл
    exit_code = app.exec()
    
    logger.info(f"Приложение завершено с кодом {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

