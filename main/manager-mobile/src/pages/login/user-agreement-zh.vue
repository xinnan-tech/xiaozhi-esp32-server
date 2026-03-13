<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "用户协议"
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
            {{ t('login.userAgreement') }}
          </text>
        </view>
        <view class="mb-[40rpx] text-center">
          <text class="text-[24rpx] text-[#666666]">
            更新日期：2026年3月10日
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            提示条款
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            欢迎您使用小智后端服务（以下简称"本服务"）。本服务旨在为小智AI硬件设备提供后端服务支持，包括但不限于智能语音交互、视觉理解、意图识别、对话记忆、知识库问答、设备管理、智能体管理等功能。本服务的运营方为本服务的实际部署者和管理者（以下简称"运营者"或"我们"）。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            在您注册、登录或使用本服务之前，请您务必审慎阅读、充分理解本协议各条款内容，特别是以加粗形式提示您注意的可能与您利益有重大关系的条款，包括但不限于免责声明、责任限制等条款。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            当您按照页面提示完成注册、登录或以其他方式使用本服务时，即表示您已充分阅读、理解并接受本协议的全部内容。如果您不同意本协议或其中任何条款，请立即停止使用本服务。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            本协议可能根据实际情况进行更新和修订，修订后的协议将通过本平台公告等方式予以公示。修订后的协议自公示之日起生效，如您在协议修订后继续使用本服务，则视为您已接受修订后的协议。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            一、定义
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            小智后端服务：指小智后端服务及其部署运行的后端服务系统，包括但不限于智控台（管理后台）、API接口、WebSocket通信服务等。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            智控台：指本服务提供的Web管理界面，用于设备管理、智能体配置、用户管理等功能。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            用户：指通过注册或其他方式使用本服务的自然人、法人或其他组织，以下简称"您"。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            智能体：指在本服务中创建和配置的AI角色，包含语言模型、语音识别、语音合成、视觉理解、意图识别、对话记忆、知识库等能力的集合。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            设备：指通过本服务进行连接和管理的ESP32等硬件设备。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            二、协议范围
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            本协议是您与运营者之间关于使用本服务的法律协议。本协议适用于您通过智控台或其他方式使用本服务的全部行为。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            本服务的源代码遵循相应的开源许可证。本协议约束您对本服务的使用行为，不影响开源许可证本身赋予您的权利。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            三、账号注册与使用
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.1 用户资格：您确认，在使用本服务前，您应当具备中华人民共和国法律规定的与您行为相适应的民事行为能力。若您为未成年人，应在法定监护人的陪同和指导下使用本服务。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.2 账号注册：您可通过手机号验证码或用户名密码等方式注册和登录本服务。您应当提供真实、准确、完整的注册信息，并及时更新。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.3 账号安全：您应妥善保管您的账号和密码，因您的原因导致账号泄露或被他人冒用所产生的一切后果，由您自行承担。如发现账号存在安全隐患，请立即联系运营者。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.4 账号使用限制：您的账号仅限您本人使用，未经运营者同意，不得以任何方式将账号转让、出租或借给第三方使用。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.5 账号注销：如您需要注销账号，可通过智控台的账号设置功能进行操作，或联系运营者进行处理。账号注销后，相关数据将被删除且无法恢复，请谨慎操作。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            四、服务内容
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.1 服务概述：本服务依托人工智能技术，通过API接口调用第三方生成式人工智能模型，为连接的硬件设备提供智能交互服务，包括但不限于语音活动检测（VAD）、语音识别（ASR）、语义理解（LLM）、语音合成（TTS）、视觉理解（VLLM）、意图识别（Intent）、对话记忆（Memory）、知识库（RAG）等。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.2 智能体管理：您可通过智控台创建和配置智能体，包括设定角色模板、选择语言模型、配置语音参数、设置意图识别规则、管理知识库、开启对话记忆、配置智能体插件等。智能体的设定内容不得违反国家法律法规。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.3 设备管理：您可通过智控台绑定和管理您的硬件设备，进行设备配置、固件更新、OTA远程升级等操作。您应确保所管理的设备为您合法拥有或已获得授权。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.4 视觉理解：本服务支持通过设备摄像头采集图像，调用第三方视觉模型进行图像识别和场景理解。您应确保采集图像的行为符合相关法律法规，不得侵犯他人隐私。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.5 意图识别：本服务可通过意图识别功能理解用户指令的意图，并据此触发相应的操作或服务，如控制智能设备、查询信息等。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.6 对话记忆：本服务可记录和存储您与智能体的交互历史摘要，以便在后续对话中提供更连贯、个性化的交互体验。您可在智控台管理或清除记忆数据。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.7 知识库：本服务支持您上传文档、文本等内容构建知识库，智能体可在对话中检索知识库内容为您提供问答服务。您应确保上传的知识库内容不侵犯第三方知识产权，且不包含违反法律法规的内容。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.8 声纹识别：本服务支持声纹识别功能，您可注册声纹样本以实现说话人身份验证和个性化服务。声纹数据将用于身份验证目的。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.9 语音克隆：本服务支持语音克隆功能，您可通过提供音频样本克隆自定义音色。克隆音色仅供您本人使用，不得用于仿冒他人或从事违法违规活动。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.10 MCP接入点：本服务支持MCP（Model Context Protocol）协议，可作为MCP Server向外部提供工具调用能力，也可作为MCP Client调用外部MCP服务，实现与外部系统的标准化集成。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.11 上下文提供者：本服务支持上下文提供者（Context Provider）功能，可从外部数据源获取实时信息，如天气、新闻、股票等，为智能体提供更丰富的知识来源。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.12 MQTT协议：本服务支持MQTT（Message Queuing Telemetry Transport）协议，用于与物联网设备之间的消息通信。您可通过MQTT协议实现设备控制指令下发、设备状态监控等功能。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.13 服务说明：本服务所依赖的第三方AI模型生成的对话、答复内容仅供参考，不构成任何专业建议。您不得将输出内容作为医疗、法律、金融等领域的专业建议。您根据输出内容所作的任何判断或决策，由您自行承担全部责任。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.14 服务费用：本服务为免费开源项目，不向用户收取任何使用费用，仅提供调用第三方服务的平台能力，不涉及任何付费功能或增值服务。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            本服务支持多种AI服务提供商，不同提供商的收费模式如下：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）免费服务：部分服务商提供免费额度或完全免费的服务，如智谱AI（glm-4-flash等免费模型）、微软EdgeTTS语音合成等。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）按量付费服务：部分服务商按API调用量计费，如OpenAI、阿里云智能语音、百度文心、讯飞等。您需要自行向第三方服务商支付相应费用，该等费用与本服务无关。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[60rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （3）本地部署方案：本服务支持完全本地部署的AI方案，如FunASR语音识别、FishSpeech语音合成、Ollama本地大模型等。本地部署无需网络费用和API调用费用，但需要本地具备足够的计算资源。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.15 服务变更：运营者保留根据实际情况对服务内容进行调整、升级或终止的权利，并将尽可能提前予以通知。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            五、用户行为规范
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.1 合法使用：您在使用本服务时，应遵守中华人民共和国的法律法规及相关国际条约，不得利用本服务从事任何违法违规活动。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.2 禁止行为：您承诺在使用本服务时不得实施以下行为：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）发布、传输、存储危害国家安全、社会稳定的内容，包括但不限于涉及颠覆国家政权、损害国家荣誉和利益、煽动民族仇恨等内容。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）发布、传输、存储侵犯他人合法权益的内容，包括但不限于侵犯知识产权、隐私权、名誉权等。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （3）发布、传输、存储淫秽、色情、暴力、恐怖或教唆犯罪的内容。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （4）发布虚假信息、散布谣言或从事欺诈行为。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （5）以任何方式干扰本服务的正常运行，包括但不限于攻击服务器、传播恶意程序、恶意消耗系统资源等。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （6）未经授权对本服务进行反向工程、反编译或其他试图获取系统源代码的行为（本条不限制您依据开源许可证对开源代码的合法使用）。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （7）利用本服务进行自动化批量操作，恶意消耗API调用配额或其他系统资源。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （8）在智能体设定中输入违反法律法规或社会公序良俗的内容。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （9）利用本服务伤害或企图伤害未成年人。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （10）其他违反法律法规、本协议约定或可能损害运营者及第三方合法权益的行为。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.3 违规处理：如您违反上述行为规范，运营者有权视情节严重程度采取警告、限制功能、暂停服务、封禁账号等措施，并保留追究法律责任的权利。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            六、知识产权
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.1 开源许可：本服务为开源项目，其源代码遵循相应的开源许可证。您可以在遵守该许可证条款的前提下使用相关源代码。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.2 服务内容权属：除开源代码外，本服务中的界面设计、图标、文案及其他运营者独立创作的内容，其知识产权归运营者所有。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.3 用户内容：您通过本服务输入、上传或生成的内容，其知识产权归属依照相关法律法规确定。您授予运营者为维护和改进服务之目的，对您输入内容进行存储和必要处理的权利。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.4 第三方权益：您在使用本服务时，应尊重第三方的知识产权及其他合法权益。因您侵犯第三方权益而引发的纠纷，由您自行承担全部责任。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            七、隐私保护
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.1 信息收集：为提供本服务，运营者可能会收集您的注册信息（如手机号、用户名）、设备信息、使用日志等。具体的个人信息收集和使用规则请参阅《隐私政策》。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.2 信息保护：运营者将采取合理的技术和管理措施保护您的个人信息安全。但由于互联网的开放性，运营者不能绝对保证信息安全，请您注意保护个人敏感信息。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.3 信息安全提示：请勿在使用本服务过程中向AI透露您的财产账户、银行卡、密码等敏感个人信息，否则由此带来的损失由您自行承担。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            八、免责声明
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.1 AI生成内容：本服务依赖第三方AI模型提供智能交互能力，AI生成的内容可能存在不准确、不完整或不恰当之处。运营者不对AI生成内容的真实性、准确性、完整性作任何保证。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.2 服务中断：因以下原因导致服务中断或异常，运营者不承担责任：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）不可抗力因素，如自然灾害、疫情、战争等。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）电力供应故障、通信网络故障等公共服务因素。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （3）第三方AI模型服务商的服务故障或政策调整。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （4）系统维护、升级导致的临时性服务中断。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （5）黑客攻击、计算机病毒等网络安全事件。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （6）法律法规或政府管制导致的服务调整。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （7）其他非运营者过错导致的情形。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.3 第三方服务：本服务可能涉及第三方提供的语言模型、语音识别、语音合成、视觉模型、意图识别等服务。您在使用时应同时遵守第三方的服务条款。因第三方服务引发的问题，请直接与第三方联系。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.4 开源声明：本服务为开源项目，按"现状"提供。在法律允许的最大范围内，运营者不就本服务的适销性、特定用途适用性或不侵权性作任何明示或暗示的保证。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.5 开源软件特别声明：本项目为开源软件，本服务与对接的任何第三方API服务商（包括但不限于语音识别、大模型、语音合成等平台）均不存在商业合作关系，不为其服务质量及资金安全提供任何形式的担保。本软件不托管任何账户密钥、不参与资金流转、不承担充值资金损失风险。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.6 安全警告：本项目功能未完善，且未通过网络安全测评，请勿在生产环境中使用。如果您在公网环境中部署学习本项目，请务必做好必要的防护措施，包括但不限于设置强密码、限制访问权限、启用HTTPS加密传输等。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            九、未成年人保护
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.1 若您是未满18周岁的未成年人，应在监护人的指导和同意下使用本服务。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.2 监护人应加强对未成年人使用本服务的监督，引导未成年人合理使用，避免过度依赖。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.3 未成年人在使用本服务时应注意个人信息保护，避免上传或透露个人敏感信息。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            十、协议终止
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.1 用户终止：您有权随时停止使用本服务并注销账号。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.2 运营者终止：出现以下情形时，运营者有权终止向您提供服务：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）您违反本协议的约定。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）您利用本服务从事违法违规活动。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （3）根据法律法规或政策要求。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （4）运营者决定停止运营本服务。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.3 终止后处理：协议终止后，运营者无义务保留您的账号信息及相关数据。运营者仍有权依据本协议追究您在协议有效期内的违约责任。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            十一、法律适用与争议解决
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.1 本协议的订立、生效、解释、修订、终止及争议解决均适用中华人民共和国法律。
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.2 因本协议或本服务引发的争议，双方应友好协商解决；协商不成的，任何一方有权向运营者所在地有管辖权的人民法院提起诉讼。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.3 本协议的任何条款被认定为无效或不可执行，不影响其余条款的效力。
          </text>
        </view>

        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] font-semibold">
            十二、其他
          </text>
        </view>
        <view class="mb-[24rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            12.1 本协议构成您与运营者之间关于使用本服务的完整协议。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            12.2 运营者未行使或延迟行使本协议项下的任何权利，不构成对该权利的放弃。
          </text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
</style>
