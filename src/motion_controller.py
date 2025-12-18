"""
Контроллер движения для тренажёра "Конь".
Управляет синхронизацией двух сервоприводов для имитации шага и галопа.
"""

import logging
import math
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto
from threading import Thread, Event

logger = logging.getLogger(__name__)


class MotionMode(Enum):
    """Режимы движения тренажёра."""
    STOPPED = auto()    # Остановлен
    MANUAL = auto()     # Ручной режим
    WALK = auto()       # Шаг
    GALLOP = auto()     # Галоп
    CUSTOM = auto()     # Пользовательский паттерн


@dataclass
class MotionPattern:
    """Параметры паттерна движения."""
    name: str                   # Название паттерна
    cycle_time_ms: int          # Время полного цикла в мс
    front_amplitude: int        # Амплитуда переднего привода (градусы или импульсы)
    rear_amplitude: int         # Амплитуда заднего привода
    phase_shift: int            # Сдвиг фазы между приводами (градусы)
    front_offset: int = 0       # Смещение центра переднего привода
    rear_offset: int = 0        # Смещение центра заднего привода
    
    def calculate_positions(self, phase: float) -> tuple[int, int]:
        """
        Рассчитать позиции приводов для заданной фазы.
        
        Args:
            phase: Текущая фаза цикла (0.0 - 1.0)
            
        Returns:
            Кортеж (позиция_переднего, позиция_заднего)
        """
        # Синусоидальное движение
        front_angle = 2 * math.pi * phase
        rear_angle = 2 * math.pi * phase + math.radians(self.phase_shift)
        
        front_pos = int(self.front_offset + self.front_amplitude * math.sin(front_angle))
        rear_pos = int(self.rear_offset + self.rear_amplitude * math.sin(rear_angle))
        
        return front_pos, rear_pos


# Предустановленные паттерны
PRESET_PATTERNS = {
    MotionMode.WALK: MotionPattern(
        name="Шаг",
        cycle_time_ms=2000,     # 2 секунды на цикл = медленный шаг
        front_amplitude=3000,   # Амплитуда в импульсах энкодера
        rear_amplitude=3000,
        phase_shift=180         # Противофаза - когда перед вверху, зад внизу
    ),
    MotionMode.GALLOP: MotionPattern(
        name="Галоп",
        cycle_time_ms=600,      # 0.6 секунды = быстрый галоп
        front_amplitude=5000,   # Большая амплитуда
        rear_amplitude=5000,
        phase_shift=90          # Сдвиг 90° - волнообразное движение
    )
}


class MotionController:
    """
    Контроллер синхронного движения двух сервоприводов.
    """
    
    def __init__(self, front_servo, rear_servo):
        """
        Инициализация контроллера.
        
        Args:
            front_servo: Передний сервопривод (A5ServoDevice)
            rear_servo: Задний сервопривод (A5ServoDevice)
        """
        self.front_servo = front_servo
        self.rear_servo = rear_servo
        
        self.current_mode = MotionMode.STOPPED
        self.current_pattern: Optional[MotionPattern] = None
        
        # Поток движения
        self._motion_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Колбэки для UI
        self._on_position_update: Optional[Callable[[int, int], None]] = None
        self._on_mode_change: Optional[Callable[[MotionMode], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Пользовательские паттерны
        self.custom_patterns: Dict[str, MotionPattern] = {}
    
    def set_callbacks(self, 
                     on_position_update: Optional[Callable[[int, int], None]] = None,
                     on_mode_change: Optional[Callable[[MotionMode], None]] = None,
                     on_error: Optional[Callable[[str], None]] = None):
        """Установить колбэки для событий."""
        self._on_position_update = on_position_update
        self._on_mode_change = on_mode_change
        self._on_error = on_error
    
    def start_motion(self, mode: MotionMode, pattern: Optional[MotionPattern] = None):
        """
        Запустить движение в указанном режиме.
        
        Args:
            mode: Режим движения
            pattern: Паттерн (для CUSTOM режима)
        """
        # Сначала остановим текущее движение
        self.stop_motion()
        
        if mode == MotionMode.STOPPED:
            return
        
        if mode == MotionMode.MANUAL:
            self.current_mode = mode
            if self._on_mode_change:
                self._on_mode_change(mode)
            return
        
        # Получить паттерн
        if mode == MotionMode.CUSTOM:
            if pattern is None:
                logger.error("Для CUSTOM режима требуется паттерн")
                return
            self.current_pattern = pattern
        else:
            self.current_pattern = PRESET_PATTERNS.get(mode)
        
        if self.current_pattern is None:
            logger.error(f"Паттерн для режима {mode} не найден")
            return
        
        self.current_mode = mode
        self._stop_event.clear()
        
        # Запустить поток движения
        self._motion_thread = Thread(target=self._motion_loop, daemon=True)
        self._motion_thread.start()
        
        logger.info(f"Запущен режим: {self.current_pattern.name}")
        
        if self._on_mode_change:
            self._on_mode_change(mode)
    
    def stop_motion(self):
        """Остановить движение."""
        self._stop_event.set()
        
        if self._motion_thread and self._motion_thread.is_alive():
            self._motion_thread.join(timeout=2.0)
        
        self._motion_thread = None
        self.current_mode = MotionMode.STOPPED
        self.current_pattern = None
        
        # Остановить приводы
        if self.front_servo.is_connected:
            self.front_servo.set_target_speed(0)
        if self.rear_servo.is_connected:
            self.rear_servo.set_target_speed(0)
        
        logger.info("Движение остановлено")
        
        if self._on_mode_change:
            self._on_mode_change(MotionMode.STOPPED)
    
    def _motion_loop(self):
        """Главный цикл движения (выполняется в отдельном потоке)."""
        if self.current_pattern is None:
            return
        
        cycle_time_s = self.current_pattern.cycle_time_ms / 1000.0
        update_interval = 0.02  # 50 Гц обновление
        
        start_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                # Вычислить текущую фазу
                elapsed = time.time() - start_time
                phase = (elapsed % cycle_time_s) / cycle_time_s
                
                # Рассчитать позиции
                front_pos, rear_pos = self.current_pattern.calculate_positions(phase)
                
                # Отправить команды на приводы
                if self.front_servo.is_connected:
                    self.front_servo.set_target_position(front_pos)
                
                if self.rear_servo.is_connected:
                    self.rear_servo.set_target_position(rear_pos)
                
                # Уведомить UI
                if self._on_position_update:
                    self._on_position_update(front_pos, rear_pos)
                
                # Ждать следующего обновления
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле движения: {e}")
                if self._on_error:
                    self._on_error(str(e))
                break
    
    def manual_move(self, front_position: Optional[int] = None, 
                   rear_position: Optional[int] = None):
        """
        Ручное перемещение приводов.
        
        Args:
            front_position: Позиция переднего привода (None = не менять)
            rear_position: Позиция заднего привода (None = не менять)
        """
        if self.current_mode != MotionMode.MANUAL:
            logger.warning("Ручное управление доступно только в режиме MANUAL")
            return
        
        if front_position is not None and self.front_servo.is_connected:
            self.front_servo.set_target_position(front_position)
        
        if rear_position is not None and self.rear_servo.is_connected:
            self.rear_servo.set_target_position(rear_position)
        
        if self._on_position_update:
            self._on_position_update(
                front_position or 0,
                rear_position or 0
            )
    
    def manual_jog(self, servo: str, direction: int, speed: int = 100):
        """
        Толчковое перемещение в ручном режиме.
        
        Args:
            servo: "front" или "rear"
            direction: 1 = вперёд, -1 = назад, 0 = стоп
            speed: Скорость об/мин
        """
        if servo == "front" and self.front_servo.is_connected:
            self.front_servo.jog(direction, speed)
        elif servo == "rear" and self.rear_servo.is_connected:
            self.rear_servo.jog(direction, speed)
    
    def add_custom_pattern(self, name: str, pattern: MotionPattern):
        """Добавить пользовательский паттерн."""
        self.custom_patterns[name] = pattern
        logger.info(f"Добавлен паттерн: {name}")
    
    def get_pattern_info(self) -> Dict[str, Any]:
        """Получить информацию о текущем паттерне."""
        if self.current_pattern is None:
            return {"mode": "STOPPED", "pattern": None}
        
        return {
            "mode": self.current_mode.name,
            "pattern": {
                "name": self.current_pattern.name,
                "cycle_time_ms": self.current_pattern.cycle_time_ms,
                "front_amplitude": self.current_pattern.front_amplitude,
                "rear_amplitude": self.current_pattern.rear_amplitude,
                "phase_shift": self.current_pattern.phase_shift
            }
        }
    
    def emergency_stop(self):
        """Аварийная остановка - немедленно останавливает все приводы."""
        logger.warning("АВАРИЙНАЯ ОСТАНОВКА!")
        
        # Остановить поток
        self._stop_event.set()
        
        # Немедленно остановить приводы
        try:
            if self.front_servo.is_connected:
                self.front_servo.set_target_speed(0)
                self.front_servo.enable(False)
        except:
            pass
        
        try:
            if self.rear_servo.is_connected:
                self.rear_servo.set_target_speed(0)
                self.rear_servo.enable(False)
        except:
            pass
        
        self.current_mode = MotionMode.STOPPED
        
        if self._on_mode_change:
            self._on_mode_change(MotionMode.STOPPED)

