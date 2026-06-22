"""
列举包含"benlai"的数据库脚本
严格遵守只读规则，只执行查询操作
"""
import pymysql

def list_benlai_databases():
    """列举所有包含benlai的数据库"""
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
            
            print("列举包含'benlai'的数据库:")
            print("-" * 60)
            
            found = []
            for db in databases:
                db_name = db['Database']
                
                # 检查是否包含'benlai'（不区分大小写）
                if 'benlai' in db_name.lower():
                    found.append(db_name)
            
            # 按名称排序并打印
            found.sort()
            for db_name in found:
                print(f"✓ {db_name}")
            
            print("-" * 60)
            print(f"总共找到 {len(found)} 个包含'benlai'的数据库")
            
    except pymysql.MySQLError as e:
        print(f"连接失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    list_benlai_databases()