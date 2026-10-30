# WPF 画像判定要点

> **口径声明**：本文件摘自 `optimus-frontend` 的 `wpf-code-review` skill，只保留 `project-analyze` 判定项目画像所需的要点。**判定口径以彼为准**，开展 WPF 代码审查请用 `wpf-code-review`，不要以本文代替。

本文件服务于「识别出这是 WPF 项目之后，如何描述它的结构与状态管理」。它是**描述性**的——用来读懂一个既有项目长什么样，不是审查清单。

## 1. 命名判定

用命名反推项目是否遵循 MVVM 约定，以及 View 与 ViewModel 的配对关系：

- View 命名 `{Name}View.xaml`（`LoginView.xaml`），ViewModel 命名 `{Name}ViewModel.cs`（`LoginViewModel.cs`），一一配对
- 资源 `x:Key` 用 PascalCase，不含空格与 `/`
- 控件命名（`x:Name`）用 PascalCase，UI 元素常以类型名做后缀（`LoginButton`、`UsernameTextBox`）
- 常见偏离信号（描述项目现状时如实记录，不判定为违规）：匈牙利命名 `btnLogin`、无意义缩写 `txt1`、`lblMsg`

**配对关系的判定方法**：按 `XxxView.xaml` 找同名 `XxxViewModel`；找不到则查看 `DataContext` 在何处赋值（code-behind、`DataTemplate`、DI 注册、设计时资源）。三者都没有时，该项目可能未采用 View/ViewModel 分离，报告中应如实写明。

## 2. MVVM 框架识别

从项目的基类与命令类型反查框架，这是判断「状态管理与命令机制」的核心依据：

| 框架 | 基类 / 命令 | 识别信号 | 常见适用 |
|---|---|---|---|
| **Prism** | `BindableBase` / `DelegateCommand` | 出现 `Prism.` 命名空间、`IRegionManager`、模块注册 | 大型多模块应用 |
| **CommunityToolkit.Mvvm** | `ObservableObject` / `RelayCommand` | 出现 `[ObservableProperty]` / `[RelayCommand]` 源生成器特性 | 中小型、追求简洁 |
| **原生 MVVM** | 自写 `INotifyPropertyChanged` + `ICommand` | 项目内有 `ViewModelBase` 之类的自建基类 | 极简应用 / 教学 |
| 其他（MVVMLight 等） | — | 社区库；描述时注明维护状态 | 存量项目 |

**判定方法**：先看 ViewModel 的基类全名，再看命令类型。两者不一致时（如基类来自 Prism 而命令用自带 `RelayCommand`），说明项目存在混用，报告中如实记录——混用会导致基类与命令混乱，属值得在概览中提示的结构风险。

**描述其他状态管理要素**：DI 容器注册位置与生命周期（`App.xaml.cs`、`Startup`、模块 `ConfigureServices`）、导航实现方式（Region 导航 / `Frame` / 自建 `NavigationService`）、对话框机制。

## 3. 控件库与交互库选型识别

从引用清单（`.csproj` 的 `PackageReference`、`packages.config`）识别，用于描述技术栈：

- **控件库**：MaterialDesignInXamlToolkit、MahApps.Metro、HandyControl、DevExpress、Telerik、原生只用系统控件
- **图标库**：MaterialDesignThemes 内置图标、MahApps 内置图标、Fluent Icons
- **交互库**：`Microsoft.Xaml.Behaviors.Wpf`（Behaviors / Interactivity 的通行选择）
- **版本管理方式**：`Directory.Packages.props`（中央包管理）或逐项目 `PackageReference`

描述时记录「引入了哪些、版本是否集中管理」，不评价选型好坏——选型评估属 `wpf-code-review` 的职责。

**值得在概览中提示的信号**：同一能力存在两套实现（两个日志库、两个对话框库、两个 MVVM 框架），或多套功能重叠的控件库并存。这类混用会影响后续维护，属事实性观察，不是审查结论。

