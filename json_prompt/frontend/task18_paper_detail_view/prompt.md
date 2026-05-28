# Task18: PaperDetailView + 论文元数据展示

## 任务概述
实现PaperDetailView论文详情页面，展示论文完整元数据，支持收藏操作，提供触发AI分析功能，包含Loading/Empty/Error三态完整。

## 里程碑
FM3：论文分析+对比页面可用

## 涉及模块
- F1.3.1 论文详情

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/PaperDetailView.vue | 替换空壳为完整论文详情页面 |

## 功能要求

### P0 - 必须实现
1. **返回导航**：el-page-header @back='router.back()'，标题显示论文标题
2. **论文数据加载**：onMounted从route.params.paperId获取，调用paperApi.getDetail(paperId)
3. **论文元数据卡片**：标题/作者·年份·会议·引用数/摘要/关键词标签
4. **触发AI分析**：创建会话→analyzePaper→轮询getStatus(3s间隔)→完成显示5维度结果
5. **AI分析区域**：未分析=空状态引导、分析中=loading+进度、分析完成=5维度展示
6. **Loading状态**：el-skeleton或v-loading覆盖
7. **Empty状态**：论文不存在→el-result未找到+返回首页
8. **Error状态**：加载失败→错误+重试；分析失败→错误+重新分析
9. **轮询清理**：onUnmounted中clearInterval
10. **BEM样式**：paper-detail-view__*类名规范，scoped CSS

### P1 - 应该实现
1. **收藏按钮**：Star/StarFilled图标，调用paperStore.toggleFavorite
2. **通俗解释控制**：beginner/intermediate显示，advanced/expert不显示
3. **AI内容标注**：'AI生成，仅供参考'
4. **分析后操作**：[生成综述]→ReportView、[选择对比]→CompareView

### P2 - 可以实现
1. **查看PDF按钮**：pdfUrl存在时显示，新标签页打开

## 交互状态覆盖
| 状态 | 实现 |
|------|------|
| Loading | el-skeleton / v-loading |
| Empty | el-result '论文未找到' |
| Error | el-result '加载失败' + 重试按钮 |
| Success | 论文元数据+分析结果展示 |
| Hover | 卡片shadow="hover" |
| Transition | skeleton→content |

## 验收标准
- [ ] 论文元数据完整展示（标题/作者/年份/会议/引用数/摘要/关键词）
- [ ] Loading/Empty/Error三态完整
- [ ] 触发AI分析→轮询→展示5维度结果流程通畅
- [ ] 收藏按钮状态正确，操作有反馈
- [ ] 通俗解释根据用户画像显示/隐藏
- [ ] AI内容标注'AI生成，仅供参考'
- [ ] 轮询定时器onUnmounted清理
- [ ] BEM命名+CSS变量+8px间距
- [ ] TypeScript类型检查通过
- [ ] 单组件≤300行
