"""
数据库搜索脚本
用于搜索与"汇农通"相关的数据库
严格遵守只读规则，只执行查询操作
"""
import pymysql

def search_huitong_databases():
    """搜索与汇农通相关的数据库"""
    try:
        # 连接参数
        host = 'blsh-branch.rwlb.rds.aliyuncs.com'
        user = 'db_admin'
        password = 'BenlaiBranch@717'
        port = 3306
        
        print(f"正在连接到 MySQL 服务器: {host}:{port}")
        print(f"用户名: {user}")
        
        # 建立连接
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("连接成功！")
        print("=" * 60)
        
        # 创建游标
        with connection.cursor() as cursor:
            # 执行查询所有数据库的SQL语句
            sql = "SHOW DATABASES"
            cursor.execute(sql)
            
            # 获取结果
            databases = cursor.fetchall()
            
            print("搜索与'汇农通'相关的数据库:")
            print("-" * 60)
            
            # 搜索关键词
            keywords = ['huitong', 'huitong', 'agri', 'agriculture', 'farm', 'rural', 'huinong']
            
            found = False
            for db in databases:
                db_name = db['Database'].lower()
                
                # 检查是否包含相关关键词
                if any(keyword in db_name for keyword in keywords):
                    print(f"✓ {db['Database']}")
                    found = True
            
            # 检查是否有包含中文"汇"或"农"的数据库
            print("\n搜索包含'汇'或'农'的数据库:")
            print("-" * 60)
            
            for db in databases:
                db_name = db['Database']
                if '汇' in db_name or '农' in db_name:
                    print(f"✓ {db_name}")
                    found = True
            
            print("-" * 60)
            if not found:
                print("未找到与'汇农通'相关的数据库")
            
    except pymysql.MySQLError as e:
        print(f"连接失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    search_huitong_databases()