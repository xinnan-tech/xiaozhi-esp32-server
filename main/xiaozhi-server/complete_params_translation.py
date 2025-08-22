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
        print("Complete Parameter Remark Translation:")
        print("=" * 60)
        
        # Direct mapping for each parameter's remark
        remark_translations = {
            "aliyun.sms.access_key_id": "Aliyun platform access key",
            "aliyun.sms.access_key_secret": "Aliyun platform access key secret",
            "aliyun.sms.sign_name": "Aliyun SMS signature",
            "aliyun.sms.sms_code_template_code": "Aliyun SMS template code",
            "close_connection_no_voice_time": "Disconnect time without voice input (seconds)",
            "delete_audio": "Delete audio files after use",
            "device_max_output_size": "Maximum output characters per device per day, 0 means unlimited",
            "enable_greeting": "Enable greeting reply",
            "enable_stop_tts_notify": "Enable end notification sound",
            "enable_wakeup_words_response_cache": "Enable wake word acceleration cache",
            "end_prompt.enable": "Enable ending prompt",
            "end_prompt.prompt": "Ending prompt text",
            "exit_commands": "Exit command list",
            "log.data_dir": "Data directory",
            "log.log_dir": "Log directory",
            "log.log_file": "Log file name",
            "log.log_format": "Console log format",
            "log.log_format_file": "File log format",
            "log.log_level": "Log level",
            "server.allow_user_register": "Allow non-admin user registration",
            "server.beian_ga_num": "Public security registration number, set null to disable",
            "server.beian_icp_num": "ICP registration number, set null to disable",
            "server.enable_mobile_register": "Enable mobile phone registration",
            "server.fronted_url": "Dashboard URL displayed when sending 6-digit verification code",
            "server.mcp_endpoint": "MCP endpoint address",
            "server.name": "System name",
            "server.ota": "OTA address",
            "server.secret": "Server secret key",
            "server.sms_max_send_count": "Maximum SMS sends per phone number per day",
            "server.voice_print": "Voice print interface address",
            "server.websocket": "WebSocket address, separate multiple with semicolon",
            "stop_tts_notify_voice": "End notification sound file path",
            "tts_timeout": "TTS request timeout (seconds)",
            "wakeup_words": "Wake word list for recognition",
            "xiaozhi": "Xiaozhi type configuration"
        }
        
        total_updated = 0
        
        # Update each parameter's remark
        for param_code, english_remark in remark_translations.items():
            cursor.execute("""
            UPDATE sys_params 
            SET remark = %s 
            WHERE param_code = %s
            """, (english_remark, param_code))
            
            if cursor.rowcount > 0:
                print(f"✓ Updated: {param_code}")
                print(f"  New remark: {english_remark}")
                total_updated += 1
        
        connection.commit()
        
        print(f"\n✅ Successfully updated {total_updated} parameter remarks!")
        
        # Show final results
        print("\n" + "=" * 60)
        print("All Parameter Remarks (Final):")
        print("=" * 60)
        
        cursor.execute("""
        SELECT param_code, remark
        FROM sys_params
        ORDER BY param_code
        """)
        
        for param_code, remark in cursor.fetchall():
            print(f"{param_code:<40} : {remark or 'No remark'}")
            
finally:
    connection.close()