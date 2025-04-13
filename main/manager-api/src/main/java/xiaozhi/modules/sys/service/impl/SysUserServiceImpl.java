package xiaozhi.modules.sys.service.impl;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.password.PasswordUtils;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.AdminPageUserDTO;
import xiaozhi.modules.sys.dto.PasswordDTO;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.enums.SuperAdminEnum;
import xiaozhi.modules.sys.service.SysUserService;
import xiaozhi.modules.sys.vo.AdminPageUserVO;

/**
 * 系统用户
 */
@AllArgsConstructor
@Service
public class SysUserServiceImpl extends BaseServiceImpl<SysUserDao, SysUserEntity> implements SysUserService {
    private final SysUserDao sysUserDao;

    private final DeviceService deviceService;

    private final AgentService agentService;

    @Override
    public SysUserDTO getByUsername(String username) {
        QueryWrapper<SysUserEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", username);
        List<SysUserEntity> users = sysUserDao.selectList(queryWrapper);
        if (users == null || users.isEmpty()) {
            return null;
        }
        SysUserEntity entity = users.getFirst();
        return ConvertUtils.sourceToTarget(entity, SysUserDTO.class);
    }

    @Override
    public SysUserDTO getByUserId(Long userId) {
        SysUserEntity sysUserEntity = sysUserDao.selectById(userId);

        return ConvertUtils.sourceToTarget(sysUserEntity, SysUserDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(SysUserDTO dto) {
        SysUserEntity entity = ConvertUtils.sourceToTarget(dto, SysUserEntity.class);

        // 密码强度
        if (!isStrongPassword(entity.getPassword())) {
            throw new RenException(ErrorCode.PASSWORD_WEAK_ERROR);
        }

        // 密码加密
        String password = PasswordUtils.encode(entity.getPassword());
        entity.setPassword(password);

        // 保存用户
        Long userCount = getUserCount();
        if (userCount == 0) {
            entity.setSuperAdmin(SuperAdminEnum.YES.value());
        } else {
            entity.setSuperAdmin(SuperAdminEnum.NO.value());
        }
        entity.setStatus(1);

        insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteById(Long id) {
        // 删除用户
        baseDao.deleteById(id);
        // 删除设备
        deviceService.deleteByUserId(id);
        // 删除智能体
        agentService.deleteAgentByUserId(id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void changePassword(Long userId, PasswordDTO passwordDTO) {
        SysUserEntity sysUserEntity = sysUserDao.selectById(userId);

        if (null == sysUserEntity) {
            throw new RenException(ErrorCode.TOKEN_INVALID);
        }

        // 判断旧密码是否正确
        if (!PasswordUtils.matches(passwordDTO.getPassword(), sysUserEntity.getPassword())) {
            throw new RenException("旧密码输入错误");
        }

        // 新密码强度
        if (!isStrongPassword(passwordDTO.getNewPassword())) {
            throw new RenException(ErrorCode.PASSWORD_WEAK_ERROR);
        }

        // 密码加密
        String password = PasswordUtils.encode(passwordDTO.getNewPassword());
        sysUserEntity.setPassword(password);

        updateById(sysUserEntity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void changePasswordDirectly(Long userId, String password) {
        SysUserEntity sysUserEntity = new SysUserEntity();
        sysUserEntity.setId(userId);
        sysUserEntity.setPassword(PasswordUtils.encode(password));
        updateById(sysUserEntity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public String resetPassword(Long userId) {
        String password = generatePassword();
        changePasswordDirectly(userId, password);
        return password;
    }

    private Long getUserCount() {
        QueryWrapper<SysUserEntity> queryWrapper = new QueryWrapper<>();
        return baseDao.selectCount(queryWrapper);
    }

    @Override
    public PageData<AdminPageUserVO> page(AdminPageUserDTO dto) {
        Map<String, Object> params = new HashMap<String, Object>();
        params.put(Constant.PAGE, dto.getPage());
        params.put(Constant.LIMIT, dto.getLimit());
        IPage<SysUserEntity> page = baseDao.selectPage(
                getPage(params, "id", true),
                new QueryWrapper<SysUserEntity>().eq(StringUtils.isNotBlank(dto.getMobile()), "username",
                        dto.getMobile()));
        // 循环处理page获取回来的数据，返回需要的字段
        List<AdminPageUserVO> list = page.getRecords().stream().map(user -> {
            AdminPageUserVO adminPageUserVO = new AdminPageUserVO();
            adminPageUserVO.setUserid(user.getId().toString());
            adminPageUserVO.setMobile(user.getUsername());
            String deviceCount = deviceService.selectCountByUserId(user.getId()).toString();
            adminPageUserVO.setDeviceCount(deviceCount);
            adminPageUserVO.setStatus(user.getStatus());
            return adminPageUserVO;
        }).toList();
        return new PageData<>(list, page.getTotal());
    }

    private boolean isStrongPassword(String password) {
        // 弱密码的正则表达式
        String weakPasswordRegex = "^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z]).+$";
        Pattern pattern = Pattern.compile(weakPasswordRegex);
        Matcher matcher = pattern.matcher(password);
        return matcher.matches();
    }

    private static final String CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()";
    private static final Random random = new Random();

    /**
     * 生成随机密码
     * 
     * @return 随机生成的密码
     */
    private String generatePassword() {
        StringBuilder password = new StringBuilder();
        for (int i = 0; i < 12; i++) {
            password.append(CHARACTERS.charAt(random.nextInt(CHARACTERS.length())));
        }
        return password.toString();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void changeStatus(Integer status, String[] userIds) {
        for (String userId : userIds) {
            SysUserEntity entity = new SysUserEntity();
            entity.setId(Long.parseLong(userId));
            entity.setStatus(status);
            updateById(entity);
        }
    }
}
