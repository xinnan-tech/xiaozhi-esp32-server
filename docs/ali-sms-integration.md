# Alibaba Cloud SMS統合ガイド

Alibaba Cloudコンソールにログインし、「SMSサービス」ページに移動します：https://dysms.console.aliyun.com/overview

## ステップ1：署名の追加
![ステップ](images/alisms/sms-01.png)
![ステップ](images/alisms/sms-02.png)

上記の手順で署名が取得できます。これをインテリジェントコントロールパネルのパラメータ `aliyun.sms.sign_name` に書き込んでください。

## ステップ2：テンプレートの追加
![ステップ](images/alisms/sms-11.png)

上記の手順でテンプレートコードが取得できます。これをインテリジェントコントロールパネルのパラメータ `aliyun.sms.sms_code_template_code` に書き込んでください。

注意：署名は通信事業者への登録が成功するまで7営業日かかり、その後でないと送信できません。

注意：署名は通信事業者への登録が成功するまで7営業日かかり、その後でないと送信できません。

注意：署名は通信事業者への登録が成功するまで7営業日かかり、その後でないと送信できません。

登録が成功してから、次の操作に進んでください。

## ステップ3：SMSアカウントの作成と権限の付与

Alibaba Cloudコンソールにログインし、「アクセス制御」ページに移動します：https://ram.console.aliyun.com/overview?activeTab=overview

![ステップ](images/alisms/sms-21.png)
![ステップ](images/alisms/sms-22.png)
![ステップ](images/alisms/sms-23.png)
![ステップ](images/alisms/sms-24.png)
![ステップ](images/alisms/sms-25.png)

上記の手順でaccess_key_idとaccess_key_secretが取得できます。これらをインテリジェントコントロールパネルのパラメータ `aliyun.sms.access_key_id`、`aliyun.sms.access_key_secret` に書き込んでください。
## ステップ4：携帯電話登録機能の有効化

1. 通常、上記の情報がすべて入力されると、このようになります。もしそうでなければ、いずれかの手順が抜けている可能性があります。

![ステップ](images/alisms/sms-31.png)

2. 非管理者ユーザーの登録を許可するには、パラメータ `server.allow_user_register` を `true` に設定します。

3. 携帯電話登録機能を有効にするには、パラメータ `server.enable_mobile_register` を `true` に設定します。
![ステップ](images/alisms/sms-32.png)