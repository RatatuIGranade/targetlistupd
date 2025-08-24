
from app import app, db
from sqlalchemy import text
import schedule
import time
import logging

def vacuum_analyze():
    """Выполняет VACUUM ANALYZE для оптимизации PostgreSQL"""
    try:
        with app.app_context():
            # Проверяем, что используется PostgreSQL
            if 'postgresql' in str(db.engine.url):
                logging.info("Выполняем VACUUM ANALYZE...")
                db.session.execute(text("VACUUM ANALYZE;"))
                db.session.commit()
                logging.info("VACUUM ANALYZE выполнен успешно")
            else:
                logging.info("VACUUM ANALYZE пропущен - используется не PostgreSQL")
    except Exception as e:
        logging.error(f"Ошибка при выполнении VACUUM ANALYZE: {e}")

def update_table_statistics():
    """Обновляет статистику таблиц PostgreSQL"""
    try:
        with app.app_context():
            if 'postgresql' in str(db.engine.url):
                logging.info("Обновляем статистику таблиц...")
                db.session.execute(text("ANALYZE;"))
                db.session.commit()
                logging.info("Статистика таблиц обновлена")
    except Exception as e:
        logging.error(f"Ошибка при обновлении статистики: {e}")

def reindex_tables():
    """Переиндексирует таблицы для оптимизации"""
    try:
        with app.app_context():
            if 'postgresql' in str(db.engine.url):
                logging.info("Переиндексация таблиц...")
                # Переиндексируем основные таблицы
                tables = ['player', 'quest', 'achievement', 'shop_item']
                for table in tables:
                    db.session.execute(text(f"REINDEX TABLE {table};"))
                db.session.commit()
                logging.info("Переиндексация завершена")
    except Exception as e:
        logging.error(f"Ошибка при переиндексации: {e}")

# Планировщик задач
schedule.every().hour.do(update_table_statistics)
schedule.every(6).hours.do(vacuum_analyze)
schedule.every().day.at("03:00").do(reindex_tables)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту
