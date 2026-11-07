# 11 · 测试

> 更新历史：2026-08-21 创建；2026-08-28 测试分层与集成测试的通用条款去重，改为引用 C# 测试规范，本篇仅保留 WPF 特有的测试约束；2026-10-27 判据内聚到插件，原跨域指针改为就地内联要点；2026-11-07 新增 Converter 测试、STA 测试特性选型（`[WpfFact]` 等）、View 与控件测试、分层测试项目命名约定、反模式速查，并按「分层模型 → 单元层 → 组件层 → 集成层 → UI 自动化层 → 跨层规范」重组全篇。

WPF 测试分三层：单元测试（ViewModel / Converter，多、快）、集成测试（真实协作）、UI 自动化测试（少、慢）。测试框架与断言库团队统一，通用测试策略沿用团队约定，本篇聚焦 WPF 特有测试问题。

测试分层的通用判据，在此列明（它们是审查时的检查项，不再外引）：

- **必须**：测试分层——单元（多、快）→ 集成（真实协作）→ E2E（少、慢）
- **必须**：新功能配测试；修复 bug 先写能复现的测试再修
- **禁止**：只有 E2E 没有单元测试（慢、脆、故障难以定位）
- **应该**：E2E 只覆盖关键用户路径，普通逻辑下沉到单元 / 集成

本篇只写这些原则落到 WPF 上的差异（UI 自动化测试对应通用分层里的 E2E 层）。章节按层组织：**分层模型**（第 1 节）→ **单元层**（第 2 节）→ **组件层**（第 3 节）→ **集成层**（第 4 节）→ **UI 自动化层**（第 5 节）→ **跨层规范**（第 6 节）→ **反模式**（第 7 节）。

## 1. 分层模型

### 1.1 分层边界

- **必须**：通用分层的三层在 WPF 中对应——ViewModel/服务单元测试（多、快）→ 集成测试（真实协作）→ UI 自动化测试（少、慢）；通用规范里的 E2E 层在 WPF 即 UI 自动化测试

组件测试（第 3 节）在进程内、不触外部资源，但需要 STA 与 `Dispatcher`，所以单独成层——与纯 CLR 的单元层区分，也把 WPF 的线程模型（第 3.1 节）集中讲清，避免每条断言都重复一遍线程约束。

| 层 | 测什么 | 执行条件 | 量级 |
|---|---|---|---|
| 单元 | ViewModel、Converter、领域服务 | 纯 CLR，无 UI 上下文 | 毫秒 |
| 组件 | View 绑定、控件 DP / 模板 / 视觉状态 | STA + `Dispatcher`（进程内） | 百毫秒 |
| 集成 | ViewModel ↔ 服务 ↔ 持久化 | 真实协作（Testcontainers / 本地实例） | 秒 |
| UI 自动化 | 登录、主流程等关键用户路径 | 真实窗口 + 交互式桌面 | 十秒 |

- **应该**：断言尽量落在单元层（ViewModel + Converter），组件层只锁契约，UI 自动化只覆盖关键路径——越往上，单个断言的维护成本越高

### 1.2 测试项目结构

- **必须**：测试项目命名 `<被测>.Tests`，目录镜像源码结构
- **必须**：被测类 `UserManager` 对应测试类 `UserManagerTests`
- **禁止**：测试项目引用 UI 项目中的 `App.xaml` / 资源（测 ViewModel 不需要 UI 上下文）
- **应该**：组件层测试单独建项目，不把 STA / `Application` 依赖带进单元测试项目
- **应该**：同一被测单元同时有单元与集成测试时，项目名加层限定——单元 `<被测>.Tests`、集成 `<被测>.IntegrationTests`（或按范围 `App.IntegrationTests`）、组件 `App.Component.Tests`、UI 自动化 `App.E2E.Tests`
- **应该**：类名默认仍 `<被测类>Tests`；同一类型在单元与集成两侧都测时，集成侧加 `Integration` 后缀（`OrderRepositoryIntegrationTests`），避免 CI 报告与堆栈里无法区分

## 2. 单元层

不变量：纯 CLR、毫秒级、失败直接定位到方法；不启动窗口，不依赖 `Application`，不触真实 I/O。

### 2.1 ViewModel

- **必须**：ViewModel 依赖为接口（DI 注入），mock 外部边界（I/O、服务、时间），**禁止** mock 被测单元自身逻辑
- **必须**：命令测试——`CanExecute` → `Execute` → 状态断言（属性、集合、导航调用）
- **必须**：异步命令测试 `await` 完成，**禁止** `.Result` / `.Wait()` 同步等待（死锁，联动 `09` 章）
- **应该**：`INotifyPropertyChanged` 变更断言（`PropertyChanged` 事件触发、触发属性名正确）
- **禁止**：ViewModel 依赖具体 UI 类型（`Brush`、`Dispatcher` 直接使用），否则不可测（联动 `03` 章第 2 节）

**示例：属性变更与命令**

```csharp
[Fact]
public async Task SaveCommand_WhenValid_InvokesRepositoryAndRaisesPropertyChanged()
{
    // Arrange
    var repo = Substitute.For<IOrderRepository>();
    var vm = new OrderViewModel(repo) { Amount = 42 };
    var raised = false;
    vm.PropertyChanged += (_, e) => { if (e.PropertyName == nameof(vm.IsSaving)) raised = true; };

    // Act
    await vm.SaveCommand.ExecuteAsync(null);

    // Assert
    await repo.Received(1).Save(Arg.Is<Order>(o => o.Amount == 42));
    Assert.True(raised);
}
```

- **必须**：派生属性与被依赖属性一起通知（改 `Amount` 必须同时触发 `Error`、`CanExecuteChanged`），只测值不测通知会漏掉"按钮永远灰着"这类缺陷
- **应该**：架构测试兜底——反射断言 ViewModel 类型的公开成员不出现 `System.Windows.Media` / `Controls` / `Threading` 等 UI 类型（放行 `System.Windows.Input.ICommand`），比人工 review 稳定

### 2.2 Converter

- **必须**：Converter 按纯函数测——直接调用 `Convert` / `ConvertBack`，**禁止**为测转换器创建窗口或依赖 `Application`
- **必须**：覆盖 `null`、类型不符、`parameter` 分支、`culture` 四类输入；非法输入返回 `DependencyProperty.UnsetValue` 或安全默认值，**禁止**抛异常（联动 `05` 章第 4 节）
- **必须**：`ConvertBack` 往返一致；不可逆转换返回 `Binding.DoNothing`，不抛异常
- **必须**：`IMultiValueConverter` 单独覆盖 `values` 长度不足 / 多余——运行期最常见的静默失败来源
- **应该**：断言具体值（`Visibility.Visible`、格式化后的字符串），不断言"不为 null"
- **应该**：验证无状态——同一实例连续调用结果一致（Converter 注册在资源字典中是单例，联动 `07` 章）
- **禁止**：测试间共享未 `Freeze()` 的 `Freezable`（`SolidColorBrush` 有线程亲和性；用 `Brushes.*` 或先 `Freeze()`）

```csharp
public sealed class BoolToVisibilityConverterTests
{
    private readonly BoolToVisibilityConverter _sut = new();
    private static readonly CultureInfo Zh = CultureInfo.GetCultureInfo("zh-CN");

    [Theory]
    [InlineData(true, Visibility.Visible)]
    [InlineData(false, Visibility.Collapsed)]
    public void Convert_Bool_MapsToVisibility(bool value, Visibility expected)
        => Assert.Equal(expected, _sut.Convert(value, typeof(Visibility), null, Zh));

    [Theory]
    [InlineData(null)]
    [InlineData("true")]     // 类型不符
    [InlineData(1)]
    public void Convert_InvalidInput_ReturnsUnsetValueWithoutThrowing(object? value)
        => Assert.Same(DependencyProperty.UnsetValue,
                       _sut.Convert(value, typeof(Visibility), null, Zh));

    [Fact]
    public void Convert_ParameterInvert_FlipsResult()
        => Assert.Equal(Visibility.Collapsed,
                        _sut.Convert(true, typeof(Visibility), "Invert", Zh));
}
```

- 经 `BindingOperations.SetBinding` 验证「VM 属性 → Converter → 目标值」的整条绑定链路，需要 STA 宿主，归组件层（第 3.2 节）

### 2.3 调度器替身

- **必须**：ViewModel 单元测试不依赖真实 UI 线程（纯逻辑可测），涉及 `Dispatcher` 时注入调度接口
- **禁止**：测试依赖 `Application.Current.Dispatcher`——测试进程没有 `Application` 实例，直接空引用
- **禁止**：为测调度逻辑启动真实消息泵或窗口；调度逻辑用假实现同步执行

```csharp
// ❌ 测试直接依赖 Application.Current.Dispatcher：测试进程无 WPF Application 实例，抛异常
[Fact]
public void Update_WithValidData_UpdatesStatus()
{
    var vm = new OrderViewModel();
    Application.Current.Dispatcher.Invoke(() => vm.Update());   // NullReferenceException

    Assert.Equal("已更新", vm.Status);
}

// ✅ 依赖注入调度接口：测试注入假调度器，生产注入真 Dispatcher
public interface IDispatcher { void Invoke(Action action); }

[Fact]
public void Update_WithValidData_UpdatesStatus()
{
    var vm = new OrderViewModel(new FakeDispatcher());   // 假调度：同步执行
    vm.Update();

    Assert.Equal("已更新", vm.Status);
}
```

## 3. 组件层（需要 UI 上下文）

不变量：进程内实例化 View / 控件，走真实 WPF 对象模型；不 `Show()` 窗口、不点按钮、不覆盖真实交互。只锁「契约」——绑定、依赖属性、模板部件、视觉状态。

### 3.1 线程模型与 STA 测试特性

`[Fact]` 在 MTA 线程执行，直接构造控件、调用输入 / OLE 相关 API 会抛 `The calling thread must be STA, because many UI components require this`。`Xunit.StaFact` 包提供按线程模型划分的测试特性，`[WpfFact]` 是其中**面向 WPF 的那一个**：

| 特性 | 线程 | SynchronizationContext | Application | 适用 |
|---|---|---|---|---|
| `[Fact]` | MTA | 无 | 无 | ViewModel、Converter 等纯逻辑 |
| `[StaFact]` | STA | 不保证 `await` 后回到 STA 线程 | 无 | 同步构造控件、只读依赖属性 |
| `[WpfFact]` | STA | `DispatcherSynchronizationContext` | 无 | 绑定、模板、`Dispatcher` 调度 |
| `[UIFact]` | STA（Windows） | 通用单线程 SyncContext | 无 | 跨平台控件逻辑 |

- **应该**：需要 UI 上下文的测试项目设置 `<UseWPF>true</UseWPF>`
- **必须**：WPF 控件与绑定测试用 `[WpfFact]` / `[WpfTheory]`——它装在 STA 线程并安装 `DispatcherSynchronizationContext`，`await` 后仍回到同一线程，`Dispatcher.InvokeAsync` 这类调度才表现得和应用里一致
- ⚠️ **`[WpfFact]` 不创建 `Application`**：`Application.Current` 仍为 `null`，测试结束还会关闭该线程的 `Dispatcher`；需要应用级资源（`App.xaml` 合并的主题字典）时由测试自己创建一次 `Application`（AppDomain 内只能有一个），放进集合级 fixture 共享，**禁止**每个测试各建一个
- **必须**：有 `await` 的 STA 测试用 `[WpfFact]`，**禁止**用 `[StaFact]`——后者没有 `SynchronizationContext`，`await` 恢复后已不在 STA 线程
- **应该**：多个测试共享同一 UI 线程 / `Application` 时用集合级 fixture（`ICollectionFixture`）持有，不要在每个用例里重复创建
- **必须**：UI 测试放进同一 `[Collection]` 串行执行，**禁止**并行（抢焦点、`Application` 单例、控件静态状态互相污染）
- **禁止**：在组件层启动真实窗口（属 UI 自动化测试范畴）

版本对应：`Xunit.StaFact` 的主版本须与所用 xUnit 版本（v2 / v3）匹配，具体对应以该包 README 为准；不匹配时测试特性可能不被发现，用例会被忽略而非报错——升级 xUnit 后核对用例数。

```csharp
[WpfFact]
public void Status_WhenChanged_UpdatesBoundTarget()
{
    var vm = new OrderViewModel();
    var text = new TextBlock { DataContext = vm };
    BindingOperations.SetBinding(text, TextBlock.TextProperty, new Binding(nameof(vm.Status)));

    vm.Status = "已完成";

    Assert.Equal("已完成", text.Text);
    Assert.Equal(ApartmentState.STA, Thread.CurrentThread.GetApartmentState()); // 仍在 STA
}
```

### 3.2 View：绑定接线与错误

- **必须**：View 测试只验证契约——绑定接线、模板部件、视觉状态、关键交互；**禁止**断言 XAML 结构与硬编码文案（样式重构即碎，却挡不住真实缺陷）
- **必须**：View 保持薄——逻辑下沉 ViewModel / Behavior / 附加属性，code-behind 只留纯视图代码（联动 `03` 章、`16` 章）
- **应该**：每个 View 至少一条绑定冒烟测试；关键 View 再补 UI 自动化
- **禁止**：把只有真实窗口才能验证的行为（拖拽、焦点、输入法）塞进组件测试——交第 5 节

WPF 绑定失败是静默的（属性名拼错、`DataContext` 未设，界面只是空着）。布局前挂 `PresentationTraceSources` 监听，断言零 Error：

```csharp
public sealed class BindingErrorListener : TraceListener
{
    private readonly StringBuilder _errors = new();
    private readonly SourceLevels _original;

    public BindingErrorListener()
    {
        PresentationTraceSources.Refresh();
        var source = PresentationTraceSources.DataBindingSource;
        _original = source.Switch.Level;
        source.Switch.Level = SourceLevels.Error;   // Warning 噪音大，只收 Error
        source.Listeners.Add(this);
    }

    public bool HasErrors => _errors.Length > 0;
    public string Errors => _errors.ToString();
    public override void Write(string? message) => _errors.Append(message);
    public override void WriteLine(string? message) => _errors.AppendLine(message);

    protected override void Dispose(bool disposing)
    {
        var source = PresentationTraceSources.DataBindingSource;
        source.Listeners.Remove(this);
        source.Switch.Level = _original;
        base.Dispose(disposing);
    }
}
```

- **必须**：绑定冒烟测试放在 STA 宿主（`[WpfFact]`）里，`Measure` / `Arrange` / `UpdateLayout` 之后再断言——不布局，绑定不会被求值
- **应该**：用 `Border` / `ContentControl` 作根而不是 `Window`，无需 `Show()`，可在无交互桌面的 CI 上跑
- **禁止**：用 `Thread.Sleep` 等绑定"生效"——布局与绑定求值是同步的，等不到说明真有异步源，应显式等待那个源

```csharp
[WpfFact]
public void LoginView_WithViewModel_HasNoBindingErrors()
{
    using var listener = new BindingErrorListener();
    var view = new LoginView { DataContext = new LoginViewModel(Substitute.For<IAuthService>()) };
    var root = new Border { Child = view, Width = 1024, Height = 768 };

    root.Measure(new Size(1024, 768));
    root.Arrange(new Rect(0, 0, 1024, 768));
    root.UpdateLayout();

    Assert.False(listener.HasErrors, listener.Errors);
}
```

### 3.3 自定义控件：依赖属性与模板契约

- **必须**：自定义控件脱离业务数据测——依赖属性 + 模板是纯 UI 契约（联动 `06` 章第 9 节）
- **必须**：覆盖 DP 默认值、`CoerceValueCallback`、`PropertyChangedCallback`、继承属性（`Inherits`）
- **必须**：模板应用后校验全部 `PART_*` 部件存在（`FindName` 非空）；`ApplyTemplate()` 的返回值只表示本次是否新建了可视树，布局之后再调必为 `false`，**禁止**拿它当契约判据
- **必须**：视觉状态按名断言——`VisualStateManager.GoToState` 返回 `true`，且对应 `VisualStateGroup.CurrentState` 匹配
- **应该**：同时校验 `AutomationPeer` 的 `AutomationId` / `ControlType`（UI 自动化依赖它，联动 `14` 章）
- **禁止**：控件内部依赖外部单例 / 静态服务（不可测 + 难维护，联动 `03` 章）

```csharp
[WpfFact]
public void NumericBox_Template_ExposesRequiredParts()
{
    var box = new NumericBox();
    var root = new Border { Child = box, Width = 200, Height = 40 };
    root.Measure(new Size(200, 40));
    root.Arrange(new Rect(0, 0, 200, 40));

    Assert.NotNull(box.Template);
    Assert.NotNull(box.Template.FindName("PART_TextBox", box));
    Assert.NotNull(box.Template.FindName("PART_UpButton", box));
}
```

⚠️ 视觉状态组挂在**模板根**上，取组要用 `VisualStateManager.GetVisualStateGroups((FrameworkElement)box.Template.FindName("PART_Root", box))`；对控件本身调用 `GetVisualStateGroups(box)` 通常拿到空集合。

### 3.4 XAML 与资源（构建期）

- **必须**：XAML 编译（BAML）通过（构建期），**禁止**运行期才暴露 XAML 解析错误
- **必须**：资源字典合并验证——`App.xaml` 合并清单与资源键不冲突（联动 `02` 章第 2 节）
- **应该**：静态分析资源引用（`StaticResource` 找不到的 key 在构建期排查）
- **禁止**：测试依赖设计器生成代码（`InitializeComponent` 生成的字段仅由框架管理）

### 3.5 视觉回归（截图）

- **应该**：主题、密度、字体缩放这类视觉回归用截图对比（`RenderTargetBitmap`），阈值化比较，避免逐像素断言的抖动
- **必须**：截图测试固定渲染参数（96 DPI、`RenderOptions.ProcessRenderMode = RenderMode.SoftwareOnly`），**禁止**依赖机器显卡 / 缩放设置
- **禁止**：把截图对比当功能测试——它只证明"画面没变"，不证明"行为正确"

## 4. 集成层

不变量：连真实协作组件（数据库、HTTP、消息中间件），但不连生产资源；每个用例走完整数据链路。

- **必须**：集成测试验证真实协作（数据库、HTTP、消息中间件）
- **必须**：集成测试运行在可控环境（Testcontainers、本地实例、契约测试桩），**禁止**连生产资源
- **禁止**：把集成测试写成慢速 E2E（每个测试走完整链路）
- **应该**：集成测试使用专用测试配置（测试数据库、测试队列），与开发 / 生产隔离

WPF 侧只补一条：

- **应该**：WPF 集成测试重点验证 ViewModel ↔ 服务 ↔ 持久化链路，UI 层由自动化测试覆盖

## 5. UI 自动化层（E2E）

不变量：真实窗口 + 真实输入路径；只覆盖关键路径，失败要能靠截图与日志定位。

- **必须**：关键用户路径配 UI 自动化测试（登录、主流程、关键交互）
- **必须**：UI 测试框架团队统一（**FlaUI** / **White** 二选一），**禁止**混用
- **必须**：UI 测试元素定位用稳定标识（`AutomationId`，联动 `04` 章第 10 节、`14` 章），**禁止**按坐标 / 文本脆弱定位
- **应该**：UI 测试独立于单元测试运行（慢、脆），CI 单独阶段或独立任务
- **禁止**：UI 测试依赖真实网络 / 数据库（用桩 / 假服务，保持确定性）
- **必须**：UI 自动化需要**交互式桌面会话**——Session 0、锁屏、断开的 RDP 会话会找不到窗口；CI 用常登录的自托管 agent，或只在合并前触发
- **必须**：等待用显式条件（`WaitUntil` / 轮询重试），**禁止** `Thread.Sleep`
- **应该**：失败时留存截图 + 日志（TRX 一起归档），WPF 渲染问题看截图比看日志快十倍

```csharp
// FlaUI 示例：稳定定位 + 显式等待
using var app = Application.Launch("App.exe");
using var window = app.GetMainWindow(new UIA3Automation());
var loginBtn = window.FindFirstDescendant(cf => cf.ByAutomationId("LoginButton")).AsButton();
var wait = new WaitHelpers(window);
Assert.True(wait.WaitUntil(() => loginBtn.IsEnabled));
loginBtn.Click();
```

## 6. 跨层规范

### 6.1 测试数据与确定性

- **必须**：测试数据自包含（工厂 / 构建器），**禁止**依赖生产数据
- **必须**：测试确定性——固定输入 / 注入时钟，**禁止**随机性 / 时间依赖

### 6.2 覆盖率

- **应该**：覆盖率目标（行覆盖 ≥ 70%，关键路径 ≥ 80%），按模块而非总量考核
- **禁止**：把覆盖率当唯一标准——无断言覆盖是假质量
- **应该**：金额、安全、并发等高风险领域提高覆盖率要求
- **禁止**：为凑覆盖率写无效断言
- **应该**：覆盖率排除生成代码（`*.g.cs`、`App.xaml.cs`、设计器文件），否则数字虚高且噪声大

### 6.3 执行与 CI

- **必须**：测试框架与断言库团队统一（联动团队测试约定）
- **应该**：UI 测试在 CI 用独立任务（不拖慢单元测试主流程）
- **禁止**：测试对执行顺序有依赖（每个测试独立可重复）
- **必须**：单元测试项目整体保持秒级——UI 测试用 `[Trait("Category", "UI")]` 标记并按此过滤（VSTest 下 `dotnet test --filter "Category!=UI"`；xUnit v3 / MTP 的过滤语法不同，以所用 runner 文档为准）

## 7. 反模式速查

| 反模式 | 后果 | 正确做法 |
|---|---|---|
| 断言 XAML 结构 / 硬编码文案 | 重构即碎，挡不住真实缺陷 | 测 ViewModel 行为 + 绑定错误冒烟 |
| 用 UI 自动化代替单元测试 | 慢、脆、故障难定位 | 逻辑下沉 ViewModel，UI 自动化只覆盖关键路径 |
| `Thread.Sleep` / 固定延时 | 随机失败，CI 不稳定 | 显式等待（`WaitUntil` / `TaskCompletionSource`） |
| 依赖 `Application.Current` / 真实 `Dispatcher` | 无 Application 时 NRE | 注入调度接口，或 `[WpfFact]` |
| `.Result` / `.Wait()` 等异步 | 死锁（联动 `09` 章） | `await` |
| mock 被测类自身 | 测的是 mock 的假设，不是行为 | 只 mock 外部边界 |
| 每个测试各建一个 `Application` | AppDomain 单例冲突、资源查找错乱 | 集合级 fixture 共享一个 |
