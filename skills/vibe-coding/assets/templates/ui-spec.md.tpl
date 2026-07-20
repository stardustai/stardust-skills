# UI/UX 规范

> 仅当 `PROJECT.yaml.features.business_ui=true` 时启用。

## 事实源与设计系统

- Spec：`__SPEC_PATH__`
- 已批准 Wireframe：`__WIREFRAME_PATH__`
- 现有 Design System / 组件库：__DESIGN_SYSTEM__
- 用户确认人 / 时间：__UI_APPROVER__ / __APPROVED_AT__

## 用户流程

__USER_JOURNEY_WITH_SUCCESS_AND_FAILURE__

## 页面与状态

| Screen ID | 角色/权限 | 目的 | 复用组件 | Loading | Empty | Success | Validation/System Error | No Permission |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| __SCREEN_ID__ | __ROLE__ | __PURPOSE__ | __COMPONENTS__ | __LOADING__ | __EMPTY__ | __SUCCESS__ | __ERRORS__ | __NO_PERMISSION__ |

## 字段与操作

| Field/Action ID | 类型 | 必填/默认 | 校验 | 错误提示 | 敏感性 | 可见角色 | 可编辑角色 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| __FIELD_OR_ACTION_ID__ | __TYPE__ | __REQUIRED_DEFAULT__ | __VALIDATION__ | __ERROR_MESSAGE__ | __SENSITIVITY__ | __VISIBLE_ROLES__ | __EDITABLE_ROLES__ |

## 验证

- 关键流程浏览器测试：__BROWSER_TEST__
- 截图/视觉回归：__VISUAL_EVIDENCE__
- 可访问性：__ACCESSIBILITY_CHECK__
- 响应式：__RESPONSIVE_CHECK__
- 实际页面业务验收：__USER_ACCEPTANCE__

不得擅自改变流程、字段、操作入口或权限。真实数据或交互使 Wireframe 不适配时，向用户提供
“保持原设计”“局部调整”“返回产品设计”三个选项并说明影响。
