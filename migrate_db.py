#!/usr/bin/env python3
"""
Database migration script to add missing columns to existing tables
"""

from app import app, db
import sqlite3
import os
from sqlalchemy import text, inspect
import time

def migrate_database():
    """Migrate database with enhanced error handling and progress tracking"""
    print("🚀 Starting database migration...")
    migration_start = time.time()

    try:
        # Enhanced database connection with timeout
        db.engine.execute(text('PRAGMA journal_mode=WAL'))
        db.engine.execute(text('PRAGMA synchronous=NORMAL'))
        db.engine.execute(text('PRAGMA cache_size=10000'))
        db.engine.execute(text('PRAGMA temp_store=MEMORY'))

        print("✅ Database connection optimized")

        # Step 1: Create all tables
        print("📋 Creating database tables...")
        db.create_all()
        print("✅ All tables created successfully")

        # Step 1.5: Remove reward_title column from quests if it exists
        print("🔧 Checking quest table structure...")
        try:
            # Check if reward_title column exists
            inspector = inspect(db.engine)
            quest_columns = inspector.get_columns('quest')
            has_reward_title = any(col['name'] == 'reward_title' for col in quest_columns)

            if has_reward_title:
                print("  📝 Removing deprecated reward_title column from quests...")
                # SQLite doesn't support DROP COLUMN, so we need to recreate the table
                db.engine.execute(text('''
                    CREATE TABLE quest_new AS
                    SELECT id, title, description, type, target_value, reward_xp, reward_coins,
                           reward_reputation, icon, difficulty, quest_category, is_active,
                           is_repeatable, expires_at, created_at, last_refresh
                    FROM quest
                '''))
                db.engine.execute(text('DROP TABLE quest'))
                db.engine.execute(text('ALTER TABLE quest_new RENAME TO quest'))
                print("    ✅ reward_title column removed")
        except Exception as e:
            print(f"    ⚠️ Could not modify quest table: {e}")

        # Step 2: Initialize default data with progress tracking
        print("🔧 Initializing default data...")

        # Initialize default themes with progress
        print("  🎨 Creating default themes...")
        SiteTheme.create_default_themes()
        print("    ✅ Themes initialized")

        # Initialize default gradient themes
        print("  🌈 Creating default gradient themes...")
        GradientTheme.create_default_themes()
        print("    ✅ Gradient themes initialized")

        # Initialize default achievements
        print("  🏆 Creating default achievements...")
        Achievement.create_default_achievements()
        print("    ✅ Achievements initialized")

        # Initialize default quests
        print("  📜 Creating default quests...")
        Quest.create_default_quests()
        print("    ✅ Quests initialized")

        # Initialize default custom titles
        print("  👑 Creating default custom titles...")
        CustomTitle.create_default_titles()
        print("    ✅ Custom titles initialized")

        # Initialize default shop items
        print("  🛒 Creating default shop items...")
        ShopItem.create_default_items()
        print("    ✅ Shop items initialized")

        # Initialize default badges
        print("  🎖️ Creating default badges...")
        Badge.create_default_badges()
        print("    ✅ Badges initialized")

        # Initialize default admin roles
        print("  🔧 Creating default admin roles...")
        AdminCustomRole.create_default_roles()
        print("    ✅ Admin roles initialized")

        # Initialize reputation logs
        print("  📊 Initializing reputation tracking...")
        ReputationLog.init_for_existing_players()
        print("    ✅ Reputation tracking initialized")

        db.session.commit()

        migration_time = time.time() - migration_start
        print(f"🎉 Database migration completed successfully in {migration_time:.2f} seconds!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    migrate_database()