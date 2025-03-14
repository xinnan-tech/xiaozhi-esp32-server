package xiaozhi.modules.security.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.AssertUtils;
import xiaozhi.modules.security.dto.LoginDTO;
import xiaozhi.modules.security.password.PasswordUtils;
import xiaozhi.modules.security.service.CaptchaService;
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.service.SysUserService;

import java.io.IOException;

/**
 * 登录控制层
 */
@Tag(name = "登录管理")
@AllArgsConstructor
@RestController
@RequestMapping("/user")
@Tag(name = "登录管理")
public class LoginController {
    private final SysUserService sysUserService;
    private final SysUserTokenService sysUserTokenService;
    private final CaptchaService captchaService;


    @GetMapping("/captcha")
    @Operation(summary = "验证码")
    public void captcha(HttpServletResponse response, String uuid) throws IOException {
        //uuid不能为空
        AssertUtils.isBlank(uuid, ErrorCode.IDENTIFIER_NOT_NULL);

        //生成验证码
        captchaService.create(response, uuid);
    }

    @PostMapping("/login")
    @Operation(summary = "登录")
    public Result login( @RequestBody LoginDTO login) {
        // 验证是否正确输入验证码
        boolean validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha());
        if (!validate) {
            throw new RenException("验证码错误，请重新获取");
        }
        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        // 判断用户是否存在
        if (userDTO == null) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        // 判断密码是否正确，不一样则进入if
        if (!PasswordUtils.matches(login.getPassword(), userDTO.getPassword())) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        return sysUserTokenService.createToken(userDTO.getId());
    }

    @PostMapping("/register")
    @Operation(summary = "注册")
    public Result<Void> register(@RequestBody LoginDTO login) {
        // 验证是否正确输入验证码
        boolean validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha());
        if (!validate) {
            throw new RenException("验证码错误，请重新获取");
        }
        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        if (userDTO != null){
            throw new RenException("此手机号码已经注册过");
        }
        userDTO = new SysUserDTO();
        userDTO.setUsername(login.getUsername());
        userDTO.setPassword(login.getPassword());
        sysUserService.save(userDTO);
        return new Result<Void>();

    }

}