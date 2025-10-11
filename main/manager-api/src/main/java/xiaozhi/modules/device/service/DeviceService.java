package xiaozhi.modules.device.service;

import java.util.Date;
import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.dto.DevicePageUserDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;

public interface DeviceService extends BaseService<DeviceEntity> {

    /**
     * デバイスがアクティブかどうかをチェック
     */
    DeviceReportRespDTO checkDeviceActive(String macAddress, String clientId,
            DeviceReportReqDTO deviceReport);

    /**
     * ユーザー指定エージェントのデバイスリストを取得
     */
    List<DeviceEntity> getUserDevices(Long userId, String agentId);

    /**
     * デバイスのバインド解除
     */
    void unbindDevice(Long userId, String deviceId);

    /**
     * デバイスアクティベーション
     */
    Boolean deviceActivation(String agentId, String activationCode);

    /**
     * このユーザーのすべてのデバイスを削除
     * 
     * @param userId ユーザーID
     */
    void deleteByUserId(Long userId);

    /**
     * 指定エージェントに関連するすべてのデバイスを削除
     * 
     * @param agentId エージェントID
     */
    void deleteByAgentId(String agentId);

    /**
     * 指定ユーザーのデバイス数を取得
     * 
     * @param userId ユーザーID
     * @return デバイス数
     */
    Long selectCountByUserId(Long userId);

    /**
     * すべてのデバイス情報をページング取得
     *
     * @param dto ページング検索パラメータ
     * @return ユーザーリストページングデータ
     */
    PageData<UserShowDeviceListVO> page(DevicePageUserDTO dto);

    /**
     * MACアドレスによりデバイス情報を取得
     * 
     * @param macAddress MACアドレス
     * @return デバイス情報
     */
    DeviceEntity getDeviceByMacAddress(String macAddress);

    /**
     * デバイスIDによりアクティベーションコードを取得
     * 
     * @param deviceId デバイスID
     * @return アクティベーションコード
     */
    String geCodeByDeviceId(String deviceId);

    /**
     * このエージェントデバイスの最新の最終接続時間を取得
     * @param agentId エージェントID
     * @return デバイスの最新の最終接続時間を返す
     */
    Date getLatestLastConnectionTime(String agentId);

    /**
     * 手動でデバイスを追加
     */
    void manualAddDevice(Long userId, DeviceManualAddDTO dto);

    /**
     * デバイス接続情報を更新
     */
    void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion);

}