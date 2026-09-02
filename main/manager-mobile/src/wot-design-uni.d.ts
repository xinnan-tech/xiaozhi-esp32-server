import type { ExtractPropTypes } from 'vue'
import type { actionSheetProps } from 'wot-design-uni/components/wd-action-sheet/types'
import type { buttonProps } from 'wot-design-uni/components/wd-button/types'
import type { checkboxProps } from 'wot-design-uni/components/wd-checkbox/types'
import type { configProviderProps } from 'wot-design-uni/components/wd-config-provider/types'
import type { fabProps } from 'wot-design-uni/components/wd-fab/types'
import type { iconProps } from 'wot-design-uni/components/wd-icon/types'
import type { imgProps } from 'wot-design-uni/components/wd-img/types'
import type { inputProps } from 'wot-design-uni/components/wd-input/types'
import type { loadingProps } from 'wot-design-uni/components/wd-loading/types'
import type { messageBoxProps } from 'wot-design-uni/components/wd-message-box/types'
import type { navbarProps } from 'wot-design-uni/components/wd-navbar/types'
import type { pickerProps } from 'wot-design-uni/components/wd-picker/types'
import type { popupProps } from 'wot-design-uni/components/wd-popup/types'
import type { segmentedProps } from 'wot-design-uni/components/wd-segmented/types'
import type { sliderProps } from 'wot-design-uni/components/wd-slider/types'
import type { statusTipProps } from 'wot-design-uni/components/wd-status-tip/types'
import type { swipeActionProps } from 'wot-design-uni/components/wd-swipe-action/types'
import type { switchProps } from 'wot-design-uni/components/wd-switch/types'
import type { tabbarItemProps } from 'wot-design-uni/components/wd-tabbar-item/types'
import type { tabbarProps } from 'wot-design-uni/components/wd-tabbar/types'
import type { tagProps } from 'wot-design-uni/components/wd-tag/types'
import type { toastProps } from 'wot-design-uni/components/wd-toast/types'

type TypedGlobalComponent<Props> = new () => { $props: Partial<Props> }

// wot-design-uni 1.9.1 exposes raw Vue source through its global declarations.
// Rebuild lightweight global components from the published prop objects without
// pulling the package's raw Vue source into vue-tsc. Partial preserves Vue's
// runtime defaults while retaining prop names and value types.
declare module 'vue' {
  export interface GlobalComponents {
    WdActionSheet: TypedGlobalComponent<ExtractPropTypes<typeof actionSheetProps>>
    WdButton: TypedGlobalComponent<ExtractPropTypes<typeof buttonProps>>
    WdCheckbox: TypedGlobalComponent<ExtractPropTypes<typeof checkboxProps>>
    WdConfigProvider: TypedGlobalComponent<ExtractPropTypes<typeof configProviderProps>>
    WdFab: TypedGlobalComponent<ExtractPropTypes<typeof fabProps>>
    WdIcon: TypedGlobalComponent<ExtractPropTypes<typeof iconProps>>
    WdImg: TypedGlobalComponent<ExtractPropTypes<typeof imgProps>>
    WdInput: TypedGlobalComponent<ExtractPropTypes<typeof inputProps>>
    WdLoading: TypedGlobalComponent<ExtractPropTypes<typeof loadingProps>>
    WdMessageBox: TypedGlobalComponent<ExtractPropTypes<typeof messageBoxProps>>
    WdNavbar: TypedGlobalComponent<ExtractPropTypes<typeof navbarProps>>
    WdPicker: TypedGlobalComponent<ExtractPropTypes<typeof pickerProps>>
    WdPopup: TypedGlobalComponent<ExtractPropTypes<typeof popupProps>>
    WdSegmented: TypedGlobalComponent<ExtractPropTypes<typeof segmentedProps>>
    WdSlider: TypedGlobalComponent<ExtractPropTypes<typeof sliderProps>>
    WdStatusTip: TypedGlobalComponent<ExtractPropTypes<typeof statusTipProps>>
    WdSwipeAction: TypedGlobalComponent<ExtractPropTypes<typeof swipeActionProps>>
    WdSwitch: TypedGlobalComponent<ExtractPropTypes<typeof switchProps>>
    WdTabbar: TypedGlobalComponent<ExtractPropTypes<typeof tabbarProps>>
    WdTabbarItem: TypedGlobalComponent<ExtractPropTypes<typeof tabbarItemProps>>
    WdTag: TypedGlobalComponent<ExtractPropTypes<typeof tagProps>>
    WdToast: TypedGlobalComponent<ExtractPropTypes<typeof toastProps>>
  }
}
