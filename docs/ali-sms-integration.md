# 阿里云短信集成指南

登录阿里云控制台，进入“短信服务”页面：https://dysms.console.aliyun.com/overview

## 第一步 添加签名
![步骤](images/alisms/sms-01.png)
![步骤](images/alisms/sms-02.png)

以上步骤，会得到签名，请把它写入到智控台参数，`aliyun.sms.sign_name`

## 第二步 添加模版
![步骤](images/alisms/sms-11.png)

以上步骤，会得到模版code，请把它写入到智控台参数，`aliyun.sms.sms_code_template_code`

注意，签名要等7个工作日，等运营商报备成功后才能发送成功。

注意，签名要等7个工作日，等运营商报备成功后才能发送成功。

注意，签名要等7个工作日，等运营商报备成功后才能发送成功。

可以等报备成功后，再继续往下操作。

## 第三步 创建短信账户和开通权限

登录阿里云控制台，进入“访问控制”页面：https://ram.console.aliyun.com/overview?activeTab=overview

![步骤](images/alisms/sms-21.png)
![步骤](images/alisms/sms-22.png)
![步骤](images/alisms/sms-23.png)
![步骤](images/alisms/sms-24.png)
![步骤](images/alisms/sms-25.png)

以上步骤，会得到access_key_id和access_key_secret，请把它写入到智控台参数，`aliyun.sms.access_key_id`、`aliyun.sms.access_key_secret`
## 第四步 启动手机注册功能

1、正常来说，以上信息都填完后，会有这个效果，如果没有，可能缺少了某个步骤

![步骤](images/alisms/sms-31.png)

2、开启允许非管理员用户可注册，将参数`server.allow_user_register`设置成`true`

3、开启手机注册功能，将参数`server.enable_mobile_register`设置成`true`
![步骤](images/alisms/sms-32.png)