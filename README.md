# appharbor-repacked

> **⚠️ 免责声明 — 请先读**
>
> 本仓库是**非官方**重打包产物，与上游作者无任何关联；产物用于替换**系统应用商店**
> `com.xiaomi.market`（HyperOS 的 MIUISuperMarket）。替换系统应用可能导致**商店无法打开、
> 依赖商店的系统功能异常、开机循环（bootloop）、OTA 失败、数据丢失、必须线刷恢复**。
> 一切后果由使用者自行承担，本仓库不提供任何担保与技术支持。
> 请仅在**你本人拥有、且具备救砖能力**的设备上使用。完整条款见 [免责声明](#免责声明)。

把 [BeiChen-CN/AppHarbor](https://github.com/BeiChen-CN/AppHarbor) 重新打包成 **`com.xiaomi.market`**
（HyperOS 的 MIUISuperMarket）身份。每天检查上游 release，有新版本就自动重打包、签名、发 Release。

仓库只负责产出可装的 APK，**不碰你的设备**：没有 adb 自动化、没有定时安装、不需要 token。

## 产物

<https://github.com/FairyJJ/appharbor-repacked/releases>

```
appharbor-<upstream-tag>-repacked.apk
SHA256SUMS.txt
```

取用：

```sh
./scripts/download-latest.sh              # 下到 ./dist
adb install -r -t ./dist/appharbor-*-repacked.apk
```

## 替换映射

| | |
|---|---|
| 上游 | `BeiChen-CN/AppHarbor`（含 prerelease） |
| 原始包名 | `com.app.market` |
| 目标包名 | `com.xiaomi.market` |
| versionCode | 钉死 **99999999** |
| 类目录 | **搬**（`--move-classes`） |
| Compose 资源 | **改名**（`--rename-assets`） |

## 为什么 versionCode 钉死 99999999

`PackageManagerService` 开机扫描系统包时，若 `/data/app` 里该包 versionCode **小于**系统分区上的版本，
判定为「系统应用已升级、data 版是旧残留」，直接删掉 data 版 → 退回原版。

所以「不装模块、纯覆盖安装」要长期有效，data 版 versionCode 必须 **大于** 系统原版。

代价：应用内「检查更新」永远认为已是最新，升级只能从本仓库 Release 手动拉包覆盖安装。

## 工作流

`.github/workflows/build.yml`

- 触发：每天 03:00 UTC（11:00 CST）+ 手动 `workflow_dispatch`（勾 `force` 可强制重建）
- 解析上游最新 release（**包含 prerelease**）
- 若 `appharbor-<tag>` 这个 Release 已存在 → 跳过，不浪费构建时间
- 否则下载 APK → `scripts/repack.py` → 发布 Release + 上传 artifact

## 坑（脚本里已处理）

1. **apktool 的 build 缓存**：改完 `apktool.yml` 的 `versionInfo.versionCode` 直接 `b`，
   apktool 打印 `AndroidManifest.xml and resources have not changed` 且**不写入**新 versionCode。
   必须先 `rm -rf src/build`，脚本会强制清理并在构建后校验。
2. **Compose Multiplatform 资源路径**：`assets/composeResources/<pkg>.resources` 是按包名生成的目录，
   只改 smali 字符串不改目录名 → 启动即 `Missing resource with path` 崩溃。这里必须 `--rename-assets`。
3. **类目录要跟着搬**：`smali/com/app/market` → `smali/com/xiaomi/market`，否则 `ClassNotFoundException`。
4. **签名固定**：uber-apk-signer 内置 debug key，每次构建签名一致，覆盖安装不冲突。

## 手动构建（本地）

```sh
curl -fsSL -o apktool.jar https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar
curl -fsSL -o uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar

APKTOOL_JAR=./apktool.jar SIGNER_JAR=./uber-apk-signer.jar \
python3 scripts/repack.py \
  --apk AppHarbor.apk \
  --old com.app.market \
  --new com.xiaomi.market \
  --version-code 99999999 \
  --move-classes --rename-assets \
  --out-dir dist
```

## 回退

```sh
adb shell "pm uninstall-system-updates com.xiaomi.market"
```

## 上游与致谢

| | |
|---|---|
| 上游项目 | [BeiChen-CN/AppHarbor](https://github.com/BeiChen-CN/AppHarbor) |
| 上游作者 | [@BeiChen-CN](https://github.com/BeiChen-CN) |
| 上游前身 | [YXBwbWFya2V0/AppMarket](https://github.com/YXBwbWFya2V0/AppMarket)（KMP 跨平台应用商店） |
| 上游许可证 | **未声明**（上游仓库及其 fork 源均无 LICENSE 文件） |
| 本仓库性质 | 非官方，仅做包名替换 + 重签名 |

AppHarbor 的全部功能、界面、业务逻辑均为上游作者的成果。本仓库**不修改任何业务代码**，
只把 `applicationId` 从 `com.app.market` 换成 `com.xiaomi.market`、抬 versionCode，
以便顶替 HyperOS 自带的 MIUISuperMarket。原项目请见上方链接，建议优先支持上游。

⚠️ **授权提示**：上游未提供开源许可证，按默认版权保留（All rights reserved）处理。
本仓库产物仅供个人在自有设备上做系统应用替换实验，**不构成再分发授权**。
如需向他人分发，请先联系上游作者取得许可。

## 许可证

- `scripts/`、`.github/` 下的构建脚本由本仓库维护者编写，可自由使用与修改。
- APK 产物是上游作品的派生：版权与许可归 **BeiChen-CN / YXBwbWFya2V0** 所有，适用其原始条款。

## 免责声明

**下载、安装或使用本仓库任何产物，即表示你已阅读、理解并同意以下全部条款。如不同意，请立即停止使用。**

### 1. 非官方、无关联

本仓库由第三方维护，与 [BeiChen-CN/AppHarbor](https://github.com/BeiChen-CN/AppHarbor)、
[@BeiChen-CN](https://github.com/BeiChen-CN) 及其上游 [YXBwbWFya2V0/AppMarket](https://github.com/YXBwbWFya2V0/AppMarket)
**没有任何隶属、授权、赞助或背书关系**。产物不是上游作者的正式发布版本。
**请勿**就本仓库产物的问题到上游仓库提 issue、向作者索要支持或要求其承担责任。

### 2. 系统级操作风险

本产物用于替换系统应用商店 `com.xiaomi.market`（HyperOS 的 MIUISuperMarket），属于**系统级改动**。
已知或可能的风险包括但不限于：

- 应用商店打不开、闪退，或反复触发签名/校验异常
- 依赖商店的系统功能异常（应用更新、开屏推荐、部分系统组件的分发通道）
- 开机循环（bootloop）、系统服务起不来、无法进入桌面
- 系统 OTA 更新失败、更新后产物被覆盖或与新系统版本冲突
- 应用数据、设备数据丢失
- 需要恢复出厂设置、线刷/9008 救砖，甚至设备变砖

**风险与后果全部由使用者承担。** 请在使用前自行确认：设备可解锁、有可用的 fastboot / 9008 通道、
已完整备份重要数据（含 `/data`），并清楚回退方法（`pm uninstall-system-updates`）。

### 3. 无担保

产物按**「现状」（AS IS）**提供，不作任何明示或暗示的担保，包括但不限于适销性、
特定用途适用性、不侵权、无缺陷、以及不间断或无错误运行。是否可用、是否适配你的机型与系统版本，
需你自行验证。

### 4. 不提供技术支持

本仓库不承诺响应任何 issue、不提供安装指导、不承担因使用产物导致的任何直接或间接损失
（含数据丢失、设备损坏、业务中断、利润损失）。Issue 可以提，但不保证回复或修复。

### 5. 合法合规使用

仅限在**你本人拥有所有权，或已获得设备所有者明确授权**的设备上使用。
使用者应自行遵守所在地法律法规、设备厂商条款与保修约定。
**禁止**将本产物用于绕过付费、规避授权校验、欺诈、侵犯他人权利或其它违法用途。

### 6. 版权与授权（重要）

**上游项目未声明任何开源许可证**（AppHarbor 及其 fork 源 AppMarket 的仓库中均无 LICENSE 文件），
按默认版权保留（All rights reserved）处理：

- APK 的全部代码、界面、资源版权归上游作者所有，本仓库**不主张任何权利**
- 本仓库仅提供包名替换与重签名这一层改动（见 `scripts/repack.py`），不含业务代码
- 本仓库产物**仅供个人在自有设备上使用**，不构成对任何第三方的再分发授权；
  如需公开分发、商用或集成，请先自行联系上游作者取得许可
- 若你认为本仓库的存在侵犯了你的权利，请提交 issue，维护者会及时处理（含删除仓库与相关 Release）

### 7. 条款变更

本免责声明可能随时更新，以本文件当前内容为准，不另行通知。继续使用即视为接受更新后的条款。


