"""
数据读取脚本
用于读取asset_daily表的前10条数据
严格遵守只读规则，只执行查询操作
"""
import pymysql

def read_asset_daily_data():
    """读取asset_daily表的前10条数据"""
    try:
        # 连接参数
        host = 'blsh-branch.rwlb.rds.aliyuncs.com'
        user = 'db_admin'
        password = 'BenlaiBranch@717'
        port = 3306
        database = 'benlai_bizfin'
        
        print(f"正在连接到 MySQL 服务器: {host}:{port}")
        print(f"用户名: {user}")
        print(f"数据库: {database}")
        
        # 建立连接
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("连接成功！")
        print("=" * 60)
        
        # 创建游标
        with connection.cursor() as cursor:
            # 执行查询前10条数据的SQL语句
            print("读取asset_daily表的前10条数据:")
            print("-" * 60)
            
            sql = "SELECT * FROM asset_daily LIMIT 10"
            cursor.execute(sql)
            
            # 获取结果
            rows = cursor.fetchall()
            
            if rows:
                # 打印表头
                headers = list(rows[0].keys())
                print(" | ".join([f"{h:<15}" for h in headers]))
                print("-" * 60)
                
                # 打印数据
                for i, row in enumerate(rows, 1):
                    values = [f"{str(row[h]):<15}" for h in headers]
                    print(f"{i}. " + " | ".join(values))
                
                print("-" * 60)
                print(f"总共读取 {len(rows)} 条数据")
            else:
                print("表中没有数据")
            
    except pymysql.MySQLError as e:
        print(f"连接失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    read_asset_daily_data()