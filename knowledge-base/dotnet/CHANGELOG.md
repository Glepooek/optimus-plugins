# Changelog — .NET 平台与运行时

本领域自 7.2.1 起使用**独立版本号**。7.2.0 及之前为知识库统一全局版本号时代，相关条目见下方「全局版本时代」，其版本号为当时的全局版本。

## [7.3.1] - 2026-11-14

### Fixed
- `reference/windows-dotnet-support-matrix.md`：依 Microsoft Learn 官方页修正——.NET 7 终止日 2024.05.14；STS 支持期 24 个月（.NET 7 及更早为 18 个月）；.NET 8/9 状态改「已终止」并补 .NET 11 行；Win10 21H2 / 22H2 不再写「最终版本（Ent/Edu 至 2028.10）/ 全版本支持」，改为官方仅列 LTSC/Enterprise；Win10 1607 LTSB 已于 2026.10.13 结束；Win11 26H1 不再写「预览」，补 26H1/26H2 行与日期口径说明；删除无官方出处的「4.8.1 为最终版本」
- `reference/wpf-cpu-architecture-support.md`：「.NET Framework 从未支持 ARM32」收窄为「WPF 从未支持 ARM32」（Windows RT/8.1 ARM 随系统提供过 4.5/4.5.1，不含 WPF）；「.NET 5.0.0~5.0.7 只能运行控制台/ASP.NET Core」改为「WPF 以 x86 模拟运行」；「.NET 7 起性能追平 x64」「推荐 .NET 8+」改为官方原文措辞并注明出处；补 .NET 11 行、.NET 8/9 已终止

## [7.3.0] - 2026-09-03

### Added
- 新增 `dotnet/reference/wpf-cpu-architecture-support.md`：WPF 与 .NET 的 CPU 架构（x86/x64/ARM32/ARM64）支持矩阵整理稿，覆盖 .NET Framework 4.8.1 与 .NET 5.0.8 两个 ARM64 支持起点、ARM32 从未支持的事实、ARM64 上 x86/x64 模拟运行的适用条件
- 索引新增条目 `dotnet.ref.wpf-cpu-architecture-support`

### Changed
- `reference/windows-dotnet-support-matrix.md` 头部补充与新 reference 的交叉引用，说明两份矩阵分别为 Windows 版本轴与 CPU 架构轴，维度互补
- 领域 `README.md` 阅读路径表新增「判断 WPF 能否在 ARM64 / x86 / x64 上原生运行」一行

## [7.2.1] - 2026-08-29

### Changed
- 领域元数据文件 `00-README.md` 改名为 `README.md`

---

## 全局版本时代（2026-08-22 .. 2026-08-29）

### 衍生自全局 1.11.0 - 2026-08-27

- 新增 `dotnet` 领域：收纳 .NET Framework、现代 .NET、Windows 兼容性与生命周期的描述性知识
- 新增 `dotnet/reference/windows-dotnet-support-matrix.md`：Windows 与 .NET Framework / .NET 5+ 支持矩阵整理稿
- 根知识库领域说明补充 `dotnet`、`csharp`、`wpf` 三者的职责边界
