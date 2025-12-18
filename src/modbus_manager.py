"""
Менеджер Modbus RTU соединений.
Управляет подключениями к COM-портам для работы с сервоприводами A5.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Конфигурация подключения к устройству."""
    port: str           # COM-порт (например, "COM3")
    slave_id: int       # Адрес устройства Modbus (1-247)
    baudrate: int = 115200
    parity: str = 'N'   # N - нет, E - чётность, O - нечётность
    stopbits: int = 1
    bytesize: int = 8
    timeout: float = 1.0


class ModbusManager:
    """
    Менеджер для работы с Modbus RTU устройствами.
    Поддерживает функции: 0x03 (чтение), 0x06 (запись одного), 0x10 (запись нескольких).
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Инициализация менеджера.
        
        Args:
            config: Конфигурация подключения
        """
        self.config = config
        self.client: Optional[ModbusSerialClient] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        Установить соединение с устройством.
        
        Returns:
            True если соединение успешно, иначе False
        """
        try:
            self.client = ModbusSerialClient(
                port=self.config.port,
                baudrate=self.config.baudrate,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                bytesize=self.config.bytesize,
                timeout=self.config.timeout
            )
            
            self._connected = self.client.connect()
            
            if self._connected:
                logger.info(f"Подключено к {self.config.port}, slave_id={self.config.slave_id}")
            else:
                logger.error(f"Не удалось подключиться к {self.config.port}")
            
            return self._connected
            
        except Exception as e:
            logger.error(f"Ошибка подключения к {self.config.port}: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Закрыть соединение."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info(f"Отключено от {self.config.port}")
    
    @property
    def is_connected(self) -> bool:
        """Проверка активности соединения."""
        return self._connected and self.client is not None
    
    def read_registers(self, address: int, count: int = 1) -> Optional[List[int]]:
        """
        Чтение holding-регистров (функция 0x03).
        
        Args:
            address: Начальный адрес регистра
            count: Количество регистров для чтения
            
        Returns:
            Список значений регистров или None при ошибке
        """
        if not self.is_connected:
            logger.error("Нет подключения к устройству")
            return None
        
        try:
            result = self.client.read_holding_registers(
                address=address,
                count=count,
                slave=self.config.slave_id
            )
            
            if result.isError():
                logger.error(f"Ошибка чтения регистров с адреса {hex(address)}: {result}")
                return None
            
            return list(result.registers)
            
        except ModbusException as e:
            logger.error(f"Modbus ошибка при чтении: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении регистров: {e}")
            return None
    
    def write_register(self, address: int, value: int) -> bool:
        """
        Запись одного регистра (функция 0x06).
        
        Args:
            address: Адрес регистра
            value: Значение для записи (16-бит)
            
        Returns:
            True если запись успешна
        """
        if not self.is_connected:
            logger.error("Нет подключения к устройству")
            return False
        
        try:
            result = self.client.write_register(
                address=address,
                value=value,
                slave=self.config.slave_id
            )
            
            if result.isError():
                logger.error(f"Ошибка записи в регистр {hex(address)}: {result}")
                return False
            
            logger.debug(f"Записано {value} в регистр {hex(address)}")
            return True
            
        except ModbusException as e:
            logger.error(f"Modbus ошибка при записи: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при записи регистра: {e}")
            return False
    
    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        Запись нескольких регистров (функция 0x10).
        
        Args:
            address: Начальный адрес
            values: Список значений для записи
            
        Returns:
            True если запись успешна
        """
        if not self.is_connected:
            logger.error("Нет подключения к устройству")
            return False
        
        try:
            result = self.client.write_registers(
                address=address,
                values=values,
                slave=self.config.slave_id
            )
            
            if result.isError():
                logger.error(f"Ошибка записи регистров с адреса {hex(address)}: {result}")
                return False
            
            logger.debug(f"Записано {len(values)} регистров с адреса {hex(address)}")
            return True
            
        except ModbusException as e:
            logger.error(f"Modbus ошибка при записи: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при записи регистров: {e}")
            return False
    
    def read_32bit_value(self, address: int) -> Optional[int]:
        """
        Чтение 32-битного значения (2 регистра).
        Формат A5: младший регистр первый.
        
        Args:
            address: Начальный адрес
            
        Returns:
            32-битное значение или None
        """
        registers = self.read_registers(address, count=2)
        if registers is None or len(registers) < 2:
            return None
        
        # A5 формат: [low_word, high_word] -> high_word << 16 | low_word
        return (registers[1] << 16) | registers[0]
    
    def write_32bit_value(self, address: int, value: int) -> bool:
        """
        Запись 32-битного значения (2 регистра).
        
        Args:
            address: Начальный адрес
            value: 32-битное значение
            
        Returns:
            True если запись успешна
        """
        low_word = value & 0xFFFF
        high_word = (value >> 16) & 0xFFFF
        return self.write_registers(address, [low_word, high_word])

