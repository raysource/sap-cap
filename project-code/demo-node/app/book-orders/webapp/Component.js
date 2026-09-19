sap.ui.define([
  "sap/fe/core/AppComponent"
], function (AppComponent) {
  "use strict";

  /**
   * Fiori Elements 应用的组件入口。
   * 什么都不用实现：ListReport / Object Page 的行为全部由 manifest.json + annotations.cds 决定。
   * 只有需要全局逻辑（例如自定义鉴权、扩展 Controller）时才在这里写代码。
   */
  return AppComponent.extend("sap.training.bookorder.manage.Component", {
    metadata: {
      manifest: "json"
    }
  });
});
