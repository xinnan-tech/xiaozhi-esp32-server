<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "隐私政策"
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
    <scroll-view scroll-y class="box-border flex-1 px-[20rpx] py-[30rpx]" :scroll-with-animation="true">
      <view class="rounded-[16rpx] bg-white px-[30rpx] py-[40rpx] shadow-[0_4rpx_20rpx_rgba(0,0,0,0.05)]">
        <view class="mb-[40rpx] text-center">
          <text class="text-[36rpx] text-[#1a1a1a] font-bold">
            {{ t('login.privacyPolicy') }}
          </text>
        </view>
        <view class="mb-[40rpx] text-center">
          <text class="text-[24rpx] text-[#666666]">
            更新日期：2026年3月10日
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            引言
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            欢迎您使用小智后端服务（以下简称"本服务"）。本服务的运营方为本服务的实际部署者和管理者（以下简称"运营者"或"我们"）。我们深知个人信息对您的重要性，将尽全力保护您的个人信息安全。
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            请您在使用本服务前，仔细阅读并充分理解本隐私政策的全部内容。一旦您开始使用本服务，即表示您已阅读并同意本隐私政策。
          </text>
        </view>
        <view class="mb-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            本隐私政策适用于您通过智控台（管理后台）、API接口及其他方式使用本服务时，我们对您个人信息的收集、存储、使用、共享、保护等行为。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            一、我们收集的信息
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            为向您提供服务，我们可能需要收集以下信息：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.1 账号注册信息：当您注册账号时，我们会收集您的手机号码或用户名、密码等信息，用于创建和验证您的账号。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.2 设备信息：当您绑定硬件设备时，我们会收集设备的标识信息（如设备编码、MAC地址等）、设备型号、固件版本等，用于设备管理和服务提供。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.3 智能体配置信息：当您创建和配置智能体时，我们会收集您设定的角色模板、语言模型选择、语音参数配置等信息，用于提供个性化的AI交互服务。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.4 语音交互数据：在您使用语音交互功能时，本服务会通过语音活动检测（VAD）判断您的语音起止状态，并处理您的语音输入数据，将其传输至第三方语音识别（ASR）和语言模型（LLM）服务进行处理，以实现语音交互功能。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.5 图像数据：当您使用视觉模型功能时，我们可能会处理您通过设备摄像头采集的图像数据，并将其传输至第三方视觉模型服务进行分析和理解，用于实现图像识别、场景理解等功能。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.6 对话记忆数据：当您开启记忆功能时，本服务会存储您与智能体的交互历史摘要，用于在后续对话中提供更连贯、个性化的交互体验。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.7 知识库数据：当您使用知识库功能时，我们会收集和存储您上传的文档、文本等知识库内容，用于智能体在对话中进行知识检索和问答。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.8 声纹数据：当您使用声纹识别功能时，我们会收集和存储您的声纹特征样本，用于说话人身份验证和个性化服务。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.9 聊天历史数据：我们会存储您与智能体的对话历史记录，包括文本对话内容、对话时间、交互上下文等信息，用于提供连续性对话体验和历史查询功能。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.10 对话音频数据：在您使用语音交互功能时，我们可能会存储您与智能体交互的音频数据，用于优化语音交互质量和回溯查询。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.11 智能体配置数据：当您配置智能体时，我们会收集您设定的标签、插件配置、上下文提供者设置等信息，用于提供智能体定制化服务。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.12 设备固件数据：当您使用OTA升级功能时，我们会记录设备固件版本、升级历史等信息，用于设备管理和固件追溯。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.13 日志信息：当您使用本服务时，我们会自动收集服务日志信息，包括但不限于访问时间、IP地址、浏览器类型、操作记录等，用于服务运维和安全保障。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            1.14 验证码信息：当您使用手机号登录时，我们会通过短信服务向您发送验证码，用于身份验证。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            二、我们如何使用收集的信息
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            我们收集的信息将用于以下目的：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）提供、维护和改进本服务，包括账号管理、设备管理、智能体配置等核心功能。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）处理您的语音交互请求，通过语音活动检测（VAD）识别语音输入，调用第三方AI模型服务完成语音识别、意图识别、语义理解和语音合成。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （3）处理您的图像数据，调用第三方视觉模型服务完成图像识别和场景理解。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （4）存储和管理您的对话记忆数据，以便在后续交互中提供更连贯的服务体验。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （5）存储和检索您上传的知识库内容，以便智能体在对话中为您提供更准确的知识问答。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （6）保障服务的安全性和稳定性，包括身份验证、安全防护、故障排查等。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （7）遵守适用的法律法规和监管要求。
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            我们不会将您的个人信息用于与上述目的无关的其他用途。如需将信息用于本隐私政策未载明的其他目的，我们会事先征得您的同意。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            三、信息的共享与披露
          </text>
        </view>
        <view class="mb-[24rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            我们不会向第三方出售您的个人信息。仅在以下情形下，我们可能会共享或披露您的信息：
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.1 第三方服务调用：为实现语音交互、视觉理解等功能，您的语音数据、图像数据和文本内容可能会被传输至第三方AI服务提供商（如语言模型、语音识别、语音合成、视觉模型服务商）进行处理。我们会选择具备合理安全保障能力的服务商，但请您知悉第三方服务商将按照其自身的隐私政策处理相关数据。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.2 法律要求：根据适用的法律法规、法律程序或政府主管部门的要求，我们可能需要披露您的个人信息。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.3 安全保障：为保护运营者、其他用户或公众的权益、财产或安全免遭损害，在合理必要的范围内使用或披露个人信息。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            3.4 征得同意：在获得您明确同意的前提下，我们可能会与第三方共享您的个人信息。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            四、信息的存储与保护
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.1 存储地点：您的个人信息将存储在运营者部署本服务的服务器上，包括但不限于数据库（MySQL/PostgreSQL）和缓存服务（Redis）。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.2 存储期限：我们将在为您提供服务所必需的期限内保留您的个人信息。当您注销账号后，我们将在合理时间内删除或匿名化处理您的个人信息，法律法规另有规定的除外。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.3 安全措施：我们采取合理的技术和管理措施保护您的个人信息安全，包括但不限于数据加密、访问控制、安全审计等。但请您理解，互联网并非绝对安全的环境，我们无法保证信息传输和存储的绝对安全性。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.4 安全事件处理：如发生个人信息安全事件，我们将按照法律法规的要求，及时向您告知安全事件的基本情况、可能的影响、已采取或将要采取的处置措施等。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.5 开源项目特别说明：本服务为开源项目，存在两种运营模式：
          </text>
        </view>
        <view class="mb-[8rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （1）自行部署：如您自行部署本服务，运营者仅为代码提供方，实际的数据存储和处理由您自行负责。
          </text>
        </view>
        <view class="mb-[8rpx] ml-[40rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            （2）测试平台：如您使用运营者部署的测试平台，您的数据将由运营人员负责管理和保护。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            4.6 数据跨境传输：本服务在提供智能交互功能时，可能需要调用境外第三方AI服务提供商的接口。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            五、您的权利
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.1 查询与访问：您可通过智控台查看和管理您的账号信息、设备信息、智能体配置等个人信息。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.2 更正与修改：当您发现个人信息有误时，您可通过智控台自行更正，或联系运营者协助处理。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.3 删除：在以下情形下，您可请求我们删除您的个人信息：（1）处理目的已实现、无法实现或不再必要；（2）我们违反法律法规或与您的约定收集、使用个人信息；（3）注销账号。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.4 账号注销：您可通过智控台的账号设置功能注销账号，或联系运营者进行处理。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            5.5 撤回同意：您可随时撤回您此前向我们作出的同意授权。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            六、未成年人信息保护
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.1 我们高度重视未成年人个人信息的保护。若您是未满18周岁的未成年人，请在监护人的指导和同意下使用本服务。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.2 如果监护人发现未成年人未经其同意向我们提供了个人信息，请联系运营者，我们将尽快删除相关信息。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            6.3 对于经监护人同意使用本服务的未成年人，我们将按照法律法规的规定，给予其个人信息更严格的保护。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            七、第三方服务说明
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.1 本服务在提供智能交互功能时，需要调用第三方服务，包括但不限于：语音活动检测服务（VAD）、语音识别服务（ASR）、大语言模型服务（LLM）、语音合成服务（TTS）、视觉模型服务、短信验证码服务、MQTT消息代理服务、数据库服务。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            7.2 上述第三方服务提供商将按照其各自的隐私政策对数据进行处理。我们建议您在使用本服务前，了解相关第三方服务商的隐私政策。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            八、Cookie及类似技术的使用
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.1 本服务可能使用Cookie及类似技术来保存您的登录状态、记录您的偏好设置等，以便为您提供更好的使用体验。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            8.2 您可以通过浏览器设置管理Cookie。但请注意，如果禁用Cookie，可能会影响本服务的部分功能。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            九、隐私政策的变更
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.1 我们可能会根据业务调整、法律法规变化等原因对本隐私政策进行修订。修订后的隐私政策将通过本平台公告等方式予以发布。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            9.2 如您在隐私政策修订后继续使用本服务，则视为您已接受修订后的隐私政策。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            十、信息安全提示
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.1 请勿在与AI的语音或文字交互中透露您的财产账户、银行卡号、信用卡号、密码、身份证号等敏感个人信息，否则由此带来的损失由您自行承担。
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.2 请妥善保管您的账号和密码，不要将账号信息告知他人或与他人共享账号。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            10.3 如您发现个人信息可能被泄露，请及时联系运营者采取措施。
          </text>
        </view>
        <view class="mb-[32rpx]">
          <text class="text-[30rpx] text-[#1a1a1a] font-bold">
            十一、适用法律
          </text>
        </view>
        <view class="mb-[16rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.1 本隐私政策的制定、解释、执行及争议解决均适用中华人民共和国法律法规（为本隐私政策之目的，不包括港澳台地区法律）。
          </text>
        </view>
        <view class="mb-[40rpx] ml-[20rpx]">
          <text class="text-[28rpx] text-[#333333] leading-[1.8]">
            11.2 如本隐私政策的任何条款与中华人民共和国现行法律法规相抵触，以法律法规的规定为准，其余条款仍然有效。
          </text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>
