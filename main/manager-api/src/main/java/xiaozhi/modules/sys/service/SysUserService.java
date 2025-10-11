package xiaozhi.modules.sys.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.AdminPageUserDTO;
import xiaozhi.modules.sys.dto.PasswordDTO;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.vo.AdminPageUserVO;

/**
 * システムユーザー
 */
public interface SysUserService extends BaseService<SysUserEntity> {

    SysUserDTO getByUsername(String username);

    SysUserDTO getByUserId(Long userId);

    void save(SysUserDTO dto);

    /**
     * 指定ユーザーを削除し、関連するデータデバイスとエージェントも削除
     * 
     * @param ids
     */
    void deleteById(Long ids);

    /**
     * パスワード変更が許可されているかを検証
     * 
     * @param userId      ユーザーID
     * @param passwordDTO パスワード検証パラメータ
     */
    void changePassword(Long userId, PasswordDTO passwordDTO);

    /**
     * パスワードを直接変更、検証不要
     * 
     * @param userId   ユーザーID
     * @param password パスワード
     */
    void changePasswordDirectly(Long userId, String password);

    /**
     * パスワードをリセット
     * 
     * @param userId ユーザーID
     * @return ランダムに生成された規範に準拠したパスワード
     */
    String resetPassword(Long userId);

    /**
     * 管理者ページングユーザー情報
     * 
     * @param dto ページング検索パラメータ
     * @return ユーザーリストページングデータ
     */
    PageData<AdminPageUserVO> page(AdminPageUserDTO dto);

    /**
     * ユーザーステータスを一括変更
     * 
     * @param status  ユーザーステータス
     * @param userIds ユーザーID配列
     */
    void changeStatus(Integer status, String[] userIds);

    /**
     * ユーザー登録が許可されているかを取得
     * 
     * @return ユーザー登録が許可されているか
     */
    boolean getAllowUserRegister();
}
