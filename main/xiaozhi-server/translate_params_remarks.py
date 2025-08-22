#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import sys

# Set UTF-8 encoding for output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Database connection
connection = pymysql.connect(
    host='nozomi.proxy.rlwy.net',
    port=25037,
    user='root',
    password='OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    database='railway',
    charset='utf8mb4'
)

try:
    with connection.cursor() as cursor:
        print("=" * 60)
        print("Current Parameter Remarks in Database:")
        print("=" * 60)
        
        # Get all parameters with their remarks
        cursor.execute("""
        SELECT id, param_code, param_value, remark
        FROM sys_params
        ORDER BY param_code
        """)
        
        params = cursor.fetchall()
        
        print(f"Found {len(params)} parameters:")
        print("-" * 60)
        
        for param in params:
            if param[3]:  # If remark exists
                print(f"Code: {param[1]}")
                print(f"  Remark: {param[3]}")
        
        print("\n" + "=" * 60)
        print("Translating Chinese Remarks to English:")
        print("=" * 60)
        
        # Translation mappings for common parameter remarks
        translations = [
            # System parameters
            ("是否允许用户注册", "Allow user registration"),
            ("允许用户注册", "Allow user registration"),
            ("是否启用手机号注册", "Enable mobile phone registration"),
            ("启用手机号注册", "Enable mobile phone registration"),
            ("系统公告", "System announcement"),
            ("系统版本", "System version"),
            ("系统名称", "System name"),
            ("系统描述", "System description"),
            ("系统邮箱", "System email"),
            ("系统电话", "System phone"),
            ("系统地址", "System address"),
            ("系统备案号", "System ICP number"),
            ("版权信息", "Copyright information"),
            
            # Security parameters
            ("密码最小长度", "Minimum password length"),
            ("密码最大长度", "Maximum password length"),
            ("密码复杂度要求", "Password complexity requirements"),
            ("登录失败次数限制", "Login failure limit"),
            ("账户锁定时长", "Account lock duration"),
            ("会话超时时间", "Session timeout period"),
            ("验证码有效期", "Verification code validity period"),
            ("刷新令牌有效期", "Refresh token validity period"),
            ("访问令牌有效期", "Access token validity period"),
            
            # Email/SMS configuration
            ("邮件服务器地址", "Email server address"),
            ("邮件服务器端口", "Email server port"),
            ("邮件发送者", "Email sender"),
            ("邮件密码", "Email password"),
            ("短信服务商", "SMS service provider"),
            ("短信API密钥", "SMS API key"),
            ("短信签名", "SMS signature"),
            ("短信模板", "SMS template"),
            
            # File upload
            ("文件上传大小限制", "File upload size limit"),
            ("允许上传的文件类型", "Allowed file types for upload"),
            ("文件存储路径", "File storage path"),
            ("图片压缩质量", "Image compression quality"),
            
            # API configuration
            ("API请求限制", "API request limit"),
            ("API密钥", "API key"),
            ("API密钥有效期", "API key validity period"),
            ("接口调用频率限制", "API call frequency limit"),
            ("接口超时时间", "API timeout period"),
            
            # Database configuration
            ("数据库备份路径", "Database backup path"),
            ("数据库备份周期", "Database backup cycle"),
            ("数据保留天数", "Data retention days"),
            
            # Common terms
            ("启用", "Enable"),
            ("禁用", "Disable"),
            ("开启", "Turn on"),
            ("关闭", "Turn off"),
            ("默认值", "Default value"),
            ("配置项", "Configuration item"),
            ("参数设置", "Parameter setting"),
            ("系统配置", "System configuration"),
            ("基础设置", "Basic settings"),
            ("高级设置", "Advanced settings"),
            
            # Feature flags
            ("功能开关", "Feature toggle"),
            ("实验性功能", "Experimental feature"),
            ("调试模式", "Debug mode"),
            ("开发模式", "Development mode"),
            ("生产模式", "Production mode"),
            
            # Limits and thresholds
            ("最大连接数", "Maximum connections"),
            ("最小连接数", "Minimum connections"),
            ("连接超时", "Connection timeout"),
            ("请求超时", "Request timeout"),
            ("重试次数", "Retry count"),
            ("重试间隔", "Retry interval"),
            
            # Other common terms
            ("备注", "Remark"),
            ("说明", "Description"),
            ("注意事项", "Notes"),
            ("提示", "Hint"),
            ("警告", "Warning"),
            ("错误", "Error"),
            ("成功", "Success"),
            ("失败", "Failure"),
            ("状态", "Status"),
            ("类型", "Type"),
            ("分类", "Category"),
            ("标签", "Tag"),
            ("优先级", "Priority"),
            ("排序", "Sort order"),
            ("序号", "Serial number"),
            ("编号", "Number"),
            ("代码", "Code"),
            ("名称", "Name"),
            ("标题", "Title"),
            ("内容", "Content"),
            ("详情", "Details"),
            ("摘要", "Summary"),
            ("创建时间", "Create time"),
            ("更新时间", "Update time"),
            ("创建人", "Creator"),
            ("更新人", "Updater"),
            ("操作人", "Operator"),
            ("负责人", "Person in charge"),
            ("联系人", "Contact person"),
            ("联系方式", "Contact information"),
        ]
        
        total_updated = 0
        
        # Update each parameter's remark
        for param_id, param_code, param_value, remark in params:
            if remark:
                new_remark = remark
                # Apply translations
                for chinese, english in translations:
                    if chinese in new_remark:
                        new_remark = new_remark.replace(chinese, english)
                
                # If remark was changed, update it
                if new_remark != remark:
                    cursor.execute("""
                    UPDATE sys_params 
                    SET remark = %s 
                    WHERE id = %s
                    """, (new_remark, param_id))
                    
                    if cursor.rowcount > 0:
                        print(f"✓ Updated: {param_code}")
                        print(f"  Old: {remark}")
                        print(f"  New: {new_remark}")
                        total_updated += 1
        
        connection.commit()
        
        if total_updated > 0:
            print(f"\n✅ Successfully updated {total_updated} parameter remarks!")
        else:
            print("\n⚠️ No parameter remarks needed updating.")
        
        # Show final results
        print("\n" + "=" * 60)
        print("Final Parameter Remarks:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT param_code, remark
        FROM sys_params
        WHERE remark IS NOT NULL AND remark != ''
        ORDER BY param_code
        """)
        
        for param_code, remark in cursor.fetchall():
            print(f"{param_code}: {remark}")
            
finally:
    connection.close()