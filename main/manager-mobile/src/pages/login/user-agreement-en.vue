<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "User Agreement"
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
      :title="t('login.userAgreement')"
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
            User Agreement
          </text>
        </view>
        <view class="mb-[40rpx] text-center">
          <text class="text-[24rpx] text-[#666666]">
            Last Updated: March 10, 2026
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            Important Notice
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Welcome to use the XiaoZhi Backend Service (hereinafter referred to as "the Service"). The Service is designed to provide backend service support for XiaoZhi AI hardware devices, including but not limited to intelligent voice interaction, visual understanding, intent recognition, conversation memory, knowledge base Q&A, device management, and agent management. The operator of this Service is the actual deployer and administrator of the Service (hereinafter referred to as "Operator" or "we").
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Before registering, logging in, or using the Service, please carefully read and fully understand all terms of this Agreement, especially the terms that are highlighted in bold and may have significant impact on your interests, including but not limited to disclaimers and liability limitations.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            When you complete registration, login, or otherwise use the Service following the on-screen instructions, it signifies that you have fully read, understood, and accepted all contents of this Agreement. If you disagree with this Agreement or any of its terms, please stop using the Service immediately.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            This Agreement may be updated and revised based on actual circumstances. The revised Agreement will be published through the Service's announcement mechanisms. The revised Agreement shall take effect from the date of publication. If you continue to use the Service after the Agreement revision, it shall be deemed that you have accepted the revised Agreement.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            I. Definitions
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            XiaoZhi Backend Service: refers to the XiaoZhi Backend Service and its backend service system, including but not limited to the Admin Console (management backend), API interfaces, WebSocket communication services, etc.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Admin Console: refers to the web management interface provided by the Service for device management, agent configuration, user management, and other functions.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            User: refers to natural persons, legal persons, or other organizations who register or otherwise use the Service, hereinafter referred to as "you".
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Intelligent Agent (Agent): refers to an AI character created and configured within the Service, containing a collection of capabilities such as language models, speech recognition, speech synthesis, visual understanding, intent recognition, conversation memory, and knowledge base.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            Device: refers to ESP32 and other hardware devices connected and managed through the Service.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            II. Scope of Agreement
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            This Agreement is a legal agreement between you and the Operator regarding your use of the Service. This Agreement applies to all your actions when using the Service through the Admin Console or other means.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            The source code of the Service follows the corresponding open-source license. This Agreement governs your use of the Service and does not affect the rights granted to you by the open-source license itself.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            III. Account Registration and Use
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.1 User Eligibility: You confirm that before using the Service, you should have the capacity for civil conduct as required by the laws of the People's Republic of China. If you are a minor, you should use the Service under the company and guidance of your legal guardian.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.2 Account Registration: You may register and log in to the Service through mobile phone verification code, username/password, or other methods. You shall provide true, accurate, and complete registration information and update it promptly.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.3 Account Security: You shall properly keep your account and password safe. All consequences arising from account leakage or unauthorized use by others due to your reasons shall be borne by you. If you discover any security risks with your account, please contact the Operator immediately.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.4 Account Usage Restrictions: Your account is for your personal use only. Without the Operator's consent, you shall not transfer, rent, or lend your account to any third party in any way.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.5 Account Cancellation: If you need to cancel your account, you may do so through the account settings in the Admin Console or contact the Operator for processing. After account cancellation, related data will be deleted and cannot be recovered. Please proceed with caution.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            IV. Service Content
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.1 Service Overview: Relying on artificial intelligence technology, the Service provides intelligent interaction services for connected hardware devices through API calls to third-party generative AI models, including but not limited to Voice Activity Detection (VAD), Automatic Speech Recognition (ASR), Large Language Model (LLM), Text-to-Speech (TTS), Vision Large Language Model (VLLM), Intent Recognition, Conversation Memory, and Retrieval-Augmented Generation (RAG).
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.2 Agent Management: You can create and configure Agents through the Admin Console, including setting role templates, selecting language models, configuring voice parameters, setting intent recognition rules, managing knowledge bases, enabling conversation memory, configuring Agent plugins, etc. The Agent settings shall not violate national laws and regulations.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.3 Device Management: You can bind and manage your hardware devices through the Admin Console, perform device configuration, firmware updates, OTA remote upgrades, etc. You shall ensure that the devices you manage are lawfully owned or authorized by you.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.4 Visual Understanding: The Service supports image capture through device cameras and uses third-party vision models for image recognition and scene understanding. You shall ensure that image capture complies with relevant laws and regulations and does not infringe upon others' privacy.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.5 Intent Recognition: The Service can understand the intent of user commands through intent recognition and trigger corresponding operations or services, such as controlling smart devices, querying information, etc.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.6 Conversation Memory: The Service can record and store summaries of your interaction history with the Agent to provide more coherent and personalized interaction experiences in subsequent conversations. You can manage or clear memory data in the Admin Console.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.7 Knowledge Base: The Service supports uploading documents, texts, and other content to build knowledge bases. Agents can retrieve knowledge base content during conversations to provide Q&A services. You shall ensure that uploaded knowledge base content does not infringe upon third-party intellectual property rights and does not contain content that violates laws and regulations.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.8 Voice Print Recognition: The Service supports voice print recognition. You can register voice print samples to achieve speaker identity verification and personalized services. Voice print data will be used for identity verification purposes.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.9 Voice Cloning: The Service supports voice cloning. You can clone custom voice timbres by providing audio samples. Cloned voices are for your personal use only and shall not be used to impersonate others or engage in illegal activities.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.10 MCP Endpoints: the Service supports MCP (Model Context Protocol) and can serve as an MCP Server to provide tool calling capabilities to external systems, or as an MCP Client to call external MCP services, achieving standardized integration with external systems.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.11 Context Providers: The Service supports Context Provider functionality, which can obtain real-time information from external data sources, such as weather, news, stocks, etc., providing Agents with richer knowledge sources.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.12 MQTT Protocol: The Service supports MQTT (Message Queuing Telemetry Transport) protocol for message communication between IoT devices. You can use the MQTT protocol to send device control commands, monitor device status, etc.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.13 Service Disclaimer: The conversations and responses generated by third-party AI models that the Service depends on are for reference only and do not constitute professional advice in any field. You shall not use the output content as professional advice in medical, legal, financial, or other professional fields. Any judgments or decisions you make based on the output content shall be entirely at your own responsibility.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.14 Service Fees: The Service is a free open-source project and does not charge any usage fees from users. It only provides platform capabilities for calling third-party services and does not involve any paid functions or value-added services.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            The Service supports multiple AI service providers with different billing models as follows:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) Free Services: Some service providers offer free quotas or completely free services, such as Zhipu AI (free models like glm-4-flash), Microsoft EdgeTTS voice synthesis, etc.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) Pay-as-you-go: Some service providers charge based on API usage, such as OpenAI, Alibaba Cloud Intelligent Speech, Baidu Wenxin, iFlytek, etc. You need to pay the corresponding fees to third-party service providers yourself. Such fees are unrelated to this Service.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (3) Local Deployment: The Service supports fully local AI deployment solutions, such as FunASR speech recognition, FishSpeech voice synthesis, Ollama local large models, etc. Local deployment does not require network fees or API usage fees but requires sufficient local computing resources.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.15 Service Changes: The Operator reserves the right to adjust, upgrade, or terminate the Service content as actual circumstances require, and will provide notice as far in advance as possible.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            V. User Conduct Standards
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.1 Legal Use: When using the Service, you shall comply with the laws and regulations of the People's Republic of China and relevant international treaties, and shall not use the Service for any illegal activities.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.2 Prohibited Conduct: You promise not to engage in the following behaviors when using the Service:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) Publishing, transmitting, or storing content that endangers national security or social stability, including but not limited to content involving subverting state power, damaging national honor and interests, or inciting ethnic hatred.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) Publishing, transmitting, or storing content that infringes upon the legitimate rights and interests of others, including but not limited to infringing upon intellectual property rights, privacy rights, reputation rights, etc.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (3) Publishing, transmitting, or storing obscene, pornographic, violent, terrorist, or crime-inciting content.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (4) Publishing false information, spreading rumors, or engaging in fraudulent activities.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (5) Interfering with the normal operation of the Service in any way, including but not limited to attacking servers, spreading malicious programs, or malicious consuming system resources.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (6) Unauthorized reverse engineering, decompiling, or attempting to obtain system source code of the Service (this clause does not limit your lawful use of open-source code according to the open-source license).
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (7) Using the Service for automated batch operations, malicious consuming API call quotas or other system resources.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (8) Entering content that violates laws, regulations, or public order and good customs in Agent settings.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (9) Using the Service to harm or attempt to harm minors.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (10) Other behaviors that violate laws, regulations, this Agreement, or may harm the legitimate rights and interests of the Operator or third parties.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.3 Handling of Violations: If you violate the above conduct standards, the Operator has the right to take measures such as warnings, feature restrictions, service suspension, or account banning based on the severity of the situation, and reserves the right to pursue legal liability.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            VI. Intellectual Property
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.1 Open-source License: The Service is an open-source project, and its source code follows the corresponding open-source license. You may use the relevant source code in compliance with the license terms.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.2 Service Content Ownership: Except for open-source code, the intellectual property rights of interface designs, icons, copy, and other independently created content in the Service belong to the Operator.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.3 User Content: The intellectual property rights of content you input, upload, or generate through the Service shall be determined according to relevant laws and regulations. You grant the Operator the right to store and process your input content for the purpose of maintaining and improving the Service.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.4 Third-party Rights: When using the Service, you should respect the intellectual property rights and other legitimate rights of third parties. You shall bear all responsibilities for any disputes arising from your infringement of third-party rights.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            VII. Privacy Protection
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.1 Information Collection: To provide the Service, the Operator may collect your registration information (such as phone number, username), device information, usage logs, etc. For specific personal information collection and usage rules, please refer to the Privacy Policy.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.2 Information Protection: The Operator will take reasonable technical and management measures to protect the security of your personal information. However, due to the openness of the Internet, the Operator cannot absolutely guarantee information security. Please pay attention to protecting your personal sensitive information.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.3 Information Security Warning: Please do not disclose your sensitive personal information such as property accounts, bank card numbers, passwords, etc. to AI during your use of the Service. Any losses resulting from this shall be borne by you.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            VIII. Disclaimer
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.1 AI-Generated Content: The Service relies on third-party AI models to provide intelligent interaction capabilities. The content generated by AI may be inaccurate, incomplete, or inappropriate. The Operator does not make any guarantees regarding the authenticity, accuracy, or completeness of AI-generated content.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.2 Service Interruption: The Operator shall not be responsible for service interruptions or abnormalities caused by the following reasons:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) Force majeure factors, such as natural disasters, pandemics, wars, etc.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) Public service factors such as power supply failures or communication network failures.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (3) Service failures or policy adjustments of third-party AI model service providers.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (4) Temporary service interruptions caused by system maintenance or upgrades.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (5) Network security incidents such as hacker attacks or computer viruses.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (6) Service adjustments due to laws, regulations, or government controls.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (7) Other situations not caused by the Operator's fault.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.3 Third-party Services: The Service may involve third-party provided language models, speech recognition, speech synthesis, vision models, intent recognition, and other services. You should also comply with the terms of service of third parties when using them. For issues arising from third-party services, please contact the third party directly.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.4 Open-source Statement: The Service is an open-source project provided "as is". To the maximum extent permitted by law, the Operator does not make any express or implied guarantees regarding the merchantability, fitness for a particular purpose, or non-infringement of the Service.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.5 Special Open-source Software Statement: This project is open-source software. This Service has no commercial cooperation relationship with any third-party API service providers it connects to (including but not limited to platforms such as speech recognition, large language models, speech synthesis, etc.) and does not provide any form of guarantee for their service quality and capital security. This software does not host any account keys, does not participate in capital flow, and does not bear the risk of recharge capital losses.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.6 Security Warning: This project functions are not fully developed and have not passed network security assessment. Please do not use it in production environments. If you deploy this project for learning in a public network environment, you must take necessary protective measures, including but not limited to setting strong passwords, restricting access permissions, enabling HTTPS encrypted transmission, etc.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            IX. Protection of Minors
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.1 If you are a minor under 18 years of age, you should use the Service under the guidance and consent of your guardian.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.2 Guardians should strengthen supervision of minors using the Service, guide minors to use it reasonably, and avoid excessive reliance.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.3 Minors should pay attention to personal information protection when using the Service and avoid uploading or disclosing personal sensitive information.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            X. Agreement Termination
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.1 User Termination: You have the right to stop using the Service and cancel your account at any time.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.2 Operator Termination: The Operator has the right to terminate providing services to you under the following circumstances:
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (1) You violate the terms of this Agreement.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (2) You use the Service for illegal activities.
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (3) As required by laws, regulations, or policies.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            (4) The Operator decides to stop operating the Service.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.3 Post-termination Handling: After the Agreement is terminated, the Operator is not obligated to retain your account information and related data. The Operator still has the right to pursue your breach of contract liability during the validity period of the Agreement.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            XI. Governing Law and Dispute Resolution
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.1 The formation, effectiveness, interpretation, revision, termination, and dispute resolution of this Agreement are governed by the laws of the People's Republic of China.
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.2 Any disputes arising from this Agreement or the Service shall be resolved through friendly negotiation between both parties; if negotiation fails, either party has the right to bring a lawsuit to the people's court with jurisdiction at the Operator's location.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.3 If any provision of this Agreement is determined to be invalid or unenforceable, it does not affect the validity of the remaining provisions.
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            XII. Miscellaneous
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            12.1 This Agreement constitutes the complete agreement between you and the Operator regarding your use of the Service.
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            12.2 The Operator's failure to exercise or delay in exercising any rights under this Agreement does not constitute a waiver of such rights.
          </text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>
