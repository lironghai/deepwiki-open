"""
解析器测试脚本
测试Java和Go解析器的功能
"""
import sys
import os
import io

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加api目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.java_parser import parse_java_file
from parsers.go_parser import parse_go_file
import json


def test_java_parser():
    """测试Java解析器"""
    print("=" * 60)
    print("测试 Java 解析器")
    print("=" * 60)
    
    java_code = """
package com.example.demo;

import java.util.List;
import java.util.ArrayList;
import com.example.utils.Helper;

/**
 * 演示类
 */
public class DemoService extends BaseService implements ServiceInterface, Runnable {
    
    private static final String CONSTANT = "value";
    private List<String> items;
    protected int count;
    
    /**
     * 构造函数
     */
    public DemoService() {
        this.items = new ArrayList<>();
        this.count = 0;
    }
    
    /**
     * 公共方法
     */
    public String processData(String input, int mode) throws IOException {
        return input.toUpperCase();
    }
    
    private void helperMethod() {
        // 私有辅助方法
    }
    
    @Override
    public void run() {
        // 实现Runnable接口
    }
}

interface ServiceInterface {
    void execute();
}

enum Status {
    ACTIVE, INACTIVE, PENDING
}
"""
    
    result = parse_java_file(java_code, "DemoService.java")
    
    print(f"\n✅ Package: {result['package']}")
    print(f"✅ Imports: {len(result['imports'])} 个")
    for imp in result['imports']:
        print(f"   - {imp}")
    
    print(f"\n✅ Classes: {len(result['classes'])} 个")
    for cls in result['classes']:
        print(f"\n   📦 类名: {cls['name']}")
        print(f"      类型: {'接口' if cls['is_interface'] else '枚举' if cls['is_enum'] else '类'}")
        print(f"      修饰符: {', '.join(cls['modifiers'])}")
        if cls['extends']:
            print(f"      继承: {cls['extends']}")
        if cls['implements']:
            print(f"      实现: {', '.join(cls['implements'])}")
        
        if cls.get('methods'):
            print(f"      方法数量: {len(cls['methods'])}")
            for method in cls['methods'][:3]:  # 只显示前3个
                params = ', '.join([f"{p['type']} {p['name']}" for p in method['parameters']])
                print(f"        - {method['return_type']} {method['name']}({params})")
        
        if cls.get('fields'):
            print(f"      字段数量: {len(cls['fields'])}")
            for field in cls['fields'][:3]:  # 只显示前3个
                print(f"        - {field['type']} {field['name']}")
    
    print("\n✅ Java解析器测试通过！\n")
    return result


def test_go_parser():
    """测试Go解析器"""
    print("=" * 60)
    print("测试 Go 解析器")
    print("=" * 60)
    
    go_code = """
package main

import (
	"fmt"
	"net/http"
	"encoding/json"
)

// User 用户结构体
type User struct {
	ID       int64  `json:"id"`
	Name     string `json:"name"`
	Email    string `json:"email" validate:"required"`
	Password string `json:"-"`
}

// UserService 用户服务接口
type UserService interface {
	GetUser(id int64) (*User, error)
	CreateUser(user *User) error
	UpdateUser(user *User) error
	DeleteUser(id int64) error
}

// UserRepository 用户仓库
type UserRepository struct {
	db *sql.DB
}

// NewUserRepository 创建用户仓库
func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{db: db}
}

// GetUser 获取用户
func (r *UserRepository) GetUser(id int64) (*User, error) {
	user := &User{}
	err := r.db.QueryRow("SELECT * FROM users WHERE id = ?", id).Scan(&user.ID, &user.Name)
	return user, err
}

// ValidateUser 验证用户（普通函数）
func ValidateUser(user *User) error {
	if user.Email == "" {
		return fmt.Errorf("email is required")
	}
	return nil
}

// HandleRequest 处理请求
func HandleRequest(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
"""
    
    result = parse_go_file(go_code, "main.go")
    
    print(f"\n✅ Package: {result['package']}")
    print(f"✅ Imports: {len(result['imports'])} 个")
    for imp in result['imports']:
        print(f"   - {imp}")
    
    print(f"\n✅ Structs/Interfaces: {len(result['structs'])} 个")
    for struct in result['structs']:
        print(f"\n   📦 结构体名: {struct['name']}")
        print(f"      类型: {'接口' if struct['is_interface'] else '结构体'}")
        print(f"      字段数量: {len(struct['fields'])}")
        for field in struct['fields'][:3]:  # 只显示前3个
            tag_info = f" `{field['tag']}`" if field['tag'] else ""
            print(f"        - {field['name']} {field['type']}{tag_info}")
    
    print(f"\n✅ Functions: {len(result['functions'])} 个")
    for func in result['functions']:
        receiver_info = ""
        if func['receiver']:
            receiver_info = f"({func['receiver']['name']} {func['receiver']['type']}) "
        
        params = ', '.join([f"{p['name']} {p['type']}" for p in func['parameters']])
        returns = ', '.join(func['returns']) if func['returns'] else 'void'
        
        func_type = "方法" if func['receiver'] else "函数"
        print(f"\n   🔧 {func_type}: func {receiver_info}{func['name']}({params}) {returns}")
        if func['receiver']:
            print(f"      接收者: {func['receiver']['type']}")
    
    print("\n✅ Go解析器测试通过！\n")
    return result


def test_integration():
    """测试集成"""
    print("=" * 60)
    print("测试解析器集成")
    print("=" * 60)
    
    # 测试Java解析器
    java_result = test_java_parser()
    
    # 测试Go解析器
    go_result = test_go_parser()
    
    # 验证结果结构
    print("=" * 60)
    print("验证结果结构")
    print("=" * 60)
    
    # Java验证
    assert 'package' in java_result, "Java结果应包含package"
    assert 'imports' in java_result, "Java结果应包含imports"
    assert 'classes' in java_result, "Java结果应包含classes"
    assert len(java_result['classes']) > 0, "Java应至少解析出一个类"
    
    first_class = java_result['classes'][0]
    assert 'name' in first_class, "Java类应包含name"
    assert 'methods' in first_class, "Java类应包含methods"
    assert 'fields' in first_class, "Java类应包含fields"
    
    print("✅ Java结果结构验证通过")
    
    # Go验证
    assert 'package' in go_result, "Go结果应包含package"
    assert 'imports' in go_result, "Go结果应包含imports"
    assert 'structs' in go_result, "Go结果应包含structs"
    assert 'functions' in go_result, "Go结果应包含functions"
    assert len(go_result['structs']) > 0, "Go应至少解析出一个结构体"
    assert len(go_result['functions']) > 0, "Go应至少解析出一个函数"
    
    print("✅ Go结果结构验证通过")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
    
    # 保存测试结果
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'java': java_result,
            'go': go_result
        }, f, indent=2, ensure_ascii=False)
    
    print("\n测试结果已保存到 test_results.json")


if __name__ == '__main__':
    try:
        test_integration()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

