"""
MySQL数据库列表查询脚本
用于连接指定的MySQL服务器并列出所有数据库名称
"""
import pymysql

def list_databases():
    """连接MySQL并列出所有数据库"""
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
        print("=" * 50)
        
        # 创建游标
        with connection.cursor() as cursor:
            # 执行查询所有数据库的SQL语句
            sql = "SHOW DATABASES"
            cursor.execute(sql)
            
            # 获取结果
            databases = cursor.fetchall()
            
            print("数据库列表:")
            print("-" * 50)
            
            for db in databases:
                print(f"✓ {db['Database']}")
            
            print("-" * 50)
            print(f"总共找到 {len(databases)} 个数据库")
            
    except pymysql.MySQLError as e:
        print(f"连接失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    list_databases()