"""
Класс для работы с сервоприводом LICHUAN A5 Series.
Содержит карту регистров и методы управления.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import IntEnum

from .modbus_manager import ModbusManager, ConnectionConfig

logger = logging.getLogger(__name__)


class ControlMode(IntEnum):
    """Режимы управления сервоприводом (P01-02)."""
    POSITION = 0        # Позиционный режим
    SPEED = 1           # Скоростной режим
    TORQUE = 2          # Моментный режим
    POSITION_SPEED = 3  # Позиция + скорость
    POSITION_TORQUE = 4 # Позиция + момент
    SPEED_TORQUE = 5    # Скорость + момент


@dataclass
class A5Registers:
    """
    Карта регистров сервопривода A5.
    Адреса в формате: группа * 256 + номер параметра
    Например: P01-02 = 0x0102
    """
    
    # P01 - Параметры привода
    P01_00_MOTOR_CODE: int = 0x0100      # Код двигателя
    P01_02_CONTROL_MODE: int = 0x0102    # Режим управления
    P01_15_ENABLE_INPUT: int = 0x010F    # Источник enable
    
    # P02 - Основные параметры управления
    P02_00_DIR_POLARITY: int = 0x0200    # Полярность направления
    
    # P03 - Параметры входов
    P03_00_DI1_FUNCTION: int = 0x0300    # Функция DI1
    P03_01_DI2_FUNCTION: int = 0x0301    # Функция DI2
    
    # P04 - Параметры выходов
    P04_00_DO1_FUNCTION: int = 0x0400    # Функция DO1
    
    # P05 - Параметры позиционного управления
    P05_00_POS_CMD_SOURCE: int = 0x0500  # Источник команды позиции
    P05_07_ELECTRONIC_GEAR_NUM: int = 0x0507  # Электронный редуктор - числитель
    P05_08_ELECTRONIC_GEAR_DEN: int = 0x0508  # Электронный редуктор - знаменатель
    
    # P06 - Параметры скоростного управления
    P06_00_SPEED_CMD_SOURCE: int = 0x0600    # Источник команды скорости
    P06_01_INTERNAL_SPEED_1: int = 0x0601    # Внутренняя скорость 1
    P06_02_ACCEL_TIME: int = 0x0602          # Время разгона
    P06_03_DECEL_TIME: int = 0x0603          # Время торможения
    
    # P07 - Параметры моментного управления
    P07_00_TORQUE_CMD_SOURCE: int = 0x0700   # Источник команды момента
    
    # P08 - Параметры усиления (Gain)
    P08_00_POS_GAIN: int = 0x0800        # Усиление позиционного контура
    P08_02_SPEED_GAIN: int = 0x0802      # Усиление скоростного контура
    
    # P0A - Параметры защиты
    P0A_00_FAULT_CODE: int = 0x0A00      # Код текущей ошибки
    
    # P0B - Параметры мониторинга (только чтение)
    P0B_00_CURRENT_POSITION: int = 0x0B00    # Текущая позиция (32-бит)
    P0B_02_CURRENT_SPEED: int = 0x0B02       # Текущая скорость
    P0B_04_CURRENT_TORQUE: int = 0x0B04      # Текущий момент (%)
    P0B_06_DC_BUS_VOLTAGE: int = 0x0B06      # Напряжение DC шины
    P0B_10_DI_STATUS: int = 0x0B10           # Статус цифровых входов
    P0B_11_DO_STATUS: int = 0x0B11           # Статус цифровых выходов
    
    # P0C - Параметры коммуникации
    P0C_00_SLAVE_ID: int = 0x0C00        # Адрес устройства Modbus
    P0C_01_BAUDRATE: int = 0x0C01        # Скорость передачи
    P0C_02_PARITY: int = 0x0C02          # Чётность
    
    # P11 - Многосегментное позиционирование
    P11_00_SEGMENT_COUNT: int = 0x1100   # Количество сегментов
    P11_02_TARGET_POS_1: int = 0x1102    # Целевая позиция 1 (32-бит)
    P11_04_SPEED_1: int = 0x1104         # Скорость сегмента 1
    
    # P17 - Виртуальные DI/DO
    P17_00_VIRTUAL_DI: int = 0x1700      # Виртуальные входы
    P17_01_VIRTUAL_DO: int = 0x1701      # Виртуальные выходы
    
    # P30 - Чтение переменных через коммуникацию
    P30_00_READ_POSITION: int = 0x3000   # Позиция для чтения (32-бит)
    P30_02_READ_SPEED: int = 0x3002      # Скорость для чтения
    P30_04_READ_TORQUE: int = 0x3004     # Момент для чтения
    
    # P31 - Запись переменных через коммуникацию
    P31_00_CMD_POSITION: int = 0x3100    # Команда позиции (32-бит)
    P31_02_CMD_SPEED: int = 0x3102       # Команда скорости
    P31_04_CMD_TORQUE: int = 0x3104      # Команда момента


@dataclass
class ServoStatus:
    """Текущее состояние сервопривода."""
    position: int = 0           # Текущая позиция (импульсы энкодера)
    speed: int = 0              # Текущая скорость (об/мин)
    torque: int = 0             # Текущий момент (%)
    dc_voltage: float = 0.0     # Напряжение DC шины
    fault_code: int = 0         # Код ошибки (0 = нет ошибок)
    di_status: int = 0          # Статус входов
    do_status: int = 0          # Статус выходов
    is_enabled: bool = False    # Привод включен
    is_running: bool = False    # В движении


class A5ServoDevice:
    """
    Класс для управления сервоприводом LICHUAN A5.
    """
    
    def __init__(self, name: str, config: ConnectionConfig):
        """
        Инициализация устройства.
        
        Args:
            name: Имя устройства (например, "Передний", "Задний")
            config: Конфигурация подключения
        """
        self.name = name
        self.config = config
        self.modbus = ModbusManager(config)
        self.registers = A5Registers()
        self.status = ServoStatus()
        
        # Пользовательские регистры для мониторинга
        self.custom_registers: Dict[int, Dict[str, Any]] = {}
    
    def connect(self) -> bool:
        """Подключиться к устройству."""
        return self.modbus.connect()
    
    def disconnect(self):
        """Отключиться от устройства."""
        self.modbus.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Проверка подключения."""
        return self.modbus.is_connected
    
    def add_custom_register(self, address: int, name: str, description: str = "", 
                           is_32bit: bool = False):
        """
        Добавить пользовательский регистр для мониторинга.
        
        Args:
            address: Адрес регистра
            name: Название
            description: Описание
            is_32bit: True если 32-битное значение
        """
        self.custom_registers[address] = {
            "name": name,
            "description": description,
            "is_32bit": is_32bit,
            "value": None
        }
    
    def read_status(self) -> bool:
        """
        Прочитать текущее состояние привода.
        
        Returns:
            True если чтение успешно
        """
        if not self.is_connected:
            return False
        
        try:
            # Читаем позицию (32-бит)
            pos = self.modbus.read_32bit_value(self.registers.P0B_00_CURRENT_POSITION)
            if pos is not None:
                # Преобразуем в знаковое значение
                if pos > 0x7FFFFFFF:
                    pos = pos - 0x100000000
                self.status.position = pos
            
            # Читаем скорость
            speed = self.modbus.read_registers(self.registers.P0B_02_CURRENT_SPEED, 1)
            if speed:
                # Знаковое 16-битное значение
                val = speed[0]
                if val > 32767:
                    val = val - 65536
                self.status.speed = val
            
            # Читаем момент
            torque = self.modbus.read_registers(self.registers.P0B_04_CURRENT_TORQUE, 1)
            if torque:
                val = torque[0]
                if val > 32767:
                    val = val - 65536
                self.status.torque = val
            
            # Читаем код ошибки
            fault = self.modbus.read_registers(self.registers.P0A_00_FAULT_CODE, 1)
            if fault:
                self.status.fault_code = fault[0]
            
            # Читаем статус DI/DO
            di = self.modbus.read_registers(self.registers.P0B_10_DI_STATUS, 1)
            if di:
                self.status.di_status = di[0]
            
            do = self.modbus.read_registers(self.registers.P0B_11_DO_STATUS, 1)
            if do:
                self.status.do_status = do[0]
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка чтения статуса {self.name}: {e}")
            return False
    
    def read_custom_registers(self) -> Dict[int, Any]:
        """
        Прочитать все пользовательские регистры.
        
        Returns:
            Словарь {адрес: значение}
        """
        results = {}
        
        for address, info in self.custom_registers.items():
            if info["is_32bit"]:
                value = self.modbus.read_32bit_value(address)
            else:
                regs = self.modbus.read_registers(address, 1)
                value = regs[0] if regs else None
            
            info["value"] = value
            results[address] = value
        
        return results
    
    def enable(self, state: bool = True) -> bool:
        """
        Включить/выключить привод через виртуальный вход.
        
        Args:
            state: True для включения, False для выключения
            
        Returns:
            True если операция успешна
        """
        # Используем виртуальный DI для включения (бит 0 = SON)
        current = self.modbus.read_registers(self.registers.P17_00_VIRTUAL_DI, 1)
        if current is None:
            return False
        
        if state:
            new_value = current[0] | 0x0001  # Установить бит SON
        else:
            new_value = current[0] & ~0x0001  # Сбросить бит SON
        
        return self.modbus.write_register(self.registers.P17_00_VIRTUAL_DI, new_value)
    
    def set_target_position(self, position: int) -> bool:
        """
        Установить целевую позицию.
        
        Args:
            position: Целевая позиция в импульсах энкодера
            
        Returns:
            True если операция успешна
        """
        return self.modbus.write_32bit_value(self.registers.P31_00_CMD_POSITION, position)
    
    def set_target_speed(self, speed: int) -> bool:
        """
        Установить целевую скорость.
        
        Args:
            speed: Целевая скорость в об/мин
            
        Returns:
            True если операция успешна
        """
        return self.modbus.write_register(self.registers.P31_02_CMD_SPEED, speed & 0xFFFF)
    
    def set_target_torque(self, torque: int) -> bool:
        """
        Установить целевой момент.
        
        Args:
            torque: Целевой момент в %
            
        Returns:
            True если операция успешна
        """
        return self.modbus.write_register(self.registers.P31_04_CMD_TORQUE, torque & 0xFFFF)
    
    def jog(self, direction: int, speed: int = 100) -> bool:
        """
        Толчковое перемещение (JOG).
        
        Args:
            direction: 1 = вперёд, -1 = назад, 0 = стоп
            speed: Скорость в об/мин
            
        Returns:
            True если операция успешна
        """
        if direction == 0:
            return self.set_target_speed(0)
        
        actual_speed = speed if direction > 0 else -speed
        return self.set_target_speed(actual_speed)
    
    def clear_fault(self) -> bool:
        """
        Сброс ошибки привода.
        
        Returns:
            True если операция успешна
        """
        # Установка бита ALMRST через виртуальный DI
        current = self.modbus.read_registers(self.registers.P17_00_VIRTUAL_DI, 1)
        if current is None:
            return False
        
        # Установить бит сброса (обычно бит 14)
        new_value = current[0] | 0x4000
        if not self.modbus.write_register(self.registers.P17_00_VIRTUAL_DI, new_value):
            return False
        
        # Сбросить бит
        new_value = current[0] & ~0x4000
        return self.modbus.write_register(self.registers.P17_00_VIRTUAL_DI, new_value)
    
    def get_fault_description(self) -> str:
        """
        Получить описание текущей ошибки.
        
        Returns:
            Строка с описанием ошибки
        """
        fault_codes = {
            0: "Нет ошибок",
            1: "Er.01 - Перегрузка по току",
            2: "Er.02 - Превышение напряжения",
            3: "Er.03 - Низкое напряжение",
            4: "Er.04 - Ошибка энкодера",
            5: "Er.05 - Перегрев",
            6: "Er.06 - Ошибка регенерации",
            7: "Er.07 - Перегрузка",
            8: "Er.08 - Ошибка позиции",
            9: "Er.09 - Ошибка скорости",
            10: "Er.10 - Ошибка EEPROM",
            # Добавить другие коды по необходимости
        }
        
        return fault_codes.get(self.status.fault_code, 
                              f"Er.{self.status.fault_code:02d} - Неизвестная ошибка")

