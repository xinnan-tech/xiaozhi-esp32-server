<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "Privacy Policy"
  }
}
</route>

<script lang="ts" setup>
import { t } from '@/i18n'

function goBack() {
  uni.navigateBack()
}
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f8fd]">
    <wd-navbar
      :title="t('login.privacyPolicy')"
      safe-area-inset-top
      left-arrow
      :bordered="false"
      @click-left="goBack"
    >
      <template #left>
        <wd-icon name="arrow-left" size="18" />
      </template>
    </wd-navbar>
    <scroll-view scroll-y class="box-border flex-1 px-[30rpx] py-[30rpx]">
      <view class="rounded-[16rpx] bg-white px-[30rpx] py-[40rpx] shadow-[0_4rpx_20rpx_rgba(0,0,0,0.05)]">
        <view class="mb-[40rpx] text-center">
          <text class="text-[36rpx] text-[#1a1a1a] font-bold">
            Privacy Policy
          </text>
        </view>
        <view class="mb-[40rpx] text-center">
          <text class="text-[24rpx] text-[#666666]">
            Last Updated: March 10, 2026
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Introduction
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Welcome to use the XiaoZhi Backend Service (hereinafter referred to as "the Service"). The operator of this Service is the actual deployer and administrator of the Service (hereinafter referred to as "Operator" or "we"). We fully understand the importance of your personal information and will do our best to protect your personal information security.
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Please carefully read and fully understand all contents of this Privacy Policy before using the Service. Once you start using the Service, it signifies that you have read and agreed to this Privacy Policy.
          </text>
        </view>
        <view class="mb-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            This Privacy Policy applies to our collection, storage, use, sharing, and protection of your personal information when you use the Service through the Admin Console (management backend), API interfaces, and other means.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            I. Information We Collect
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            To provide services to you, we may need to collect the following information:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.1 Account Registration Information: When you register an account, we collect your phone number or username, password, and other information to create and verify your account.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.2 Device Information: When you bind hardware devices, we collect device identification information (such as device code, MAC address), device model, firmware version, etc., for device management and service provision.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.3 Agent Configuration Information: When you create and configure Agents, we collect role templates, language model selections, voice parameter configurations, etc., to provide personalized AI interaction services.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.4 Voice Interaction Data: When you use the voice interaction function, the Service uses Voice Activity Detection (VAD) to determine the start and end of your voice, processes your voice input data, and transmits it to third-party Automatic Speech Recognition (ASR) and Large Language Model (LLM) services for processing to achieve voice interaction capabilities.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.5 Image Data: When you use the vision model function, we may process image data captured through the device camera and transmit it to third-party vision model services for analysis and understanding to achieve image recognition, scene understanding, and other functions.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.6 Conversation Memory Data: When you enable the memory function, the Service stores summaries of your interaction history with the Agent to provide more coherent and personalized interaction experiences in subsequent conversations.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.7 Knowledge Base Data: When you use the knowledge base function, we collect and store documents, texts, and other knowledge base content you upload for Agents to perform knowledge retrieval and Q&A during conversations.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.8 Voice Print Data: When you use the voice print recognition function, we collect and store your voice print characteristic samples for speaker identity verification and personalized services.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.9 Chat History Data: We store conversation history records between you and the Agents, including text conversation content, conversation time, interaction context, etc., to provide continuous conversation experience and history query functions.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.10 Conversation Audio Data: When you use the voice interaction function, we may store audio data of your interactions with the Agents to improve voice interaction quality and enable retrieval queries.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.11 Agent Configuration Data: When you configure Agents, we collect tags, plugin configurations, context provider settings, etc., to provide Agent customization services.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.12 Device Firmware Data: When you use the OTA upgrade function, we record device firmware version, upgrade history, etc., for device management and firmware traceability.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.13 Log Information: When you use the Service, we automatically collect service log information, including but not limited to access time, IP address, browser type, operation records, etc., for service operation and security assurance.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.14 Verification Code Information: When you use phone number login, we send verification codes via SMS service for identity verification.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            II. How We Use the Collected Information
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            The information we collect will be used for the following purposes:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) Providing, maintaining, and improving the Service, including core functions such as account management, device management, and Agent configuration.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) Processing your voice interaction requests, using Voice Activity Detection (VAD) to identify voice input, calling third-party AI model services to complete speech recognition, intent recognition, semantic understanding, and speech synthesis.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (3) Processing your image data, calling third-party vision model services to complete image recognition and scene understanding.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (4) Storing and managing your conversation memory data to provide more coherent service experiences in subsequent interactions.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (5) Storing and retrieving knowledge base content you upload so that Agents can provide more accurate knowledge Q&A during conversations.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (6) Ensuring service security and stability, including identity verification, security protection, troubleshooting, etc.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (7) Complying with applicable laws, regulations, and regulatory requirements.
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            We will not use your personal information for purposes unrelated to the above. If we need to use information for other purposes not stated in this Privacy Policy, we will obtain your consent in advance.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            III. Sharing and Disclosure of Information
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            We will not sell your personal information to third parties. Only in the following circumstances may we share or disclose your information:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.1 Third-party Service Calls: To achieve voice interaction, visual understanding, and other functions, your voice data, image data, and text content may be transmitted to third-party AI service providers for processing.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.2 Legal Requirements: According to applicable laws, regulations, legal procedures, or requirements from government authorities, we may need to disclose your personal information.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.3 Security Assurance: To protect the Operator, other users, or the public from damage, we may use or disclose personal information within a reasonably necessary scope.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.4 With Consent: We may share your personal information with third parties if we obtain your explicit consent.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            IV. Storage and Protection of Information
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.1 Storage Location: Your personal information will be stored on the server where the Operator deploys the Service, including but not limited to databases (MySQL/PostgreSQL) and cache services (Redis).
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.2 Storage Period: We will retain your personal information for the period necessary to provide you with services. After you cancel your account, we will delete or anonymize your personal information within a reasonable time.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.3 Security Measures: We take reasonable technical and management measures to protect the security of your personal information, including but not limited to data encryption, access control, security auditing, etc.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.4 Security Incident Handling: If a personal information security incident occurs, we will promptly inform you of the basic situation of the security incident, possible impacts, and measures taken or to be taken.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.5 Special Note for Open-source Projects: The Service is an open-source project with two operation modes:
          </text>
        </view>
        <view class="mb-[8rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) Self-deployment: If you self-deploy the Service, the Operator is only the code provider, and actual data storage and processing are your responsibility.
          </text>
        </view>
        <view class="mb-[8rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) Test Platform: If you use the test platform deployed by the Operator, your data will be managed and protected by the Operator.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.6 Cross-border Data Transfer: When providing intelligent interaction functions, the Service may need to call interfaces from third-party AI service providers outside mainland China.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            V. Your Rights
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.1 Query and Access: You can view and manage your personal information such as account information, device information, and Agent configuration through the Admin Console.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.2 Correction and Modification: When you find that your personal information is incorrect, you can correct it through the Admin Console or contact the Operator for assistance.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.3 Deletion: Under certain circumstances, you may request us to delete your personal information.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.4 Account Cancellation: You can cancel your account through the account settings in the Admin Console or contact the Operator for processing.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.5 Withdrawal of Consent: You may withdraw your consent granted to us at any time.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            VI. Protection of Minor Information
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.1 We attach great importance to the protection of minors' personal information. If you are a minor under 18 years of age, please use the Service under the guidance and consent of your guardian.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.2 If a guardian discovers that a minor has provided personal information to us without consent, please contact the Operator. We will delete the relevant information as soon as possible.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.3 For minors who use the Service with guardian consent, we will provide stricter protection for their personal information in accordance with laws and regulations.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            VII. Third-party Services Description
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.1 When providing intelligent interaction functions, the Service needs to call third-party services, including but not limited to: Voice Activity Detection Service (VAD), Automatic Speech Recognition Service (ASR), Large Language Model Service (LLM), Text-to-Speech Service (TTS), Vision Model Service, SMS Verification Code Service, MQTT Message Broker Service, Database Service.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.2 The above third-party service providers will process data according to their respective privacy policies. We recommend that you understand the privacy policies of relevant third-party service providers before using the Service.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            VIII. Use of Cookies and Similar Technologies
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.1 The Service may use Cookies and similar technologies to save your login status, record your preference settings, etc., to provide you with a better user experience.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.2 You can manage Cookies through browser settings. However, please note that disabling Cookies may affect some functions of the Service.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            IX. Changes to the Privacy Policy
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.1 We may revise this Privacy Policy based on business adjustments, changes in laws and regulations, and other reasons. The revised Privacy Policy will be published through the Service's announcement mechanisms.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.2 If you continue to use the Service after the Privacy Policy revision, it shall be deemed that you have accepted the revised Privacy Policy.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            X. Information Security Warning
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.1 Please do not disclose sensitive personal information such as your property account numbers, bank card numbers, credit card numbers, passwords, ID card numbers, etc., in voice or text interactions with AI. Any losses resulting from this shall be borne by you.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.2 Please properly keep your account and password secure, and do not share your account information with others or share accounts with others.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.3 If you discover that personal information may have been leaked, please contact the Operator promptly to take measures.
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            XI. Applicable Law
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.1 The formulation, interpretation, execution, and dispute resolution of this Privacy Policy shall be governed by the laws of the People's Republic of China (excluding the laws of Hong Kong, Macau, and Taiwan for the purposes of this Privacy Policy).
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.2 If any provision of this Privacy Policy conflicts with the current laws and regulations of the People's Republic of China, the provisions of laws and regulations shall prevail, and the remaining provisions shall remain valid.
          </text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>
