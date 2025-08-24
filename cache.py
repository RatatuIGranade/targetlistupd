import json
import os
import time
from functools import wraps
from datetime import timedelta

# Простой кеш в памяти
_memory_cache = {}

class Cache:
    @staticmethod
    def get(key):
        """Получить значение из кэша"""
        if key not in _memory_cache:
            return None

        item = _memory_cache[key]
        if time.time() > item['expires']:
            del _memory_cache[key]
            return None

        return item['data']

    @staticmethod
    def set(key, value, expire=3600):
        """Установить значение в кэш"""
        try:
            _memory_cache[key] = {
                'data': value,
                'expires': time.time() + expire
            }
            return True
        except:
            return False

    @staticmethod
    def delete(key):
        """Удалить ключ из кэша"""
        try:
            if key in _memory_cache:
                del _memory_cache[key]
            return True
        except:
            return False

    @staticmethod
    def clear_pattern(pattern):
        """Очистить все ключи по паттерну"""
        try:
            # Простая очистка по началу ключа
            keys_to_delete = []
            pattern_clean = pattern.replace('*', '')

            for key in _memory_cache:
                if key.startswith(pattern_clean):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del _memory_cache[key]
            return True
        except:
            return False

def cached(expire=3600, key_func=None):
    """Декоратор для кэширования результатов функций"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Пытаемся получить из кэша
            cached_result = Cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            Cache.set(cache_key, result, expire)
            return result
        return wrapper
    return decorator