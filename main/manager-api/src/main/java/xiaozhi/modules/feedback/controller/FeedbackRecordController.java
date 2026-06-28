package xiaozhi.modules.feedback.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.feedback.service.FeedbackRecordService;
import xiaozhi.modules.feedback.vo.FeedbackRecordVO;

@AllArgsConstructor
@RestController
@RequestMapping("/feedback/record")
@Tag(name = "反馈记录管理")
public class FeedbackRecordController {

    private final FeedbackRecordService feedbackRecordService;

    @GetMapping("/list")
    @Operation(summary = "反馈记录分页列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<FeedbackRecordVO>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        String storeId = (String) params.get("storeId");
        String page = (String) params.get(Constant.PAGE);
        String limit = (String) params.get(Constant.LIMIT);
        PageData<FeedbackRecordVO> data = feedbackRecordService.page(storeId, page, limit);
        return new Result<PageData<FeedbackRecordVO>>().ok(data);
    }
}
