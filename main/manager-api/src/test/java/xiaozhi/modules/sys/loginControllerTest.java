package xiaozhi.modules.sys;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.context.annotation.Import;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.config.TestConfig;
import xiaozhi.modules.security.controller.LoginController;
import xiaozhi.modules.security.dto.LoginDTO;
import xiaozhi.modules.security.dto.SmsVerificationDTO;
import xiaozhi.modules.sys.dto.RetrievePasswordDTO;
import xiaozhi.modules.sys.service.SysUserService;

@Slf4j
@SpringBootTest
@ActiveProfiles("test")
@Import(TestConfig.class)
class loginControllerTest {

    @Autowired
    LoginController loginController;

    @MockitoBean
    SysUserService sysUserService;

    @Test
    public void testRegister() {
        when(sysUserService.getAllowUserRegister()).thenReturn(false);

        LoginDTO loginDTO = new LoginDTO();
        loginDTO.setUsername("test-user");
        loginDTO.setPassword("test-password");
        Assertions.assertThrows(Exception.class, () -> loginController.register(loginDTO));
    }

    @Test
    public void testSmsVerification() {
        try {
            SmsVerificationDTO smsVerificationDTO = new SmsVerificationDTO();
            smsVerificationDTO.setPhone("+15551234567");
            smsVerificationDTO.setCaptchaId("123456");
            smsVerificationDTO.setCaptcha("123456");
            loginController.smsVerification(smsVerificationDTO);
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }
    }

    @Test
    public void testRetrievePassword() {
        try {
            RetrievePasswordDTO retrievePasswordDTO = new RetrievePasswordDTO();
            retrievePasswordDTO.setCode("123456");
            retrievePasswordDTO.setPhone("+15551234567");
            retrievePasswordDTO.setPassword("test-password");
            loginController.retrievePassword(retrievePasswordDTO);
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }

    }

}
