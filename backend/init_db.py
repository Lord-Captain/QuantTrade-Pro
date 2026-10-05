# backend/init_db.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    print("🔍 正在初始化数据库...")
    try:
        from app.database import Base, engine, SessionLocal
        from app.config import settings
        print(f"📂 数据库 URL: {settings.DATABASE_URL}")

        # 【核心步骤】先导入 models 包，这会触发 __init__.py，进而加载所有模型文件
        # 此时，Strategy 和 BacktestResult 类都已定义，并注册到 Base.metadata 中
        print("📦 加载模型定义...")
        from app.models import Strategy, BacktestResult, SimulatedTrade
        
        # 此时再调用 configure_mappers，SQLAlchemy 就能解析所有的字符串引用了
        from sqlalchemy.orm import configure_mappers
        print("⚙️ 正在配置映射关系...")
        configure_mappers() 
        print("✅ 映射配置成功。")

        print("🛠 正在创建数据表...")
        Base.metadata.create_all(bind=engine)
        print("✅ 表结构创建完毕。")

        print("🧪 验证数据库...")
        db = SessionLocal()
        try:
            count = db.query(Strategy).count()
            print(f"✅ 验证通过：strategies 表存在 ({count} 条记录)")
            return True
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if init_database():
        print("\n🎉 初始化成功！")
    else:
        sys.exit(1)