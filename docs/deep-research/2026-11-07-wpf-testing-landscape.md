# WPF 项目测试体系调研报告

- 日期：2026-11-07
- 范围：WPF 项目的单元测试、集成测试、UI 自动化、分层、工具链及周边事项；.NET Framework 4.x 与 .NET 6/8+ 两条技术栈
- 方法：deep-research 工作流，共 5 轮（每轮约 100 个 agent，多源检索 + 每条结论 3 票对抗核验）

## 0. 阅读须知（先看这里）

**本报告的证据基础偏薄。** 五轮调研后，经 3 票核验保留下来的结论只占原定范围的一部分，且多数集中在「工具许可/版本/目标框架」这类可由单一页面直接验证的事实上。**测试分层比例、UI 测试 CI 实践、遗留代码重构、内存与性能测试等核心实践类问题没有拿到经核验的结论**，见第 12 节「未获结果清单」。

使用规则：

1. 每条结论带置信度：**high** = 一手来源且 3 票一致；**medium** = 来源为博客/类推场景，或票数 2-1；**low** = 仅部分可采信。
2. 「推断」指由来源原文推出、但页面没明说的内容，已在条目中逐条标出，**不要当作引用事实**。
3. 版本号、日期、许可条款均为 2026-11-07 当日页面状态，有时效性。
4. 多数来源是博客，或针对 MAUI / WinUI / Avalonia / Web 场景，对 WPF 属类推；已在条目中注明。
5. 「被否决主张」（第 10 节）请勿采信。

---

## 1. 摘要

可由现有证据支撑的结论：

| 主题 | 结论 | 置信度 |
|---|---|---|
| STA 线程 | xUnit 测 WPF 控件必须借助 Xunit.StaFact 的 `[WpfFact]` / `[StaFact]`，普通 `[Fact]` 跑在 MTA 线程会抛 STA 异常 | high |
| 可测性设计 | ViewModel 与服务放进独立类库、用接口 + 构造函数注入；CommunityToolkit.Mvvm 的命令类不依赖 UI 框架 | high / medium（对 WPF 为类推） |
| 数据层测试 | 微软建议优先测真实数据库；需要替身时用 Repository 模式；EF Core InMemory provider 强烈不推荐 | high |
| UI 自动化 | FlaUI 是有证据支持的现行选择，TestStack.White 已弃用并指向 FlaUI，WinAppDriver 实质无人维护 | high（「首选」本身是观点） |
| Playwright | 只能经 CDP 测 WebView2 内容，不适用于原生 WPF 控件 | medium |
| 工具链 | MTP 支持 .NET Framework 4.6.2+；`dotnet test` 的原生 MTP 模式需 .NET 10 SDK；VSTest 与 MTP 项目不要混用 | high |
| 许可风险 | Fluent Assertions 8+ 商业使用要付费；Verify 对盈利组织收维护费；Moq 曾引入又移除 SponsorLink | high |
| CI | Session 0 隔离使服务进程无法呈现 UI（对 FlaUI 的影响为推断）；仅有一个已归档的微软 CI 示例 | high / 推断 |

**尚无证据的关键问题**：各层测试比例、UI 测试在 CI 上的推荐做法、遗留代码如何引入可测性——见第 12 节。

---

## 2. 测试分层

### 2.1 已核实：通用三层框架（medium）

- 底层单元测试：数量最多、快速、隔离。
- 中层集成测试：覆盖多组件协作（如控制器 + 数据库 + DI）。
- 顶层端到端测试：最慢最脆弱，只用于关键路径。
- 来源是 Web 应用课程讲义，**不是 WPF 场景**：https://courses.taltech.akaver.com/web-applications-with-csharp/lectures/testing

### 2.2 项目结构是可测性的前提（medium，对 WPF 为类推）

微软教程建议把 ViewModel 与服务放进独立的类库项目，再新增单元测试项目对其测试。教程针对 WinUI 3：https://learn.microsoft.com/is-is/windows/apps/tutorials/winui-mvvm-toolkit/intro

### 2.3 无结论

WPF 桌面场景下各层的合理比例、金字塔与奖杯模型的取舍：**无经核验的来源**（Fowler 实用测试金字塔页面已抓取，但无结论通过核验）。

---

## 3. 单元测试

### 3.1 STA 线程（high；.NET Framework 与 .NET 均适用）

- 普通 `[Fact]` 运行在 MTA 线程；WPF 控件在非 STA 线程实例化会抛 `The calling thread must be STA`。
- **Xunit.StaFact** 提供：
  - `[WpfFact]` / `[WpfTheory]`：STA + `DispatcherSynchronizationContext`，仅 Windows，`await` 后仍保持 Dispatcher 上下文；
  - `[StaFact]`：仅 STA，无同步上下文；
  - `[UIFact]`：跨平台私有上下文，仅 Windows 上为 STA。
  - 支持 xUnit v2 与 v3。
- 历史做法：2014 年 Haacked 的自定义 `STAFactAttribute`（已贡献至 xunit/samples），现应优先使用 StaFact。
- 来源：https://github.com/AArnott/Xunit.StaFact 、http://aarnott.github.io/Xunit.StaFact/docs/getting-started.html 、https://haacked.com/archive/2014/11/20/xunit-and-sta/

### 3.2 三大框架生命周期与并行差异（high）

| 方面 | xUnit | NUnit | MSTest |
|---|---|---|---|
| 并行默认 | 不同测试集合并行，同类内顺序 | 顺序 | 顺序 |
| 启用并行 | 默认开启 | 程序集级属性 | 程序集级属性 / runsettings |
| 每测试初始化 | 构造函数 / `Dispose` | `[SetUp]` / `[TearDown]` | `[TestInitialize]` / `[TestCleanup]` |
| 共享上下文 | `IClassFixture<T>` | — | — |

xUnit 每个测试新建类实例。来源是博客，但已对照三框架官方文档确认：https://qaskills.sh/blog/xunit-vs-nunit-vs-mstest-2026

> 推断（非来源原文）：涉及 WPF 全局状态（`Application.Current`、资源字典）的测试，应留意并行带来的干扰。

### 3.3 CommunityToolkit.Mvvm 与命令测试（high，对 WPF 为类推）

- 微软文档称其兼容 WinUI、WPF、.NET MAUI；`RelayCommand` / `AsyncRelayCommand` 让 ViewModel 与具体 UI 框架解耦，更易脱离 UI 做单元测试。
- `AsyncRelayCommand` 暴露 `IsRunning`、`Cancel`，默认禁止并发执行（可用 `AsyncRelayCommandOptions.AllowConcurrentExecutions` 改变），均可在 ViewModel 层断言。
- 测试异步命令时把属性声明为 `IAsyncRelayCommand`，即可 `await ExecuteAsync(...)` 返回的 Task。
- 微软页面分别针对 MAUI 与 WinUI；「无需调度器/STA 即可测试」是**推断**。
- 来源：https://learn.microsoft.com/en-us/dotnet/architecture/maui/mvvm-community-toolkit-features 、https://learn.microsoft.com/is-is/windows/apps/tutorials/winui-mvvm-toolkit/intro 、https://laurentkempe.com/2022/02/10/unit-testing-async-wpf-icommand/

命令的基本断言（medium）：对实现了 `CanExecute` 的命令直接断言 `CanExecute(null)` 的真假；若 `CanExecute` 读取参数则需给真实参数。来源为 2014 年博客（MVVM Light 示例，该库已不再维护）：https://pmichaels.net/2014/02/05/unit-testing-an-mvvm-relaycommand/

### 3.4 Prism（high，**内容已过时**）

- Prism 无专门测试工具，Model / ViewModel 与普通类一样用常规单测与 mock 框架。
- 文档技巧：`PropertyChangeTracker` 风格的辅助类测 `INotifyPropertyChanged`；`INotifyDataErrorInfo` 测有效/无效/边界值，校验 `ErrorsChanged` 与 `HasErrors`。这些辅助类是示例，不是 Prism 随库提供的 API。
- 局限：来源是 Prism 5/6（2014，.NET Framework 时代），**未覆盖当前 Prism 8/9**。
- 来源：https://prismlibrary.github.io/docs/wpf/legacy/Advanced-MVVM.html 、https://learn.microsoft.com/zh-cn/previous-versions/msp-n-p/gg405494(v=pandp.40)

### 3.5 ReactiveUI（low，仅供参考）

- `ReactiveUI.Testing` 的 `TestScheduler` 用于控制时间；但被引示例未把调度器注入 ViewModel 或 `RxApp`，可能并未真正控制命令调度。
- ReactiveUI 检测到单元测试运行器时会把 `RxApp` 切换为即时调度器，示例可能侥幸通过；使用时应显式注入调度器。
- 来源是 Avalonia 书籍而非 WPF：https://wieslawsoltes.github.io/AvaloniaBook/Chapters/Chapter11.html

### 3.6 IValueConverter（high，但**无「可直接单测」的一手陈述**）

- 微软 API 页：创建实现 `IValueConverter` 的类并实现 `Convert` / `ConvertBack`，签名均为 `(Object, Type, Object, CultureInfo)`，仅描述为 "Converts a value."，无参数级描述与示例（页面更新于 2026-05-27）。
- WPF 数据绑定概述页以 `ColorBrushConverter`（带 `[ValueConversion]`）展示转换器为**普通 public 类**。
- **两页都没有说转换器可脱离 UI 直接实例化并调用 `Convert` 做单测**。「可直接单测」是通用 C# 推理，非来源原文。
- 来源：https://learn.microsoft.com/en-us/dotnet/api/system.windows.data.ivalueconverter 、https://learn.microsoft.com/en-us/dotnet/desktop/wpf/data/data-binding-overview

---

## 4. Mock 与断言库

### 4.1 现状总表

| 库 | 许可 / 商业条款 | 目标框架 | 适用栈 | 置信度 |
|---|---|---|---|---|
| Moq | 4.20.0 引入 SponsorLink，4.20.2 移除（见 4.2） | — | 两者 | high |
| NSubstitute 6.2.0 | BSD-3-Clause；NuGet 页无商业/赞助要求 | `netstandard2.0`、`net8.0`；net461–net481 仅为 NuGet *computed* 兼容 | .NET Framework 4.6.1+（**推断**）与 .NET 8 | high |
| FakeItEasy 9.0.1（2026-01-24） | MIT；NuGet 与 GitHub 均无商业/赞助要求 | `net462`、`net8.0`、`net10.0`；**无** `netstandard2.0` / `net6.0`（由清单推断） | .NET Framework 4.6.2+ 与 .NET 8 | high |
| Fluent Assertions | **v8 及以上**仅对开源/非商业免费，商业使用需向 Xceed 购买许可；v7 保持开源并继续修复 bug（v7 许可证类型页面未写，Apache-2.0 **未确认**） | — | 两者 | high |
| Shouldly 4.3.0 | BSD-3-Clause；仓库页无商业声明，仅有 Sponsor 按钮；5.0.0 仅有预览版 | `net8.0`、`net9.0`、`netstandard2.0`；.NET Framework 4.x 经 `netstandard2.0` 使用，依赖 `Microsoft.CSharp` | 两者 | high |

补充说明：
- NSubstitute 的许可类型依据 NuGet 页；其 GitHub 页只给出 LICENSE.txt 文件名，未写类型、目标框架或最新版本。依赖 Castle.Core ≥ 5.1.1。
- FakeItEasy 依赖 Castle.Core ≥ 5.2.1。

### 4.2 Moq SponsorLink 时间线（high）

- **v4.20.0**（8 Aug）引入，发布说明 "Add 💜 SponsorLink support"（PR #1363）；**v4.20.2**（9 Aug）移除，说明 "Remove SponsorLink since it breaks MacOS restore"（PR #1375）；v4.20.69 的说明也列出该移除。
- Moq 仓库 README 本身**不提** SponsorLink，证据在 releases 页（README 静默一项为 2-1 票）；发布日期页面无年份。
- 来源：https://github.com/moq/moq/releases 、https://github.com/devlooped/moq

来源汇总：
- https://fluentassertions.com/
- https://www.nuget.org/packages/NSubstitute 、https://github.com/nsubstitute/NSubstitute
- https://www.nuget.org/packages/FakeItEasy 、https://github.com/FakeItEasy/FakeItEasy
- https://www.nuget.org/packages/shouldly/ 、https://github.com/shouldly/shouldly

---

## 5. 集成测试

### 5.1 EF Core 数据层（high；适用 EF Core 3+/.NET 8，EF6 未覆盖）

- 微软建议数据层测试尽量针对**真实生产数据库**。
- 需要测试替身时，优先 **Repository 模式**，而非伪造 EF Core provider 或 mock `DbSet`（该模式本身有显著实现与维护成本）。
- Repository 不可行时，SQLite 内存库是退路，但与 SQL Server 行为不等价（大小写敏感性不同；`EF.Functions.DateDiffDay` 等提供程序专有函数会失败）。
- EF Core InMemory provider **强烈不推荐**，仅供遗留应用：无事务、无原生 SQL、支持的查询类型比 SQLite 少、更慢。
- Testcontainers：无存活结论。
- 来源：https://learn.microsoft.com/en-us/ef/core/testing/choosing-a-testing-strategy （更新于 2026-06-26）

### 5.2 DI 与 Generic Host（high，范围窄）

- 硬编码依赖使类难以单测，因为无法替换为 mock/stub；解法是接口 + 构造函数注入。
- WPF 默认没有 Generic Host 集成，需手动引入 `Microsoft.Extensions.Hosting` 并在 `App` 的 Startup/Exit 中构建宿主；示例目标为 net10.0-windows，**.NET Framework 4.x 未覆盖**。
- 来源：https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection 、https://learn.microsoft.com/en-us/dotnet/desktop/wpf/app-development/how-to-use-host-builder

### 5.3 System.IO.Abstractions（high）

- 提供可注入的 `IFileSystem` / `FileSystem`，镜像 `System.IO`，便于测试中替换文件访问。
- `MockFileSystem` / `MockFileData` 在独立包 `TestableIO.System.IO.Abstractions.TestingHelpers` 中，并非真实文件系统的完整副本（`FileSystemWatcher` 与多盘符较弱）。
- 项目处于维护模式，新开发在同一维护者的 Testably.Abstractions。
- 进程交互的抽象与目标框架未确认。
- 来源：https://github.com/TestableIO/System.IO.Abstractions

---

## 6. UI 自动化

### 6.1 工具现状总表

| 工具 | 现状 | 置信度 | 来源 |
|---|---|---|---|
| FlaUI | MIT；封装微软 UIA；覆盖 Win32/WinForms/WPF/Store；v5.0.0 发布于 2025-02；自身无测试框架，需搭配 xUnit/NUnit/MSTest | high | https://github.com/FlaUI/FlaUI |
| TestStack.White | 标 "DEPRECATED - no longer actively maintained"，但**未归档**；README 指名 FlaUI 为继任者（FlaUI 是从零重写，支持 UIA2/UIA3） | high | https://github.com/TestStack/White |
| WinAppDriver | 支持 UWP/WinForms/WPF/Win32（Windows 10，需开发者模式），但实质无人维护：最后发布 v1.2.1（2020-11），最后 push 2025-04，仓库未归档，约 1.1k open issues | high | https://github.com/microsoft/WinAppDriver |
| Appium Windows Driver | README 标注**已弃用**：WinAppDriver 只讲旧版 JSONWP，不兼容 Appium 4+；v5.0.0+ 仅适用于 Appium 3；指定 **Appium WinCore Driver** 为官方继任者，并推荐 **NovaWindows Driver**（Automate The Planet）作替代 | high | https://github.com/appium/appium-windows-driver |
| Playwright .NET | 只能测 WebView2 内容（见 6.3） | medium | https://playwright.dev/dotnet/docs/webview2 |

说明：
- WinAppDriver 的发布日期来自核验者的 GitHub API 检查，非页面抓取。
- 「FlaUI 首选 / 仍在维护」是咨询公司博客的观点（2-1 票）：https://comcomponent.com/en/blog/windows-desktop-ui-automation-testing/

### 6.2 FlaUI 后端与目标框架

- **UIA2**：托管封装，对 WPF 支持差，缺少触控等新特性。
- **UIA3**：基于 COM，对 WPF / Store 良好；README 提到对 WinForms 可能有 UIA2 没有的 bug。
- **目标框架（high）**：FlaUI.Core 与 FlaUI.UIA3 5.0.0 只提供 `net48`、`net6.0-windows7.0`、`net8.0-windows7.0`，**无 netstandard**。net48 与 net8.0-windows 项目都能引用；低于 4.8 的 Framework 项目（如 net472）无法通过 NuGet 还原——此「无 netstandard / 低于 4.8 不可用」为**推断**（2-1 票）。
- 来源：https://www.nuget.org/packages/FlaUI.UIA3 、https://www.nuget.org/packages/FlaUI.Core

### 6.3 Playwright 与 WPF（medium）

- 通过 `BrowserType.ConnectOverCDPAsync` 经 Chrome DevTools Protocol 连接，而不是 UI Automation，因此不适用于原生 WPF 控件（后半句是**推断**，官方页面未明说）。
- 前提：WebView2 需带远程调试端口启动——设环境变量 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222`，或通过 `CoreWebView2EnvironmentOptions.AdditionalBrowserArguments` 传入；然后连 `http://localhost:9222`，取 `Contexts[0].Pages[0]`。

---

## 7. 测试工具链与框架版本

### 7.1 VSTest 与 Microsoft Testing Platform（MTP）（high）

| 事项 | 结论 | 适用 |
|---|---|---|
| 混用 | 微软明确：不要在同一解决方案或运行配置中混用 VSTest 与 MTP 项目；依赖 VSTest 的非 .NET 测试（C++/JS）应单独配置 | 两者 |
| 默认模式 | `dotnet test` 默认仍是 VSTest；运行器选择自 **.NET 10 SDK** 起可用，更早 SDK 一律 VSTest；MTP 模式需 .NET 10 SDK 与 MTP 1.7+ | SDK 侧 |
| 运行时支持 | MTP 支持 .NET 8+ 与 **.NET Framework 4.6.2+**，面向 NETStandard 2.0；直接嵌入测试项目，运行不需要 vstest.console 或 `dotnet test` | 两者 |
| 框架支持 | TUnit 只基于 MTP；MSTest、NUnit 通过各自 runner 支持；xUnit v2/v3 在 xunit.net 有 MTP 文档 | 两者 |

来源：
- https://learn.microsoft.com/en-us/dotnet/core/testing/test-platforms-overview
- https://learn.microsoft.com/en-us/dotnet/core/testing/microsoft-testing-platform-intro
- https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test 、https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test-mtp

### 7.2 框架版本

| 框架 | 结论 | 置信度 | 来源 |
|---|---|---|---|
| MSTest v4 | 取消对 .NET Core 3.1–.NET 7 的支持；现代 .NET 最低 .NET 8；**.NET Framework 最低仍为 4.6.2**；`MSTest.Sdk` 默认 MTP，v4 在 MTP 下不再添加 `Microsoft.NET.Test.Sdk`，需 vstest.console 时要手动引用；`UseVSTest=true` 时改用 VSTest | high | https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-mstest-migration-v3-v4 |
| xUnit v3 | 要求 **.NET Framework 4.7.2 或更高**（官方仅支持 Windows）；现代 .NET 最低 `net8.0`（"as of the writing"，有时效性）。MTP 支持**内置**，VSTest 经独立的 `xunit.runner.visualstudio`；`dotnet test` 默认仍走 VSTest；SDK 8/9 需设 `TestingPlatformDotnetTestSupport=true`，SDK 10+ 用 `global.json` 设 test runner 为 `Microsoft.Testing.Platform`。What's New 页较早，把 MTP 描述为可选替代体验 | high | https://xunit.net/docs/getting-started/v3/getting-started 、https://xunit.net/docs/getting-started/v3/microsoft-testing-platform 、https://xunit.net/docs/getting-started/v3/whats-new |
| Microsoft.NET.Test.Sdk 18.11.0 | NuGet 兼容 `net462`、`net8.0`、`netcoreapp2.0`、`netstandard2.0`；README 称任何 .NET 测试项目与 VS Test Platform 集成都需要它，搭配适配器后可经 `dotnet test` 或 Test Explorer 运行 | high | https://www.nuget.org/packages/Microsoft.NET.Test.SDK |

> 对 WPF 老项目的含义（由上述事实推出）：仍停留在 net462–4.7.1 的项目升级到 xUnit v3 前需先升到 4.7.2+。

### 7.3 旧式 csproj / packages.config 与 `dotnet test`（**官方文档未明文限制**）

所抓取的微软 `dotnet test` 页面**均未陈述**其对旧式（非 SDK-style）csproj、packages.config 的支持情况；SDK-style 只是在示例项目中被隐含，不是明文要求。

| 页面 | 实际陈述 |
|---|---|
| `dotnet-test` | 构建解决方案并用 VSTest 或 MTP 运行；适用 .NET 6 SDK 及以后；对项目类型、`Microsoft.NET.Test.Sdk`、.NET Framework 目标只字未提 |
| `dotnet-test-vstest` | `dotnet test` 最初为 VSTest 项目设计；示例是 SDK-style `net8.0` 项目，引用 `Microsoft.NET.Test.Sdk`、`xunit`、`xunit.runner.visualstudio`；未说 `Microsoft.NET.Test.Sdk` 是必需的 |
| NUnit 文档（medium，自述含较旧内容） | 「新式 CSPROJ 格式」的测试项目（.NET Core 或 .NET 4.x）需 `PackageReference` 到 `Microsoft.NET.Test.Sdk`；测试程序集须为 .NET Core 或 .NET 4.x，不能是 .NET Standard；未描述旧式 csproj / packages.config |
| MSTest.Sdk 博客（medium，2024-04） | 支持 MSTest 支持的任何目标框架（net462 及以上）；微软成员评论确认 net472 可用「只要是 SDK-style 项目」；旧式 csproj 未覆盖（由 MSBuild 项目 SDK 需 SDK-style 语法**推断**）；当前 Learn 文档未再确认 net462 下限，且 MSTest.Sdk 现默认 MTP |

**已有明文依据的运行途径：`vstest.console.exe`**
- 用法 `vstest.console.exe [TestFileNames] [Options]`，对象是已构建的测试容器（如 `myTestProject.dll`），按示例看不依赖 csproj 格式（页面从未提 SDK-style / packages.config / csproj，此为读示例所得）。
- `/Framework` 接受 `net48`、`net6.0`、`net10.0`、`.NETFramework,Version=v4.8` 等，默认从 `TargetFrameworkAttribute` 自动检测，缺失时默认 `Framework40`。页面更新于 2026-10-08。

小结：「`dotnet test` 不能运行旧式 csproj」**没有明文依据**，仅为推断；稳妥路径是 `vstest.console.exe` / VS Test Explorer，或先迁移到 SDK-style。

来源：
- https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test-vstest
- https://docs.nunit.org/articles/nunit/getting-started/dotnet-core-and-dotnet-standard.html
- https://devblogs.microsoft.com/dotnet/introducing-mstest-sdk/
- https://learn.microsoft.com/en-us/visualstudio/test/vstest-console-options

---

## 8. 代码覆盖率

| 工具 | 结论 | 适用 | 置信度 |
|---|---|---|---|
| coverlet.collector | VSTest 数据收集器：`dotnet test --collect:"XPlat Code Coverage"`，输出 `coverage.cobertura.xml` 到 `TestResults`。收集器自 8.0.0 起支持 .NET Framework 4.7.2+（来自 VSTest 集成文档，未单独投票） | VSTest | high |
| coverlet.msbuild | `dotnet test /p:CollectCoverage=true`，输出 `coverage.json` 到测试项目根目录 | VSTest | high |
| 共同约束 | **不要在同一测试项目同时安装 collector 与 msbuild**（README 原文）；可用于 Windows 上的 .NET Framework，但 README 称仅支持 **SDK-style 项目**（「旧式 csproj 需转换」为推断，2-1）；两个包均**不支持 MTP** | — | high / medium |
| coverlet.MTP | collector 在 MTP 上的原生扩展，`dotnet test --coverlet` 启用；支持 json/lcov/opencover/cobertura/teamcity，默认生成 `coverage.json`；自 **8.0.0** 起只列 .NET ≥ 8 运行时，要求 .NET 8 SDK+ 与 MTP 2.0.0+；文档未提及 .NET Framework，**不能当作 net48 WPF 测试项目方案**（「文档没写」≠「已证实不支持」） | MTP / .NET 8+ | high |
| Microsoft.Testing.Extensions.CodeCoverage | 为 MTP 提供 Microsoft Code Coverage，托管/非托管代码、静态/动态插桩，默认关闭；`--coverage-output-format` 支持 `coverage`/`xml`/`cobertura`（默认 `coverage`）；`dotnet test -- --coverage --coverage-output-format cobertura`。该页**未说明适用目标框架**，不能断言 net48 支持 | MTP | high |
| xUnit v3 + MTP 模式 | 官方明言「标准 Coverlet 体验不受支持」，需用 MTP 覆盖率指南（不排除 coverlet.MTP 可用） | MTP | medium |
| ReportGenerator | 可转换 coverlet、OpenCover、dotCover、Visual Studio、NCover、Cobertura、JaCoCo、Clover、gcov、lcov 报告；主包支持 **.NET Framework 4.7** 与 .NET Core 8.0+；**全局工具仅支持 .NET Core 8.0+**（无法在只有 .NET Framework 的机器上运行，由支持表推断） | 两者 | high |

来源：
- https://github.com/coverlet-coverage/coverlet
- https://github.com/coverlet-coverage/coverlet/blob/master/Documentation/Coverlet.MTP.Integration.md
- https://learn.microsoft.com/en-us/dotnet/core/testing/microsoft-testing-platform-extensions-code-coverage
- https://github.com/danielpalme/ReportGenerator
- https://xunit.net/docs/getting-started/v3/microsoft-testing-platform

> 「Cobertura 输出可交 ReportGenerator 处理」是推断：Microsoft 覆盖率页未提及 ReportGenerator。

---

## 9. 快照 / 视觉回归：Verify（high）

- 支持 net462 / net472 / net48 / net481 与 net6/8/9/10，要求 SDK 9.0.301+。
- 快照存为 `.verified`，不一致时生成 `.received`；`.received` 应进 `.gitignore`，`.verified` 应提交入库。
- README 列出 `Verify.Xaml`（验证 Xaml UI）和多个图像插件（ImageHash、ImageSharp.Compare、ImageMagick、ImageSharp、Phash），但**全文未提及 WPF**，不能据此断言 `Verify.Xaml` 支持 WPF。
- **费用提醒**：对盈利组织与政府机构征收开源维护费，适用于 2026-09-01 之后发布的版本，按员工数分档（<40 人 $5/月，40–200 人 $20，200–1000 人 $30，1000 人以上 $100）；v33 起构建时检查赞助状态；README 称 nothing phones home。
- 来源：https://github.com/VerifyTests/Verify

---

## 10. CI/CD 与被否决主张

### 10.1 CI 已核实的内容

**（a）微软桌面应用 CI 示例（high，范围很窄）**
`github-actions-for-desktop-apps`（2024-05 已归档只读，基于 .NET Core 3.x，**不涉及 .NET Framework 4.x**）展示 `windows-latest` 上的 `ci.yml`：x86/x64 矩阵；`microsoft/setup-msbuild` 用 MSBuild 构建；对测试项目运行 `dotnet test`；上传 MSIX 工件。其 action 版本已过时（.NET Core 3.1、setup-msbuild v1.0.0、upload-artifact@v1），不是当前最佳实践，也未涉及需要交互式桌面的 UI 自动化。来源：https://github.com/microsoft/github-actions-for-desktop-apps

**（b）Session 0 隔离（high；应用于 FlaUI 为推断）**
自 Windows Vista 起服务无法直接与用户交互，新代码不应使用交互式服务技术；所有服务运行在 Terminal Services Session 0，其 UI 仅对连接到 Session 0 的用户可见。`NoInteractiveServices` 注册表值在现代 Windows 默认 1（禁止交互式服务），在 XP/2003/7/2008 R2 默认 0；这是强默认而非绝对不可能。OS 层限制，对 .NET Framework 4.x 与 .NET 8 同样成立。**「以服务方式运行的 runner 无法驱动 FlaUI」是推断，没有来源针对 FlaUI 明确陈述。** 来源：https://learn.microsoft.com/en-us/windows/win32/services/interactive-services （更新于 2025-04-15）

**（c）GitHub 自托管 runner 文档（high，仅陈述文档覆盖范围）**
Windows 上服务配置是 runner 配置脚本的一部分，目的是随机器自动启动，脚本会询问是否安装为服务。文档**没说**服务用哪个账户、是否有交互式桌面，所以不能支撑「服务模式可跑 UI 测试」。企业版入门页补充：安装为服务需管理员 shell，建议目录 `C:\actions-runner`。Jenkins using-agents 页**不涉及** Session 0、交互式桌面、UI 测试或 Windows 服务安装。来源：
- https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/configuring-the-self-hosted-runner-application-as-a-service
- https://docs.github.com/en/enterprise-cloud@latest/admin/managing-github-actions-for-your-enterprise/getting-started-with-github-actions-for-your-enterprise/getting-started-with-self-hosted-runners-for-your-enterprise
- https://www.jenkins.io/doc/book/using/using-agents/

**（d）托管 vs 自托管（high；博客，作者建议非技术要求）**
GitHub 托管 runner 是临时的（每个 job 后重装磁盘）；自托管 runner 默认非临时，需自备清理策略。博客建议 Windows 与 macOS 负载用托管 runner，自托管仅用于特定场景（GHES、合规、定制硬件）。文章为 2025-04 博客，不是文档页。来源：https://github.blog/enterprise-software/ci-cd/when-to-choose-github-hosted-runners-or-self-hosted-runners-with-github-actions/

### 10.2 被否决的主张（勿采信）

| 主张 | 票数 | 来源 |
|---|---|---|
| WPF 命令测试的核心难点是 `async void`，测试无法 await | 1-2 | laurentkempe.com |
| RelayCommand 应调用 `Execute(null)` 测试 | 0-3 | pmichaels.net |
| ReactiveCommand 的 `IsExecuting` / `ThrownExceptions` 相关说法 | 0-3 | Avalonia 书籍 |
| Prism 推荐用 `InteractionRequest<T>` 或注入的交互服务替代 `MessageBox` | 0-3 | Prism 旧文档 |
| 异步服务调用：捕获回调后手动触发（微软存档页措辞） | 1-2 | 微软存档页 |
| 桌面应用须手动集成 Generic Host 生命周期 | 1-2 | MS Learn DI 页 |
| 测试可绕过组合根直接构建 `ServiceCollection` | 0-3 | MS Learn 主机页 |
| NUnit：`Microsoft.NET.Test.Sdk` 17.8.0+ 配适配器才能启用 `dotnet test` | 1-2 | NUnit 文档 |

> 上一版报告曾把「WinAppDriver 已停滞」列为被否决；第二轮用一手来源（WinAppDriver 与 appium-windows-driver 的 README）重新核实并**通过**，已并入 6.1。

---

## 11. 调研质量说明

**本轮调研的整体质量偏低，原因如下，使用结论时请相应折扣：**

1. **核验保留率低**：第一轮约 9 条、其后各轮 6–13 条通过核验；核心实践类问题（第 12.1 节）五轮均无结论。
2. **检索能力受限**：多个核验 agent 的 WebSearch 不可用，部分只靠单一一手来源确认，没有交叉搜索反例；GitHub 页面的 WebFetch 有时失败，改用 raw README / API 读取。
3. **主张写得过宽被否决**：第一至三轮检索结果中大量综合性主张在 3 票核验中被否决（见第 10.2 节），第四、五轮改为「指定页面 + 窄主张」后通过率明显提高，但覆盖面也随之收窄为「版本 / 许可 / 目标框架」类事实。
4. **来源质量**：多数来源是博客，或针对 MAUI / WinUI / Avalonia / Web 场景，对 WPF 属类推；Prism 与 MVVM Light 相关文章为 2014 年前后；ReactiveUI 来源非 WPF。
5. **时效性**：版本号、日期、许可条款（Fluent Assertions、Verify、Shouldly、NSubstitute、FakeItEasy、WinAppDriver、System.IO.Abstractions 维护状态等）均为 2026-11-07 状态。
6. **适用栈标注不均**：部分来源页面未区分 .NET Framework 4.x 与 .NET 8，正文已尽量标出；标不出的以「两者」或「未说明」表示。

---

## 12. 未获结果清单（放在最后，便于后续补查）

五轮调研后，以下内容**没有经 3 票核验的结论**。分两类：**甲类**＝已抓取指定页面，但页面本身没有陈述或没有结论通过核验；**乙类**＝没有拿到一手来源。后续补查可优先处理标 ★ 的项（对 WPF 测试方案决策影响最大）。

### 12.1 核心实践类（原调研目标，完全空白）

| # | 内容 | 类别 | 说明 |
|---|---|---|---|
| ★1 | **WPF 场景下测试金字塔 / 奖杯各层比例与边界** | 甲类 | Fowler《实用测试金字塔》与 TestPyramid 页面已抓取，无结论通过核验；报告仅有第 2.1 节的通用三层框架（Web 场景） |
| ★2 | **UI 自动化测试在 CI 上的推荐做法**（自动登录的交互式自托管 runner、Jenkins agent 以服务运行 vs 交互式启动） | 乙类 | 第 10.1 节只有 Session 0 隔离的 OS 事实与 GitHub 文档的「未说明」；**没有一手来源给出推荐做法**，「服务模式 runner 无法驱动 FlaUI」仅为推断 |
| ★3 | **GitHub 托管 runner 是否提供交互式桌面** | 甲类 | 指定的 using-github-hosted-runners 文档页无结论通过核验 |
| ★4 | **遗留 WPF 代码引入可测性的重构手法**：Seam、Humble Object、Characterization Test、MVP/MVVM 迁移 | 甲类 | Fowler Humble Object 页、Feathers 的 Characterization Test / Seam 一手说明均无结论通过核验 |
| ★5 | **内存泄漏与性能测试**：`WeakReference` + `GC.Collect` 断言模式、dotMemory Unit、BenchmarkDotNet 对 .NET Framework 与 WPF 的支持、WPF 弱事件模式 | 甲类 | 指定的 dotMemory Unit、BenchmarkDotNet、`weak-event-patterns` 页面均无结论通过核验 |
| 6 | **Verify 在 WPF 中的具体做法**（渲染为位图、XAML 序列化）；`Verify.Xaml` 是否支持 WPF | 甲类 | README 全文未提及 WPF（第 9 节） |
| 7 | 测试数据管理、Dispatcher / UI 线程性能测试 | 乙类 | 原调研清单中的子项，未检索到可核验来源 |

### 12.2 工具链与兼容性类

| # | 内容 | 类别 | 说明 |
|---|---|---|---|
| 8 | **`dotnet test` 对旧式 csproj / packages.config 的官方限制** | 甲类 | 微软 `dotnet test` 页面均未陈述（第 7.3 节）；「不能运行」仅为推断 |
| 9 | NuGet「packages.config 迁移到 PackageReference」页；xUnit / MSTest 适配器在 packages.config 项目中的说明 | 甲类 | 页面已指定抓取，无结论通过核验 |
| 10 | `IValueConverter` 可脱离 UI 直接实例化并单测的一手陈述 | 甲类 | 微软两页仅有签名与示例类（第 3.6 节） |
| 11 | NSubstitute 官网 / release notes 对 net462 支持的显式确认 | 甲类 | 目前仅为 NuGet computed 兼容的推断 |
| 12 | coverlet.collector 对 .NET Framework 的版本细节；Microsoft CodeCoverage 扩展对 net48 的支持；coverlet.MTP 对 .NET Framework 是否「已证实不支持」 | 甲类 | 文档未写目标框架，只能说「未覆盖」 |
| 13 | EF6（.NET Framework）的测试策略；Testcontainers；进程交互的抽象；Generic Host 在 .NET Framework 4.x 的用法 | 乙类 | 第 5 节仅覆盖 EF Core 3+/.NET 8 与 net10.0-windows 示例 |
| 14 | 当前 Prism 8/9 的测试影响；ReactiveUI 在 WPF 上的测试实践 | 乙类 | Prism 来源为 5/6 时代旧文档；ReactiveUI 来源是 Avalonia 书籍且部分主张被否决 |
| 15 | FlaUI 的当前维护活跃度、UIA2 / UIA3 在 net48 与 net8 上的实测差异；Appium WinCore / NovaWindows Driver 的细节 | 乙类 | 「首选」「仍在维护」只有博客观点；两个继任驱动仅有 README 中的推荐语 |

### 12.3 仅为推断、需另找一手来源验证的陈述

以下已写入正文，但**页面原文并未明说**，引用时请勿当作事实：

1. 「无需调度器 / STA 即可测试 CommunityToolkit.Mvvm 命令」（第 3.3 节）
2. 「涉及 WPF 全局状态的测试需留意并行干扰」（第 3.2 节）
3. 「NSubstitute 可在 .NET Framework 4.6.1+ 使用」「FakeItEasy 无 netstandard2.0 / net6.0」（第 4.1 节）
4. 「FlaUI 低于 4.8 的 Framework 项目无法使用」（第 6.2 节，2-1 票）
5. 「Playwright 不适用于原生 WPF 控件」（第 6.3 节，官方页面未明说）
6. 「旧式 csproj 需转换才能用 coverlet」「`dotnet test` 不能运行旧式 csproj」（第 7.3、8 节）
7. 「Cobertura 输出可交 ReportGenerator 处理」「ReportGenerator 全局工具无法在仅有 .NET Framework 的机器上运行」（第 8 节）
8. 「以服务方式运行的 runner 无法驱动 FlaUI」（第 10.1 节）
9. 「`IValueConverter` 可直接单测」（第 3.6 节）

---
