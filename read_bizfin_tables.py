"""
数据库表结构读取脚本
用于读取benlai_bizfin数据库的表结构
严格遵守只读规则，只执行查询操作
"""
import pymysql

def read_bizfin_table_structure():
    """读取benlai_bizfin数据库的表结构"""
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
            # 1. 获取所有表名
            print("获取benlai_bizfin数据库中的表:")
            print("-" * 60)
            
            sql = "SHOW TABLES"
            cursor.execute(sql)
            tables = cursor.fetchall()
            
            table_names = []
            for table in tables:
                table_name = list(table.values())[0]
                table_names.append(table_name)
            
            # 按名称排序并打印
            table_names.sort()
            for i, table_name in enumerate(table_names, 1):
                print(f"{i}. {table_name}")
            
            print("-" * 60)
            print(f"总共找到 {len(table_names)} 个表")
            print("=" * 60)
            
            # 2. 获取前3个表的详细结构（示例）
            if table_names:
                print("\n查看部分表的详细结构:")
                print("-" * 60)
                
                # 只查看前3个表作为示例
                sample_tables = table_names[:3]
                for table_name in sample_tables:
                    print(f"\n表: {table_name}")
                    print("-" * 40)
                    
                    # 查看表结构
                    desc_sql = f"DESCRIBE {table_name}"
                    cursor.execute(desc_sql)
                    columns = cursor.fetchall()
                    
                    # 打印列信息
                    print(f"{'字段名':<20} {'类型':<20} {'是否为空':<10} {'默认值':<10} {'键':<5}")
                    print("-" * 65)
                    for col in columns:
                        field = col['Field']
                        type_ = col['Type']
                        null = col['Null']
                        default = col['Default'] if col['Default'] is not None else ''
                        key = col['Key']
                        
                        print(f"{field:<20} {type_:<20} {null:<10} {default:<10} {key:<5}")
                    
                print("-" * 60)
                print("提示: 已显示前3个表的结构，如需查看更多表结构，请修改脚本")
            
    except pymysql.MySQLError as e:
        print(f"连接失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    read_bizfin_table_structure()